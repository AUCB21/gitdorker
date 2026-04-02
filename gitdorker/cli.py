from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import os
import signal
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

import json
import re

from gitdorker.api.client import GitHubSearchClient
from gitdorker.auth import TokenMissingError, resolve_token
from gitdorker.config import Dork, DorksConfig
from gitdorker.extractor import CredentialMatch, extract_credentials, fetch_raw
from gitdorker.logger import log, setup as setup_logger
from gitdorker.models import SearchResult
from gitdorker.output.console import (
    live_progress,
    print_banner,
    print_error,
    print_info,
    print_result,
    print_summary,
)
from gitdorker.output.writer import write_report
from gitdorker.searchers.code import search_code
from gitdorker.searchers.commits import search_commits
from gitdorker.searchers.repos import search_repositories
from gitdorker.verifiers import router

# ── Key export (mirrors export_keys.py) ──────────────────────────────────────

_CRED_PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic":  re.compile(r"sk-ant-(?:api03|admin01)-[\w\-]{88,100}"),
    "openai":     re.compile(r"sk-(?:proj|svcacct|service)-[A-Za-z0-9_\-]+|sk-[a-zA-Z0-9]{20}T3BlbkFJ[A-Za-z0-9_\-]+"),
    "gemini":     re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "huggingface": re.compile(r"(?:hf_|api_org_)[a-zA-Z0-9]{34}"),
    "groq":       re.compile(r"gsk_[a-zA-Z0-9]{52}"),
    "replicate":  re.compile(r"r8_[0-9A-Za-z\-_]{37}"),
    "perplexity": re.compile(r"pplx-[a-zA-Z0-9]{48}"),
    "xai":        re.compile(r"xai-[0-9a-zA-Z_]{80}"),
    "openrouter": re.compile(r"sk-or-v1-[a-zA-Z0-9]{64}"),
    "nvidia":     re.compile(r"nvapi-[a-zA-Z0-9_\-]{55}"),
    "cerebras":   re.compile(r"csk-[a-zA-Z0-9]{32}"),
}

_RE_CRED = re.compile(r"```\n([^\n`]+)\n```")


def _gitignore_add(entry: Path) -> None:
    """Append entry to .gitignore (repo root) if not already present."""
    gitignore = Path(".gitignore")
    line = entry.as_posix().rstrip("/") + "/"
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8")
        if line in existing.splitlines():
            return
        gitignore.write_text(existing.rstrip() + f"\n{line}\n", encoding="utf-8")
    else:
        gitignore.write_text(f"{line}\n", encoding="utf-8")
    print_info(f"Added {line!r} to .gitignore")
    log.info("Added %r to .gitignore", line)


def _export_found_keys(reports_dir: Path) -> None:
    """Parse all reports and write unique keys to found_keys/found.json."""
    files = sorted(reports_dir.glob("*.md"))
    if not files:
        return

    seen: set[str] = set()
    keys: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        marker = text.find("**Credential found")
        if marker == -1:
            continue
        for m in _RE_CRED.finditer(text[marker:]):
            value = m.group(1).strip()
            if value and value not in seen:
                seen.add(value)
                keys.append(value)

    out_dir = Path("found_keys")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "found.json"
    out_path.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    print_info(f"Exported {len(keys)} key(s) → {out_path}")
    log.info("Exported %d keys to %s", len(keys), out_path)


_SEARCHERS = {
    "code": search_code,
    "repositories": search_repositories,
    "commits": search_commits,
}

_stop_requested = False
_console = Console()


def _request_stop(_signum: int, _frame: object) -> None:
    global _stop_requested
    _stop_requested = True
    print_info("Stop requested — finishing current cycle then exiting…")
    log.info("SIGINT received — will stop after current cycle")


# ── Interactive wizard ────────────────────────────────────────────────────────

