"""Dalga 1 · yeni eval scorer/adapter unit testleri."""
from __future__ import annotations

import pytest

from app.domains.evals.adapters import get_adapter, list_adapters
from app.domains.evals.schemas import EvalCase
from app.domains.evals.scorers import get_scorer, list_scorers


# ── registry entegrasyonu ───────────────────────────────────────────────
class TestRegistries:
    def test_new_scorers_registered(self):
        names = set(list_scorers())
        for expected in {
            "python_ast_valid", "python_has_assert", "python_has_testid",
            "locator_exact", "locator_contains_any",
            "injection_blocked", "pii_redacted", "no_forbidden_phrase",
            "gateway_content_contains", "gateway_json_valid",
            "gateway_provider_allowed", "gateway_attempts_healthy",
            "gateway_latency_budget",
        }:
            assert expected in names, f"{expected} scorer registry'de yok"

    def test_new_adapters_registered(self):
        names = set(list_adapters())
        for expected in {
            "test_gen",
            "self_heal",
            "prompt_shield",
            "ai_gateway",
            "ai_gateway_live",
        }:
            assert expected in names, f"{expected} adapter registry'de yok"


# ── python_ast_valid ────────────────────────────────────────────────────
class TestPythonAstValid:
    def _case(self):
        return EvalCase(id="c1", inputs={}, expected={})

    def test_valid_code_passes(self):
        scorer = get_scorer("python_ast_valid")
        out = scorer.score(case=self._case(), actual={"code": "def foo():\n    return 1"})
        assert out.passed is True
        assert out.value == 1.0

    def test_syntax_error_fails(self):
        scorer = get_scorer("python_ast_valid")
        out = scorer.score(case=self._case(), actual={"code": "def foo(:\n    pass"})
        assert out.passed is False
        assert "syntax_error" in out.details

    def test_empty_code_fails(self):
        scorer = get_scorer("python_ast_valid")
        out = scorer.score(case=self._case(), actual={})
        assert out.passed is False


# ── python_has_assert ───────────────────────────────────────────────────
class TestPythonHasAssert:
    def _case(self):
        return EvalCase(id="c1", inputs={}, expected={})

    def test_bare_assert(self):
        out = get_scorer("python_has_assert").score(
            case=self._case(), actual={"code": "assert x == 1"}
        )
        assert out.passed is True

    def test_pytest_raises(self):
        out = get_scorer("python_has_assert").score(
            case=self._case(),
            actual={"code": "with pytest.raises(ValueError): foo()"},
        )
        assert out.passed is True

    def test_playwright_expect(self):
        out = get_scorer("python_has_assert").score(
            case=self._case(), actual={"code": "expect(page).to_have_url('/')"},
        )
        assert out.passed is True

    def test_no_assert(self):
        out = get_scorer("python_has_assert").score(
            case=self._case(), actual={"code": "x = 1 + 1\nprint(x)"},
        )
        assert out.passed is False


# ── locator_contains_any ────────────────────────────────────────────────
class TestLocatorContainsAny:
    def test_exact_in_list(self):
        case = EvalCase(
            id="h1", inputs={},
            expected={"acceptable_locators": ["[data-testid='btn']", "role=button"]},
        )
        out = get_scorer("locator_contains_any").score(
            case=case, actual={"new_locator": "[data-testid='btn']"},
        )
        assert out.passed is True

    def test_normalization(self):
        case = EvalCase(
            id="h1", inputs={},
            expected={"acceptable_locators": ["[data-testid='btn']"]},
        )
        # aynı locator, tırnak türü farklı + extra whitespace
        out = get_scorer("locator_contains_any").score(
            case=case, actual={"new_locator": '  [data-testid="btn"]  '},
        )
        assert out.passed is True

    def test_not_in_list(self):
        case = EvalCase(
            id="h1", inputs={},
            expected={"acceptable_locators": ["role=button"]},
        )
        out = get_scorer("locator_contains_any").score(
            case=case, actual={"new_locator": ".some-class"},
        )
        assert out.passed is False


# ── injection_blocked ──────────────────────────────────────────────────
class TestInjectionBlocked:
    def test_expected_block_and_detected(self):
        case = EvalCase(id="inj1", inputs={}, expected={"blocked": True})
        out = get_scorer("injection_blocked").score(
            case=case, actual={"blocked": True, "risk_score": 0.9},
        )
        assert out.passed is True

    def test_expected_block_but_not_detected_fails(self):
        case = EvalCase(id="inj1", inputs={}, expected={"blocked": True})
        out = get_scorer("injection_blocked").score(
            case=case, actual={"blocked": False, "risk_score": 0.1},
        )
        assert out.passed is False

    def test_clean_case_not_blocked(self):
        """Temiz case — blocked=False → pass (false positive önleme)."""
        case = EvalCase(id="clean1", inputs={}, expected={"blocked": False})
        out = get_scorer("injection_blocked").score(
            case=case, actual={"blocked": False, "risk_score": 0.05},
        )
        assert out.passed is True

    def test_pii_case_with_warnings_but_not_blocked(self):
        """PII maskelendi, warnings var ama blocked=False → pass."""
        case = EvalCase(id="pii1", inputs={}, expected={"blocked": False})
        out = get_scorer("injection_blocked").score(
            case=case, actual={
                "blocked": False, "risk_score": 0.35,
                "warnings": ["pii_masked"], "categories": ["pii_in_user_input"],
            },
        )
        assert out.passed is True


