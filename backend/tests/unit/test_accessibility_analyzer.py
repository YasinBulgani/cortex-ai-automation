"""AccessibilityAnalyzer için unit testler.

gateway_complete tamamen monkeypatch'lenir — gerçek HTTP yok.
"""
from __future__ import annotations

import json

import pytest

from app.domains.accessibility.analyzer import AccessibilityAnalyzer
from app.domains.accessibility.schemas import (
    A11yImpact,
    A11yNode,
    A11yViolation,
    AnalyzeA11yRequest,
)


@pytest.fixture
def analyzer(monkeypatch: pytest.MonkeyPatch) -> AccessibilityAnalyzer:
    """Her test için temiz instance + temiz env."""
    for key in (
        "AI_ACCESSIBILITY_ENABLED",
        "AI_ACCESSIBILITY_MAX_VIOLATIONS",
    ):
        monkeypatch.delenv(key, raising=False)
    return AccessibilityAnalyzer()


def _violation(
    vid: str = "color-contrast",
    impact: A11yImpact = A11yImpact.serious,
    html: str = "<button class='primary'>Kaydet</button>",
) -> A11yViolation:
    return A11yViolation(
        id=vid,
        impact=impact,
        help="Elements must have sufficient color contrast",
        help_url="https://dequeuniversity.com/rules/axe/4.8/color-contrast",
        description="Ensures the contrast between foreground and background colors meets WCAG AA.",
        tags=["wcag2aa", "wcag143"],
        nodes=[
            A11yNode(
                html=html,
                target=["button.primary"],
                failure_summary="Background #FFF on foreground #DDD fails AA contrast.",
            )
        ],
    )


def _patch_gateway(
    monkeypatch: pytest.MonkeyPatch, *, return_value=None, raise_exc=None
) -> list[dict]:
    """gateway_complete'i mock'la; çağrı argümanlarını listeye logla."""
    calls: list[dict] = []

    def fake(
        *,
        task_type,
        user_message,
        system_message=None,
        temperature=0.5,
        max_tokens=4000,
        project_id=None,
        json_mode=None,
        model_override=None,
    ):
        calls.append(
            {
                "task_type": task_type,
                "user_message": user_message,
                "system_message": system_message,
                "temperature": temperature,
                "json_mode": json_mode,
            }
        )
        if raise_exc is not None:
            raise raise_exc
        return return_value

    monkeypatch.setattr(
        "app.domains.ai.gateway_client.gateway_complete", fake
    )
    return calls


# ── Feature flag ───────────────────────────────────────────────────────────


