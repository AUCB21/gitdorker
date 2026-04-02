from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path("logs")

# Third-party loggers that flood the file with internal HTTP tracing
_NOISY_LOGGERS = (
    "httpx", "httpcore", "urllib3", "requests",
    "anthropic", "openai", "google",
)


def setup(verbose: bool = False) -> logging.Logger:
    _LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = _LOG_DIR / f"gitdorker_{timestamp}.log"

    level = logging.DEBUG if verbose else logging.INFO

    # Configure only the gitdorker logger — do not touch the root logger
    logger = logging.getLogger("gitdorker")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    # Silence noisy third-party loggers regardless of verbose mode
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    return logger


log: logging.Logger = logging.getLogger("gitdorker")
