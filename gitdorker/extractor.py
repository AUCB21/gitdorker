from __future__ import annotations

import math
import re
from dataclasses import dataclass

import requests

# ── Credential patterns ────────────────────────────────────────────────────────
# Lengths and formats validated against TruffleHog detectors and live key samples.
_PATTERNS: dict[str, re.Pattern[str]] = {
    # Anthropic: sk-ant-api03- or sk-ant-admin01- + 88-100 word chars (no fixed suffix)
    "anthropic":  re.compile(r"sk-ant-(?:api03|admin01)-[\w\-]{88,100}"),
    # OpenAI legacy keys embed base64("openai") = T3BlbkFJ; project/svcacct keys
    "openai":     re.compile(
        r"sk-(?:proj|svcacct|service)-[A-Za-z0-9_\-]+"
        r"|sk-[a-zA-Z0-9]{20}T3BlbkFJ[A-Za-z0-9_\-]+"
    ),
    # Google / Gemini: AIza + exactly 35 chars
    "gemini":     re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    # HuggingFace: hf_ or api_org_ + exactly 34 alphanum
    "huggingface": re.compile(r"(?:hf_|api_org_)[a-zA-Z0-9]{34}"),
    # Groq: gsk_ + exactly 52 alphanum
    "groq":       re.compile(r"gsk_[a-zA-Z0-9]{52}"),
    # Replicate: r8_ + exactly 37 alphanum/hyphen/underscore
    "replicate":  re.compile(r"r8_[0-9A-Za-z\-_]{37}"),
    # Perplexity: pplx- + 48 mixed alphanum (confirmed from live keys)
    "perplexity": re.compile(r"pplx-[a-zA-Z0-9]{48}"),
    # xAI Grok: xai- + exactly 80 alphanum/underscore
    "xai":        re.compile(r"xai-[0-9a-zA-Z_]{80}"),
    # DeepSeek: sk- + exactly 32 lowercase alphanum (requires context word nearby)
    "deepseek":   re.compile(r"(?i)(?:deepseek[^\"'\n]{0,40})sk-[a-z0-9]{32}"),
    # OpenRouter: sk-or-v1- + 64 alphanum
    "openrouter": re.compile(r"sk-or-v1-[a-zA-Z0-9]{64}"),
    # Fireworks: fw_sk_ or fw_ (observed prefixes) + 32-64 alphanum
    "fireworks":  re.compile(r"fw_[a-zA-Z0-9]{32,64}"),
    # Cohere: 40-char alphanum (no fixed prefix; require context word)
    "cohere":     re.compile(r"(?i)(?:cohere[^\"'\n]{0,40})[a-zA-Z0-9]{40}"),
    # Mistral: bearer token format observed: 32-char alphanum after context
    "mistral":    re.compile(r"(?i)(?:mistral[^\"'\n]{0,40})[a-zA-Z0-9]{32}"),
    # Together AI: 64-char hex string with context
    "together":   re.compile(r"(?i)(?:together[^\"'\n]{0,40})[a-f0-9]{64}"),
    # NVIDIA NIM: nvapi- + 55-char alphanum/hyphen
    "nvidia":     re.compile(r"nvapi-[a-zA-Z0-9_\-]{55}"),
    # Cerebras: csk- + 32 alphanum
    "cerebras":   re.compile(r"csk-[a-zA-Z0-9]{32}"),
    # GitHub PAT (classic + fine-grained) - kept as useful signal
    "github":     re.compile(
        r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}"
        r"|github_pat_[A-Za-z0-9_]{82}"
    ),
}

# ── Context-line placeholder indicators ───────────────────────────────────────
# If the LINE containing the key has any of these, treat as template/example.
_CONTEXT_PLACEHOLDERS = re.compile(
    r"(?i)"
    r"os\.environ"
    r"|os\.getenv"
    r"|process\.env"
    r"|dotenv"
    r"|your[_\-]?(?:api[_\-]?)?key"
    r"|<your"
    r"|insert.{0,20}key"
    r"|replace.{0,20}key"
    r"|add.{0,20}key"
    r"|put.{0,20}key"
    r"|env\[.{0,30}\]"        # process.env["KEY"]  / os.environ["KEY"]
    r"|#.*key"                 # commented-out key line
    r"|\/\/.*key"              # JS comment with key
)