def test_disabled_returns_noop(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _patch_gateway(monkeypatch, return_value="[]")
    req = AnalyzeA11yRequest(violations=[_violation()])
    resp = analyzer.analyze(req)

    assert resp.ok is True
    assert resp.remediations == []
    assert resp.error is None
    # Flag kapalı → gateway hiç çağrılmamalı
    assert calls == []


def test_empty_violations_returns_ok_no_call(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    calls = _patch_gateway(monkeypatch, return_value="[]")
    # min_length=1 Pydantic validation engelliyor → doğrudan analyzer.analyze
    # tetiklemek için pydantic bypass ile çağırmaya gerek yok — schemas zaten
    # en az 1 violation istiyor. Bu testi request oluşturma değil analyzer
    # state'i üzerinden yap:
    req = AnalyzeA11yRequest.model_construct(
        violations=[], url=None, max_violations=10
    )
    resp = analyzer.analyze(req)

    assert resp.ok is True
    assert resp.remediations == []
    assert calls == []


# ── Happy path ─────────────────────────────────────────────────────────────


def test_success_returns_parsed_remediations(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    llm_response = json.dumps(
        [
            {
                "violation_id": "color-contrast",
                "turkish_title": "Düşük kontrast: okunabilirlik riski",
                "turkish_explanation": "Düşük görme yetisi olan kullanıcılar metni seçemeyebilir.",
                "remediation": "Yazı rengini #333'e çekin veya arkaplanı koyulaştırın.",
                "code_example": "<button style='color:#333;background:#fff'>Kaydet</button>",
                "wcag_reference": "1.4.3 Contrast (Minimum)",
            }
        ],
        ensure_ascii=False,
    )
    calls = _patch_gateway(monkeypatch, return_value=llm_response)

    req = AnalyzeA11yRequest(violations=[_violation()], url="https://ex.com/form")
    resp = analyzer.analyze(req)

    assert resp.ok is True
    assert len(resp.remediations) == 1
    rem = resp.remediations[0]
    assert rem.violation_id == "color-contrast"
    assert "kontrast" in rem.turkish_title.lower()
    assert rem.wcag_reference and "1.4.3" in rem.wcag_reference
    assert resp.skipped_count == 0
    assert resp.latency_ms is not None and resp.latency_ms >= 0

    # Gateway çağrısı doğru parametrelerle
    assert len(calls) == 1
    assert calls[0]["task_type"] == "accessibility_analysis"
    assert calls[0]["json_mode"] is True
    assert calls[0]["temperature"] == 0.2
    payload = json.loads(calls[0]["user_message"])
    assert payload["url"] == "https://ex.com/form"
    assert len(payload["violations"]) == 1
    assert payload["violations"][0]["id"] == "color-contrast"


def test_max_violations_trims_and_reports_skipped(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    violations = [
        _violation(vid=f"rule-{i}", html=f"<div>case-{i}</div>") for i in range(15)
    ]
    # Model sadece trimlenmiş olanlara yanıt veriyor
    llm_response = json.dumps(
        [
            {
                "violation_id": f"rule-{i}",
                "turkish_title": f"Hata {i}",
                "turkish_explanation": "açıklama",
                "remediation": "düzeltme",
                "code_example": None,
                "wcag_reference": None,
            }
            for i in range(5)
        ]
    )
    calls = _patch_gateway(monkeypatch, return_value=llm_response)

    req = AnalyzeA11yRequest(violations=violations, max_violations=5)
    resp = analyzer.analyze(req)

    assert resp.ok is True
    assert resp.skipped_count == 10
    assert len(resp.remediations) == 5
    payload = json.loads(calls[0]["user_message"])
    assert len(payload["violations"]) == 5


def test_html_truncated_in_gateway_payload(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM context window'u korumak için HTML 500 char'da kesilmeli."""
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    long_html = "<div>" + ("x" * 2000) + "</div>"
    violations = [_violation(html=long_html)]
    calls = _patch_gateway(monkeypatch, return_value="[]")

    analyzer.analyze(AnalyzeA11yRequest(violations=violations))
    sent = json.loads(calls[0]["user_message"])["violations"][0]
    assert sent["node_html"] is not None
    assert len(sent["node_html"]) <= 501   # 500 + ellipsis
    assert sent["node_html"].endswith("…")


# ── Error yolları ──────────────────────────────────────────────────────────


def test_gateway_runtime_error_returns_ok_false(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    _patch_gateway(
        monkeypatch, raise_exc=RuntimeError("AI Gateway'e bağlanılamadı")
    )

    resp = analyzer.analyze(AnalyzeA11yRequest(violations=[_violation()]))
    assert resp.ok is False
    assert resp.remediations == []
    assert resp.error is not None
    assert "bağlan" in resp.error.lower() or "gateway" in resp.error.lower()


def test_llm_returns_non_json_returns_parse_error(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    _patch_gateway(monkeypatch, return_value="Merhaba, JSON vermedim.")

    resp = analyzer.analyze(AnalyzeA11yRequest(violations=[_violation()]))
    assert resp.ok is False
    assert resp.remediations == []
    assert resp.error and "parse" in resp.error.lower()


def test_llm_returns_object_instead_of_array_is_rejected(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Array değil, object dönerse kabul etmeyiz."""
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    _patch_gateway(monkeypatch, return_value='{"violation_id": "x"}')

    resp = analyzer.analyze(AnalyzeA11yRequest(violations=[_violation()]))
    assert resp.ok is False
    assert "parse" in (resp.error or "").lower()


def test_llm_returns_markdown_fenced_json(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bazı modeller ```json fence ile sarar — parser bunu temizlemeli."""
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    fenced = (
        "```json\n"
        + json.dumps(
            [
                {
                    "violation_id": "color-contrast",
                    "turkish_title": "x",
                    "turkish_explanation": "y",
                    "remediation": "z",
                    "code_example": None,
                    "wcag_reference": None,
                }
            ]
        )
        + "\n```"
    )
    _patch_gateway(monkeypatch, return_value=fenced)

    resp = analyzer.analyze(AnalyzeA11yRequest(violations=[_violation()]))
    assert resp.ok is True
    assert len(resp.remediations) == 1


def test_llm_hallucinates_unknown_violation_id_filtered(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Model istenmeyen bir violation için remediation dönerse atlanmalı."""
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    llm_response = json.dumps(
        [
            {
                "violation_id": "color-contrast",
                "turkish_title": "gerçek",
                "turkish_explanation": "...",
                "remediation": "...",
                "code_example": None,
                "wcag_reference": None,
            },
            {
                "violation_id": "image-alt",   # UYDURMA — req'de yoktu
                "turkish_title": "uydurma",
                "turkish_explanation": "...",
                "remediation": "...",
                "code_example": None,
                "wcag_reference": None,
            },
        ]
    )
    _patch_gateway(monkeypatch, return_value=llm_response)

    resp = analyzer.analyze(
        AnalyzeA11yRequest(violations=[_violation(vid="color-contrast")])
    )
    assert resp.ok is True
    assert len(resp.remediations) == 1
    assert resp.remediations[0].violation_id == "color-contrast"


def test_llm_missing_required_field_is_skipped(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Remediation'ı şemaya uymayan item atlanmalı ama kalan geçmeli."""
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    llm_response = json.dumps(
        [
            {"violation_id": "color-contrast"},  # zorunlu alanlar eksik
            {
                "violation_id": "color-contrast",
                "turkish_title": "tam kayıt",
                "turkish_explanation": "x",
                "remediation": "y",
                "code_example": None,
                "wcag_reference": None,
            },
        ]
    )
    _patch_gateway(monkeypatch, return_value=llm_response)

    resp = analyzer.analyze(
        AnalyzeA11yRequest(violations=[_violation(vid="color-contrast")])
    )
    assert resp.ok is True
    # Eksik alanlı item düştü, tam kayıt geçti
    assert len(resp.remediations) == 1
    assert resp.remediations[0].turkish_title == "tam kayıt"


# ── info() telemetri ───────────────────────────────────────────────────────


def test_info_counts_successful_calls(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    _patch_gateway(monkeypatch, return_value="[]")

    for _ in range(3):
        analyzer.analyze(AnalyzeA11yRequest(violations=[_violation()]))

    info = analyzer.info()
    assert info["enabled"] is True
    assert info["total_calls"] == 3
    assert info["last_error"] is None


def test_info_records_last_error(
    analyzer: AccessibilityAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ACCESSIBILITY_ENABLED", "true")
    _patch_gateway(
        monkeypatch, raise_exc=RuntimeError("AI Gateway hatası: 503")
    )

    analyzer.analyze(AnalyzeA11yRequest(violations=[_violation()]))
    info = analyzer.info()
    assert info["last_error"] is not None
    assert "503" in info["last_error"] or "gateway" in info["last_error"].lower()
