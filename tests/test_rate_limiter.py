from __future__ import annotations

import time

import pytest

from gitdorker.api.rate_limiter import RateLimiter


def test_allows_requests_within_limit() -> None:
    limiter = RateLimiter(max_requests=5, window_seconds=60.0)
    start = time.monotonic()
    for _ in range(5):
        limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, "5 requests within limit should not block"


def test_blocks_on_limit_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))

    limiter = RateLimiter(max_requests=2, window_seconds=10.0)
    # Fill the window
    limiter._timestamps.append(time.monotonic() - 1)
    limiter._timestamps.append(time.monotonic() - 0.5)

    limiter.acquire()
    assert len(slept) == 1
    assert slept[0] > 0
