"""Router learning + tool use + review queue + adversarial eval unit testleri."""
from __future__ import annotations

import pytest


# ── Router Learning ───────────────────────────────────────────────────


class TestRouterLearning:

    def test_compute_composite_favors_success(self):
        from app.domains.ai.router_learning import RoutingStats, _compute_composite

        good = RoutingStats(task_type="t", model="m1", success_rate=0.95, avg_cost_usd=0.001, avg_latency_ms=500)
        bad = RoutingStats(task_type="t", model="m2", success_rate=0.65, avg_cost_usd=0.001, avg_latency_ms=500)
        assert _compute_composite(good) > _compute_composite(bad)

    def test_compute_composite_penalizes_cost(self):
        from app.domains.ai.router_learning import RoutingStats, _compute_composite

        cheap = RoutingStats(task_type="t", model="m1", success_rate=0.9, avg_cost_usd=0.0001)
        expensive = RoutingStats(task_type="t", model="m2", success_rate=0.9, avg_cost_usd=0.01)
        assert _compute_composite(cheap) > _compute_composite(expensive)

    def test_compute_composite_penalizes_latency(self):
        from app.domains.ai.router_learning import RoutingStats, _compute_composite

        fast = RoutingStats(task_type="t", model="m1", success_rate=0.9, avg_latency_ms=500)
        slow = RoutingStats(task_type="t", model="m2", success_rate=0.9, avg_latency_ms=10_000)
        assert _compute_composite(fast) > _compute_composite(slow)

    def test_judge_avg_boosts_score(self):
        from app.domains.ai.router_learning import RoutingStats, _compute_composite

        with_judge = RoutingStats(
            task_type="t", model="m1", success_rate=0.9,
            judge_avg=9.0, judge_count=50, avg_latency_ms=500,
        )
        no_judge = RoutingStats(
            task_type="t", model="m2", success_rate=0.9,
            judge_avg=None, avg_latency_ms=500,
        )
        # judge=9 varsa (9/10=0.9) success=0.9 ile aynı seviyede → fark minimal
        # Ama judge dahilken W_JUDGE var, no_judge'de fallback success_rate kullanılıyor
        # Ikisi yaklaşık aynı olmalı (fallback = success_rate)
        diff = abs(_compute_composite(with_judge) - _compute_composite(no_judge))
        assert diff < 0.05

    def test_aggregate_stats_no_db_returns_empty(self, monkeypatch):
        from app.domains.ai import router_learning

        def _fail():
            raise RuntimeError("no db")

        monkeypatch.setattr("app.domains.ai.llm_trace._get_conn", _fail)
        result = router_learning.aggregate_stats(days=7)
        assert result == []

    def test_get_learned_preference_flag_off_returns_none(self, feature_flags):
        """Flag kapalı → preference yok."""
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.routing.learned",
            FlagUpdate(enabled=False, percent=0),
            actor="test",
        )
        from app.domains.ai.router_learning import get_learned_preference
        assert get_learned_preference("test_generation") is None


# ── Tool Use / Function Calling ───────────────────────────────────────


class TestTools:

    def test_list_tools_has_expected(self):
        from app.domains.ai.tools import tool_names

        names = tool_names()
        assert "get_project_stats" in names
        assert "get_recent_failures" in names
        assert "get_coverage_gaps" in names
        assert "get_scenario_by_id" in names
        assert "list_scenarios" in names

    def test_openai_tools_payload_format(self):
        from app.domains.ai.tools import openai_tools_payload

        payload = openai_tools_payload()
        assert len(payload) >= 5
        for entry in payload:
            assert entry["type"] == "function"
            assert "function" in entry
            fn = entry["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn.get("strict") is True

    def test_anthropic_tools_payload_format(self):
        from app.domains.ai.tools import anthropic_tools_payload

        payload = anthropic_tools_payload()
        assert len(payload) >= 5
        for entry in payload:
            assert "name" in entry
            assert "description" in entry
            assert "input_schema" in entry

    def test_execute_unknown_tool(self):
        from app.domains.ai.tools import execute_tool

        result = execute_tool("nonexistent_tool_xyz", {})
        assert result["ok"] is False
        assert "unknown_tool" in result["error"]

    def test_execute_disabled_tool_blocks(self, feature_flags):
        """Flag kapalı → tools_disabled_by_flag."""
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.tools",
            FlagUpdate(enabled=False, percent=0),
            actor="test",
        )
        from app.domains.ai.tools import execute_tool

        result = execute_tool("get_project_stats", {"project_id": "abc"})
        assert result["ok"] is False
        assert "tools_disabled" in result["error"]

    def test_execute_validation_error(self, feature_flags):
        """Flag açık ama parametre eksik → validation_error."""
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.tools",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )
        from app.domains.ai.tools import execute_tool

        # project_id zorunlu, yok -> validation_error
        result = execute_tool("get_project_stats", {})
        assert result["ok"] is False
        assert result["error"] == "validation_error"


# ── Review Queue ──────────────────────────────────────────────────────


