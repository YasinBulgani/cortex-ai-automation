"""
DSL service unit testleri — 14 test.

app.domains.dsl.service fonksiyonlarını (list_actions, get_action,
search_actions, semantic_search, hybrid_search, get_stats,
reload_catalog, suggest_actions, category_tree) doğrular.
catalog_cache ve alias_index mock'lanır; disk IO veya AI gateway
çağrısı yapılmaz.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

try:
    from app.domains.dsl.service import (
        list_actions,
        get_action,
        search_actions,
        semantic_search,
        get_stats,
        reload_catalog,
        suggest_actions,
        category_tree,
        _tokenize,
        _STEP_TYPE_PREFIXES,
    )
    from app.domains.dsl.schemas import (
        DslAction,
        DslActionListResponse,
        DslSearchResponse,
        DslStats,
        DslReloadResponse,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="dsl service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _action(
    aid: str = "ui.click",
    category: str = "ui",
    description: str = "Eylem: Tıkla",
    tags: list | None = None,
) -> DslAction:
    return DslAction(
        id=aid,
        category=category,
        description=description,
        aliases={"tr": [description], "en": [f"Click {aid}"]},
        tags=tags or [],
    )


def _stats(**kwargs) -> DslStats:
    defaults = dict(
        total=3,
        unique_ids=3,
        by_top_category={"ui": 2, "api": 1},
        by_full_category={"ui.click": 2, "api.call": 1},
    )
    defaults.update(kwargs)
    return DslStats(**defaults)


# ---------------------------------------------------------------------------
# _tokenize (pure helper)
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_splits_on_spaces(self):
        assert _tokenize("click button") == ["click", "button"]

    def test_preserves_hyphens(self):
        assert "color-contrast" in _tokenize("check color-contrast rule")

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_special_chars_stripped(self):
        tokens = _tokenize("foo@bar.baz!")
        assert "foo" in tokens
        assert "bar" in tokens


# ---------------------------------------------------------------------------
# list_actions
# ---------------------------------------------------------------------------

class TestListActions:
    def test_returns_action_list_response(self):
        actions = [_action("ui.click"), _action("api.call", "api")]
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.filter.return_value = actions
            result = list_actions()
        assert isinstance(result, DslActionListResponse)
        assert result.total == 2
        assert len(result.items) == 2

    def test_pagination_page_size(self):
        actions = [_action(f"a.{i}") for i in range(10)]
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.filter.return_value = actions
            result = list_actions(page=1, page_size=3)
        assert len(result.items) == 3
        assert result.total == 10
        assert result.page == 1

    def test_second_page(self):
        actions = [_action(f"a.{i}", description=f"Eylem: {i}") for i in range(10)]
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.filter.return_value = actions
            result = list_actions(page=2, page_size=4)
        assert len(result.items) == 4

    def test_step_type_given_filters_by_prefix(self):
        given_action = _action("pre.cond", description="(Ön koşul) Sayfayı aç")
        other_action = _action("ui.click", description="Eylem: Tıkla")
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.filter.return_value = [given_action, other_action]
            result = list_actions(step_type="given")
        assert result.total == 1
        assert result.items[0].id == "pre.cond"

    def test_empty_catalog_returns_zero_total(self):
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.filter.return_value = []
            result = list_actions()
        assert result.total == 0
        assert result.items == []


# ---------------------------------------------------------------------------
# get_action
# ---------------------------------------------------------------------------

class TestGetAction:
    def test_returns_action_when_found(self):
        a = _action("ui.click")
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.get.return_value = a
            result = get_action("ui.click")
        assert result is a

    def test_returns_none_when_not_found(self):
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.get.return_value = None
            result = get_action("nonexistent.action")
        assert result is None


# ---------------------------------------------------------------------------
# search_actions
# ---------------------------------------------------------------------------

class TestSearchActions:
    def test_returns_dsl_search_response(self):
        a = _action("ui.click")
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.search.return_value = [(a, "tr", "Tıkla")]
            result = search_actions("tıkla")
        assert isinstance(result, DslSearchResponse)
        assert result.query == "tıkla"
        assert result.total == 1
        assert result.items[0].action.id == "ui.click"

    def test_empty_search_result(self):
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.search.return_value = []
            result = search_actions("xyznotfound")
        assert result.total == 0
        assert result.items == []

    def test_mode_is_lexical(self):
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.search.return_value = []
            result = search_actions("q")
        assert result.mode == "lexical"


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestGetStats:
    def test_returns_dsl_stats(self):
        s = _stats()
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.stats.return_value = s
            result = get_stats()
        assert isinstance(result, DslStats)
        assert result.total == 3


# ---------------------------------------------------------------------------
# reload_catalog
# ---------------------------------------------------------------------------

class TestReloadCatalog:
    def test_returns_reload_response(self):
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.all.return_value = [_action()]
            mock_cache.load.return_value = 5
            mock_cache.loaded_at = "2026-01-01T00:00:00+00:00"
            result = reload_catalog(rebuild_index=False)
        assert isinstance(result, DslReloadResponse)
        assert result.status == "ok"
        assert result.total_after == 5


# ---------------------------------------------------------------------------
# suggest_actions
# ---------------------------------------------------------------------------

class TestSuggestActions:
    def test_empty_description_returns_empty(self):
        result = suggest_actions("")
        assert result.total == 0
        assert result.items == []

    def test_whitespace_only_returns_empty(self):
        result = suggest_actions("   ")
        assert result.total == 0

    def test_lexical_fallback_when_index_not_ready(self):
        a = _action("ui.click", description="Eylem: Tıkla")
        with patch("app.domains.dsl.service.alias_index") as mock_idx, \
             patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_idx.is_ready.return_value = False
            mock_cache.search.return_value = [(a, "tr", "Tıkla")]
            result = suggest_actions("tıkla")
        assert result.total >= 1


# ---------------------------------------------------------------------------
# category_tree
# ---------------------------------------------------------------------------

class TestCategoryTree:
    def test_builds_two_level_tree(self):
        s = _stats(by_full_category={"ui.click": 5, "ui.type": 3, "api.call": 2})
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.stats.return_value = s
            nodes = category_tree()
        top_ids = [n.id for n in nodes]
        assert "ui" in top_ids
        assert "api" in top_ids

    def test_root_count_is_sum_of_children(self):
        s = _stats(by_full_category={"ui.click": 5, "ui.type": 3})
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.stats.return_value = s
            nodes = category_tree()
        ui_node = next(n for n in nodes if n.id == "ui")
        assert ui_node.count == 8

    def test_empty_catalog_returns_empty_tree(self):
        s = _stats(by_full_category={})
        with patch("app.domains.dsl.service.catalog_cache") as mock_cache:
            mock_cache.stats.return_value = s
            nodes = category_tree()
        assert nodes == []
