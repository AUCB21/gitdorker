from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class TokenMissingError(Exception):
    """Raised when no GitHub token is available from any source."""


def resolve_token(token_flag: str | None) -> str:
    token = token_flag or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise TokenMissingError(
            "GITHUB_TOKEN not found in .env, environment, or --token flag."
        )
    return token