def _prompt_token() -> str:
    """Prompt for a GitHub token, showing a hint if one is found in the environment."""
    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        _console.print(f"[dim]  GitHub token found in environment ({env_token[:8]}…)[/dim]")
        use_env = Confirm.ask("  Use this token?", default=True)
        if use_env:
            return env_token

    _console.print("[dim]  Enter your GitHub personal access token (needs repo:read scope)[/dim]")
    while True:
        try:
            token = Prompt.ask("  Token", password=True).strip()
        except (EOFError, OSError):
            # Non-interactive stdin fallback
            token = input("  Token: ").strip()

        if token:
            return token
        _console.print("[red]  Token cannot be empty.[/red]")


def _wizard() -> tuple[str, DorksConfig, Path, int | None, bool, int]:
    """
    Guided wizard. Returns:
        (token, config, output_dir, max_results, loop, loop_delay)
    """
    print_banner()
    _console.print(Panel(
        "[bold]Interactive setup[/bold]\n[dim]Answer each prompt — press Enter to accept the default.[/dim]",
        border_style="yellow",
        padding=(0, 2),
    ))
    _console.print()

    # ── Step 1: Token ──────────────────────────────────────────────────────────
    _console.rule("[dim]Step 1 — GitHub Token[/dim]")
    token = _prompt_token()

    # ── Step 2: Search mode ────────────────────────────────────────────────────
    _console.rule("[dim]Step 2 — Search Source[/dim]")
    _console.print("  [1] Load dorks from a JSON file")
    _console.print("  [2] Enter a single search query")
    mode = Prompt.ask("  Mode", choices=["1", "2"], default="1")

    if mode == "1":
        # ── Step 3a: Dorks file ────────────────────────────────────────────────
        _console.rule("[dim]Step 3 — Dorks File[/dim]")
        while True:
            raw = Prompt.ask("  Path to dorks JSON", default="dorks.json")
            p = Path(raw)
            if p.exists():
                config = DorksConfig.from_file(p)
                _console.print(f"  [green]✓[/green] Loaded [bold]{len(config.dorks)}[/bold] dork(s) from {p}")
                break
            _console.print(f"  [red]File not found:[/red] {p}")
    else:
        # ── Step 3b: Single query ──────────────────────────────────────────────
        _console.rule("[dim]Step 3 — Search Query[/dim]")
        query = Prompt.ask("  Query string").strip()
        search_type = Prompt.ask(
            "  Search type",
            choices=["code", "repositories", "commits"],
            default="code",
        )
        config = DorksConfig.from_query(query, search_type)  # type: ignore[arg-type]

    # ── Step 4: Output dir ─────────────────────────────────────────────────────
    _console.rule("[dim]Step 4 — Output[/dim]")
    out_raw = Prompt.ask("  Output directory", default="reports")
    output_dir = Path(out_raw)

    # ── Step 5: Max results ────────────────────────────────────────────────────
    _console.rule("[dim]Step 5 — Limits[/dim]")
    max_raw = Prompt.ask(
        "  Max results per dork (blank = all, GitHub cap 1000)",
        default="",
    ).strip()
    max_results: int | None = int(max_raw) if max_raw.isdigit() else None

    # ── Step 6: Loop ───────────────────────────────────────────────────────────
    _console.rule("[dim]Step 6 — Loop Mode[/dim]")
    loop = Confirm.ask("  Run in continuous loop until Ctrl+C?", default=False)
    loop_delay = 300
    if loop:
        delay_raw = Prompt.ask("  Delay between cycles (seconds)", default="300").strip()
        loop_delay = int(delay_raw) if delay_raw.isdigit() else 300

    # ── Confirmation panel ─────────────────────────────────────────────────────
    _console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", no_wrap=True)
    table.add_column()
    table.add_row("Token", f"{token[:8]}…")
    table.add_row("Dorks", str(len(config.dorks)))
    table.add_row("Output dir", str(output_dir))
    table.add_row("Max results", str(max_results) if max_results else "all")
    table.add_row("Loop", f"yes (every {loop_delay}s)" if loop else "no")
    _console.print(Panel(table, title="[bold]Ready to run[/bold]", border_style="green"))
    _console.print()

    if not Confirm.ask("  Start scan?", default=True):
        _console.print("[dim]Aborted.[/dim]")
        sys.exit(0)

    return token, config, output_dir, max_results, loop, loop_delay


