"""
Provider rate-limit awareness — X-RateLimit-* header'lari oku, proaktif throttle.

Ihtiyac:
    OpenAI/Anthropic 429 attiginda retry ediyoruz ama bu ani latency spike
    yaratiyor. Daha iyisi: her response'taki rate-limit header'larini okuyup,
    kota %10'un altina dustukunde *proaktif* fallback tier'a gec.

Desteklenen header'lar:
    OpenAI:
        x-ratelimit-remaining-requests
        x-ratelimit-remaining-tokens
        x-ratelimit-reset-requests
        x-ratelimit-reset-tokens
        retry-after
    Anthropic:
        anthropic-ratelimit-requests-remaining
        anthropic-ratelimit-tokens-remaining
        anthropic-ratelimit-requests-reset
        anthropic-ratelimit-tokens-reset
        retry-after

AI Gateway response'larinda bu header'lar proxy'lenirse:
    record_rate_limit_headers(model, headers) -> module-level state update
    should_throttle(model) -> True/False
    get_rate_limit_state(model) -> observability için

Module-level in-memory state yeterli — multi-pod durumunda Redis'e tasimak kolay.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Rate limit guard esigi — kalan kota %10'un altinda ise throttle
_THROTTLE_PCT = 10.0

# State retention — 1 dakika uzun okunmadi ise stale say
_STATE_STALE_SECS = 60.0


@dataclass
class RateLimitState:
    """Bir model için son bilinen rate-limit durumu."""

    model: str
    remaining_requests: Optional[int] = None
    remaining_tokens: Optional[int] = None
    limit_requests: Optional[int] = None
    limit_tokens: Optional[int] = None
    reset_requests_secs: Optional[float] = None
    reset_tokens_secs: Optional[float] = None
    retry_after_secs: Optional[float] = None
    updated_at: float = field(default_factory=time.time)
    provider: str = "unknown"

    def is_stale(self) -> bool:
        return (time.time() - self.updated_at) > _STATE_STALE_SECS

    def pct_remaining_requests(self) -> Optional[float]:
        if self.remaining_requests is None or not self.limit_requests:
            return None
        return (self.remaining_requests / self.limit_requests) * 100.0

    def pct_remaining_tokens(self) -> Optional[float]:
        if self.remaining_tokens is None or not self.limit_tokens:
            return None
        return (self.remaining_tokens / self.limit_tokens) * 100.0

    def should_throttle(self) -> tuple[bool, str]:
        """(throttle_mi, sebep) doner."""
        if self.is_stale():
            return False, "stale"
        if self.retry_after_secs and self.retry_after_secs > 0:
            return True, f"retry_after={self.retry_after_secs:.0f}s"
        req_pct = self.pct_remaining_requests()
        tok_pct = self.pct_remaining_tokens()
        if req_pct is not None and req_pct < _THROTTLE_PCT:
            return True, f"req_remaining={req_pct:.1f}%"
        if tok_pct is not None and tok_pct < _THROTTLE_PCT:
            return True, f"tok_remaining={tok_pct:.1f}%"
        return False, "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "remaining_requests": self.remaining_requests,
            "remaining_tokens": self.remaining_tokens,
            "limit_requests": self.limit_requests,
            "limit_tokens": self.limit_tokens,
            "retry_after_secs": self.retry_after_secs,
            "updated_at": self.updated_at,
            "age_secs": round(time.time() - self.updated_at, 1),
            "pct_remaining_requests": self.pct_remaining_requests(),
            "pct_remaining_tokens": self.pct_remaining_tokens(),
        }


# ── Module-level state (in-memory) ──────────────────────────────────────


_state: dict[str, RateLimitState] = {}


# ── Header parsing ──────────────────────────────────────────────────────


def _parse_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _parse_duration(val: Any) -> Optional[float]:
    """OpenAI duration format: "12s", "1m30s", "500ms", veya int saniye.

    Anthropic: ISO 8601 timestamp ("2026-04-19T12:34:56Z") — bunu da handle et.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Pure int/float -> saniye
    try:
        return float(s)
    except ValueError:
        pass
    # OpenAI format: 1h30m45s, 500ms (compound duration)
    # Once "ms" yakala (milliseconds), sonra temizlenmis string'de "s"/"m"/"h"
    import re
    total = 0.0
    working = s
    # ms — 500ms -> 0.5s
    for mo in re.finditer(r"(\d+(?:\.\d+)?)ms", working):
        total += float(mo.group(1)) / 1000.0
    working = re.sub(r"\d+(?:\.\d+)?ms", "", working)
    # h — 1h30m -> 3600 * 1
    for mo in re.finditer(r"(\d+(?:\.\d+)?)h", working):
        total += float(mo.group(1)) * 3600
    working = re.sub(r"\d+(?:\.\d+)?h", "", working)
    # m — 30m -> 30 * 60
    for mo in re.finditer(r"(\d+(?:\.\d+)?)m", working):
        total += float(mo.group(1)) * 60
    working = re.sub(r"\d+(?:\.\d+)?m", "", working)
    # s — 45s -> 45
    for mo in re.finditer(r"(\d+(?:\.\d+)?)s", working):
        total += float(mo.group(1))
    if total > 0:
        return total
    # ISO timestamp -> relative
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        delta = (dt - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delta)
    except Exception:
        return None


