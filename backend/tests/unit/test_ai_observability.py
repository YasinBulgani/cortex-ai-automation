"""Correlation ID, token counter, rate-limit monitor unit testleri."""
from __future__ import annotations

import pytest


# ── Correlation ID ────────────────────────────────────────────────────


class TestCorrelationID:

    def test_get_when_unset_returns_none(self, monkeypatch):
        from app.domains.ai.correlation import get_correlation_id, set_correlation_id
        set_correlation_id(None)
        assert get_correlation_id() is None

    def test_set_and_get(self):
        from app.domains.ai.correlation import get_correlation_id, set_correlation_id
        set_correlation_id("abc-123")
        assert get_correlation_id() == "abc-123"

    def test_ensure_generates_uuid_when_unset(self):
        from app.domains.ai.correlation import (
            ensure_correlation_id,
            get_correlation_id,
            set_correlation_id,
        )
        set_correlation_id(None)
        cid = ensure_correlation_id()
        assert cid is not None
        assert len(cid) >= 32
        assert get_correlation_id() == cid

    def test_ensure_preserves_existing(self):
        from app.domains.ai.correlation import (
            ensure_correlation_id,
            set_correlation_id,
        )
        set_correlation_id("existing-id")
        cid = ensure_correlation_id()
        assert cid == "existing-id"

    def test_header_name_constant(self):
        from app.domains.ai.correlation import HEADER_NAME
        assert HEADER_NAME == "X-Correlation-ID"


