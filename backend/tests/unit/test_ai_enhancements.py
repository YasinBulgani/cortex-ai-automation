"""Semantic cache, PII redaction, self-refine, finetune_export unit testleri."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


# ── Semantic Cache ─────────────────────────────────────────────────────


class TestSemanticCacheKeying:
    """Redis yokken bile key uretimi ve normalize deterministik olmali."""

    def test_normalize_message_collapses_whitespace(self):
        from app.domains.ai.semantic_cache import _normalize_message

        a = _normalize_message("  Hello   World!  ")
        b = _normalize_message("hello world")
        # Normalize: collapse + rstrip punctuation + lower
        assert a == "hello world"
        assert a == b

    def test_exact_key_is_deterministic(self):
        from app.domains.ai.semantic_cache import _exact_key
        k1 = _exact_key("chat", "Merhaba dunya", "Sen bir asistansin")
        k2 = _exact_key("chat", "Merhaba dunya", "Sen bir asistansin")
        assert k1 == k2
        assert len(k1) == 40  # sha1 hex

    def test_exact_key_differs_by_task_type(self):
        from app.domains.ai.semantic_cache import _exact_key
        k1 = _exact_key("chat", "q", None)
        k2 = _exact_key("test_generation", "q", None)
        assert k1 != k2

    def test_cosine_similarity(self):
        from app.domains.ai.semantic_cache import _cosine
        # Identical -> 1.0
        v = [0.1, 0.2, 0.3]
        assert abs(_cosine(v, v) - 1.0) < 1e-6
        # Orthogonal -> 0.0
        assert abs(_cosine([1, 0], [0, 1]) - 0.0) < 1e-6
        # Opposite -> -1.0
        assert abs(_cosine([1, 0], [-1, 0]) - (-1.0)) < 1e-6
        # Empty -> 0
        assert _cosine([], [1, 2]) == 0.0

    def test_ttl_security_audit_is_zero(self):
        from app.domains.ai.semantic_cache import _CACHE_TTL_SECS
        assert _CACHE_TTL_SECS["security_audit"] == 0
        assert _CACHE_TTL_SECS["quality_judge"] == 0

    def test_cache_get_without_redis_returns_none(self, monkeypatch):
        from app.domains.ai import semantic_cache
        # Redis yokluğunu simüle et
        monkeypatch.setattr(semantic_cache, "_get_redis", lambda: None)
        result = semantic_cache.cache_get("chat", "test query")
        assert result is None

    def test_cache_disabled_by_flag_returns_none(self, monkeypatch):
        from app.domains.ai import semantic_cache
        monkeypatch.setattr(semantic_cache, "_cache_enabled", lambda tenant_id=None: False)
        result = semantic_cache.cache_get("chat", "test query")
        assert result is None

    def test_cache_zero_ttl_skips(self, monkeypatch):
        """security_audit TTL=0 -> cache bypass."""
        from app.domains.ai import semantic_cache
        monkeypatch.setattr(semantic_cache, "_cache_enabled", lambda tenant_id=None: True)
        # Redis mock olsa bile TTL=0 ise None doner
        class FakeRedis:
            def hgetall(self, *a, **kw): return {}
            def zrevrange(self, *a, **kw): return []
        monkeypatch.setattr(semantic_cache, "_get_redis", lambda: FakeRedis())
        result = semantic_cache.cache_get("security_audit", "q")
        assert result is None


# ── PII Redaction Pre-LLM ──────────────────────────────────────────────


class TestPIIRedactionPreLLM:

    def test_redacts_iban_in_user_message(self):
        from app.domains.ai.gateway_client import _redact_pii
        text = "Hesap bilgim TR330006100519786457841326 lutfen kontrol et"
        redacted, count = _redact_pii(text)
        assert "[IBAN]" in redacted
        assert "TR330006100519786457841326" not in redacted
        assert count >= 1

    def test_redacts_email(self):
        from app.domains.ai.gateway_client import _redact_pii
        text = "User test@example.com giris yapamiyor"
        redacted, count = _redact_pii(text)
        assert "[EMAIL]" in redacted
        assert "test@example.com" not in redacted
        assert count >= 1

    def test_empty_text_returns_zero(self):
        from app.domains.ai.gateway_client import _redact_pii
        redacted, count = _redact_pii("")
        assert redacted == ""
        assert count == 0

    def test_no_pii_returns_unchanged(self):
        from app.domains.ai.gateway_client import _redact_pii
        text = "Merhaba dunya, bu basit bir metin."
        redacted, count = _redact_pii(text)
        assert redacted == text
        assert count == 0

    def test_flag_disabled_bypasses_redaction(self, monkeypatch):
        """ai.pii.redact kapaliysa ham metin gecer."""
        try:
            from app.domains.feature_flags.service import feature_flags
            from app.domains.feature_flags.schemas import FlagUpdate
            feature_flags.set_flag(
                "ai.pii.redact",
                FlagUpdate(enabled=False, percent=0),
                actor="test",
            )
        except Exception:
            pytest.skip("feature_flags missing")

        from app.domains.ai.gateway_client import _redact_pii
        text = "IBAN: TR330006100519786457841326"
        redacted, count = _redact_pii(text)
        assert redacted == text
        assert count == 0


# ── Prompt Registry Resolution ─────────────────────────────────────────


class TestPromptRegistryResolve:

    def test_registry_disabled_by_default_returns_none(self):
        """ai.prompts.registry default False."""
        try:
            from app.domains.feature_flags.service import feature_flags
            feature_flags.clear()
        except Exception:
            pass

        from app.domains.ai.gateway_client import _resolve_from_registry
        sys, meta = _resolve_from_registry("test_generation")
        assert sys is None
        assert meta is None

    def test_registry_flag_on_but_no_prompt_returns_none(self, monkeypatch):
        """Flag acik ama DB'de prompt yoksa None."""
        try:
            from app.domains.feature_flags.service import feature_flags
            from app.domains.feature_flags.schemas import FlagUpdate
            feature_flags.set_flag(
                "ai.prompts.registry",
                FlagUpdate(enabled=True, percent=100),
                actor="test",
            )
        except Exception:
            pytest.skip("feature_flags missing")

        # Mock resolve -> None (DB'de yok)
        monkeypatch.setattr(
            "app.domains.prompts.service.resolve",
            lambda *a, **kw: None,
        )
        from app.domains.ai.gateway_client import _resolve_from_registry
        sys, meta = _resolve_from_registry("unknown_task")
        assert sys is None