# ── Value-level placeholder detection ─────────────────────────────────────────
_PLACEHOLDER_WORDS = re.compile(
    r"(?i)"
    r"your[_\-]?"
    r"|here"
    r"|placeholder"
    r"|example"
    r"|replace"
    r"|changeme"
    r"|insert"
    r"|sample"
    r"|dummy"
    r"|fake"
    r"|test"
    r"|x{4,}"           # XXXX or more
    r"|<[^>]+>"         # <API_KEY> style
    r"|\.\.\."          # ellipsis
    r"|todo"
    r"|fixme"
    r"|add[_\-]?key"
    r"|api[_\-]?key[_\-]?here"
    r"|invalid"
    r"|redacted"
    r"|hidden"
    r"|secret_here"
    r"|key_here"
)

_MIN_UNIQUE_CHAR_RATIO = 0.10  # payload must have >10% unique chars
_MIN_ENTROPY_BITS = 3.0        # Shannon entropy threshold for payload


def _shannon_entropy(s: str) -> float:
    """Shannon entropy in bits per character."""
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((n / length) * math.log2(n / length) for n in freq.values())


def _extract_payload(value: str) -> str:
    """Return the high-entropy suffix of a key (after the last known separator)."""
    # Walk from right: skip fixed-format suffixes like 'AA' on Anthropic keys
    # Use the last '-' or '_' as the boundary between prefix and payload.
    for sep in ("-", "_"):
        idx = value.rfind(sep)
        if idx != -1 and idx < len(value) - 4:
            return value[idx + 1:]
    return value


def _is_placeholder(value: str, context_line: str = "") -> bool:
    """Return True if the value looks like a template/placeholder, not a real key."""
    # 1. Context line has template indicators (env var reference, comment, etc.)
    if context_line and _CONTEXT_PLACEHOLDERS.search(context_line):
        return True

    # 2. Value itself contains placeholder words
    if _PLACEHOLDER_WORDS.search(value):
        return True

    payload = _extract_payload(value)
    if not payload or len(payload) < 8:
        return True

    # 3. Low character diversity
    if len(set(payload)) / len(payload) < _MIN_UNIQUE_CHAR_RATIO:
        return True

    # 4. Low Shannon entropy - catches repetition patterns like "abcabcabc"
    if _shannon_entropy(payload) < _MIN_ENTROPY_BITS:
        return True

    return False


@dataclass(frozen=True, slots=True)
class CredentialMatch:
    key_type: str   # provider name
    value: str      # raw key value


def fetch_raw(url: str, timeout: int = 15) -> str | None:
    """Fetch raw file content from GitHub. Returns None on any error."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def extract_credentials(content: str) -> list[CredentialMatch]:
    """Return all non-placeholder credential matches found in raw file content."""
    # Build a line-index map: character offset → line text, for context checks.
    lines = content.splitlines(keepends=True)
    line_starts: list[int] = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line)

    def _line_at(pos: int) -> str:
        # Binary search for the line containing character position `pos`.
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1  # noqa: SIM113
        return lines[lo] if lo < len(lines) else ""

    matches: list[CredentialMatch] = []
    seen: set[str] = set()

    for key_type, pattern in _PATTERNS.items():
        for m in pattern.finditer(content):
            raw = m.group(0)

            # For context-anchored patterns (cohere, mistral, together, deepseek)
            # the actual key is the last contiguous alphanum token in the match.
            if key_type in ("cohere", "mistral", "together", "deepseek"):
                tokens = re.findall(r"[a-zA-Z0-9]{20,}", raw)
                value = tokens[-1] if tokens else raw
            else:
                value = raw

            if value in seen:
                continue

            context = _line_at(m.start())
            if _is_placeholder(value, context_line=context):
                continue

            seen.add(value)
            matches.append(CredentialMatch(key_type=key_type, value=value))

    return matches
