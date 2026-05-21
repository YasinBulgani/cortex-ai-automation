"""Template rendering — unit tests, no I/O."""

from __future__ import annotations

import pytest

from app.domains.email.templates import TEMPLATES, render


def test_all_templates_have_required_fields() -> None:
    expected_ids = {
        "welcome",
        "plan_changed",
        "payment_failed",
        "password_reset",
        "subscription_canceled",
    }
    assert set(TEMPLATES.keys()) == expected_ids
    for tpl in TEMPLATES.values():
        assert tpl.subject
        assert tpl.html
        assert tpl.text


def test_render_substitutes_values() -> None:
    subject, html, text = render(
        "welcome",
        {"full_name": "Yasin", "dashboard_url": "https://app.example.com"},
    )
    assert "Yasin" in subject
    assert "Yasin" in html
    assert "https://app.example.com" in html
    assert "https://app.example.com" in text


def test_render_escapes_html_in_user_input() -> None:
    """User-controlled fields must not break the HTML."""
    subject, html_body, text = render(
        "welcome",
        {"full_name": "<script>alert(1)</script>", "dashboard_url": "/x"},
    )
    # HTML output must have the tag escaped
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    # Plain text version is allowed to contain it raw
    assert "<script>alert(1)</script>" in text


def test_render_missing_context_leaves_placeholder() -> None:
    """Missing keys should NOT raise — render anything we have."""
    subject, html, text = render("payment_failed", {"billing_url": "/bill"})
    # grace_days was missing → literal "{grace_days}" remains
    assert "{grace_days}" in html
    assert "{grace_days}" in text


def test_render_unknown_template_raises() -> None:
    with pytest.raises(KeyError, match="Bilinmeyen template"):
        render("does_not_exist", {})


def test_plan_changed_includes_monthly_price() -> None:
    subject, html, text = render(
        "plan_changed",
        {
            "plan_label": "Profesyonel",
            "monthly_price": "199.00",
            "period_start": "2026-01-01",
            "billing_url": "/bill",
        },
    )
    assert "Profesyonel" in subject
    assert "199.00" in html
    assert "2026-01-01" in html


def test_password_reset_uses_provided_ttl() -> None:
    subject, html, text = render(
        "password_reset",
        {"ttl_minutes": 30, "reset_url": "https://x/reset?t=abc"},
    )
    assert "30" in html
    assert "https://x/reset?t=abc" in html


def test_subscription_canceled_includes_period_end() -> None:
    subject, html, text = render(
        "subscription_canceled",
        {"period_end": "2026-12-31", "billing_url": "/bill"},
    )
    assert "2026-12-31" in html
    assert "iptal" in subject.lower()