def record_rate_limit_headers(model: str, headers: dict[str, str]) -> Optional[RateLimitState]:
    """
    Response header'larindan rate-limit state guncelle.

    Args:
        model:    Model adi (gpt-4o vb.)
        headers:  HTTP response headers (case-insensitive dict)

    Returns:
        Guncellenen RateLimitState veya header yoksa None.
    """
    if not model or not headers:
        return None

    # Normalize header key'leri lowercase
    lower = {str(k).lower(): v for k, v in headers.items()}

    state = _state.get(model) or RateLimitState(model=model)

    # OpenAI
    rem_req = lower.get("x-ratelimit-remaining-requests")
    rem_tok = lower.get("x-ratelimit-remaining-tokens")
    lim_req = lower.get("x-ratelimit-limit-requests")
    lim_tok = lower.get("x-ratelimit-limit-tokens")
    reset_req = lower.get("x-ratelimit-reset-requests")
    reset_tok = lower.get("x-ratelimit-reset-tokens")

    # Anthropic
    ant_rem_req = lower.get("anthropic-ratelimit-requests-remaining")
    ant_rem_tok = lower.get("anthropic-ratelimit-tokens-remaining")
    ant_lim_req = lower.get("anthropic-ratelimit-requests-limit")
    ant_lim_tok = lower.get("anthropic-ratelimit-tokens-limit")
    ant_reset_req = lower.get("anthropic-ratelimit-requests-reset")
    ant_reset_tok = lower.get("anthropic-ratelimit-tokens-reset")

    retry_after = lower.get("retry-after")

    found = False

    if rem_req is not None or ant_rem_req is not None:
        state.remaining_requests = _parse_int(rem_req) if rem_req is not None else _parse_int(ant_rem_req)
        state.provider = "openai" if rem_req else "anthropic"
        found = True
    if rem_tok is not None or ant_rem_tok is not None:
        state.remaining_tokens = _parse_int(rem_tok) if rem_tok is not None else _parse_int(ant_rem_tok)
        found = True
    if lim_req is not None or ant_lim_req is not None:
        state.limit_requests = _parse_int(lim_req) if lim_req is not None else _parse_int(ant_lim_req)
        found = True
    if lim_tok is not None or ant_lim_tok is not None:
        state.limit_tokens = _parse_int(lim_tok) if lim_tok is not None else _parse_int(ant_lim_tok)
        found = True
    if reset_req is not None or ant_reset_req is not None:
        state.reset_requests_secs = _parse_duration(reset_req or ant_reset_req)
        found = True
    if reset_tok is not None or ant_reset_tok is not None:
        state.reset_tokens_secs = _parse_duration(reset_tok or ant_reset_tok)
        found = True
    if retry_after is not None:
        state.retry_after_secs = _parse_duration(retry_after)
        found = True

    if not found:
        return None

    state.updated_at = time.time()
    _state[model] = state

    throttle, reason = state.should_throttle()
    if throttle:
        logger.warning(
            "Rate-limit warning %s: %s (req_rem=%s, tok_rem=%s)",
            model, reason, state.remaining_requests, state.remaining_tokens,
        )
    return state


def should_throttle(model: str) -> tuple[bool, str]:
    """Model için proaktif throttle sart mi?

    Router bunu kontrol edip fallback tier'a inebilir.
    """
    state = _state.get(model)
    if state is None:
        return False, "no_data"
    return state.should_throttle()


def get_rate_limit_state(model: str) -> Optional[RateLimitState]:
    """Model için son bilinen state."""
    return _state.get(model)


def get_all_rate_limits() -> dict[str, dict[str, Any]]:
    """Tüm modellerin state'i — /ai/model-router/stats için."""
    return {m: s.to_dict() for m, s in _state.items()}


def clear_rate_limit(model: Optional[str] = None) -> None:
    """Test/reset için."""
    if model:
        _state.pop(model, None)
    else:
        _state.clear()
