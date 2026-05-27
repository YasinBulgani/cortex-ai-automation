"""Unit tests for agents.banking_team.script_cache.ScriptCache.

Tests are fully self-contained: no DB, no HTTP, no LLM.
Uses pytest tmp_path fixture for filesystem isolation.

Covers:
  - ScriptCache._make_key: deterministic SHA-256 truncated key
  - ScriptCache._escape: backslash, quote, newline escaping
  - ScriptCache._resolve_locator: testid/role/label/css/xpath/fallback strategies
  - ScriptCache._actions_to_script: click/fill/select/navigate/wait/
    assert_visible/assert_text/scroll/press/hover/screenshot/unknown
  - ScriptCache.get: miss (None), hit (script string), DOM hash invalidation
  - ScriptCache.save: writes .py + .meta.json, increments saves stat
  - ScriptCache.invalidate: removes files, returns bool
  - ScriptCache.invalidate_all: clears all .py files, returns count
  - ScriptCache.stats: hits, misses, saves, hit_rate, cached_scripts
"""
from __future__ import annotations

import json
import pytest

try:
    from app.domains.agents.banking_team.script_cache import ScriptCache
    _CACHE_OK = True
except ImportError:
    _CACHE_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache(tmp_path):
    return ScriptCache(cache_dir=tmp_path)


# ---------------------------------------------------------------------------
# _make_key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestMakeKey:
    def test_returns_string(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert isinstance(cache._make_key("SCN-001", "https://app.bank.com"), str)

    def test_length_16(self, tmp_path):
        cache = _make_cache(tmp_path)
        key = cache._make_key("SCN-001", "https://app.bank.com")
        assert len(key) == 16

    def test_deterministic(self, tmp_path):
        cache = _make_cache(tmp_path)
        k1 = cache._make_key("SCN-001", "https://app.bank.com")
        k2 = cache._make_key("SCN-001", "https://app.bank.com")
        assert k1 == k2

    def test_different_scenario_different_key(self, tmp_path):
        cache = _make_cache(tmp_path)
        k1 = cache._make_key("SCN-001", "https://app.bank.com")
        k2 = cache._make_key("SCN-002", "https://app.bank.com")
        assert k1 != k2

    def test_different_url_different_key(self, tmp_path):
        cache = _make_cache(tmp_path)
        k1 = cache._make_key("SCN-001", "https://app.bank.com")
        k2 = cache._make_key("SCN-001", "https://app.bank.com/login")
        assert k1 != k2

    def test_hex_characters_only(self, tmp_path):
        cache = _make_cache(tmp_path)
        key = cache._make_key("SCN-001", "https://app.bank.com")
        assert all(c in "0123456789abcdef" for c in key)


# ---------------------------------------------------------------------------
# _escape
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestEscape:
    def test_clean_string_unchanged(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache._escape("hello world") == "hello world"

    def test_backslash_escaped(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache._escape("a\\b") == "a\\\\b"

    def test_double_quote_escaped(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache._escape('a"b') == 'a\\"b'

    def test_newline_escaped(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache._escape("a\nb") == "a\\nb"

    def test_empty_string(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache._escape("") == ""

    def test_returns_string(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert isinstance(cache._escape("test"), str)


# ---------------------------------------------------------------------------
# _resolve_locator
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestResolveLocator:
    def _lmap(self, **locators):
        """Build locator_map from keyword args: key=('type', 'value')"""
        return {k: v for k, v in locators.items()}

    def test_testid_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"btn": ("testid", "login-btn")}
        result = cache._resolve_locator("btn", lmap)
        assert 'get_by_test_id("login-btn")' in result

    def test_role_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"btn": ("role", "button")}
        result = cache._resolve_locator("btn", lmap)
        assert 'get_by_role("button")' in result

    def test_label_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"inp": ("label", "Username")}
        result = cache._resolve_locator("inp", lmap)
        assert 'get_by_label("Username")' in result

    def test_aria_label_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"inp": ("aria-label", "Password")}
        result = cache._resolve_locator("inp", lmap)
        assert 'get_by_label("Password")' in result

    def test_placeholder_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"inp": ("placeholder", "Enter email")}
        result = cache._resolve_locator("inp", lmap)
        assert 'get_by_placeholder("Enter email")' in result

    def test_text_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"lnk": ("text", "Sign in")}
        result = cache._resolve_locator("lnk", lmap)
        assert 'get_by_text("Sign in")' in result

    def test_id_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"btn": ("id", "submit-btn")}
        result = cache._resolve_locator("btn", lmap)
        assert '#submit-btn' in result

    def test_css_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"div": ("css", ".main-panel")}
        result = cache._resolve_locator("div", lmap)
        assert 'locator(".main-panel")' in result

    def test_xpath_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"btn": ("xpath", "//button[@id='x']")}
        result = cache._resolve_locator("btn", lmap)
        assert "xpath=" in result

    def test_name_locator(self, tmp_path):
        cache = _make_cache(tmp_path)
        lmap = {"inp": ("name", "username")}
        result = cache._resolve_locator("inp", lmap)
        assert "name=" in result

    def test_fallback_css_selector(self, tmp_path):
        cache = _make_cache(tmp_path)
        result = cache._resolve_locator("#submit-btn", {})
        assert 'locator("#submit-btn")' in result

    def test_fallback_class_selector(self, tmp_path):
        cache = _make_cache(tmp_path)
        result = cache._resolve_locator(".submit-btn", {})
        assert 'locator(".submit-btn")' in result

    def test_fallback_xpath_selector(self, tmp_path):
        cache = _make_cache(tmp_path)
        result = cache._resolve_locator("//button[@id='x']", {})
        assert "xpath=" in result

    def test_fallback_testid_for_unknown(self, tmp_path):
        cache = _make_cache(tmp_path)
        result = cache._resolve_locator("login-form", {})
        assert "get_by_test_id" in result


