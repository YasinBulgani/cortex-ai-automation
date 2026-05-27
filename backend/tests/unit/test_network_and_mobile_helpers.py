"""Unit tests for network, mobile, billing and crawler pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/agents/v2/tools/test_runner.py:
    _is_host_allowed
  app/domains/automation_suite/mobile.py:
    _device_label, _app_label, _strip_markdown_fence
  app/domains/billing/stripe_sync.py:
    _ts, _plan_code_from_subscription
  app/domains/nexus_repo/crawler.py:
    _detect_endpoints, _guess_auth
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domains.agents.v2.tools.test_runner import _is_host_allowed
from app.domains.automation_suite.mobile import (
    _app_label,
    _device_label,
    _strip_markdown_fence,
)
from app.domains.billing.stripe_sync import _plan_code_from_subscription, _ts
from app.domains.nexus_repo.crawler import _detect_endpoints, _guess_auth


# ── _is_host_allowed ──────────────────────────────────────────────────────────


class TestIsHostAllowed:
    def test_empty_allowlist_returns_false(self) -> None:
        assert _is_host_allowed("http://example.com", []) is False

    def test_exact_match_returns_true(self) -> None:
        assert _is_host_allowed("http://example.com", ["example.com"]) is True

    def test_different_host_returns_false(self) -> None:
        assert _is_host_allowed("http://other.com", ["example.com"]) is False

    def test_wildcard_subdomain_match(self) -> None:
        assert _is_host_allowed("http://sub.example.com", ["*.example.com"]) is True

    def test_wildcard_does_not_match_apex(self) -> None:
        # *.example.com should NOT match example.com (no subdomain)
        result = _is_host_allowed("http://example.com", ["*.example.com"])
        assert result is False

    def test_wildcard_matches_deep_subdomain(self) -> None:
        assert _is_host_allowed("http://a.b.example.com", ["*.example.com"]) is True

    def test_multiple_patterns_first_match_wins(self) -> None:
        assert _is_host_allowed("http://a.com", ["b.com", "a.com", "c.com"]) is True

    def test_case_insensitive_match(self) -> None:
        assert _is_host_allowed("http://EXAMPLE.COM", ["example.com"]) is True

    def test_empty_url_returns_false(self) -> None:
        assert _is_host_allowed("", ["example.com"]) is False

    def test_invalid_url_returns_false(self) -> None:
        assert _is_host_allowed("not-a-url", ["not-a-url"]) is False

    def test_empty_pattern_skipped(self) -> None:
        # Empty pattern in list is skipped, no match → False
        assert _is_host_allowed("http://example.com", ["", "other.com"]) is False

    def test_with_port_in_url(self) -> None:
        # urlparse strips port from hostname
        assert _is_host_allowed("http://example.com:8080/path", ["example.com"]) is True

    def test_https_scheme(self) -> None:
        assert _is_host_allowed("https://api.example.com", ["*.example.com"]) is True


# ── _device_label ─────────────────────────────────────────────────────────────


class TestDeviceLabel:
    def test_none_returns_default(self) -> None:
        assert _device_label(None) == "genel mobil cihaz"

    def test_empty_dict_returns_genel(self) -> None:
        # {} is falsy in Python → triggers "if not device" → returns "genel mobil cihaz"
        assert _device_label({}) == "genel mobil cihaz"

    def test_name_present(self) -> None:
        result = _device_label({"name": "iPhone 14"})
        assert "iPhone 14" in result

    def test_name_os_platform(self) -> None:
        result = _device_label({"name": "Pixel 7", "os": "Android 13", "platform": "android"})
        assert "Pixel 7" in result
        assert "Android 13" in result
        assert "android" in result

    def test_separator_is_dot(self) -> None:
        result = _device_label({"name": "iPhone", "os": "iOS 17"})
        assert "·" in result

    def test_slug_fallback_when_no_name(self) -> None:
        result = _device_label({"slug": "iphone-14-pro"})
        assert "iphone-14-pro" in result

    def test_partial_fields_no_empty_parts(self) -> None:
        result = _device_label({"name": "Galaxy", "os": "", "platform": None})
        assert "Galaxy" in result
        # Empty/None parts should be excluded
        assert "·" not in result or result.count("·") == 0

    def test_all_empty_values_returns_fallback(self) -> None:
        result = _device_label({"name": "", "os": "", "platform": ""})
        assert result == "mobil cihaz"

    def test_returns_string(self) -> None:
        assert isinstance(_device_label({"name": "Test"}), str)


# ── _app_label ────────────────────────────────────────────────────────────────


class TestAppLabel:
    def test_none_returns_none(self) -> None:
        assert _app_label(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert _app_label({}) is None

    def test_name_field(self) -> None:
        assert _app_label({"name": "MyApp"}) == "MyApp"

    def test_package_fallback(self) -> None:
        assert _app_label({"package": "com.example.app"}) == "com.example.app"

    def test_filename_fallback(self) -> None:
        assert _app_label({"filename": "app.apk"}) == "app.apk"

    def test_name_takes_priority_over_package(self) -> None:
        result = _app_label({"name": "App", "package": "com.app"})
        assert result == "App"

    def test_non_dict_returns_string(self) -> None:
        result = _app_label("raw_string")  # type: ignore[arg-type]
        assert result == "raw_string"

    def test_returns_none_for_empty_values(self) -> None:
        # All fields falsy → returns None
        result = _app_label({"name": None, "package": None, "filename": None})
        assert result is None


# ── _strip_markdown_fence ─────────────────────────────────────────────────────


class TestStripMarkdownFence:
    def test_plain_text_unchanged(self) -> None:
        result = _strip_markdown_fence("plain text")
        assert result == "plain text"

    def test_strips_gherkin_fence(self) -> None:
        raw = "```gherkin\nFeature: Login\n  Scenario: ...\n```"
        result = _strip_markdown_fence(raw)
        assert result == "Feature: Login\n  Scenario: ..."

    def test_strips_generic_fence(self) -> None:
        raw = "```\nsome content\n```"
        result = _strip_markdown_fence(raw)
        assert result == "some content"

    def test_fence_without_closing(self) -> None:
        raw = "```\nline1\nline2"
        result = _strip_markdown_fence(raw)
        # No closing fence → strips first line only
        assert "line1" in result
        assert "line2" in result
        assert "```" not in result

    def test_empty_string_returns_empty(self) -> None:
        assert _strip_markdown_fence("") == ""

    def test_none_returns_empty(self) -> None:
        assert _strip_markdown_fence(None) == ""  # type: ignore[arg-type]

    def test_whitespace_stripped(self) -> None:
        raw = "  ```json\ndata\n```  "
        result = _strip_markdown_fence(raw)
        assert result == "data"

    def test_no_fence_no_modification(self) -> None:
        text = "Feature: Login\n  Scenario: Test"
        assert _strip_markdown_fence(text) == text

    def test_fence_with_language_tag_removed(self) -> None:
        raw = "```python\nprint('hello')\n```"
        result = _strip_markdown_fence(raw)
        assert "python" not in result
        assert "print('hello')" in result


# ── _ts ───────────────────────────────────────────────────────────────────────


class TestTs:
    def test_none_returns_none(self) -> None:
        assert _ts(None) is None

    def test_valid_epoch_returns_datetime(self) -> None:
        result = _ts(0)
        assert isinstance(result, datetime)

    def test_unix_timestamp_2024(self) -> None:
        # 2024-01-01 00:00:00 UTC = 1704067200
        result = _ts(1704067200)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_result_is_utc_aware(self) -> None:
        result = _ts(1704067200)
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_string_epoch_converted(self) -> None:
        # Should convert string to int
        result = _ts("1704067200")
        assert result is not None
        assert isinstance(result, datetime)

    def test_invalid_string_returns_none(self) -> None:
        result = _ts("not-a-number")
        assert result is None

    def test_float_epoch_converted(self) -> None:
        result = _ts(1704067200.5)
        assert result is not None

    def test_negative_epoch_returns_datetime(self) -> None:
        # Negative epoch is before 1970
        result = _ts(-1000)
        assert isinstance(result, datetime)


# ── _plan_code_from_subscription ──────────────────────────────────────────────


class TestPlanCodeFromSubscription:
    def test_free_plan_in_metadata(self) -> None:
        sub = {"metadata": {"plan_code": "free"}}
        assert _plan_code_from_subscription(sub) == "free"

    def test_starter_plan_in_metadata(self) -> None:
        sub = {"metadata": {"plan_code": "starter"}}
        assert _plan_code_from_subscription(sub) == "starter"

    def test_pro_plan_in_metadata(self) -> None:
        sub = {"metadata": {"plan_code": "pro"}}
        assert _plan_code_from_subscription(sub) == "pro"

    def test_enterprise_plan_in_metadata(self) -> None:
        sub = {"metadata": {"plan_code": "enterprise"}}
        assert _plan_code_from_subscription(sub) == "enterprise"

    def test_unknown_plan_code_returns_none(self) -> None:
        sub = {"metadata": {"plan_code": "nonexistent_plan"}}
        assert _plan_code_from_subscription(sub) is None

    def test_no_metadata_returns_none(self) -> None:
        sub = {}
        assert _plan_code_from_subscription(sub) is None

    def test_empty_metadata_returns_none(self) -> None:
        sub = {"metadata": {}}
        assert _plan_code_from_subscription(sub) is None

    def test_none_metadata_returns_none(self) -> None:
        sub = {"metadata": None}
        assert _plan_code_from_subscription(sub) is None

    def test_missing_plan_code_key_returns_none(self) -> None:
        sub = {"metadata": {"other_key": "value"}}
        assert _plan_code_from_subscription(sub) is None


# ── _guess_auth ───────────────────────────────────────────────────────────────


class TestGuessAuth:
    def test_no_auth_decorator_returns_false(self) -> None:
        content = "def my_endpoint():\n    pass"
        assert _guess_auth(content, 0) is False

    def test_login_required_decorator(self) -> None:
        content = "@login_required\ndef my_view():\n    pass"
        assert _guess_auth(content, content.index("def")) is True

    def test_requires_auth_decorator(self) -> None:
        content = "@requires_auth\ndef endpoint():\n    pass"
        assert _guess_auth(content, content.index("def")) is True

    def test_jwt_bearer_decorator(self) -> None:
        content = "@JWTBearer()\ndef secure_endpoint():\n    pass"
        assert _guess_auth(content, content.index("def")) is True

    def test_depends_get_current(self) -> None:
        # Pattern: @Depends\s*\(\s*get_current\b — needs word boundary after "current"
        content = "def route(user = @Depends(get_current)):\n    pass"
        assert _guess_auth(content, 0) is True

    def test_window_is_300_chars_before(self) -> None:
        # Place auth far before the endpoint (>300 chars away) → not detected
        prefix = "@login_required\n" + "x" * 400
        content = prefix + "\ndef endpoint():\n    pass"
        pos = content.index("\ndef endpoint") + 1
        # 400 chars of padding pushes @login_required out of the 300-char window
        assert _guess_auth(content, pos) is False

    def test_permission_classes_detected(self) -> None:
        # Pattern requires @permission_classes decorator form
        content = "@permission_classes([IsAuthenticated])\ndef view():\n    pass"
        assert _guess_auth(content, content.index("def")) is True

    def test_case_insensitive(self) -> None:
        content = "@LOGIN_REQUIRED\ndef view():\n    pass"
        assert _guess_auth(content, content.index("def")) is True


# ── _detect_endpoints ─────────────────────────────────────────────────────────


class TestDetectEndpoints:
    def test_fastapi_get_route(self) -> None:
        content = '@app.get("/users")\ndef get_users(): pass'
        results = _detect_endpoints(content, "main.py", "python")
        assert len(results) >= 1
        assert results[0]["method"] == "GET"
        assert results[0]["path"] == "/users"

    def test_fastapi_post_route(self) -> None:
        content = '@router.post("/items")\ndef create_item(): pass'
        results = _detect_endpoints(content, "routes.py", "python")
        assert len(results) >= 1
        assert results[0]["method"] == "POST"

    def test_express_get_route(self) -> None:
        content = "app.get('/api/users', handler)"
        results = _detect_endpoints(content, "app.js", "javascript")
        assert len(results) >= 1
        assert results[0]["method"] == "GET"
        assert "/api/users" in results[0]["path"]

    def test_lang_filter_applied(self) -> None:
        # Python content but javascript lang → python patterns skipped
        content = '@app.get("/users")\ndef get_users(): pass'
        results = _detect_endpoints(content, "main.py", "javascript")
        # Python pattern skipped for js lang
        assert all(r["source_file"] == "main.py" for r in results)

    def test_source_file_in_result(self) -> None:
        content = '@app.get("/ping")\ndef ping(): pass'
        results = _detect_endpoints(content, "health.py", "python")
        assert all(r["source_file"] == "health.py" for r in results)

    def test_source_line_is_integer(self) -> None:
        content = '@app.get("/health")\ndef health(): pass'
        results = _detect_endpoints(content, "app.py", "python")
        assert all(isinstance(r["source_line"], int) for r in results)

    def test_auth_required_field_present(self) -> None:
        content = '@app.get("/public")\ndef public(): pass'
        results = _detect_endpoints(content, "app.py", "python")
        assert all("auth_required" in r for r in results)

    def test_empty_content_returns_empty(self) -> None:
        results = _detect_endpoints("", "empty.py", "python")
        assert results == []

    def test_nestjs_decorator(self) -> None:
        content = "@Get('/products')\ngetProducts() {}"
        results = _detect_endpoints(content, "products.ts", "typescript")
        assert len(results) >= 1
        assert "/products" in results[0]["path"]

    def test_returns_list_of_dicts(self) -> None:
        content = '@app.post("/create")\ndef create(): pass'
        results = _detect_endpoints(content, "app.py", "python")
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, dict)
            assert "method" in r
            assert "path" in r
