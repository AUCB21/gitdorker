from __future__ import annotations

from gitdorker.api.client import GitHubSearchClient
from gitdorker.models import SearchResult, SearchType


def search_repositories(
    client: GitHubSearchClient, query: str, dork_query: str
) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in client.search(query, "repositories"):
        owner = item.get("owner", {}).get("login", "unknown")
        repo_name = item.get("name", "unknown")
        html_url: str = item.get("html_url", "")
        description: str = item.get("description") or ""
        results.append(
            SearchResult(
                owner=owner,
                repo=repo_name,
                repo_description=description,
                file_path=None,
                url=html_url,
                snippet=description[:500],
                dork_query=dork_query,
                search_type=SearchType.REPOSITORIES,
            )
        )
    return results
