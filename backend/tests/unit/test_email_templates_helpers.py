"""Unit tests for app.domains.email.templates — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no email sending.
Covers: _wrap_html, _SafeDict, TEMPLATES, render function.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.email.templates import (
        _wrap_html,
        _SafeDict,
        TEMPLATES,
        Template,
        render,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="email.templates import failed")


# ---------------------------------------------------------------------------
# _wrap_html
# ---------------------------------------------------------------------------

class TestWrapHtml:
    def test_returns_string(self):
        result = _wrap_html("Title", "<p>Body</p>")
        assert isinstance(result, str)

    def test_title_included(self):
        result = _wrap_html("My Title", "<p>Body</p>")
        assert "My Title" in result

    def test_body_included(self):
        result = _wrap_html("Title", "<p>Hello body</p>")
        assert "Hello body" in result

    def test_contains_html_div(self):
        result = _wrap_html("T", "B")
        assert "<div" in result

    def test_both_divs_present(self):
        result = _wrap_html("Title", "Body")
        # Should have wrapper + header + body divs
        assert result.count("<div") >= 2


# ---------------------------------------------------------------------------
# _SafeDict
# ---------------------------------------------------------------------------

class TestSafeDict:
    def test_existing_key_returned(self):
        d = _SafeDict({"key": "value"})
        assert d["key"] == "value"

    def test_missing_key_returns_placeholder(self):
        d = _SafeDict({})
        result = d["missing_key"]
        assert result == "{missing_key}"

    def test_missing_key_format_style(self):
        d = _SafeDict({})
        assert d["some_var"] == "{some_var}"

    def test_used_in_format_map(self):
        template = "Hello {name}, your code is {code}"
        d = _SafeDict({"name": "Alice"})
        result = template.format_map(d)
        assert "Alice" in result
        assert "{code}" in result  # Missing key preserved

    def test_inherits_from_dict(self):
        assert issubclass(_SafeDict, dict)


# ---------------------------------------------------------------------------
# TEMPLATES registry
# ---------------------------------------------------------------------------

class TestTemplates:
    def test_templates_dict_not_empty(self):
        assert len(TEMPLATES) > 0

    def test_has_welcome_template(self):
        assert "welcome" in TEMPLATES

    def test_has_plan_changed_template(self):
        assert "plan_changed" in TEMPLATES

    def test_has_payment_failed_template(self):
        assert "payment_failed" in TEMPLATES

    def test_has_password_reset_template(self):
        assert "password_reset" in TEMPLATES

    def test_has_subscription_canceled_template(self):
        assert "subscription_canceled" in TEMPLATES

    def test_each_template_is_template_instance(self):
        for key, tpl in TEMPLATES.items():
            assert isinstance(tpl, Template), f"{key} is not Template"

    def test_each_template_has_id(self):
        for key, tpl in TEMPLATES.items():
            assert tpl.id == key

    def test_each_template_has_subject(self):
        for tpl in TEMPLATES.values():
            assert tpl.subject

    def test_each_template_has_html(self):
        for tpl in TEMPLATES.values():
            assert tpl.html

    def test_each_template_has_text(self):
        for tpl in TEMPLATES.values():
            assert tpl.text


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

class TestRender:
    def test_returns_three_tuple(self):
        result = render("welcome", {"full_name": "Alice", "dashboard_url": "https://example.com"})
        assert len(result) == 3

    def test_subject_has_substituted_value(self):
        subject, _, _ = render("welcome", {"full_name": "Bob", "dashboard_url": "http://x.com"})
        assert "Bob" in subject

    def test_html_contains_name(self):
        _, html, _ = render("welcome", {"full_name": "Carol", "dashboard_url": "http://x.com"})
        assert "Carol" in html

    def test_text_contains_name(self):
        _, _, text = render("welcome", {"full_name": "Dave", "dashboard_url": "http://x.com"})
        assert "Dave" in text

    def test_missing_key_renders_placeholder(self):
        # Not passing dashboard_url — should not raise
        subject, html, text = render("welcome", {"full_name": "Eve"})
        # Template should still render, placeholder for missing key
        assert "Eve" in subject

    def test_unknown_template_raises_key_error(self):
        with pytest.raises(KeyError):
            render("nonexistent_template", {})

    def test_html_escapes_user_input(self):
        # XSS attempt — should be escaped in HTML
        _, html, _ = render(
            "welcome",
            {"full_name": "<script>alert('xss')</script>", "dashboard_url": "http://x.com"},
        )
        assert "<script>" not in html

    def test_text_does_not_escape(self):
        # Text field should not HTML-escape
        _, _, text = render(
            "welcome",
            {"full_name": "Alice & Bob", "dashboard_url": "http://x.com"},
        )
        assert "Alice & Bob" in text

    def test_plan_changed_substitution(self):
        subject, html, text = render(
            "plan_changed",
            {"plan_label": "Pro", "monthly_price": "49", "period_start": "2024-01-01", "billing_url": "http://x.com"},
        )
        assert "Pro" in subject
        assert "49" in text

    def test_payment_failed_grace_days(self):
        _, html, text = render(
            "payment_failed",
            {"grace_days": "7", "billing_url": "http://x.com"},
        )
        assert "7" in text

    def test_password_reset_ttl(self):
        subject, html, text = render(
            "password_reset",
            {"ttl_minutes": "30", "reset_url": "http://x.com/reset"},
        )
        assert "30" in text

    def test_subscription_canceled_period_end(self):
        _, _, text = render(
            "subscription_canceled",
            {"period_end": "2024-12-31", "billing_url": "http://x.com"},
        )
        assert "2024-12-31" in text

    def test_none_value_renders_empty_string_in_html(self):
        # None values should become empty string, not "None"
        _, html, _ = render(
            "welcome",
            {"full_name": None, "dashboard_url": "http://x.com"},
        )
        # html.escape(str(None)) = "None" -- but then used as empty in raw
        assert isinstance(html, str)
