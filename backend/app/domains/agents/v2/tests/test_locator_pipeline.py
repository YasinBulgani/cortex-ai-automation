"""Locator pipeline — 5 katman testleri."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from app.domains.agents.v2.schemas.locator import (
    ElementCard,
    LocatorCandidate,
    LocatorStrategy,
    LocatorSuggestion,
)
from app.domains.agents.v2.tools.locator import (
    LocatorPipeline,
    score_locator,
    aggregate_score,
    escape_css,
    escape_text,
)
from app.domains.agents.v2.tools.locator.extraction import extract_from_html
from app.domains.agents.v2.tools.locator.generation import (
    strategy_testid,
    strategy_role_name,
    strategy_text,
    strategy_css_semantic,
    strategy_id_fallback,
    generate_locators_for_element,
)
from app.domains.agents.v2.tools.locator.registry import (
    LocatorRegistry,
    url_pattern,
    get_registry,
)


HTML_LOGIN = """
<html><body>
  <form id="login-form">
    <input type="email" name="email" data-testid="login-email" placeholder="E-posta"/>
    <input type="password" name="password" data-testid="login-pass"/>
    <button type="submit" class="btn btn-primary" data-testid="login-submit">Giriş Yap</button>
    <a href="/forgot">Şifremi unuttum</a>
  </form>
</body></html>
"""


HTML_NO_TESTID = """
<html><body>
  <form class="search-form">
    <input type="text" class="search-input" placeholder="Ara..."/>
    <button class="btn primary">Ara</button>
  </form>
