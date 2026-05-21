"""
Unit tests for core.locator_manager — JSON Locator Yoneticisi
"""
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.locator_manager import LocatorManager


@pytest.fixture(autouse=True)
def clean_locators():
    LocatorManager.clear()
    yield
    LocatorManager.clear()


@pytest.fixture
def locator_dir(tmp_path):
    """Gecici dizinde ornek locator JSON dosyalari olusturur."""
    login_data = [
        {"key": "UsernameInput", "type": "name", "value": "UserName"},
        {"key": "PasswordInput", "type": "name", "value": "Password"},
        {"key": "LoginButton", "type": "id", "value": "btnLogin"},
        {"key": "ErrorMessage", "type": "xpath", "value": "//div[@class='error']"},
        {"key": "Logo", "type": "css", "value": "img.logo"},
        {"key": "RememberMe", "type": "className", "value": "remember-checkbox"},
        {"key": "HelpLink", "type": "linkText", "value": "Yardim"},
        {"key": "SearchBox", "type": "testid", "value": "search-input"},
        {"key": "SubmitRole", "type": "role", "value": "button[name=Submit]"},
    ]
    (tmp_path / "login.json").write_text(json.dumps(login_data), encoding="utf-8")

    dashboard_data = [
        {"key": "WelcomeText", "type": "text", "value": "Hosgeldiniz"},
        {"key": "MenuButton", "type": "id", "value": "mainMenu"},
    ]
    (tmp_path / "dashboard.json").write_text(json.dumps(dashboard_data), encoding="utf-8")
    return tmp_path


class TestLocatorManagerLoad:
    def test_load_feature_locators(self, locator_dir):
        result = LocatorManager.load("login", locator_dir)
        assert "UsernameInput" in result
        assert "PasswordInput" in result
        assert "LoginButton" in result

    def test_load_all_features(self, locator_dir):
        result = LocatorManager.load_all(locator_dir)
        assert "UsernameInput" in result
        assert "WelcomeText" in result
        assert "MenuButton" in result

    def test_load_nonexistent_feature(self, locator_dir):
        result = LocatorManager.load("nonexistent", locator_dir)
        assert isinstance(result, dict)

    def test_load_caches(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        count_before = len(LocatorManager.keys())
        LocatorManager.load("login", locator_dir)
        assert len(LocatorManager.keys()) == count_before


class TestSeleniumToPlaywrightConversion:
    def test_id_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("LoginButton") == "#btnLogin"

    def test_name_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("UsernameInput") == '[name="UserName"]'

    def test_xpath_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("ErrorMessage") == "//div[@class='error']"

    def test_css_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("Logo") == "img.logo"

    def test_classname_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("RememberMe") == ".remember-checkbox"

    def test_linktext_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("HelpLink") == "text=Yardim"

    def test_testid_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("SearchBox") == '[data-testid="search-input"]'

    def test_role_conversion(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("SubmitRole") == "role=button[name=Submit]"


class TestResolve:
    def test_resolve_registered_key(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert LocatorManager.resolve("LoginButton") == "#btnLogin"

    def test_resolve_unregistered_returns_raw(self):
        assert LocatorManager.resolve("#someSelector") == "#someSelector"
        assert LocatorManager.resolve("//div[@id='x']") == "//div[@id='x']"

    def test_get_returns_none_for_missing(self):
        assert LocatorManager.get("nonexistent") is None

    def test_keys_returns_list(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        keys = LocatorManager.keys()
        assert isinstance(keys, list)
        assert "LoginButton" in keys

    def test_as_dict(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        d = LocatorManager.as_dict()
        assert isinstance(d, dict)
        assert d["LoginButton"] == "#btnLogin"


class TestClear:
    def test_clear_removes_all(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        assert len(LocatorManager.keys()) > 0
        LocatorManager.clear()
        assert len(LocatorManager.keys()) == 0
