from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import signal
from pathlib import Path

import click

from gitdorker.api.client import GitHubSearchClient
from gitdorker.auth import resolve_token
from gitdorker.config import Dork, DorksConfig
from gitdorker.extractor import CredentialMatch, extract_credentials, fetch_raw
from gitdorker.logger import log, setup as setup_logger
from gitdorker.models import SearchResult
from gitdorker.output.console import print_error, print_info, print_result, print_summary
from gitdorker.output.writer import write_report
from gitdorker.searchers.code import search_code
from gitdorker.searchers.commits import search_commits
from gitdorker.searchers.repos import search_repositories
from gitdorker.verifiers import router

_SEARCHERS = {
    "code": search_code,
    "repositories": search_repositories,
    "commits": search_commits,
}

# Signals the main loop to stop after the current cycle finishes
_stop_requested = False


def _request_stop(_signum: int, _frame: object) -> None:
    global _stop_requested
    _stop_requested = True
    print_info("Stop requested — finishing current cycle then exiting…")
    log.info("SIGINT received — will stop after current cycle")


async def _verify_result(
    result: SearchResult,
    dork: Dork,
    output_dir: Path,
    seen_keys: set[str],
) -> list[tuple[SearchResult, Path]]:
    """Return one entry per valid credential found in the file (may be >1)."""
    raw_url = result.raw_url
    if not raw_url:
        log.info("Non-code result — writing without verification: %s", result.url)
        report_path = await asyncio.to_thread(
            write_report, result, dork.description, dork.remediation, output_dir
        )
        return [(result, report_path)]

    log.debug("Fetching raw content: %s", raw_url)
    raw_content = await asyncio.to_thread(fetch_raw, raw_url)
    if not raw_content:
        log.debug("Empty or unreachable raw URL: %s", raw_url)
        return []

    matches: list[CredentialMatch] = extract_credentials(raw_content)
    if not matches:
        log.debug("No credential patterns found in %s", raw_url)
        return []

    log.debug("Found %d credential candidate(s) in %s", len(matches), raw_url)

    found: list[tuple[SearchResult, Path]] = []

    for match in matches:
        key_hash = hashlib.sha256(match.value.encode()).hexdigest()
        if key_hash in seen_keys:
            log.debug("Skipping already-tested key from %s", result.repo_full_name)
            continue

        seen_keys.add(key_hash)
        log.info("Verifying [%s] credential from %s", match.key_type, result.repo_full_name)
        is_valid = await asyncio.to_thread(router.verify, match)

        if is_valid:
            log.info("VALID credential [%s] in %s — writing report", match.key_type, result.repo_full_name)
            verified = dataclasses.replace(result, extracted_credential=match.value)
            report_path = await asyncio.to_thread(
                write_report, verified, dork.description, dork.remediation, output_dir
            )
            found.append((verified, report_path))
        else:
            log.debug("Invalid/expired [%s] credential in %s", match.key_type, result.repo_full_name)

    return found


async def _process_page(
    page_results: list[SearchResult],
    dork: Dork,
    output_dir: Path,
    reports_written: set[str],
    seen_keys: set[str],
) -> None:
    tasks = [_verify_result(r, dork, output_dir, seen_keys) for r in page_results]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    for outcome in outcomes:
        if isinstance(outcome, Exception):
            print_error(str(outcome))
            log.error("Verification error: %s", outcome)
        else:
            for verified_result, report_path in outcome:
                print_result(verified_result, report_path)
                log.info("Report written: %s", report_path)
                reports_written.add(str(report_path))


async def _run_cycle(
    token: str,
    config: DorksConfig,
    output_dir: Path,
    max_results: int | None,
    cycle: int,
    seen_keys: set[str],
    total_reports: set[str],
) -> int:
    """Run one full pass over all dorks. Returns number of candidates found."""
    candidates = 0

    with GitHubSearchClient(token, max_results=max_results) as client:
        for dork in config.dorks:
            print_info(f"[cycle {cycle}] Searching [{dork.type}] {dork.query!r}")
            log.info("Cycle %d — dork type=%s query=%r", cycle, dork.type, dork.query)
            searcher = _SEARCHERS[dork.type]

            page_buffer: list[SearchResult] = []
            page_num = 1

            try:
                for result in searcher(client, dork.query, dork_query=dork.query):
                    page_buffer.append(result)
                    candidates += 1

                    if len(page_buffer) == 100:
                        print_info(f"  Page {page_num}: verifying {len(page_buffer)} results…")
                        log.info("Cycle %d page %d (%d results) for %r", cycle, page_num, len(page_buffer), dork.query)
                        await _process_page(page_buffer, dork, output_dir, total_reports, seen_keys)
                        page_buffer = []
                        page_num += 1

            except Exception as exc:
                print_error(f"Query failed: {dork.query!r} — {exc}")
                log.error("Cycle %d query failed: %r — %s", cycle, dork.query, exc)

            if page_buffer:
                print_info(f"  Page {page_num}: verifying {len(page_buffer)} results…")
                await _process_page(page_buffer, dork, output_dir, total_reports, seen_keys)

    return candidates


