"""Unit tests for the marketplace service facade.

Covers:
    - list_items with no filter returns all items (list of dicts)
    - list_items with category filter narrows results
    - list_items with tag filter narrows results
    - list_items with query uses search path
    - get_item returns a dict for a known template_id
    - get_item raises KeyError for an unknown template_id
    - install_item raises KeyError for an unknown template_id
    - install_item success returns dict with template, project_id, installed keys
    - install_item with project_id propagates it to the result
"""
from __future__ import annotations

try:
    from app.domains.marketplace import service as marketplace_svc  # noqa: F401
    _import_ok = True
except ImportError:
    _import_ok = False

import pytest

pytestmark = pytest.mark.skipif(
    not _import_ok,
    reason="app.domains.marketplace not importable — skipping marketplace service tests",
)


# ── list_items ───────────────────────────────────────────────────────────


def test_list_items_no_filter_returns_list():
    items = marketplace_svc.list_items()
    assert isinstance(items, list)
    assert len(items) > 0


def test_list_items_no_filter_items_are_dicts():
    items = marketplace_svc.list_items()
    for item in items:
        assert isinstance(item, dict)


def test_list_items_category_filter_payments():
    items = marketplace_svc.list_items(category="payments")
    assert isinstance(items, list)
    assert len(items) > 0
    for item in items:
        assert item["category"] == "payments"


def test_list_items_category_filter_unknown_returns_empty():
    items = marketplace_svc.list_items(category="nonexistent_category_xyz")
    assert items == []


def test_list_items_tag_filter_narrows_results():
    # "happy-path" tag exists in multiple templates
    items = marketplace_svc.list_items(tag="happy-path")
    assert isinstance(items, list)
    assert len(items) > 0
    for item in items:
        assert "happy-path" in item["tags"]


def test_list_items_tag_filter_unknown_returns_empty():
    items = marketplace_svc.list_items(tag="nonexistent_tag_zzzz")
    assert items == []


def test_list_items_query_filter_returns_matches():
    # "EFT" appears in multiple template names/descriptions
    items = marketplace_svc.list_items(query="EFT")
    assert isinstance(items, list)
    assert len(items) > 0


# ── get_item ─────────────────────────────────────────────────────────────


def test_get_item_known_id_returns_dict():
    item = marketplace_svc.get_item("eft.happy_path")
    assert isinstance(item, dict)
    assert item["id"] == "eft.happy_path"


def test_get_item_dict_has_expected_keys():
    item = marketplace_svc.get_item("eft.happy_path")
    for key in ("id", "category", "name", "description", "gherkin", "tags"):
        assert key in item, f"Missing key: {key}"


def test_get_item_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        marketplace_svc.get_item("nonexistent.template.xyz")


# ── install_item ─────────────────────────────────────────────────────────


def test_install_item_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        marketplace_svc.install_item("nonexistent.template.xyz")


def test_install_item_success_returns_dict_with_required_keys():
    result = marketplace_svc.install_item("eft.happy_path")
    assert isinstance(result, dict)
    assert "template" in result
    assert "project_id" in result
    assert "installed" in result


def test_install_item_installed_flag_is_true():
    result = marketplace_svc.install_item("fast.instant_transfer")
    assert result["installed"] is True


def test_install_item_with_project_id_propagates_project_id():
    result = marketplace_svc.install_item("loan.application_approved", project_id="proj-42")
    assert result["project_id"] == "proj-42"


def test_install_item_template_contains_correct_id():
    result = marketplace_svc.install_item("card.activation")
    assert result["template"]["id"] == "card.activation"
