from __future__ import annotations

from unittest.mock import MagicMock, patch

from gitdorker.verifiers import anthropic_verifier, gemini_verifier, openai_verifier


# ── Anthropic ─────────────────────────────────────────────────────────────────

def test_anthropic_valid_key_returns_true() -> None:
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock()
    with patch("anthropic.Anthropic", return_value=mock_client):
        assert anthropic_verifier.verify("sk-ant-api03-validkey") is True
    mock_client.models.list.assert_called_once()


def test_anthropic_invalid_key_returns_false() -> None:
    import anthropic
    mock_client = MagicMock()
    mock_client.models.list.side_effect = anthropic.AuthenticationError(
        message="invalid key", response=MagicMock(status_code=401), body={}
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        assert anthropic_verifier.verify("sk-ant-api03-badkey") is False


def test_anthropic_network_error_returns_false() -> None:
    mock_client = MagicMock()
    mock_client.models.list.side_effect = ConnectionError("timeout")
    with patch("anthropic.Anthropic", return_value=mock_client):
        assert anthropic_verifier.verify("sk-ant-api03-somekey") is False


# ── OpenAI ────────────────────────────────────────────────────────────────────

def test_openai_valid_key_returns_true() -> None:
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock()
    with patch("openai.OpenAI", return_value=mock_client):
        assert openai_verifier.verify("sk-proj-validkey") is True
    mock_client.models.list.assert_called_once()


def test_openai_invalid_key_returns_false() -> None:
    import openai
    mock_client = MagicMock()
    mock_client.models.list.side_effect = openai.AuthenticationError(
        message="bad key", response=MagicMock(status_code=401), body={}
    )
    with patch("openai.OpenAI", return_value=mock_client):
        assert openai_verifier.verify("sk-proj-badkey") is False


# ── Gemini ────────────────────────────────────────────────────────────────────

def test_gemini_valid_key_returns_true() -> None:
    mock_client = MagicMock()
    mock_client.models.list.return_value = iter([MagicMock()])
    with patch("google.genai.Client", return_value=mock_client):
        assert gemini_verifier.verify("AIzaSyValidKey123456789012345678901234") is True


def test_gemini_invalid_key_returns_false() -> None:
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("API key not valid. Please pass a valid API key.")
    with patch("google.genai.Client", return_value=mock_client):
        assert gemini_verifier.verify("AIzaSyBadKey1234567890123456789012345") is False