# ---------------------------------------------------------------------------
# _actions_to_script
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestActionsToScript:
    def _basic_script(self, cache, actions):
        return cache._actions_to_script(actions, "https://app.bank.com/login", [], {})

    def test_script_is_string(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [])
        assert isinstance(script, str)

    def test_script_has_goto(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [])
        assert 'page.goto("https://app.bank.com/login")' in script

    def test_script_has_playwright_import(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [])
        assert "sync_playwright" in script

    def test_click_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "click", "target": "#btn", "value": ""}])
        assert ".click()" in script

    def test_fill_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "fill", "target": "#inp", "value": "admin"}])
        assert '.fill("admin")' in script

    def test_select_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "select", "target": "#sel", "value": "option1"}])
        assert "select_option" in script

    def test_navigate_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "navigate", "target": "https://login.bank.com", "value": ""}])
        assert "page.goto" in script

    def test_wait_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "wait", "target": "", "value": "", "timeout": 3000}])
        assert "wait_for_timeout" in script
        assert "3000" in script

    def test_assert_visible_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "assert_visible", "target": "#msg", "value": ""}])
        assert "to_be_visible" in script

    def test_assert_text_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "assert_text", "target": "#msg", "value": "Success"}])
        assert "to_contain_text" in script
        assert "Success" in script

    def test_scroll_down_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "scroll", "target": "", "value": "", "direction": "down", "pixels": 400}])
        assert "mouse.wheel" in script
        assert "400" in script

    def test_scroll_up_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "scroll", "target": "", "value": "", "direction": "up", "pixels": 200}])
        assert "mouse.wheel" in script
        assert "-200" in script

    def test_press_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "press", "target": "", "value": "Enter"}])
        assert "keyboard.press" in script
        assert "Enter" in script

    def test_hover_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "hover", "target": "#menu", "value": ""}])
        assert ".hover()" in script

    def test_screenshot_action(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "screenshot", "target": "", "value": ""}])
        assert "screenshot" in script

    def test_unknown_action_commented(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [{"type": "unknown_op", "target": "", "value": ""}])
        assert "Unknown action" in script or "unknown_op" in script

    def test_test_data_interpolation(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = cache._actions_to_script(
            [{"type": "fill", "target": "#inp", "value": "USERNAME_KEY"}],
            "https://app.bank.com",
            [],
            {"USERNAME_KEY": "john_doe"},
        )
        assert "john_doe" in script

    def test_script_has_cleanup(self, tmp_path):
        cache = _make_cache(tmp_path)
        script = self._basic_script(cache, [])
        assert "context.close()" in script
        assert "browser.close()" in script


# ---------------------------------------------------------------------------
# ScriptCache.get / save
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestScriptCacheGetSave:
    def test_get_on_empty_cache_returns_none(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.get("SCN-001", "https://app.bank.com") is None

    def test_get_after_save_returns_script(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [{"type": "click", "target": "#btn", "value": ""}])
        script = cache.get("SCN-001", "https://app.bank.com")
        assert script is not None
        assert isinstance(script, str)

    def test_save_returns_cache_key(self, tmp_path):
        cache = _make_cache(tmp_path)
        key = cache.save("SCN-001", "https://app.bank.com", [])
        assert isinstance(key, str)
        assert len(key) == 16

    def test_save_writes_script_file(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) == 1

    def test_save_writes_meta_json(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        meta_files = list(tmp_path.glob("*.meta.json"))
        assert len(meta_files) == 1

    def test_meta_json_has_scenario_id(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        meta_file = list(tmp_path.glob("*.meta.json"))[0]
        meta = json.loads(meta_file.read_text())
        assert meta["scenario_id"] == "SCN-001"

    def test_meta_json_has_url(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        meta_file = list(tmp_path.glob("*.meta.json"))[0]
        meta = json.loads(meta_file.read_text())
        assert meta["url"] == "https://app.bank.com"

    def test_meta_json_has_action_count(self, tmp_path):
        cache = _make_cache(tmp_path)
        actions = [{"type": "click", "target": "#btn", "value": ""} for _ in range(3)]
        cache.save("SCN-001", "https://app.bank.com", actions)
        meta_file = list(tmp_path.glob("*.meta.json"))[0]
        meta = json.loads(meta_file.read_text())
        assert meta["action_count"] == 3

    def test_dom_hash_mismatch_returns_none(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [], dom_hash="hash_v1")
        result = cache.get("SCN-001", "https://app.bank.com", dom_hash="hash_v2")
        assert result is None

    def test_dom_hash_match_returns_script(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [], dom_hash="hash_v1")
        result = cache.get("SCN-001", "https://app.bank.com", dom_hash="hash_v1")
        assert result is not None

    def test_no_dom_hash_check_returns_script(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [], dom_hash="hash_v1")
        # No dom_hash arg → skip hash check
        result = cache.get("SCN-001", "https://app.bank.com")
        assert result is not None


# ---------------------------------------------------------------------------
# ScriptCache.invalidate / invalidate_all
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestScriptCacheInvalidate:
    def test_invalidate_existing_returns_true(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        assert cache.invalidate("SCN-001", "https://app.bank.com") is True

    def test_invalidate_missing_returns_false(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.invalidate("SCN-999", "https://app.bank.com") is False

    def test_get_after_invalidate_returns_none(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        cache.invalidate("SCN-001", "https://app.bank.com")
        assert cache.get("SCN-001", "https://app.bank.com") is None

    def test_invalidate_all_returns_count(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com/a", [])
        cache.save("SCN-002", "https://app.bank.com/b", [])
        count = cache.invalidate_all()
        assert count == 2

    def test_invalidate_all_empty_returns_zero(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.invalidate_all() == 0

    def test_invalidate_all_clears_cache(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com/a", [])
        cache.invalidate_all()
        assert list(tmp_path.glob("*.py")) == []


# ---------------------------------------------------------------------------
# ScriptCache.stats
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CACHE_OK, reason="script_cache import failed")
class TestScriptCacheStats:
    def test_initial_stats_zeros(self, tmp_path):
        cache = _make_cache(tmp_path)
        s = cache.stats
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["saves"] == 0

    def test_miss_increments_misses(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.get("SCN-001", "https://app.bank.com")
        assert cache.stats["misses"] == 1

    def test_save_increments_saves(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        assert cache.stats["saves"] == 1

    def test_hit_increments_hits(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        cache.get("SCN-001", "https://app.bank.com")
        assert cache.stats["hits"] == 1

    def test_hit_rate_zero_initially(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.stats["hit_rate"] == pytest.approx(0.0)

    def test_hit_rate_100_after_one_hit(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.save("SCN-001", "https://app.bank.com", [])
        cache.get("SCN-001", "https://app.bank.com")
        assert cache.stats["hit_rate"] == pytest.approx(100.0)

    def test_cached_scripts_reflects_file_count(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.stats["cached_scripts"] == 0
        cache.save("SCN-001", "https://app.bank.com/a", [])
        cache.save("SCN-002", "https://app.bank.com/b", [])
        assert cache.stats["cached_scripts"] == 2

    def test_stats_returns_dict(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert isinstance(cache.stats, dict)
