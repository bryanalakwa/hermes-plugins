"""
Self-Healing Dependency Protocol (SHDP)

A lightweight decorator/factory that makes any dependency resilient by default.
Instead of writing try/except + fallback logic at every call site, annotate the
dependency and let the protocol handle it.

Usage:
    from self_healing import self_healing

    @self_healing(fallback=None, label="vector_store")
    def get_vector_store():
        import chromadb
        return chromadb.PersistentClient(...)

    # If chromadb is not installed or initialization fails, returns None
    # and logs the recovery. No crash, no manual try/except.

The protocol does three things:
  1. Checks if the dependency is available (lazy initialization)
  2. Attempts initialization with configurable retries
  3. Falls back to a degraded mode on failure, logging the recovery
"""

import functools
import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """Raised when a dependency cannot be initialized even after retries."""
    pass


class SelfHealingResult:
    """Wrapper that indicates whether a result came from the primary or fallback path."""

    def __init__(self, value: Any, healthy: bool, recovery_log: Optional[str] = None):
        self.value = value
        self.healthy = healthy
        self.recovery_log = recovery_log

    def __repr__(self):
        status = "healthy" if self.healthy else "degraded"
        return f"SelfHealingResult({status}, value={type(self.value).__name__})"

    # Allow transparent use of the wrapped value for common types
    def __str__(self):
        return str(self.value) if self.value is not None else ""

    def __bool__(self):
        return self.value is not None

    def get(self, default=None):
        """Return value or default, similar to dict.get()."""
        return self.value if self.value is not None else default


def self_healing(
    fallback: Any = None,
    label: str = "dependency",
    retries: int = 1,
    retry_delay: float = 0.0,
    suppress_exceptions: bool = True,
):
    """Decorator that makes a dependency function self-healing.

    Args:
        fallback: Value to return if the dependency fails. None = return SelfHealingResult.
        label: Human-readable name for log messages.
        retries: Number of initialization attempts before falling back.
        retry_delay: Seconds between retries.
        suppress_exceptions: If True, catches all exceptions and returns fallback.
                             If False, raises DependencyError after all retries fail.

    Returns:
        Decorated function that never crashes — returns fallback on failure.

    Example:
        @self_healing(fallback={}, label="chroma_db")
        def get_chroma_collection():
            import chromadb
            client = chromadb.PersistentClient(path="/tmp/chroma")
            return client.get_or_create_collection("facts")
    """
    def decorator(func: Callable) -> Callable:
        _cache = {"instance": _UNINITIALIZED, "failed": False}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Return cached instance if already initialized
            if _cache["instance"] is not _UNINITIALIZED:
                return _cache["instance"]

            # Don't retry if we already failed (unless enough time has passed)
            if _cache["failed"]:
                return fallback if fallback is not None else SelfHealingResult(
                    value=None, healthy=False,
                    recovery_log=f"{label}: using cached failure state"
                )

            # Attempt initialization
            last_exception = None
            for attempt in range(retries):
                try:
                    result = func(*args, **kwargs)
                    _cache["instance"] = result
                    if attempt > 0:
                        logger.info("%s: recovered on attempt %d", label, attempt + 1)
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1 and retry_delay > 0:
                        time.sleep(retry_delay)

            # All retries failed — fall back
            _cache["failed"] = True
            logger.warning(
                "%s: initialization failed after %d attempt(s): %s — using fallback",
                label, retries, last_exception
            )

            if suppress_exceptions:
                return fallback if fallback is not None else SelfHealingResult(
                    value=None, healthy=False,
                    recovery_log=f"{label}: {last_exception}"
                )
            raise DependencyError(f"{label} unavailable: {last_exception}") from last_exception

        def reset():
            """Reset the cache, forcing re-initialization on next call."""
            _cache["instance"] = _UNINITIALIZED
            _cache["failed"] = False

        wrapper.reset = reset
        wrapper.is_healthy = lambda: _cache["instance"] is not _UNINITIALIZED

        return wrapper
    return decorator


# Sentinel object for "not yet initialized"
class _UninitializedSentinel:
    def __repr__(self):
        return "<UNINITIALIZED>"

_UNINITIALIZED = _UninitializedSentinel()