# ── Self-Refine ───────────────────────────────────────────────────────


class TestSelfRefine:

    def test_should_not_refine_when_flag_disabled(self):
        try:
            from app.domains.feature_flags.service import feature_flags
            from app.domains.feature_flags.schemas import FlagUpdate
            feature_flags.set_flag(
                "ai.self_refine",
                FlagUpdate(enabled=False, percent=0),
                actor="test",
            )
        except Exception:
            pytest.skip("feature_flags missing")

        from app.domains.ai.self_refine import should_self_refine
        assert should_self_refine("security_audit", risk_level="critical") is False

    def test_should_refine_when_flag_on_and_critical(self, monkeypatch):
        try:
            from app.domains.feature_flags.service import feature_flags
            from app.domains.feature_flags.schemas import FlagUpdate
            feature_flags.set_flag(
                "ai.self_refine",
                FlagUpdate(enabled=True, percent=100),
                actor="test",
            )
        except Exception:
            pytest.skip("feature_flags missing")

        from app.domains.ai.self_refine import should_self_refine
        assert should_self_refine("security_audit", risk_level="critical") is True
        # Low risk security_audit -> False
        assert should_self_refine("security_audit", risk_level="low") is False
        # Chat asla
        assert should_self_refine("chat") is False
        # test_generation + financial -> True
        assert should_self_refine("test_generation", has_financial=True) is True
        # test_generation + medium risk + no financial -> False
        assert should_self_refine("test_generation", risk_level="medium") is False

    def test_refine_fallback_on_empty_initial(self):
        from app.domains.ai.self_refine import refine_response
        # Kisa cevap -> original'i dondur
        result = refine_response("security_audit", "soru", "kisa")
        assert result == "kisa"

    def test_refine_critique_fail_returns_original(self, monkeypatch):
        """Critique LLM hata verirse original donmeli."""
        from app.domains.ai import self_refine

        def _fail(*args, **kwargs):
            raise RuntimeError("gateway down")

        monkeypatch.setattr(self_refine, "gateway_complete", _fail)
        long_response = "x" * 100
        result = self_refine.refine_response(
            "security_audit", "soru uzun bir metin", long_response
        )
        assert result == long_response


# ── Fine-Tune Export ───────────────────────────────────────────────────


class TestFinetuneExport:

    def test_readiness_without_db_returns_unavailable(self, monkeypatch):
        from app.domains.ai import finetune_export

        def _fail():
            raise RuntimeError("no db")

        monkeypatch.setattr(
            "app.domains.ai.llm_trace._get_conn",
            _fail,
        )
        result = finetune_export.get_export_readiness()
        assert result.get("ready") is False

    def test_export_writes_jsonl_with_empty_data(self, monkeypatch, tmp_path):
        """DB yoksa bile dosya yaratilir (bos JSONL)."""
        from app.domains.ai import finetune_export

        def _fail():
            raise RuntimeError("no db")

        monkeypatch.setattr(
            "app.domains.ai.llm_trace._get_conn",
            _fail,
        )

        result = finetune_export.export_finetune_jsonl(
            output_dir=str(tmp_path),
            min_judge_score=9.0,
            include_few_shot=False,
        )
        assert result.total_pairs == 0
        assert result.from_judge == 0
        from pathlib import Path
        assert Path(result.path).exists()

    def test_export_jsonl_structure_has_messages(self, monkeypatch, tmp_path):
        """Olasi bir pair'in format'ini test et: messages list + role'ler."""
        from app.domains.ai import finetune_export

        # Mock: judge'dan 1 pair don
        monkeypatch.setattr(
            finetune_export,
            "_collect_from_judge",
            lambda *a, **kw: [{
                "messages": [
                    {"role": "system", "content": "s"},
                    {"role": "user", "content": "u"},
                    {"role": "assistant", "content": "a"},
                ],
                "_task_type": "test_generation",
                "_source": "judge",
                "_judge_overall": 9.5,
            }],
        )
        monkeypatch.setattr(
            finetune_export, "_collect_from_few_shot", lambda *a, **kw: []
        )

        result = finetune_export.export_finetune_jsonl(
            output_dir=str(tmp_path),
            include_few_shot=False,
        )
        assert result.total_pairs == 1
        # Dosyayi oku
        from pathlib import Path
        content = Path(result.path).read_text(encoding="utf-8").strip()
        parsed = json.loads(content)
        assert "messages" in parsed
        assert len(parsed["messages"]) == 3
        roles = [m["role"] for m in parsed["messages"]]
        assert roles == ["system", "user", "assistant"]
        # Internal fields JSONL'de olmamali
        assert "_task_type" not in parsed
        assert "_source" not in parsed
