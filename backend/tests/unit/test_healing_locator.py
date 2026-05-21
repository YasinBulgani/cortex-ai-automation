"""LocatorHealer unit testleri — JSON parse, güvenlik filtresi, sıralama."""
from __future__ import annotations

import json
from typing import List

import pytest

from app.domains.coverup.healing.locator_healer import LocatorHealer
from app.domains.coverup.healing.schemas import FailureEvent


def _event(
    *,
    dom: str = "<button data-testid='submit'>Gönder</button>",
    locator: str = ".submit-btn",
) -> FailureEvent:
    return FailureEvent(
        run_id="r1",
        test_file_path="tests/login.spec.ts",
        locator=locator,
        dom_snapshot=dom,
        error_message="Timeout waiting for locator('.submit-btn')",
    )


def _llm_json(payload: dict) -> str:
    return json.dumps(payload)


def _fake_llm(response_text: str):
    calls: list = []

    def _call(system_prompt: str, user_prompt: str) -> str:
        calls.append((system_prompt, user_prompt))
        return response_text

    return _call, calls


# ── Happy path ───────────────────────────────────────────────────────────


def test_propose_parses_json_and_sorts_by_confidence() -> None:
    resp = _llm_json(
        {
            "proposals": [
                {"new_locator": "[data-testid='submit']", "new_locator_kind": "test-id", "confidence": 0.92, "rationale": "Stabil"},
                {"new_locator": "button:has-text('Gönder')", "new_locator_kind": "text", "confidence": 0.65},
                {"new_locator": "xpath=//button[@class='s']", "new_locator_kind": "xpath", "confidence": 0.40},
            ]
        }
    )
    call, _ = _fake_llm(resp)
    h = LocatorHealer(call_llm=call)
    out = h.propose(_event())
    assert [p.confidence for p in out] == [0.92, 0.65, 0.40]
    assert out[0].new_locator == "[data-testid='submit']"
    assert out[0].new_locator_kind == "test-id"


def test_propose_tolerates_markdown_fences() -> None:
    body = json.dumps({"proposals": [{"new_locator": "role=button", "new_locator_kind": "role", "confidence": 0.8}]})
    resp = f"```json\n{body}\n```"
    call, _ = _fake_llm(resp)
    out = LocatorHealer(call_llm=call).propose(_event())
    assert len(out) == 1
    assert out[0].new_locator == "role=button"


def test_propose_truncates_to_three() -> None:
    props = [
        {"new_locator": f"#id-{i}", "confidence": 0.5 + i * 0.05}
        for i in range(6)
    ]
    call, _ = _fake_llm(_llm_json({"proposals": props}))
    out = LocatorHealer(call_llm=call).propose(_event())
    assert len(out) == 3


# ── Safety filter ────────────────────────────────────────────────────────


def test_propose_rejects_javascript_href() -> None:
    resp = _llm_json(
        {
            "proposals": [
                {"new_locator": "javascript:alert(1)", "confidence": 0.9},
                {"new_locator": "[data-testid='x']", "confidence": 0.7},
            ]
        }
    )
    call, _ = _fake_llm(resp)
    out = LocatorHealer(call_llm=call).propose(_event())
    assert len(out) == 1
    assert out[0].new_locator == "[data-testid='x']"


def test_propose_rejects_event_handler_injection() -> None:
    resp = _llm_json(
        {
            "proposals": [
                {"new_locator": "img[onerror=fetch('/steal')]", "confidence": 0.95},
                {"new_locator": "button[aria-label='Gönder']", "confidence": 0.6},
            ]
        }
    )
    call, _ = _fake_llm(resp)
    out = LocatorHealer(call_llm=call).propose(_event())
    assert len(out) == 1
    assert "onerror" not in out[0].new_locator


def test_propose_clamps_confidence() -> None:
    resp = _llm_json(
        {
            "proposals": [
                {"new_locator": "a", "confidence": 1.5},
                {"new_locator": "b", "confidence": -0.2},
            ]
        }
    )
    call, _ = _fake_llm(resp)
    out = LocatorHealer(call_llm=call).propose(_event())
    conf = sorted([p.confidence for p in out])
    assert conf == [0.0, 1.0]


# ── Degraded paths ───────────────────────────────────────────────────────


def test_propose_no_llm_returns_empty() -> None:
    out = LocatorHealer().propose(_event())
    assert out == []


def test_propose_empty_snapshot_returns_empty() -> None:
    call, _ = _fake_llm(_llm_json({"proposals": [{"new_locator": "x", "confidence": 0.9}]}))
    out = LocatorHealer(call_llm=call).propose(_event(dom=""))
    assert out == []


def test_propose_invalid_json_returns_empty() -> None:
    call, _ = _fake_llm("bu JSON değil just prose")
    out = LocatorHealer(call_llm=call).propose(_event())
    assert out == []


def test_propose_wrong_shape_returns_empty() -> None:
    call, _ = _fake_llm(_llm_json({"wrong": "shape"}))
    assert LocatorHealer(call_llm=call).propose(_event()) == []


def test_propose_llm_exception_returns_empty() -> None:
    def _raises(s: str, u: str) -> str:
        raise RuntimeError("network down")

    out = LocatorHealer(call_llm=_raises).propose(_event())
    assert out == []


def test_prompt_includes_locator_and_snapshot() -> None:
    call, calls = _fake_llm(_llm_json({"proposals": []}))
    LocatorHealer(call_llm=call).propose(
        _event(dom="<div role='button'>Kaydet</div>", locator=".save-btn")
    )
    assert calls, "LLM çağrılmadı"
    system, user = calls[0]
    assert "Playwright" in system or "playwright" in system.lower()
    assert ".save-btn" in user
    assert "Kaydet" in user