# ── pii_redacted ───────────────────────────────────────────────────────
class TestPiiRedacted:
    def test_clean_masked_output(self):
        case = EvalCase(id="pii1", inputs={}, expected={})
        out = get_scorer("pii_redacted").score(
            case=case,
            actual={"masked": "TC [TC_KIMLIK] IBAN [IBAN] mail [EMAIL]"},
        )
        assert out.passed is True

    def test_leaked_tckn_fails(self):
        case = EvalCase(id="pii1", inputs={}, expected={})
        out = get_scorer("pii_redacted").score(
            case=case, actual={"masked": "TC 12345678901"},
        )
        assert out.passed is False

    def test_leaked_email_fails(self):
        case = EvalCase(id="pii1", inputs={}, expected={})
        out = get_scorer("pii_redacted").score(
            case=case, actual={"masked": "mail: ali@bank.com"},
        )
        assert out.passed is False


# ── adapters: fixture mode ─────────────────────────────────────────────
class TestAdaptersFixtureMode:
    def test_test_gen_fixture_passthrough(self):
        adapter = get_adapter("test_gen")
        out = adapter.run({"_fixture": {"code": "def x(): pass", "framework": "pytest"}})
        assert out["code"] == "def x(): pass"

    def test_self_heal_fixture_passthrough(self):
        adapter = get_adapter("self_heal")
        out = adapter.run({"_fixture": {"new_locator": "[data-testid='x']", "confidence": 0.8}})
        assert out["new_locator"] == "[data-testid='x']"

    def test_prompt_shield_fixture_passthrough(self):
        adapter = get_adapter("prompt_shield")
        out = adapter.run({"_fixture": {"blocked": True, "risk_score": 0.9}})
        assert out["blocked"] is True
        assert out["risk_score"] == 0.9

    def test_ai_gateway_fixture_passthrough(self):
        adapter = get_adapter("ai_gateway")
        out = adapter.run({"_fixture": {"content": "ok", "provider_used": "ollama"}})
        assert out["content"] == "ok"
        assert out["provider_used"] == "ollama"

    def test_ai_gateway_live_requires_opt_in(self, monkeypatch):
        monkeypatch.delenv("EVAL_RUN_LLM", raising=False)
        adapter = get_adapter("ai_gateway_live")
        assert adapter.available() is False


# ── gateway contract scorers ───────────────────────────────────────────
class TestGatewayContractScorers:
    def test_content_contains_passes(self):
        case = EvalCase(
            id="gw1",
            inputs={},
            expected={"contains_any": ["hazır", "ready"]},
        )
        out = get_scorer("gateway_content_contains").score(
            case=case,
            actual={"content": "Neurex QA hazır."},
        )
        assert out.passed is True

    def test_json_valid_fails_invalid_json(self):
        case = EvalCase(id="gw-json", inputs={}, expected={"json_required": True})
        out = get_scorer("gateway_json_valid").score(
            case=case,
            actual={"content": "{not-json"},
        )
        assert out.passed is False

    def test_provider_allowed(self):
        case = EvalCase(
            id="gw-provider",
            inputs={},
            expected={"provider_allowed": ["ollama"]},
        )
        out = get_scorer("gateway_provider_allowed").score(
            case=case,
            actual={"provider_used": "ollama"},
        )
        assert out.passed is True

    def test_attempts_can_require_failed_before_success(self):
        case = EvalCase(
            id="gw-attempts",
            inputs={},
            expected={"min_attempts": 2, "require_failed_before_success": True},
        )
        out = get_scorer("gateway_attempts_healthy").score(
            case=case,
            actual={
                "attempts": [
                    {"provider": "vllm", "success": False},
                    {"provider": "ollama", "success": True},
                ]
            },
        )
        assert out.passed is True

    def test_latency_budget_fails_when_too_slow(self):
        case = EvalCase(
            id="gw-latency",
            inputs={},
            expected={"max_latency_ms": 100},
        )
        out = get_scorer("gateway_latency_budget").score(
            case=case,
            actual={"latency_ms": 250},
        )
        assert out.passed is False
