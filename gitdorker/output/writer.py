from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from gitdorker.models import DisclosureReport, SearchResult, SearchType

_SAFE_RE = re.compile(r"[^\w\-]")


def _slugify(text: str) -> str:
    return _SAFE_RE.sub("_", text)[:60].strip("_")


def _remediation_hint(result: SearchResult, custom_remediation: str) -> str:
    if custom_remediation:
        return custom_remediation
    match result.search_type:
        case SearchType.CODE:
            return (
                "Rotate or revoke any exposed credentials immediately. "
                "Add the file to `.gitignore`, purge it from git history using "
                "`git filter-repo`, and audit downstream systems for unauthorized access."
            )
        case SearchType.REPOSITORIES:
            return (
                "Review repository visibility settings and remove any sensitive "
                "data from the repository description or topics."
            )
        case SearchType.COMMITS:
            return (
                "Rotate exposed secrets immediately. Rewrite git history with "
                "`git filter-repo` to permanently remove the commit containing "
                "sensitive data, then force-push all branches."
            )


def write_report(
    result: SearchResult,
    dork_description: str,
    dork_remediation: str,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    owner_slug = _slugify(result.owner)
    repo_slug = _slugify(result.repo)
    query_slug = _slugify(result.dork_query)
    filename = f"{owner_slug}__{repo_slug}__{query_slug}.md"
    report_path = output_dir / filename

    mode = "a" if report_path.exists() else "w"

    with report_path.open(mode, encoding="utf-8") as fh:
        if mode == "w":
            fh.write(_render_header(result, dork_description))
        fh.write(_render_finding(result, dork_remediation))

    return report_path


def _render_header(result: SearchResult, description: str) -> str:
    repo_desc = result.repo_description or "No description provided."
    return f"""# Vulnerability Disclosure Report

**Repository:** [{result.repo_full_name}](https://github.com/{result.repo_full_name})
**Owner:** {result.owner}
**Description:** {repo_desc}
**Search type:** {result.search_type.value}
**Dork query:** `{result.dork_query}`
**Finding context:** {description or "Potential sensitive data exposure detected via GitHub search."}

> This report was generated automatically by gitdorker.
> All credentials listed below were verified as **active** at time of discovery.
> Please treat this as an urgent security issue.

---

## Findings

"""


def _render_finding(result: SearchResult, custom_remediation: str) -> str:
    lines: list[str] = []

    if result.file_path:
        lines.append(f"### File: `{result.file_path}`")

    lines.append(f"**URL:** {result.url}")

    if result.sha:
        lines.append(f"**SHA:** `{result.sha}`")

    if result.raw_url:
        lines.append(f"**Raw file:** {result.raw_url}")

    if result.extracted_credential:
        lines.append("\n**Credential found (verified active):**")
        lines.append("```")
        lines.append(result.extracted_credential)
        lines.append("```")
    elif result.snippet:
        lines.append("\n**Matched content:**")
        lines.append("```")
        lines.append(result.snippet)
        lines.append("```")

    lines.append("\n**Recommended remediation:**")
    lines.append(_remediation_hint(result, custom_remediation))
    lines.append("\n---\n")

    return "\n".join(lines)


def group_by_owner(results: list[SearchResult]) -> dict[str, DisclosureReport]:
    reports: dict[str, DisclosureReport] = defaultdict(
        lambda: DisclosureReport(owner="")
    )
    for r in results:
        if r.owner not in reports:
            reports[r.owner] = DisclosureReport(owner=r.owner)
        reports[r.owner].add(r)
    return dict(reports)