</body></html>
"""


# ═══════════════════════════════════════════════════════════════════════════
# Extraction
# ═══════════════════════════════════════════════════════════════════════════


class TestExtraction:
    def test_extracts_login_form_elements(self):
        cards = extract_from_html(HTML_LOGIN)
        # 2 input + 1 button + 1 link = 4
        assert len(cards) >= 4
        # testid'ler korunmuş
        testids = [c.testid for c in cards if c.testid]
        assert "login-email" in testids
        assert "login-pass" in testids
        assert "login-submit" in testids

    def test_preserves_parent_context(self):
        cards = extract_from_html(HTML_LOGIN)
        form_children = [c for c in cards if c.parent_context and "form" in c.parent_context]
        assert len(form_children) >= 3

    def test_no_testid_still_extracts(self):
        cards = extract_from_html(HTML_NO_TESTID)
        assert len(cards) >= 2
        # visible_text "Ara" olan button var
        buttons = [c for c in cards if c.tag == "button"]
        assert any(b.visible_text == "Ara" for b in buttons)

    def test_fingerprint_stable(self):
        cards1 = extract_from_html(HTML_LOGIN)
        cards2 = extract_from_html(HTML_LOGIN)
        fps1 = sorted(c.fingerprint for c in cards1)
        fps2 = sorted(c.fingerprint for c in cards2)
        assert fps1 == fps2


# ═══════════════════════════════════════════════════════════════════════════
# Generation strategies
# ═══════════════════════════════════════════════════════════════════════════


class TestStrategies:
    def test_strategy_testid(self):
        el = ElementCard(idx=0, tag="button", testid="login-submit", fingerprint="x")
        c = strategy_testid(el)
        assert c is not None
        assert c.strategy == LocatorStrategy.TESTID
        assert c.selector == '[data-testid="login-submit"]'
        assert 'page.getByTestId' in c.playwright_expr

    def test_strategy_testid_returns_none_without_testid(self):
        el = ElementCard(idx=0, tag="button", fingerprint="x")
        assert strategy_testid(el) is None

    def test_strategy_role_name(self):
        el = ElementCard(
            idx=0, tag="button", role="button", visible_text="Giriş Yap",
            fingerprint="x",
        )
        c = strategy_role_name(el)
        assert c is not None
        assert c.strategy == LocatorStrategy.ROLE_NAME
        assert "role=button" in c.selector
        assert "Giriş Yap" in c.selector

    def test_strategy_text(self):
        el = ElementCard(idx=0, tag="button", visible_text="Ara", fingerprint="x")
        c = strategy_text(el)
        assert c is not None
        assert c.strategy == LocatorStrategy.TEXT
        assert "Ara" in c.selector

    def test_strategy_text_skip_too_short(self):
        el = ElementCard(idx=0, tag="button", visible_text="X", fingerprint="x")
        assert strategy_text(el) is None

    def test_strategy_css_semantic(self):
        el = ElementCard(
            idx=0, tag="button",
            class_list=["btn", "primary"],
            parent_context="form#login",
            fingerprint="x",
        )
        c = strategy_css_semantic(el)
        assert c is not None
        assert "button" in c.selector
        assert "btn" in c.selector

    def test_strategy_id_fallback(self):
        el = ElementCard(
            idx=0, tag="button", element_id="submit-btn", fingerprint="x"
        )
        c = strategy_id_fallback(el)
        assert c is not None
        assert "#submit-btn" in c.selector

    def test_strategy_id_skip_hash_looking(self):
        el = ElementCard(
            idx=0, tag="button", element_id="random-a3f9c8b2de", fingerprint="x"
        )
        assert strategy_id_fallback(el) is None


# ═══════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════


class TestScoring:
    def test_unverified_candidate_neutral_score(self):
        c = LocatorCandidate(
            strategy=LocatorStrategy.TESTID,
            selector="[data-testid=x]",
            semantic_strength=1.0,
            count=-1,
        )
        score = score_locator(c)
        # Uniqueness 0.5 (unverified) × 0.4 + semantic 1.0 × 0.3 + temporal 0.5 × 0.3
        # = 0.2 + 0.3 + 0.15 = 0.65
        assert 0.6 <= score <= 0.7

    def test_unique_high_semantic_scores_high(self):
        c = LocatorCandidate(
            strategy=LocatorStrategy.TESTID,
            selector="[data-testid=x]",
            semantic_strength=1.0,
            count=1,
        )
        score = score_locator(c, history_success_rate=0.95)
        assert score >= 0.95

    def test_not_found_scores_zero(self):
        c = LocatorCandidate(
            strategy=LocatorStrategy.TESTID,
            selector="[data-testid=x]",
            semantic_strength=1.0,
            count=0,
        )
        score = score_locator(c)
        # Uniqueness = 0 → 0.3 (semantic) + 0.15 (temporal) = 0.45
        assert score < 0.5

    def test_aggregate_picks_best(self):
        testid_c = LocatorCandidate(
            strategy=LocatorStrategy.TESTID,
            selector="[data-testid=x]",
            semantic_strength=1.0,
            count=1,
            stability_score=0.95,
        )
        text_c = LocatorCandidate(
            strategy=LocatorStrategy.TEXT,
            selector='text="Ok"',
            semantic_strength=0.75,
            count=1,
            stability_score=0.72,
        )
        primary, fallbacks = aggregate_score([testid_c, text_c])
        assert primary is testid_c
        assert len(fallbacks) == 1
        assert fallbacks[0] is text_c


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline offline mode
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_offline_generates_suggestions():
    cards = extract_from_html(HTML_LOGIN)
    pipeline = LocatorPipeline(tenant_id="t1", project_id="p1", registry=LocatorRegistry())
    suggestions, stats = await pipeline.run_offline(cards, url="/login")

    assert stats.elements_found == len(cards)
    assert stats.suggestions_created > 0
    assert len(suggestions) >= 3  # at least email/pass/submit
    # Submit button için testid strateji tercih
    submit_suggestions = [s for s in suggestions if "submit" in s.primary_selector.lower()]
    assert any(
        s.primary_strategy == LocatorStrategy.TESTID
        for s in submit_suggestions
    )


# ═══════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════


class TestRegistry:
    def test_put_and_get(self):
        reg = LocatorRegistry()
        s = LocatorSuggestion(
            element_id="el_1",
            element_description="Giriş",
            primary_strategy=LocatorStrategy.TESTID,
            primary_selector='[data-testid="x"]',
        )
        reg.put(tenant_id="t", project_id="p", url_pattern="/login", suggestion=s)
        e = reg.get(tenant_id="t", project_id="p", url_pattern="/login", fingerprint="el_1")
        assert e is not None
        assert e.suggestion.primary_selector == '[data-testid="x"]'

    def test_version_bump_on_selector_change(self):
        reg = LocatorRegistry()
        s1 = LocatorSuggestion(
            element_id="el_1",
            element_description="Giriş",
            primary_strategy=LocatorStrategy.TESTID,
            primary_selector='[data-testid="old"]',
        )
        reg.put(tenant_id="t", project_id="p", url_pattern="/login", suggestion=s1)
        s2 = LocatorSuggestion(
            element_id="el_1",
            element_description="Giriş",
            primary_strategy=LocatorStrategy.TESTID,
            primary_selector='[data-testid="new"]',
        )
        reg.put(tenant_id="t", project_id="p", url_pattern="/login", suggestion=s2)
        e = reg.get(tenant_id="t", project_id="p", url_pattern="/login", fingerprint="el_1")
        assert e.version == 2

    def test_success_rate_updates(self):
        reg = LocatorRegistry()
        s = LocatorSuggestion(
            element_id="el_1",
            element_description="x",
            primary_strategy=LocatorStrategy.TESTID,
            primary_selector='[data-testid="x"]',
        )
        reg.put(tenant_id="t", project_id="p", url_pattern="/login", suggestion=s)
        for _ in range(4):
            reg.record_verify(tenant_id="t", project_id="p", url_pattern="/login",
                              fingerprint="el_1", success=True)
        reg.record_verify(tenant_id="t", project_id="p", url_pattern="/login",
                          fingerprint="el_1", success=False)
        e = reg.get(tenant_id="t", project_id="p", url_pattern="/login", fingerprint="el_1")
        assert e.success_rate() == pytest.approx(4 / 5)

    def test_url_pattern_normalization(self):
        assert url_pattern("/p/123/runs/456") == "/p/:id/runs/:id"
        # Gerçek UUID v4 formatı: 8-4-4-4-12
        assert url_pattern("/p/12345678-abcd-4ef0-9abc-def012345678/runs") == "/p/:uuid/runs"
        assert url_pattern("https://example.com/login") == "/login"


# ═══════════════════════════════════════════════════════════════════════════
# Escape helpers
# ═══════════════════════════════════════════════════════════════════════════


def test_escape_css_escapes_quote():
    assert escape_css('say "hi"') == 'say \\"hi\\"'


def test_escape_text_strips_newlines():
    assert "\n" not in escape_text("a\nb")
