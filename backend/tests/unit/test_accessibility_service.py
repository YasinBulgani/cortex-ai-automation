"""
Accessibility service unit testleri — 14 test.

app.domains.accessibility.service facade'ını ve analyzer davranışlarını
(feature flag, boş violations, gateway mock, JSON parse) doğrular.
DB veya gerçek HTTP çağrısı yoktur; gateway_complete monkeypatch ile stub'lanır.
"""
from __future__ import annotations

import json
import pytest

try:
    from app.domains.accessibility.service import analyze_violations, analyzer_info
    from app.domains.accessibility.analyzer import (
        AccessibilityAnalyzer,
        _parse_json_array,
    )
    from app.domains.accessibility.schemas import (
        A11yImpact,
        A11yNode,
        A11yViolation,
        AnalyzeA11yRequest,
        AnalyzeA11yResponse,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="accessibility service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_violation(vid: str = "color-contrast", impact: str = "serious") -> A11yViolation:
    return A11yViolation(
        id=vid,
        impact=A11yImpact(impact),
        help="Elements must have sufficient color contrast",
        nodes=[A11yNode(html="<p>test</p>", target=["p"])],
    )


def _make_request(n: int = 1, url: str = "https://example.com") -> AnalyzeA11yRequest:
    return AnalyzeA11yRequest(
        violations=[_make_violation(f"v-{i}") for i in range(n)],
        url=url,
    )


def _valid_llm_response(violation_ids: list[str]) -> str:
    items = [
        {
            "violation_id": vid,
            "turkish_title": f"Başlık: {vid}",
            "turkish_explanation": "Açıklama.",
            "remediation": "Düzelt.",
            "code_example": None,
            "wcag_reference": "1.4.3",
        }
        for vid in violation_ids
    ]
    return json.dumps(items, ensure_ascii=False)


# ---------------------------------------------------------------------------
# _parse_json_array (pure helper)
# ---------------------------------------------------------------------------

class TestParseJsonArray:
    def test_plain_json_array(self):
        raw = '[{"a": 1}]'
        result = _parse_json_array(raw)
        assert result == [{"a": 1}]

    def test_markdown_fence_stripped(self):
        raw = "```json\n[{\"x\": 2}]\n```"
        result = _parse_json_array(raw)
        assert result == [{"x": 2}]

    def test_empty_string_returns_none(self):
        assert _parse_json_array("") is None

    def test_plain_string_returns_none(self):
        assert _parse_json_array("not json") is None

    def test_object_not_array_returns_none(self):
        assert _parse_json_array('{"key": "val"}') is None

    def test_array_embedded_in_prose(self):
        raw = 'Here is the result: [{"violation_id": "x"}] done.'
        result = _parse_json_array(raw)
        assert isinstance(result, list)
        assert result[0]["violation_id"] == "x"


# ---------------------------------------------------------------------------
# analyzer_info
# ---------------------------------------------------------------------------

class TestAnalyzerInfo:
    def test_returns_dict_with_required_keys(self):
        info = analyzer_info()
        assert isinstance(info, dict)
        for key in ("enabled", "total_calls", "last_error"):
            assert key in info

    def test_enabled_reflects_env(self, monkeypatch):
        monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "false")
        info = analyzer_info()
        assert info["enabled"] is False

    def test_enabled_true_when_flag_set(self, monkeypatch):
        monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
        info = analyzer_info()
        assert info["enabled"] is True


# ---------------------------------------------------------------------------
# analyze_violations — feature flag OFF (default)
# ---------------------------------------------------------------------------

class TestAnalyzeViolationsFlagOff:
    def test_flag_off_returns_ok_empty(self, monkeypatch):
        monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "false")
        req = _make_request(2)
        resp = analyze_violations(req)
        assert isinstance(resp, AnalyzeA11yResponse)
        assert resp.ok is True
        assert resp.remediations == []
        assert resp.error is None

    def test_flag_off_no_gateway_call(self, monkeypatch):
        """Gateway must not be called when feature flag is disabled."""
        monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "false")
        called = []

        def fake_gateway(**kwargs):
            called.append(kwargs)
            return "[]"

        monkeypatch.setattr(
            "app.domains.accessibility.analyzer.gateway_complete",
            fake_gateway,
            raising=False,
        )
        analyze_violations(_make_request(1))
        assert called == []


# ---------------------------------------------------------------------------
# analyze_violations — feature flag ON
# ---------------------------------------------------------------------------

class TestAnalyzeViolationsFlagOn:
    def _patch_gateway(self, monkeypatch, return_value: str):
        monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
        # The analyzer imports gateway_complete lazily inside analyze(); patch via sys.modules.
        import sys
        import importlib
        from unittest.mock import MagicMock
        gw_module_path = "app.domains.ai.gateway_client"
        if gw_module_path not in sys.modules:
            fake_mod = MagicMock()
            fake_mod.gateway_complete = lambda **kw: return_value
            sys.modules[gw_module_path] = fake_mod
            monkeypatch.setitem(sys.modules, gw_module_path, fake_mod)
        else:
            # Use monkeypatch.setattr so the change is properly undone after the test
            monkeypatch.setattr(sys.modules[gw_module_path], "gateway_complete", lambda **kw: return_value)

    def test_successful_analysis_returns_remediations(self, monkeypatch):
        self._patch_gateway(monkeypatch, _valid_llm_response(["v-0"]))
        req = _make_request(1)
        resp = analyze_violations(req)
        assert resp.ok is True
        assert len(resp.remediations) == 1
        assert resp.remediations[0].violation_id == "v-0"

    def test_gateway_runtime_error_returns_ok_false(self, monkeypatch):
        monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
        import sys
        from unittest.mock import MagicMock
        gw_module_path = "app.domains.ai.gateway_client"
        if gw_module_path not in sys.modules:
            fake_mod = MagicMock()
            fake_mod.gateway_complete = MagicMock(side_effect=RuntimeError("gateway down"))
            monkeypatch.setitem(sys.modules, gw_module_path, fake_mod)
        else:
            monkeypatch.setattr(sys.modules[gw_module_path], "gateway_complete", MagicMock(side_effect=RuntimeError("gateway down")))

        req = _make_request(1)
        resp = analyze_violations(req)
        assert resp.ok is False
        assert resp.error is not None
        assert "gateway" in resp.error.lower() or "erişilemedi" in resp.error.lower()

    def test_unparseable_llm_response_returns_ok_false(self, monkeypatch):
        self._patch_gateway(monkeypatch, "this is not JSON at all")
        req = _make_request(1)
        resp = analyze_violations(req)
        assert resp.ok is False
        assert resp.remediations == []

    def test_skipped_count_when_exceeds_max(self, monkeypatch):
        ids = [f"v-{i}" for i in range(5)]
        self._patch_gateway(monkeypatch, _valid_llm_response(ids[:3]))
        req = AnalyzeA11yRequest(
            violations=[_make_violation(f"v-{i}") for i in range(5)],
            max_violations=3,
        )
        resp = analyze_violations(req)
        assert resp.skipped_count == 2

    def test_unknown_violation_id_from_llm_ignored(self, monkeypatch):
        """LLM-fabricated violation_ids not in request must be filtered out."""
        self._patch_gateway(monkeypatch, _valid_llm_response(["totally-made-up-id"]))
        req = _make_request(1)
        resp = analyze_violations(req)
        assert resp.ok is True
        assert resp.remediations == []
