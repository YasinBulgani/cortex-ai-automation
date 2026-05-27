"""Unit tests for app.domains.playwright_mcp.schemas — Pydantic models.

Tests are fully self-contained: no DB, no HTTP, no browser.
Covers all 18 schema classes with defaults, validation, and instantiation.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.playwright_mcp.schemas import (
        BrowserSessionCreate,
        BrowserSessionInfo,
        NavigateRequest,
        NavigateResponse,
        SelectorValidateRequest,
        SelectorResult,
        SelectorValidateResponse,
        DOMSnapshotRequest,
        DOMNode,
        DOMSnapshotResponse,
        ScreenshotRequest,
        ScreenshotResponse,
        ActionRequest,
        ActionResponse,
        SelectorSuggestRequest,
        SelectorSuggestResponse,
        HealVerifyRequest,
        HealVerifyResponse,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="playwright_mcp.schemas import failed")


# ---------------------------------------------------------------------------
# BrowserSessionCreate
# ---------------------------------------------------------------------------

class TestBrowserSessionCreate:
    def test_defaults(self):
        req = BrowserSessionCreate()
        assert req.headless is True
        assert req.viewport_width == 1280
        assert req.viewport_height == 720
        assert req.locale == "tr-TR"
        assert req.timezone == "Europe/Istanbul"

    def test_custom_viewport(self):
        req = BrowserSessionCreate(viewport_width=1920, viewport_height=1080)
        assert req.viewport_width == 1920

    def test_viewport_width_min(self):
        with pytest.raises(Exception):
            BrowserSessionCreate(viewport_width=100)  # below 320

    def test_viewport_height_min(self):
        with pytest.raises(Exception):
            BrowserSessionCreate(viewport_height=100)  # below 240

    def test_viewport_width_max(self):
        with pytest.raises(Exception):
            BrowserSessionCreate(viewport_width=5000)  # above 3840


# ---------------------------------------------------------------------------
# BrowserSessionInfo
# ---------------------------------------------------------------------------

class TestBrowserSessionInfo:
    def test_creation(self):
        info = BrowserSessionInfo(
            session_id="sess-001",
            status="active",
            created_at="2026-01-01T00:00:00Z",
        )
        assert info.session_id == "sess-001"
        assert info.status == "active"

    def test_optional_fields_none(self):
        info = BrowserSessionInfo(
            session_id="s",
            status="idle",
            created_at="2026-01-01T00:00:00Z",
        )
        assert info.current_url is None
        assert info.page_title is None


# ---------------------------------------------------------------------------
# NavigateRequest
# ---------------------------------------------------------------------------

class TestNavigateRequest:
    def test_creation(self):
        req = NavigateRequest(url="https://example.com")
        assert req.url == "https://example.com"

    def test_defaults(self):
        req = NavigateRequest(url="https://example.com")
        assert req.wait_until == "domcontentloaded"
        assert req.timeout_ms == 30000

    def test_timeout_min(self):
        with pytest.raises(Exception):
            NavigateRequest(url="https://x.com", timeout_ms=500)  # below 1000

    def test_timeout_max(self):
        with pytest.raises(Exception):
            NavigateRequest(url="https://x.com", timeout_ms=200000)  # above 120000


# ---------------------------------------------------------------------------
# NavigateResponse
# ---------------------------------------------------------------------------

class TestNavigateResponse:
    def test_creation(self):
        resp = NavigateResponse(url="https://x.com", title="X", load_time_ms=200)
        assert resp.title == "X"
        assert resp.load_time_ms == 200

    def test_status_code_optional(self):
        resp = NavigateResponse(url="https://x.com", title="X", load_time_ms=100)
        assert resp.status_code is None


# ---------------------------------------------------------------------------
# SelectorValidateRequest
# ---------------------------------------------------------------------------

class TestSelectorValidateRequest:
    def test_creation(self):
        req = SelectorValidateRequest(selectors=["#btn", ".link"])
        assert len(req.selectors) == 2

    def test_default_timeout(self):
        req = SelectorValidateRequest(selectors=["#btn"])
        assert req.timeout_ms == 5000

    def test_timeout_min(self):
        with pytest.raises(Exception):
            SelectorValidateRequest(selectors=["#x"], timeout_ms=100)


# ---------------------------------------------------------------------------
# SelectorResult
# ---------------------------------------------------------------------------

class TestSelectorResult:
    def test_creation(self):
        result = SelectorResult(selector="#btn", found=True)
        assert result.selector == "#btn"
        assert result.found is True

    def test_defaults(self):
        result = SelectorResult(selector="#btn", found=False)
        assert result.count == 0
        assert result.visible is False
        assert result.tag_name is None
        assert result.attributes == {}
        assert result.bounding_box is None
        assert result.stability_score == 0
        assert result.suggested_alternatives == []

    def test_stability_score_bounds(self):
        with pytest.raises(Exception):
            SelectorResult(selector="#x", found=True, stability_score=6)

    def test_stability_score_valid(self):
        result = SelectorResult(selector="#x", found=True, stability_score=5)
        assert result.stability_score == 5


# ---------------------------------------------------------------------------
# DOMSnapshotRequest
# ---------------------------------------------------------------------------

class TestDOMSnapshotRequest:
    def test_defaults(self):
        req = DOMSnapshotRequest()
        assert req.selector is None
        assert req.max_depth == 5
        assert req.include_styles is False
        assert req.include_hidden is False

    def test_max_depth_min(self):
        with pytest.raises(Exception):
            DOMSnapshotRequest(max_depth=0)

    def test_max_depth_max(self):
        with pytest.raises(Exception):
            DOMSnapshotRequest(max_depth=20)  # above 15

    def test_with_selector(self):
        req = DOMSnapshotRequest(selector="#root")
        assert req.selector == "#root"


# ---------------------------------------------------------------------------
# DOMNode
# ---------------------------------------------------------------------------

class TestDOMNode:
    def test_creation(self):
        node = DOMNode(tag="div")
        assert node.tag == "div"

    def test_defaults(self):
        node = DOMNode(tag="span")
        assert node.attributes == {}
        assert node.text is None
        assert node.children == []
        assert node.bounding_box is None

    def test_nested_children(self):
        child = DOMNode(tag="a", text="Click")
        parent = DOMNode(tag="div", children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].tag == "a"


# ---------------------------------------------------------------------------
# DOMSnapshotResponse
# ---------------------------------------------------------------------------

class TestDOMSnapshotResponse:
    def test_creation(self):
        resp = DOMSnapshotResponse(url="https://x.com", title="X", snapshot_at="2026-01-01T00:00:00Z")
        assert resp.title == "X"

    def test_defaults(self):
        resp = DOMSnapshotResponse(url="https://x.com", title="X", snapshot_at="2026-01-01T00:00:00Z")
        assert resp.root is None
        assert resp.element_count == 0


# ---------------------------------------------------------------------------
# ScreenshotRequest
# ---------------------------------------------------------------------------

class TestScreenshotRequest:
    def test_defaults(self):
        req = ScreenshotRequest()
        assert req.selector is None
        assert req.full_page is False
        assert req.format == "png"
        assert req.quality == 80

    def test_quality_min(self):
        with pytest.raises(Exception):
            ScreenshotRequest(quality=5)  # below 10

    def test_quality_max(self):
        with pytest.raises(Exception):
            ScreenshotRequest(quality=101)


# ---------------------------------------------------------------------------
# ScreenshotResponse
# ---------------------------------------------------------------------------

class TestScreenshotResponse:
    def test_creation(self):
        resp = ScreenshotResponse(
            image_base64="abc123",
            format="png",
            width=1280,
            height=720,
            url="https://x.com",
        )
        assert resp.width == 1280
        assert resp.height == 720
        assert resp.format == "png"


# ---------------------------------------------------------------------------
# ActionRequest
# ---------------------------------------------------------------------------

class TestActionRequest:
    def test_creation(self):
        req = ActionRequest(action="click", selector="#btn")
        assert req.action == "click"
        assert req.selector == "#btn"

    def test_defaults(self):
        req = ActionRequest(action="fill", selector="#input")
        assert req.value is None
        assert req.timeout_ms == 5000

    def test_timeout_min(self):
        with pytest.raises(Exception):
            ActionRequest(action="click", selector="#x", timeout_ms=100)


# ---------------------------------------------------------------------------
# ActionResponse
# ---------------------------------------------------------------------------

class TestActionResponse:
    def test_creation(self):
        resp = ActionResponse(action="click", selector="#btn", success=True, duration_ms=100)
        assert resp.success is True
        assert resp.duration_ms == 100

    def test_defaults(self):
        resp = ActionResponse(action="click", selector="#x", success=False, duration_ms=50)
        assert resp.error is None
        assert resp.screenshot_after is None


# ---------------------------------------------------------------------------
# SelectorSuggestRequest
# ---------------------------------------------------------------------------

class TestSelectorSuggestRequest:
    def test_creation(self):
        req = SelectorSuggestRequest(target_description="Login butonu")
        assert "Login" in req.target_description

    def test_defaults(self):
        req = SelectorSuggestRequest(target_description="test")
        assert req.dom_context is None
        assert req.page_url is None


# ---------------------------------------------------------------------------
# SelectorSuggestResponse
# ---------------------------------------------------------------------------

class TestSelectorSuggestResponse:
    def test_defaults(self):
        resp = SelectorSuggestResponse(suggestions=[])
        assert resp.suggestions == []
        assert resp.ai_analysis is None

    def test_with_suggestions(self):
        s = SelectorResult(selector="#login-btn", found=True, count=1)
        resp = SelectorSuggestResponse(suggestions=[s])
        assert len(resp.suggestions) == 1


# ---------------------------------------------------------------------------
# HealVerifyRequest
# ---------------------------------------------------------------------------

class TestHealVerifyRequest:
    def test_creation(self):
        req = HealVerifyRequest(
            original_selector="#old-btn",
            healed_selector="#new-btn",
        )
        assert req.original_selector == "#old-btn"
        assert req.healed_selector == "#new-btn"

    def test_optional_fields_none(self):
        req = HealVerifyRequest(original_selector="#x", healed_selector="#y")
        assert req.expected_tag is None
        assert req.expected_text is None


# ---------------------------------------------------------------------------
# HealVerifyResponse
# ---------------------------------------------------------------------------

class TestHealVerifyResponse:
    def test_creation(self):
        resp = HealVerifyResponse(
            original_found=True,
            healed_found=True,
            healed_matches_expected=True,
        )
        assert resp.healed_matches_expected is True

    def test_defaults(self):
        resp = HealVerifyResponse(
            original_found=False,
            healed_found=True,
            healed_matches_expected=False,
        )
        assert resp.confidence == pytest.approx(0.0)
        assert resp.recommendation == ""

    def test_with_confidence(self):
        resp = HealVerifyResponse(
            original_found=True,
            healed_found=True,
            healed_matches_expected=True,
            confidence=0.95,
            recommendation="Use data-testid",
        )
        assert resp.confidence == pytest.approx(0.95)
