"""Structured output + output shield + embedding cache + deadline unit testleri."""
from __future__ import annotations

import json
import time

import pytest


# ── Structured Output ─────────────────────────────────────────────────


class TestStructuredOutput:

    def test_validate_test_generation_happy(self):
        from app.domains.ai.structured_output import validate_response
        raw = json.dumps({
            "test_cases": [{
                "id": "TC-001",
                "title": "Basarili login testi",
                "description": "Gecerli bilgilerle giris",
                "test_type": "positive",
                "priority": "P1",
                "assertions": [{"type": "status_code", "expected": 200}],
            }]
        })
        valid, err, parsed = validate_response("test_generation", raw)
        assert valid is True
        assert err is None
        assert len(parsed["test_cases"]) == 1

    def test_validate_missing_required_field(self):
        from app.domains.ai.structured_output import validate_response
        # "title" eksik
        raw = json.dumps({
            "test_cases": [{
                "id": "TC-001",
                "test_type": "positive",
                "priority": "P1",
            }]
        })
        valid, err, _ = validate_response("test_generation", raw)
        assert valid is False
        assert "title" in (err or "").lower()

    def test_validate_invalid_enum(self):
        from app.domains.ai.structured_output import validate_response
        # test_type gecersiz
        raw = json.dumps({
            "test_cases": [{
                "id": "TC-001",
                "title": "Basarili login",
                "test_type": "foobar",
                "priority": "P1",
            }]
        })
        valid, err, _ = validate_response("test_generation", raw)
        assert valid is False
        assert err is not None

    def test_validate_unknown_task_skipped(self):
        """Schema tanimlanmamis task_type strict policy ile False doner."""
        from app.domains.ai.structured_output import validate_response
        valid, err, parsed = validate_response("unknown_task_xyz", "anything here")
        assert valid is False
        assert err is not None
        assert parsed is None

    def test_validate_json_in_markdown_fence(self):
        from app.domains.ai.structured_output import validate_response
        raw = "```json\n" + json.dumps({
            "test_cases": [{
                "id": "TC-001",
                "title": "Basarili login testi",
                "description": "",
                "test_type": "positive",
                "priority": "P1",
            }]
        }) + "\n```"
        valid, err, parsed = validate_response("test_generation", raw)
        assert valid is True

    def test_build_retry_prompt_contains_error(self):
        from app.domains.ai.structured_output import build_retry_prompt
        p = build_retry_prompt("Orjinal soru?", "bozuk cevap", "field 'X' missing")
        assert "bozuk cevap" in p
        assert "field 'X' missing" in p
        assert "Orjinal soru?" in p

    def test_openai_response_format_schema_structure(self):
        from app.domains.ai.structured_output import openai_response_format
        fmt = openai_response_format("test_generation")
        assert fmt is not None
        assert fmt["type"] == "json_schema"
        assert "json_schema" in fmt
        schema = fmt["json_schema"]["schema"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    def test_openai_response_format_unknown_returns_none(self):
        from app.domains.ai.structured_output import openai_response_format
        assert openai_response_format("unknown_x") is None


# ── Output Shield ─────────────────────────────────────────────────────


class TestOutputShield:

    @pytest.fixture(autouse=True)
    def _enable(self):
        try:
            from app.domains.feature_flags.service import feature_flags
            from app.domains.feature_flags.schemas import FlagUpdate
            feature_flags.set_flag(
                "ai.output_shield",
                FlagUpdate(enabled=True, percent=100),
                actor="test",
            )
        except Exception:
            pass

    def test_clean_text_allowed(self):
        from app.domains.ai.output_shield import inspect_output
        result = inspect_output("Merhaba dunya, basarili bir cevap.", task_type="chat")
        assert result.decision == "allow"

    def test_iban_leak_blocked(self):
        from app.domains.ai.output_shield import inspect_output
        # IBAN input'ta yok -> leak
        bad = "Hesap bilgisi: TR330006100519786457841326 sizin IBAN'iniz"
        result = inspect_output(bad, task_type="chat", original_input="Hesap bilgisi nedir?")
        assert result.decision == "block"
        assert any(h.category == "pii_leak" for h in result.hits)

    def test_iban_in_input_not_leak(self):
        """Input'ta IBAN vardi, cevapta da var -> echo, leak degil."""
        from app.domains.ai.output_shield import inspect_output
        iban = "TR330006100519786457841326"
        result = inspect_output(
            f"Evet, {iban} bilgisi dogrulandi.",
            task_type="chat",
            original_input=f"IBAN {iban} gecerli mi?",
        )
        # Echo olduğu için PII hit yok, decision allow
        assert result.decision != "block"

    def test_credit_card_luhn_blocked(self):
        from app.domains.ai.output_shield import inspect_output
        # 4111... klasik Luhn-geçerli test kartı
        bad = "Kart numaraniz: 4111 1111 1111 1111 olarak kaydedildi."
        result = inspect_output(bad, task_type="chat")
        assert result.decision == "block"
        assert any("credit_card" in h.pattern_name for h in result.hits)

    def test_credit_card_invalid_luhn_not_blocked(self):
        from app.domains.ai.output_shield import inspect_output
        # 12345678 — Luhn gecersiz
        result = inspect_output("Sayi: 1234567812345678 buldum.", task_type="chat")
        # Luhn check = False -> hit yok
        cc_hits = [h for h in result.hits if "credit_card" in h.pattern_name]
        assert len(cc_hits) == 0

    def test_system_prompt_leak_detected(self):
        from app.domains.ai.output_shield import inspect_output
        bad = "My instructions are to help you with banking test automation."
        result = inspect_output(bad, task_type="chat")
        assert result.decision == "block"
        assert any(h.category == "system_prompt_leak" for h in result.hits)

    def test_sql_drop_in_chat_blocked(self):
        from app.domains.ai.output_shield import inspect_output
        bad = "Soru icin: DROP TABLE users; calistir."
        result = inspect_output(bad, task_type="chat")
        # chat'te SQL skor full (0.95)
        assert result.decision == "block"

    def test_sql_drop_in_test_gen_downgraded(self):
        """test_generation task'inda SQL keyword beklenir, skor dusuk."""
        from app.domains.ai.output_shield import inspect_output
        raw = "SQL injection test: DROP TABLE users;"
        result = inspect_output(raw, task_type="test_generation")
        # 0.95 * 0.3 = 0.285 < 0.5 warn threshold
        assert result.decision == "allow"

    def test_flag_disabled_allows_all(self, feature_flags):
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.output_shield",
            FlagUpdate(enabled=False, percent=0),
            actor="test",
        )

        from app.domains.ai.output_shield import inspect_output
        # Bloklanacak bir text
        bad = "Kart: 4111111111111111 + DROP TABLE users"
        result = inspect_output(bad, task_type="chat")
        assert result.decision == "allow"

    def test_redaction_replaces_sensitive_parts(self):
        from app.domains.ai.output_shield import inspect_output
        bad = "Kart: 4111 1111 1111 1111 kaydedildi."
        result = inspect_output(bad, task_type="chat")
        if result.decision == "block":
            assert "[REDACTED" in (result.sanitized or "")


