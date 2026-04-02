from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SearchType(StrEnum):
    CODE = "code"
    REPOSITORIES = "repositories"
    COMMITS = "commits"


@dataclass(frozen=True, slots=True)
class SearchResult:
    owner: str
    repo: str
    repo_description: str
    file_path: str | None
    url: str
    snippet: str
    dork_query: str
    search_type: SearchType
    sha: str | None = None
    extracted_credential: str | None = None

    @property
    def repo_full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def raw_url(self) -> str | None:
        if self.search_type == SearchType.CODE and self.sha and self.file_path:
            return (
                f"https://raw.githubusercontent.com/{self.owner}/{self.repo}"
                f"/{self.sha}/{self.file_path}"
            )
        return None


@dataclass(slots=True)
class DisclosureReport:
    owner: str
    results: list[SearchResult] = field(default_factory=list)

    def add(self, result: SearchResult) -> None:
        self.results.append(result)

    @property
    def repos(self) -> set[str]:
        return {r.repo_full_name for r in self.results}
