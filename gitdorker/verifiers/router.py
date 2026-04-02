from __future__ import annotations

from gitdorker.extractor import CredentialMatch
from gitdorker.verifiers import (
    anthropic_verifier,
    gemini_verifier,
    github_verifier,
    openai_verifier,
)

_VERIFIERS = {
    "anthropic": anthropic_verifier.verify,
    "openai":    openai_verifier.verify,
    "gemini":    gemini_verifier.verify,
    "github":    github_verifier.verify,
}


def verify(match: CredentialMatch) -> bool:
    """Route a credential to its native verifier. Returns True if valid."""
    verifier = _VERIFIERS.get(match.key_type)
    if verifier is None:
        return False
    return verifier(match.value)
