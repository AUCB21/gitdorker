from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import requests

from gitdorker.api.rate_limiter import RateLimiter

_BASE = "https://api.github.com"
_SEARCH_TYPES = {"code", "repositories", "commits"}
_GITHUB_MAX = 1000   # GitHub hard cap: max 1000 results per search query
_MAX_RETRIES = 3

log = logging.getLogger("gitdorker")


class GitHubSearchClient:
    def __init__(self, token: str, max_results: int | None = None) -> None:
        self._max_results = max_results if max_results is not None else _GITHUB_MAX
        self._limiter = RateLimiter()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def search_page(
        self, query: str, search_type: str, page: int
    ) -> list[dict[str, Any]]:
        """Fetch a single page of results with retry on 403/429. Returns [] when exhausted."""
        if search_type not in _SEARCH_TYPES:
            raise ValueError(f"search_type must be one of {_SEARCH_TYPES}")

        for attempt in range(1, _MAX_RETRIES + 1):
            self._limiter.acquire()
            resp = self._session.get(
                f"{_BASE}/search/{search_type}",
                params={"q": query, "per_page": 100, "page": page},
                timeout=30,
            )

            if resp.status_code == 422:
                return []

            if resp.status_code in (403, 429):
                # GitHub secondary rate limit - respect Retry-After if present
                retry_after = int(
                    resp.headers.get("Retry-After")
                    or resp.headers.get("x-ratelimit-reset", 60)
                )
                # x-ratelimit-reset is an epoch timestamp; convert to wait seconds
                if "Retry-After" not in resp.headers and retry_after > 1_000_000:
                    retry_after = max(0, retry_after - int(time.time()))
                retry_after = min(retry_after, 120)  # cap at 2 min per retry
                log.warning(
                    "GitHub %d on page %d for %r - waiting %ds (attempt %d/%d)",
                    resp.status_code, page, query, retry_after, attempt, _MAX_RETRIES,
                )
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp.json().get("items", [])

        log.error("Giving up on query %r page %d after %d retries", query, page, _MAX_RETRIES)
        return []

    def search(self, query: str, search_type: str) -> Iterator[dict[str, Any]]:
        """Yield all results up to max_results, paginating automatically."""
        fetched = 0
        page = 1

        while fetched < self._max_results:
            items = self.search_page(query, search_type, page)
            if not items:
                return

            for item in items:
                if fetched >= self._max_results:
                    return
                yield item
                fetched += 1

            if len(items) < 100:
                return

            page += 1

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "GitHubSearchClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
