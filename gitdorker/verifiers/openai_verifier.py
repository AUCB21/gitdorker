from __future__ import annotations

import logging

log = logging.getLogger("gitdorker")


def verify(api_key: str) -> bool:
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        return True
    except openai.AuthenticationError:
        return False
    except Exception as exc:
        log.debug("openai verifier unexpected error: %s: %s", type(exc).__name__, exc)
        return False