class TestCorrelationMiddleware:

    def test_middleware_generates_id_when_missing(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.domains.ai.correlation import CorrelationMiddleware, get_correlation_id

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        observed: dict = {}

        @app.get("/test")
        def _handler():
            observed["cid"] = get_correlation_id()
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        # Header echo'su var
        assert "X-Correlation-ID" in resp.headers
        assert len(resp.headers["X-Correlation-ID"]) >= 32
        # Handler contextvar'dan okuyabildi
        assert observed["cid"] == resp.headers["X-Correlation-ID"]

    def test_middleware_preserves_client_id(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.domains.ai.correlation import CorrelationMiddleware

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        def _handler():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test", headers={"X-Correlation-ID": "client-given-abc"})
        assert resp.headers["X-Correlation-ID"] == "client-given-abc"

    def test_middleware_truncates_long_ids(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.domains.ai.correlation import CorrelationMiddleware

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        def _handler():
            return {"ok": True}

        client = TestClient(app)
        long_id = "x" * 200
        resp = client.get("/test", headers={"X-Correlation-ID": long_id})
        assert len(resp.headers["X-Correlation-ID"]) <= 64


# ── Token Counter ─────────────────────────────────────────────────────


class TestTokenCounter:

    def test_count_tokens_empty(self):
        from app.domains.ai.token_counter import count_tokens
        assert count_tokens("") == 0
        assert count_tokens(None) == 0  # type: ignore

    def test_count_tokens_non_empty(self):
        from app.domains.ai.token_counter import count_tokens
        # tiktoken varsa gercek, yoksa len/4 — her iki durumda > 0
        assert count_tokens("Merhaba dunya") > 0

    def test_count_messages_sums(self):
        from app.domains.ai.token_counter import count_messages_tokens
        msgs = [
            {"role": "system", "content": "sistem"},
            {"role": "user", "content": "kullanici mesaji"},
        ]
        total = count_messages_tokens(msgs, model="gpt-4o")
        assert total > 0

    def test_context_limit_known_models(self):
        from app.domains.ai.token_counter import context_limit
        assert context_limit("gpt-4o") == 128_000
        assert context_limit("gpt-4o-mini") == 128_000
        assert context_limit("claude-sonnet-4-20250514") == 200_000

    def test_context_limit_unknown_defaults(self):
        from app.domains.ai.token_counter import context_limit
        assert context_limit("absolutely-unknown-xyz") == 32_768

    def test_context_limit_handles_tag_suffix(self):
        from app.domains.ai.token_counter import context_limit
        # qwen2.5:32b -> qwen2.5 -> 32768
        assert context_limit("qwen2.5:32b") == 32_768
        assert context_limit("ollama:qwen2.5-coder:7b") == 32_768

    def test_plan_tokens_fits_normal(self):
        from app.domains.ai.token_counter import plan_tokens
        plan = plan_tokens(
            "gpt-4o",
            messages=[{"role": "user", "content": "kisa soru"}],
            requested_max_output=4096,
        )
        assert plan.fits is True
        assert plan.allowed_output_tokens >= 4000

    def test_plan_tokens_rejects_oversized(self):
        from app.domains.ai.token_counter import plan_tokens
        # 40K karakter ~ 10K token, qwen2.5 context 32K
        # 35K output istersen input+buffer ile tasiyor
        huge = "a" * 100_000  # ~25K token
        plan = plan_tokens(
            "qwen2.5:32b",
            messages=[{"role": "user", "content": huge}],
            requested_max_output=20_000,
        )
        # Model limit 32768, input ~25K, 20K output sigmayacak
        assert plan.allowed_output_tokens < 20_000

    def test_plan_tokens_exhausted_context(self):
        from app.domains.ai.token_counter import plan_tokens
        # qwen2.5 context = 32K. 40K tiktoken token -> kesin asmali
        huge = "hello world " * 20_000  # ~50K token
        plan = plan_tokens(
            "qwen2.5",
            messages=[{"role": "user", "content": huge}],
            requested_max_output=2000,
        )
        assert plan.fits is False


# ── Rate Limit Monitor ────────────────────────────────────────────────


class TestRateLimitMonitor:

    def test_no_state_returns_no_throttle(self):
        from app.domains.ai.rate_limit_monitor import should_throttle, clear_rate_limit
        clear_rate_limit()
        throttle, reason = should_throttle("gpt-4o")
        assert throttle is False
        assert reason == "no_data"

    def test_record_openai_headers(self):
        from app.domains.ai.rate_limit_monitor import (
            record_rate_limit_headers,
            get_rate_limit_state,
            clear_rate_limit,
        )
        clear_rate_limit()
        headers = {
            "x-ratelimit-remaining-requests": "500",
            "x-ratelimit-limit-requests": "1000",
            "x-ratelimit-remaining-tokens": "50000",
            "x-ratelimit-limit-tokens": "100000",
        }
        state = record_rate_limit_headers("gpt-4o", headers)
        assert state is not None
        assert state.remaining_requests == 500
        assert state.limit_requests == 1000
        assert state.pct_remaining_requests() == 50.0

    def test_low_remaining_triggers_throttle(self):
        from app.domains.ai.rate_limit_monitor import (
            record_rate_limit_headers,
            should_throttle,
            clear_rate_limit,
        )
        clear_rate_limit()
        # %5 kalan -> throttle (esik %10)
        record_rate_limit_headers("gpt-4o", {
            "x-ratelimit-remaining-requests": "50",
            "x-ratelimit-limit-requests": "1000",
            "x-ratelimit-remaining-tokens": "80000",
            "x-ratelimit-limit-tokens": "100000",
        })
        throttle, reason = should_throttle("gpt-4o")
        assert throttle is True
        assert "req_remaining" in reason

    def test_retry_after_triggers_throttle(self):
        from app.domains.ai.rate_limit_monitor import (
            record_rate_limit_headers,
            should_throttle,
            clear_rate_limit,
        )
        clear_rate_limit()
        record_rate_limit_headers("gpt-4o", {"retry-after": "30"})
        throttle, reason = should_throttle("gpt-4o")
        assert throttle is True
        assert "retry_after" in reason

    def test_anthropic_headers_parsed(self):
        from app.domains.ai.rate_limit_monitor import (
            record_rate_limit_headers,
            get_rate_limit_state,
            clear_rate_limit,
        )
        clear_rate_limit()
        state = record_rate_limit_headers("claude-sonnet-4", {
            "anthropic-ratelimit-requests-remaining": "100",
            "anthropic-ratelimit-requests-limit": "1000",
        })
        assert state is not None
        assert state.remaining_requests == 100
        assert state.provider == "anthropic"

    def test_empty_headers_returns_none(self):
        from app.domains.ai.rate_limit_monitor import record_rate_limit_headers
        assert record_rate_limit_headers("gpt-4o", {}) is None
        assert record_rate_limit_headers("gpt-4o", {"content-type": "text/plain"}) is None

    def test_duration_parse_variants(self):
        from app.domains.ai.rate_limit_monitor import _parse_duration
        assert _parse_duration("30") == 30.0
        assert _parse_duration("30s") == 30.0
        assert _parse_duration("1m30s") == 90.0
        assert _parse_duration("500ms") == 0.5
        assert _parse_duration("") is None
        assert _parse_duration(None) is None

    def test_get_all_rate_limits_shape(self):
        from app.domains.ai.rate_limit_monitor import (
            record_rate_limit_headers,
            get_all_rate_limits,
            clear_rate_limit,
        )
        clear_rate_limit()
        record_rate_limit_headers("gpt-4o", {"x-ratelimit-remaining-requests": "500"})
        record_rate_limit_headers("gpt-4o-mini", {"x-ratelimit-remaining-requests": "1000"})
        all_states = get_all_rate_limits()
        assert "gpt-4o" in all_states
        assert "gpt-4o-mini" in all_states
        assert "remaining_requests" in all_states["gpt-4o"]


# ── Router rate-limit integration ─────────────────────────────────────


class TestRouterRateLimitFallback:

    def test_rate_limited_premium_falls_to_mid(self, monkeypatch, feature_flags):
        """Premium model kota bittiginde MID'e dusmeli."""
        from app.domains.ai import smart_model_router as router
        from app.domains.ai.smart_model_router import route_model, Tier
        from app.domains.ai import rate_limit_monitor as rlm

        router._circuit_state.clear()
        rlm.clear_rate_limit()
        monkeypatch.setattr(router.settings, "anthropic_api_key", "sk-ant", raising=False)
        monkeypatch.setattr(router.settings, "anthropic_premium_model", "claude-sonnet-4-20250514", raising=False)
        monkeypatch.setattr(router.settings, "openai_mid_model", "gpt-4o", raising=False)
        monkeypatch.setattr(router.settings, "ai_routing_mode", "balanced", raising=False)

        # Feature flag aktif
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.router.v2",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )

        # Premium rate-limit'i bitir
        rlm.record_rate_limit_headers("claude-sonnet-4-20250514", {
            "anthropic-ratelimit-requests-remaining": "5",
            "anthropic-ratelimit-requests-limit": "1000",
        })

        rec = route_model("chain_builder")  # normal PREMIUM
        assert rec.tier is Tier.MID
        assert "rate-limit" in rec.reason.lower()


# ── Gateway_client integrations ────────────────────────────────────────


class TestGatewayHeadersIncludeCorrelation:

    def test_gateway_headers_include_correlation_when_set(self):
        from app.domains.ai.correlation import set_correlation_id
        from app.domains.ai.gateway_client import _gateway_headers

        set_correlation_id("test-corr-456")
        h = _gateway_headers()
        assert h.get("X-Correlation-ID") == "test-corr-456"

    def test_gateway_headers_no_correlation_when_unset(self):
        from app.domains.ai.correlation import set_correlation_id
        from app.domains.ai.gateway_client import _gateway_headers

        set_correlation_id(None)
        h = _gateway_headers()
        assert "X-Correlation-ID" not in h
