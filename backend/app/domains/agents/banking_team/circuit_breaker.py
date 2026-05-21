"""Thread-safe circuit breaker for Ollama (and any external LLM service).

States
------
CLOSED   — normal operation; requests flow through.
OPEN     — too many consecutive failures; requests are blocked.
HALF_OPEN — after ``recovery_timeout`` seconds the circuit allows ONE probe
            request.  Success → CLOSED, failure → OPEN again.

Usage
-----
>>> from app.domains.agents.banking_team.circuit_breaker import ollama_breaker
>>> if ollama_breaker.can_execute():
...     try:
...         result = call_ollama(...)
...         ollama_breaker.record_success()
...     except ConnectionError:
...         ollama_breaker.record_failure()
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

# State constants
CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreaker:
    """Lightweight circuit breaker — safe to share across threads."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = CLOSED
        self._lock = threading.Lock()

    # -- public API --------------------------------------------------------

    def can_execute(self) -> bool:
        """Return *True* if a request is allowed right now."""
        with self._lock:
            if self._state == CLOSED:
                return True

            if self._state == OPEN:
                # Check whether enough time has passed to transition to HALF_OPEN
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = HALF_OPEN
                    logger.info(
                        "Circuit breaker → HALF_OPEN (%.0fs since last failure)",
                        time.time() - self._last_failure_time,
                    )
                    return True  # allow one probe request
                return False

            # HALF_OPEN — allow the single probe request
            return True

    def record_success(self) -> None:
        """Call after a successful request."""
        with self._lock:
            if self._state != CLOSED:
                logger.info("Circuit breaker → CLOSED (success)")
            self._failure_count = 0
            self._state = CLOSED

    def record_failure(self) -> None:
        """Call after a connection/timeout failure."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == HALF_OPEN:
                # Probe failed — back to OPEN
                self._state = OPEN
                logger.warning(
                    "Circuit breaker → OPEN (half-open probe failed, %d failures)",
                    self._failure_count,
                )
            elif self._failure_count >= self._failure_threshold:
                self._state = OPEN
                logger.warning(
                    "Circuit breaker → OPEN (%d consecutive failures)",
                    self._failure_count,
                )

    @property
    def state(self) -> str:
        """Current state: ``'closed'``, ``'open'``, or ``'half_open'``."""
        with self._lock:
            # Auto-transition OPEN → HALF_OPEN if timeout elapsed (read-only check)
            if (
                self._state == OPEN
                and time.time() - self._last_failure_time >= self._recovery_timeout
            ):
                self._state = HALF_OPEN
            return self._state

    @property
    def failure_count(self) -> int:
        """Number of consecutive failures recorded so far."""
        with self._lock:
            return self._failure_count

    def reset(self) -> None:
        """Force-reset the breaker to *CLOSED* (useful in tests)."""
        with self._lock:
            self._failure_count = 0
            self._last_failure_time = 0.0
            self._state = CLOSED


# Global instance — shared across all agents talking to Ollama.
ollama_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
