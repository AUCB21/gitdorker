from __future__ import annotations

import logging

log = logging.getLogger("gitdorker")


def verify(api_key: str) -> bool:
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        list(client.models.list())
        return True
    except Exception as exc:
        # google.genai raises ClientError for invalid/revoked keys
        msg = str(exc).lower()
        if "invalid" in msg or "api key" in msg or "401" in msg or "403" in msg or "400" in msg:
            return False
        log.debug("gemini verifier unexpected error: %s: %s", type(exc).__name__, exc)
        return False
