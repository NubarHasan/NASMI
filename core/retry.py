from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from functools import wraps
from typing import TypeVar

from core.exceptions import RetryError
from core.guards import require

T = TypeVar("T")

_DEFAULT_ATTEMPTS: int = 3
_DEFAULT_DELAY: float = 1.0
_DEFAULT_MAX_DELAY: float = 60.0
_DEFAULT_BACKOFF: float = 2.0
_JITTER_RANGE: float = 0.5


class RetryStrategy(StrEnum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"


@dataclass(frozen=True)
class RetryConfig:
    attempts: int = _DEFAULT_ATTEMPTS
    delay: float = _DEFAULT_DELAY
    max_delay: float = _DEFAULT_MAX_DELAY
    backoff: float = _DEFAULT_BACKOFF
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    # Exception only — KeyboardInterrupt/SystemExit/GeneratorExit
    # inherit from BaseException and must never be retried.
    retryable_on: tuple[type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        require(self.attempts >= 1, "attempts must be >= 1")
        require(self.delay >= 0.0, "delay must be >= 0")
        require(self.max_delay >= self.delay, "max_delay must be >= delay")
        require(self.backoff >= 1.0, "backoff must be >= 1.0")


def _compute_delay(
    config: RetryConfig,
    attempt: int,
) -> float:
    """
    attempt is 0-indexed: 0 = after first failure.
    """
    if config.strategy == RetryStrategy.FIXED:
        wait = config.delay

    elif config.strategy == RetryStrategy.EXPONENTIAL:
        wait = config.delay * (config.backoff**attempt)

    else:  # JITTER
        base = config.delay * (config.backoff**attempt)
        jitter = config.rng.uniform(-_JITTER_RANGE * base, _JITTER_RANGE * base)
        wait = base + jitter

    return max(0.0, min(wait, config.max_delay))


def retry(
    fn: Callable[[], T],
    config: RetryConfig | None = None,
) -> T:
    cfg = config or RetryConfig()
    last_exc: Exception | None = None

    for attempt in range(cfg.attempts):
        try:
            return fn()
        except cfg.retryable_on as exc:
            last_exc = exc
            if attempt < cfg.attempts - 1:
                wait = _compute_delay(cfg, attempt)
                time.sleep(wait)

    raise RetryError(
        f"retry failed after {cfg.attempts} attempt(s) "
        f"(strategy={cfg.strategy}, error={type(last_exc).__name__})"
    ) from last_exc


def retryable(
    config: RetryConfig | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> T:
            return retry(lambda: fn(*args, **kwargs), config)

        return wrapper

    return decorator
