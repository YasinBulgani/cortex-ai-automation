"""Unit tests for automation_templates service.

Tests: 14 total
- list_templates (3)
- get_template (2)
- create_template (3)
- delete_template (2)
- apply_template (4)
"""
from __future__ import annotations

import copy
import pytest


def _fresh_service():
    """Return a freshly reset service module so tests are isolated."""
    import app.domains.automation_templates.service as svc

    # Reset the store to builtins only
    svc._STORE.clear()
    for t in svc.BUILTIN_TEMPLATES:
        svc._STORE[t["id"]] = copy.deepcopy(t)
    return svc


@pytest.fixture()
def svc():
    return _fresh_service()


# ── list_templates ──────────────────────────────────────────────────────────


def test_list_templates_returns_all_builtins(svc):
    result = svc.list_templates()
    assert len(result) == 3


def test_list_templates_filter_by_category(svc):
    result = svc.list_templates(category="auth")
    assert len(result) == 1
    assert result[0]["id"] == "login-flow"


def test_list_templates_unknown_category_returns_empty(svc):
    result = svc.list_templates(category="nonexistent")
    assert result == []


# ── get_template ────────────────────────────────────────────────────────────


def test_get_template_returns_copy(svc):
    t = svc.get_template("login-flow")
    assert t["id"] == "login-flow"
    assert t["name"] == "Login Akışı"
    assert isinstance(t["steps"], list)


def test_get_template_raises_key_error_when_not_found(svc):
    with pytest.raises(KeyError, match="not found"):
        svc.get_template("does-not-exist")


# ── create_template ─────────────────────────────────────────────────────────


def test_create_template_creates_new_record(svc):
    data = {"name": "Smoke Test", "category": "smoke", "steps": ["open app", "verify title"]}
    created = svc.create_template(data)
    assert created["name"] == "Smoke Test"
    assert created["category"] == "smoke"
    assert created["id"] is not None
    # Persisted
    fetched = svc.get_template(created["id"])
    assert fetched["name"] == "Smoke Test"


def test_create_template_raises_value_error_when_name_missing(svc):
    with pytest.raises(ValueError, match="'name' is required"):
        svc.create_template({"category": "api"})


def test_create_template_raises_value_error_on_duplicate_id(svc):
    with pytest.raises(ValueError, match="already exists"):
        svc.create_template({"id": "login-flow", "name": "Duplicate"})


# ── delete_template ─────────────────────────────────────────────────────────


def test_delete_template_removes_record(svc):
    svc.delete_template("api-crud")
    with pytest.raises(KeyError):
        svc.get_template("api-crud")


def test_delete_template_raises_key_error_when_not_found(svc):
    with pytest.raises(KeyError, match="not found"):
        svc.delete_template("ghost-template")


# ── apply_template ──────────────────────────────────────────────────────────


def test_apply_template_returns_rendered_steps(svc):
    # Add a parameterised template
    svc.create_template(
        {
            "id": "parameterised",
            "name": "Parametreli",
            "category": "ui",
            "steps": ["goto {url}", "assert {title}"],
        }
    )
    result = svc.apply_template("parameterised", {"url": "https://example.com", "title": "Home"})
    assert result["rendered_steps"] == ["goto https://example.com", "assert Home"]


def test_apply_template_no_params_leaves_steps_unchanged(svc):
    result = svc.apply_template("login-flow", {})
    original = svc.get_template("login-flow")
    assert result["rendered_steps"] == original["steps"]


def test_apply_template_raises_key_error_when_not_found(svc):
    with pytest.raises(KeyError):
        svc.apply_template("ghost", {})


def test_apply_template_result_has_metadata(svc):
    result = svc.apply_template("api-crud", {"env": "staging"})
    assert result["template_id"] == "api-crud"
    assert result["params"] == {"env": "staging"}
    assert "rendered_steps" in result
    assert result["category"] == "api"
