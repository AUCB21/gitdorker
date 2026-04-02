from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def resolve_token(token_flag: str | None) -> str:
    token = token_flag or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        sys.exit(
            "[auth] GITHUB_TOKEN not found in .env, environment, or --token flag. Aborting."
        )
    return token