@click.command(context_settings={"max_content_width": 100})
@click.option("--dorks-file", "-f", type=click.Path(exists=True, path_type=Path), default=None,
              help="Path to JSON file containing dork definitions.")
@click.option("--query", "-q", default=None,
              help="Single dork query string (alternative to --dorks-file).")
@click.option("--type", "-t", "search_type", type=click.Choice(["code", "repositories", "commits"]),
              default="code", show_default=True, help="GitHub Search API type (used with --query).")
@click.option("--token", envvar="GITHUB_TOKEN", default=None,
              help="GitHub personal access token. Defaults to GITHUB_TOKEN env var.")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=Path("reports"),
              show_default=True, help="Directory where disclosure reports will be written.")
@click.option("--max-results", "-n", default=None, type=int,
              help="Max results per dork query. Defaults to all available (GitHub cap: 1000).")
@click.option("--loop", "-l", is_flag=True, default=False,
              help="Keep running: restart all dorks after each cycle until Ctrl+C.")
@click.option("--loop-delay", default=300, show_default=True,
              help="Seconds to wait between loop cycles (default: 300 = 5 min).")
@click.option("--verbose", "-v", is_flag=True, default=False,
              help="Enable DEBUG-level logging to the log file.")
def main(
    dorks_file: Path | None,
    query: str | None,
    search_type: str,
    token: str | None,
    output_dir: Path,
    max_results: int | None,
    loop: bool,
    loop_delay: int,
    verbose: bool,
) -> None:
    """GitHub Dorker — search GitHub for exposed LLM API keys and secrets.

    Use --loop to run continuously until Ctrl+C. Already-tested keys are cached
    across cycles so the same revoked key is never verified twice.
    """
    if not dorks_file and not query:
        raise click.UsageError("Provide --dorks-file or --query.")

    setup_logger(verbose=verbose)
    log.info(
        "gitdorker started — loop=%s delay=%ds max_results=%s",
        loop, loop_delay, max_results or "all",
    )

    signal.signal(signal.SIGINT, _request_stop)

    resolved_token = resolve_token(token)
    config = (
        DorksConfig.from_file(dorks_file)
        if dorks_file
        else DorksConfig.from_query(query, search_type)  # type: ignore[arg-type]
    )

    log.info("Loaded %d dork(s)", len(config.dorks))
    asyncio.run(_loop(resolved_token, config, output_dir, max_results, loop, loop_delay))


async def _loop(
    token: str,
    config: DorksConfig,
    output_dir: Path,
    max_results: int | None,
    loop: bool,
    loop_delay: int,
) -> None:
    global _stop_requested

    seen_keys: set[str] = set()   # SHA-256 hashes of already-tested credential values
    total_reports: set[str] = set()
    total_candidates = 0
    cycle = 1

    while True:
        log.info("Starting cycle %d", cycle)
        candidates = await _run_cycle(
            token, config, output_dir, max_results,
            cycle, seen_keys, total_reports,
        )
        total_candidates += candidates

        print_summary(total_candidates, len(total_reports), output_dir, cycle=cycle)
        log.info(
            "Cycle %d done — candidates=%d seen_keys=%d total_reports=%d",
            cycle, candidates, len(seen_keys), len(total_reports),
        )

        if not loop or _stop_requested:
            break

        print_info(f"Waiting {loop_delay}s before next cycle… (Ctrl+C to stop)")
        log.info("Sleeping %ds before cycle %d", loop_delay, cycle + 1)

        # Sleep in 1-second ticks so Ctrl+C is responsive
        for _ in range(loop_delay):
            if _stop_requested:
                break
            await asyncio.sleep(1)

        if _stop_requested:
            break

        cycle += 1

    log.info("Stopped after %d cycle(s) — total candidates=%d reports=%d", cycle, total_candidates, len(total_reports))
