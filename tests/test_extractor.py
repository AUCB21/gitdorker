from __future__ import annotations

import pytest

from gitdorker.extractor import extract_credentials, _is_placeholder

# ── _is_placeholder ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", [
    "sk-ant-api03-YOUR_API_KEY_HERE",
    "sk-ant-api03-replace_this_with_your_real_key_from_console_anthropic_com_settings_page",
    "sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "AIzaSyYOUR_GEMINI_KEY_HERE_REPLACE_ME",
    "ghp_PLACEHOLDER_TOKEN_HERE_CHANGEME_12345",
    "sk-proj-example_key_add_your_real_openai_key_here_from_platform_openai_com",
    "sk-ant-api03-<YOUR_ANTHROPIC_KEY>",
    "sk-ant-api03-....",
    "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
])
def test_is_placeholder_true(value: str) -> None:
    assert _is_placeholder(value) is True, f"Expected placeholder: {value!r}"


@pytest.mark.parametrize("value", [
    # Realistic-looking random keys (not real, just pattern-valid)
    "sk-ant-api03-xK9mR2vLpQwN8dJfHsYeAcBgTiOuZlXjWnMoVbPk3qCrDa7FtEy6hI4sU1wG5nL0zXvRmQkJpYoTbNdAeHlWcFiZuGs",
    "sk-proj-Xk9mR2vLpQwN8dJfHsYeAcBgTiOuZlXjWnMoVbPk3qCrDa7",
    "AIzaSyXk9mR2vLpQwN8dJfHsYeAcBgTiOuZ1234",
    "ghp_Xk9mR2vLpQwN8dJfHsYeAcBgTiOuZlXjWnMo",  # exactly 36 chars after ghp_
])
def test_is_placeholder_false(value: str) -> None:
    assert _is_placeholder(value) is False, f"Expected real key: {value!r}"


# ── extract_credentials ────────────────────────────────────────────────────────

def test_extract_skips_placeholder_anthropic() -> None:
    content = "ANTHROPIC_API_KEY=sk-ant-api03-YOUR_API_KEY_HERE\n"
    assert extract_credentials(content) == []


def test_extract_skips_padded_placeholder() -> None:
    content = (
        "ANTHROPIC_API_KEY=sk-ant-api03-"
        "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n"
    )
    assert extract_credentials(content) == []


def test_extract_finds_real_anthropic_key() -> None:
    real_key = "sk-ant-api03-xK9mR2vLpQwN8dJfHsYeAcBgTiOuZlXjWnMoVbPk3qCrDa7FtEy6hI4sU1wG5nL0zXvRmQkJpYoTbNdAeHlWcFiZuGs"
    content = f"ANTHROPIC_API_KEY={real_key}\n"
    results = extract_credentials(content)
    assert len(results) == 1
    assert results[0].key_type == "anthropic"
    assert results[0].value == real_key


def test_extract_finds_real_github_token() -> None:
    real_token = "ghp_Xk9mR2vLpQwN8dJfHsYeAcBgTiOuZlXjWnMo"  # exactly 36 chars after ghp_
    content = f"GITHUB_TOKEN={real_token}\n"
    results = extract_credentials(content)
    assert len(results) == 1
    assert results[0].key_type == "github"


def test_extract_deduplicates() -> None:
    real_key = "sk-ant-api03-xK9mR2vLpQwN8dJfHsYeAcBgTiOuZlXjWnMoVbPk3qCrDa7FtEy6hI4sU1wG5nL0zXvRmQkJpYoTbNdAeHlWcFiZuGs"
    content = f"KEY1={real_key}\nKEY2={real_key}\n"
    assert len(extract_credentials(content)) == 1