class TestReviewQueue:

    def test_extract_confidence_from_tag(self):
        from app.domains.ai.review_queue import extract_confidence

        assert extract_confidence("Cevap <confidence>0.85</confidence> burada") == 0.85
        assert extract_confidence("<CONFIDENCE>0.5</CONFIDENCE>") == 0.5

    def test_extract_confidence_from_json(self):
        from app.domains.ai.review_queue import extract_confidence

        assert extract_confidence('{"confidence": 0.9, "answer": "..."}') == 0.9

    def test_extract_confidence_from_keyvalue(self):
        from app.domains.ai.review_queue import extract_confidence

        assert extract_confidence("confidence: 0.4") == 0.4
        assert extract_confidence("guven=0.7") == 0.7

    def test_extract_confidence_none(self):
        from app.domains.ai.review_queue import extract_confidence

        assert extract_confidence("plain text with no score") is None
        assert extract_confidence("") is None

    def test_extract_confidence_clips_out_of_range(self):
        from app.domains.ai.review_queue import extract_confidence

        # Pattern sadece 0/0.X/1.X ile uyuştuğu için 2.5 match etmez -> None
        assert extract_confidence('"confidence": 2.5') is None

    def test_should_queue_flag_off(self, feature_flags):
        """Flag kapalı → asla queue'ya atmaz."""
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.review.queue",
            FlagUpdate(enabled=False, percent=0),
            actor="test",
        )
        from app.domains.ai.review_queue import should_queue_for_review
        queue, reason, _ = should_queue_for_review("security_audit", "...")
        assert queue is False
        assert reason == "flag_disabled"

    def test_should_queue_security_audit_always(self, feature_flags):
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.review.queue",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )
        from app.domains.ai.review_queue import should_queue_for_review
        queue, reason, _ = should_queue_for_review("security_audit", "yuksek kalite cevap")
        assert queue is True
        assert "security_audit" in reason

    def test_should_queue_low_confidence(self, feature_flags):
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.review.queue",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )
        from app.domains.ai.review_queue import should_queue_for_review
        queue, reason, conf = should_queue_for_review(
            "test_generation",
            "Cevap <confidence>0.3</confidence>"
        )
        # 0.3 < test_generation threshold 0.6
        assert queue is True
        assert "low_confidence" in reason
        assert conf == 0.3

    def test_should_queue_high_confidence_passes(self, feature_flags):
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.review.queue",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )
        from app.domains.ai.review_queue import should_queue_for_review
        queue, _, _ = should_queue_for_review(
            "test_generation",
            "Cevap <confidence>0.9</confidence>"
        )
        assert queue is False

    def test_should_queue_low_judge_score(self, feature_flags):
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.review.queue",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )
        from app.domains.ai.review_queue import should_queue_for_review
        queue, reason, _ = should_queue_for_review(
            "chat",
            "Cevap burada",
            judge_overall=4.5,
        )
        assert queue is True
        assert "low_judge" in reason


# ── Adversarial Eval Properties ───────────────────────────────────────


class TestAdversarialProperties:

    def test_no_sql_exec_passes_for_clean_text(self):
        from app.domains.ai.eval_suite import _evaluate_properties
        props = [{"type": "no_sql_exec"}]
        results = _evaluate_properties("Basarili cevap, hic SQL yok", props)
        assert results[0].passed is True

    def test_no_sql_exec_fails_for_drop(self):
        from app.domains.ai.eval_suite import _evaluate_properties
        props = [{"type": "no_sql_exec"}]
        results = _evaluate_properties("DROP TABLE users ile devam", props)
        assert results[0].passed is False

    def test_no_system_leak_catches_echo(self):
        from app.domains.ai.eval_suite import _evaluate_properties
        props = [{"type": "no_system_leak"}]
        results = _evaluate_properties("My instructions are to be helpful", props)
        assert results[0].passed is False

    def test_no_pii_leak(self):
        from app.domains.ai.eval_suite import _evaluate_properties
        props = [{"type": "no_pii_leak", "value": "4111111111111111"}]
        clean = _evaluate_properties("Cevap guvenli", props)
        assert clean[0].passed is True
        leaked = _evaluate_properties("Kart 4111111111111111 yaziliyor", props)
        assert leaked[0].passed is False

    def test_output_refused_detects_refusal(self):
        from app.domains.ai.eval_suite import _evaluate_properties
        props = [{"type": "output_refused"}]
        refused = _evaluate_properties("Sorry, I cannot help with that.", props)
        assert refused[0].passed is True
        not_refused = _evaluate_properties("Here is the answer you wanted.", props)
        assert not_refused[0].passed is False

    def test_adversarial_suite_loads(self):
        from app.domains.ai.eval_suite import _load_suite, _ADVERSARIAL_SUITE_PATH
        suite = _load_suite(_ADVERSARIAL_SUITE_PATH)
        assert suite.get("suite") == "adversarial_v1"
        assert len(suite.get("prompts", [])) >= 10