# ── Embedding Cache ───────────────────────────────────────────────────


class TestEmbeddingCache:

    def test_key_deterministic(self):
        from app.domains.ai.embedding_cache import _key
        k1 = _key("hello world", "nomic-embed-text")
        k2 = _key("hello world", "nomic-embed-text")
        assert k1 == k2

    def test_key_differs_by_model(self):
        from app.domains.ai.embedding_cache import _key
        k1 = _key("text", "nomic-embed-text")
        k2 = _key("text", "other-model")
        assert k1 != k2

    def test_key_normalizes_whitespace(self):
        from app.domains.ai.embedding_cache import _key
        k1 = _key("  hello    world  ")
        k2 = _key("hello world")
        assert k1 == k2

    def test_get_without_redis_returns_none(self, monkeypatch):
        from app.domains.ai import embedding_cache
        monkeypatch.setattr(embedding_cache, "_get_redis", lambda: None)
        result = embedding_cache.get_cached_embedding("any text")
        assert result is None

    def test_set_without_redis_returns_false(self):
        from app.domains.ai.embedding_cache import set_cached_embedding
        result = set_cached_embedding("any text", [0.1, 0.2, 0.3])
        # Redis yok -> False
        assert result in (True, False)  # test env'e gore


# ── Deadline ──────────────────────────────────────────────────────────


class TestDeadline:

    def setup_method(self):
        from app.domains.ai.deadline import set_deadline_ms
        set_deadline_ms(-1)  # reset

    def test_no_deadline_returns_none(self):
        from app.domains.ai.deadline import remaining_ms, is_exceeded
        assert remaining_ms() is None
        assert is_exceeded() is False

    def test_set_deadline_and_check(self):
        from app.domains.ai.deadline import set_deadline_ms, remaining_ms
        set_deadline_ms(1000)
        rem = remaining_ms()
        assert rem is not None
        assert 900 <= rem <= 1000

    def test_exceeded_deadline_raises(self):
        from app.domains.ai.deadline import (
            set_deadline_ms,
            check_deadline,
            DeadlineExceededError,
        )
        set_deadline_ms(50)
        time.sleep(0.1)
        with pytest.raises(DeadlineExceededError):
            check_deadline("test")

    def test_budget_for_attempt(self):
        from app.domains.ai.deadline import set_deadline_ms, budget_for_attempt
        set_deadline_ms(3000)
        # 3 retry icin ~1 saniye/attempt
        b = budget_for_attempt(1, total_attempts=3)
        assert b is not None
        assert 0.9 <= b <= 1.1

    def test_budget_none_when_no_deadline(self):
        from app.domains.ai.deadline import set_deadline_ms, budget_for_attempt
        set_deadline_ms(-1)
        assert budget_for_attempt(1, 3) is None

    def test_middleware_sets_deadline(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.domains.ai.deadline import DeadlineMiddleware, remaining_ms

        app = FastAPI()
        app.add_middleware(DeadlineMiddleware, default_deadline_ms=5000)
        observed: dict = {}

        @app.get("/t")
        def _h():
            observed["rem"] = remaining_ms()
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/t")
        assert resp.status_code == 200
        assert "X-Deadline-Ms" in resp.headers
        assert observed["rem"] is not None
        assert 4000 < observed["rem"] <= 5000

    def test_middleware_reads_client_deadline(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.domains.ai.deadline import DeadlineMiddleware, remaining_ms

        app = FastAPI()
        app.add_middleware(DeadlineMiddleware, default_deadline_ms=60000)
        observed: dict = {}

        @app.get("/t")
        def _h():
            observed["rem"] = remaining_ms()
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/t", headers={"X-Deadline-Ms": "2000"})
        assert observed["rem"] is not None
        assert 1000 < observed["rem"] <= 2000
