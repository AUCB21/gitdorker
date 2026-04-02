#!/usr/bin/env python3
"""
export_keys.py — Parse gitdorker report files and export all API keys to JSON.

Usage:
    python export_keys.py                        # reads reports/, writes keys.json
    python export_keys.py --reports path/to/dir
    python export_keys.py --out path/to/out.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── Regex patterns (mirrors gitdorker/extractor.py) ───────────────────────────
_PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic": re.compile(r"sk-ant-[a-zA-Z0-9\-_]{90,}"),
    "openai":    re.compile(r"sk-(?:proj-)?[a-zA-Z0-9]{40,}"),
    "gemini":    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "github":    re.compile(
        r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}"
        r"|github_pat_[A-Za-z0-9_]{82}"
    ),
}

# ── Markdown field patterns ────────────────────────────────────────────────────
_RE_REPO     = re.compile(r"\*\*Repository:\*\*\s*\[([^\]]+)\]\(([^)]+)\)")
_RE_OWNER    = re.compile(r"\*\*Owner:\*\*\s*(.+)")
_RE_DORK     = re.compile(r"\*\*Dork query:\*\*\s*`([^`]+)`")
_RE_CONTEXT  = re.compile(r"\*\*Finding context:\*\*\s*(.+)")
_RE_FILE_URL = re.compile(r"\*\*URL:\*\*\s*(https?://\S+)")
_RE_SHA      = re.compile(r"\*\*SHA:\*\*\s*`([^`]+)`")
_RE_RAW_URL  = re.compile(r"\*\*Raw file:\*\*\s*(https?://\S+)")
# Credential block: ```\n<key>\n```
_RE_CRED     = re.compile(r"```\n([^\n`]+)\n```")


def detect_type(value: str) -> str:
    for key_type, pat in _PATTERNS.items():
        if pat.fullmatch(value):
            return key_type
    # fallback: partial match
    for key_type, pat in _PATTERNS.items():
        if pat.search(value):
            return key_type
    return "unknown"


def parse_report(path: Path) -> list[dict]:
    """Return a list of key records extracted from a single report file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict] = []

    # Header metadata (first occurrence in file)
    repo_match    = _RE_REPO.search(text)
    owner_match   = _RE_OWNER.search(text)
    dork_match    = _RE_DORK.search(text)
    context_match = _RE_CONTEXT.search(text)

    repo_name = repo_match.group(1).strip()  if repo_match  else ""
    repo_url  = repo_match.group(2).strip()  if repo_match  else ""
    owner     = owner_match.group(1).strip() if owner_match else ""
    dork      = dork_match.group(1).strip()  if dork_match  else ""
    context   = context_match.group(1).strip() if context_match else ""

    # Split into per-finding blocks on the "### File:" heading
    blocks = re.split(r"(?=### File:)", text)

    for block in blocks:
        # Extract finding-level fields
        file_url_m = _RE_FILE_URL.search(block)
        sha_m      = _RE_SHA.search(block)
        raw_url_m  = _RE_RAW_URL.search(block)

        file_url = file_url_m.group(1).strip() if file_url_m else ""
        sha      = sha_m.group(1).strip()      if sha_m      else ""
        raw_url  = raw_url_m.group(1).strip()  if raw_url_m  else ""

        # Extract credentials from code blocks that follow "Credential found"
        # Only process the section after that marker
        marker = block.find("**Credential found")
        if marker == -1:
            continue
        cred_section = block[marker:]

        for cred_match in _RE_CRED.finditer(cred_section):
            value = cred_match.group(1).strip()
            if not value:
                continue
            rows.append({
                "key_value":       value,
                "key_type":        detect_type(value),
                "owner":           owner,
                "repo":            repo_name,
                "repo_url":        repo_url,
                "file_url":        file_url,
                "sha":             sha,
                "raw_url":         raw_url,
                "dork_query":      dork,
                "finding_context": context,
                "report_file":     path.name,
            })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Export gitdorker report keys to JSON.")
    parser.add_argument("--reports", default="reports",   help="Reports directory (default: reports/)")
    parser.add_argument("--out",     default="web/keys.json", help="Output JSON file (default: web/keys.json)")
    args = parser.parse_args()

    reports_dir = Path(args.reports)
    if not reports_dir.is_dir():
        print(f"[error] reports directory not found: {reports_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(reports_dir.glob("*.md"))

    print(f"[+] Scanning {len(files)} report(s) -> {args.out}")

    seen: set[str] = set()
    records: list[dict] = []

    for path in files:
        for row in parse_report(path):
            if row["key_value"] in seen:
                continue
            seen.add(row["key_value"])
            records.append(row)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r["key_value"] for r in records], indent=2),
        encoding="utf-8",
    )

    counts: dict[str, int] = {}
    for r in records:
        counts[r["key_type"]] = counts.get(r["key_type"], 0) + 1

    print(f"[+] Done. {len(records)} unique keys written.")
    for key_type, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {key_type:<12} {n}")


if __name__ == "__main__":
    main()