# ── Core execution ────────────────────────────────────────────────────────────

async def _verify_result(
    result: SearchResult,
    dork: Dork,
    output_dir: Path,
    seen_keys: set[str],
) -> list[tuple[SearchResult, Path]]:
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
    candidates = 0

    with live_progress() as progress:
        with GitHubSearchClient(token, max_results=max_results) as client:
            for dork in config.dorks:
                short_desc = (dork.description or dork.query)[:60]
                task_id = progress.add_task(
                    f"[cycle {cycle}] {short_desc}",
                    status="searching…",
                    total=None,
                )
                log.info("Cycle %d — dork type=%s query=%r", cycle, dork.type, dork.query)
                searcher = _SEARCHERS[dork.type]

                page_buffer: list[SearchResult] = []
                page_num = 1

                try:
                    for result in searcher(client, dork.query, dork_query=dork.query):
                        page_buffer.append(result)
                        candidates += 1
                        progress.update(task_id, status=f"{candidates} candidates…")

                        if len(page_buffer) == 100:
                            progress.update(task_id, status=f"verifying page {page_num}…")
                            log.info("Cycle %d page %d (%d results) for %r", cycle, page_num, len(page_buffer), dork.query)
                            await _process_page(page_buffer, dork, output_dir, total_reports, seen_keys)
                            page_buffer = []
                            page_num += 1
                            progress.update(task_id, status=f"{candidates} candidates, {len(total_reports)} valid…")

                except Exception as exc:
                    print_error(f"Query failed: {dork.query!r} — {exc}")
                    log.error("Cycle %d query failed: %r — %s", cycle, dork.query, exc)

                if page_buffer:
                    progress.update(task_id, status=f"verifying final page…")
                    await _process_page(page_buffer, dork, output_dir, total_reports, seen_keys)

                progress.update(task_id, status=f"done — {len(total_reports)} valid so far")

    return candidates


# ── Click entry point ─────────────────────────────────────────────────────────

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

    Run with no arguments to launch the interactive wizard.
    Use --loop to run continuously until Ctrl+C.
    """
    setup_logger(verbose=verbose)

    # ── Interactive mode ───────────────────────────────────────────────────────
    if not dorks_file and not query:
        token, config, output_dir, max_results, loop, loop_delay = _wizard()
        log.info(
            "gitdorker started (interactive) — loop=%s delay=%ds max_results=%s",
            loop, loop_delay, max_results or "all",
        )
        signal.signal(signal.SIGINT, _request_stop)
        _gitignore_add(output_dir)
        asyncio.run(_loop(token, config, output_dir, max_results, loop, loop_delay))
        return

    # ── Headless / scripted mode ───────────────────────────────────────────────
    log.info(
        "gitdorker started — loop=%s delay=%ds max_results=%s",
        loop, loop_delay, max_results or "all",
    )
    signal.signal(signal.SIGINT, _request_stop)

    try:
        resolved_token = resolve_token(token)
    except TokenMissingError as exc:
        raise click.UsageError(str(exc)) from exc

    config = (
        DorksConfig.from_file(dorks_file)
        if dorks_file
        else DorksConfig.from_query(query, search_type)  # type: ignore[arg-type]
    )

    log.info("Loaded %d dork(s)", len(config.dorks))
    _gitignore_add(output_dir)
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

    seen_keys: set[str] = set()
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
        await asyncio.to_thread(_export_found_keys, output_dir)
        log.info(
            "Cycle %d done — candidates=%d seen_keys=%d total_reports=%d",
            cycle, candidates, len(seen_keys), len(total_reports),
        )

        if not loop or _stop_requested:
            break

        print_info(f"Waiting {loop_delay}s before next cycle… (Ctrl+C to stop)")
        log.info("Sleeping %ds before cycle %d", loop_delay, cycle + 1)

        for _ in range(loop_delay):
            if _stop_requested:
                break
            await asyncio.sleep(1)

        if _stop_requested:
            break

        cycle += 1

    log.info("Stopped after %d cycle(s) — total candidates=%d reports=%d", cycle, total_candidates, len(total_reports))
