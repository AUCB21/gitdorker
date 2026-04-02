from __future__ import annotations

from gitdorker.api.client import GitHubSearchClient
from gitdorker.models import SearchResult, SearchType


def search_commits(
    client: GitHubSearchClient, query: str, dork_query: str
) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in client.search(query, "commits"):
        repo = item.get("repository", {})
        owner = repo.get("owner", {}).get("login", "unknown")
        repo_name = repo.get("name", "unknown")
        repo_description: str = repo.get("description") or ""
        html_url: str = item.get("html_url", "")
        sha: str = item.get("sha", "")
        message: str = item.get("commit", {}).get("message", "")
        results.append(
            SearchResult(
                owner=owner,
                repo=repo_name,
                repo_description=repo_description,
                file_path=None,
                url=html_url,
                snippet=message[:500],
                dork_query=dork_query,
                search_type=SearchType.COMMITS,
                sha=sha,
            )
        )
    return results
