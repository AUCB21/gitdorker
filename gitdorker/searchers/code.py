from __future__ import annotations

import re
from typing import Any

from gitdorker.api.client import GitHubSearchClient
from gitdorker.models import SearchResult, SearchType

# html_url format: https://github.com/{owner}/{repo}/blob/{commit_sha}/{path}
_COMMIT_SHA_RE = re.compile(r"/blob/([a-f0-9]{40})/")


def _commit_sha_from_html_url(html_url: str) -> str:
    """Extract the commit SHA from a GitHub blob URL (not the file blob SHA)."""
    m = _COMMIT_SHA_RE.search(html_url)
    return m.group(1) if m else ""


def search_code(
    client: GitHubSearchClient, query: str, dork_query: str
) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in client.search(query, "code"):
        repo = item.get("repository", {})
        owner = repo.get("owner", {}).get("login", "unknown")
        repo_name = repo.get("name", "unknown")
        repo_description: str = repo.get("description") or ""
        file_path: str = item.get("path", "")
        html_url: str = item.get("html_url", "")
        sha = _commit_sha_from_html_url(html_url)  # commit SHA, not blob SHA
        snippet = _extract_snippet(item)
        results.append(
            SearchResult(
                owner=owner,
                repo=repo_name,
                repo_description=repo_description,
                file_path=file_path,
                url=html_url,
                snippet=snippet,
                dork_query=dork_query,
                search_type=SearchType.CODE,
                sha=sha,
            )
        )
    return results


def _extract_snippet(item: dict[str, Any]) -> str:
    matches = item.get("text_matches", [])
    if matches:
        fragments = [m.get("fragment", "") for m in matches if m.get("fragment")]
        return "\n---\n".join(fragments[:3])
    return item.get("path", "")
