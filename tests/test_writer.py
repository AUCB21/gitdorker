from __future__ import annotations

from pathlib import Path

import pytest

from gitdorker.models import SearchResult, SearchType
from gitdorker.output.writer import write_report


@pytest.fixture
def sample_code_result() -> SearchResult:
    return SearchResult(
        owner="alice",
        repo="myapp",
        repo_description="A sample application",
        file_path="config/.env",
        url="https://github.com/alice/myapp/blob/abc/config/.env",
        snippet="DB_PASSWORD=supersecret",
        dork_query="DB_PASSWORD filename:.env",
        search_type=SearchType.CODE,
        sha="abc123",
    )


def test_write_report_creates_file(
    tmp_path: Path, sample_code_result: SearchResult
) -> None:
    report = write_report(
        result=sample_code_result,
        dork_description="Test dork",
        dork_remediation="",
        output_dir=tmp_path,
    )
    assert report.exists()
    content = report.read_text()
    assert "alice/myapp" in content
    assert "A sample application" in content
    assert "DB_PASSWORD=supersecret" in content
    assert "Rotate" in content or "revoke" in content.lower()


def test_write_report_shows_verified_credential(tmp_path: Path) -> None:
    result = SearchResult(
        owner="alice",
        repo="myapp",
        repo_description="",
        file_path="config/.env",
        url="https://github.com/alice/myapp/blob/abc/config/.env",
        snippet="",
        dork_query="sk-ant filename:.env",
        search_type=SearchType.CODE,
        sha="abc123",
        extracted_credential="sk-ant-api03-FAKEKEYVALUE",
    )
    report = write_report(result, "", "", tmp_path)
    content = report.read_text()
    assert "sk-ant-api03-FAKEKEYVALUE" in content
    assert "verified active" in content


def test_write_report_appends_on_second_call(
    tmp_path: Path, sample_code_result: SearchResult
) -> None:
    write_report(sample_code_result, "desc", "", tmp_path)
    write_report(sample_code_result, "desc", "", tmp_path)
    content = (tmp_path / next(tmp_path.iterdir()).name).read_text()
    assert content.count("# Vulnerability Disclosure Report") == 1


def test_write_report_custom_remediation(
    tmp_path: Path, sample_code_result: SearchResult
) -> None:
    report = write_report(
        result=sample_code_result,
        dork_description="",
        dork_remediation="Custom remediation step.",
        output_dir=tmp_path,
    )
    assert "Custom remediation step." in report.read_text()
