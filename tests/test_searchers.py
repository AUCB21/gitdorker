from __future__ import annotations

import responses

from gitdorker.api.client import GitHubSearchClient
from gitdorker.searchers.code import search_code
from gitdorker.searchers.repos import search_repositories
from gitdorker.models import SearchType

_TOKEN = "ghp_test_token"
_SEARCH_BASE = "https://api.github.com/search"


@responses.activate
def test_search_code_returns_results() -> None:
    responses.add(
        responses.GET,
        f"{_SEARCH_BASE}/code",
        json={
            "items": [
                {
                    "path": "src/.env",
                    "html_url": "https://github.com/alice/repo/blob/aabbccddeeff00112233445566778899aabbccdd/src/.env",
                    "sha": "blobsha_not_commit_sha",
                    "repository": {
                        "name": "repo",
                        "description": "A test repo",
                        "owner": {"login": "alice"},
                    },
                    "text_matches": [{"fragment": "DB_PASSWORD=secret"}],
                }
            ]
        },
        status=200,
    )
    with GitHubSearchClient(_TOKEN, max_results=10) as client:
        results = search_code(client, "DB_PASSWORD filename:.env", "DB_PASSWORD filename:.env")

    assert len(results) == 1
    r = results[0]
    assert r.owner == "alice"
    assert r.repo == "repo"
    assert r.repo_description == "A test repo"
    assert r.file_path == "src/.env"
    assert r.search_type == SearchType.CODE
    assert "DB_PASSWORD=secret" in r.snippet
    # Must use commit SHA from html_url, NOT the blob SHA from item["sha"]
    assert r.sha == "aabbccddeeff00112233445566778899aabbccdd"
    assert r.raw_url == "https://raw.githubusercontent.com/alice/repo/aabbccddeeff00112233445566778899aabbccdd/src/.env"


@responses.activate
def test_search_repositories_returns_results() -> None:
    responses.add(
        responses.GET,
        f"{_SEARCH_BASE}/repositories",
        json={
            "items": [
                {
                    "name": "secret-repo",
                    "html_url": "https://github.com/bob/secret-repo",
                    "description": "Contains secrets",
                    "owner": {"login": "bob"},
                }
            ]
        },
        status=200,
    )
    with GitHubSearchClient(_TOKEN, max_results=10) as client:
        results = search_repositories(client, "secret", "secret")

    assert len(results) == 1
    assert results[0].owner == "bob"
    assert results[0].repo_description == "Contains secrets"
    assert results[0].search_type == SearchType.REPOSITORIES


@responses.activate
def test_search_code_empty() -> None:
    responses.add(
        responses.GET,
        f"{_SEARCH_BASE}/code",
        json={"items": []},
        status=200,
    )
    with GitHubSearchClient(_TOKEN, max_results=10) as client:
        results = search_code(client, "nonexistent_unique_xyz", "nonexistent_unique_xyz")

    assert results == []


@responses.activate
def test_search_code_422_returns_empty() -> None:
    responses.add(
        responses.GET,
        f"{_SEARCH_BASE}/code",
        json={"message": "Validation Failed"},
        status=422,
    )
    with GitHubSearchClient(_TOKEN, max_results=10) as client:
        results = search_code(client, "bad query!!!", "bad query!!!")

    assert results == []
