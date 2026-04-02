from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    """Sliding-window rate limiter for GitHub Search API (30 req/min)."""

    def __init__(self, max_requests: int = 30, window_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._timestamps: deque[float] = deque()

    def acquire(self) -> None:
        now = time.monotonic()
        # Evict timestamps outside the current window
        while self._timestamps and now - self._timestamps[0] >= self._window:
            self._timestamps.popleft()

        if len(self._timestamps) >= self._max:
            sleep_for = self._window - (now - self._timestamps[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
            # Re-evict after sleeping
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self._window:
                self._timestamps.popleft()

        self._timestamps.append(time.monotonic())
