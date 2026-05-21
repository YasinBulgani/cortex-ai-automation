"""
Unit tests for core.locator_bridge — Birlesik Locator Cozumleme Koprusu
"""
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.locator_manager import LocatorManager
from core.locator_bridge import LocatorBridge


@pytest.fixture(autouse=True)
def clean():
    LocatorManager.clear()
    yield
    LocatorManager.clear()


@pytest.fixture
def locator_dir(tmp_path):
    data = [
        {"key": "LoginBtn", "type": "id", "value": "btnLogin"},
        {"key": "EmailInput", "type": "name", "value": "email"},
    ]
    (tmp_path / "login.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


class TestLocatorBridge:
    def test_resolve_from_json(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        bridge = LocatorBridge()
        assert bridge.resolve("LoginBtn") == "#btnLogin"

    def test_resolve_raw_fallback(self):
        bridge = LocatorBridge()
        assert bridge.resolve("#direct-css") == "#direct-css"
        assert bridge.resolve("//xpath") == "//xpath"

    def test_resolve_unknown_key_returns_raw(self):
        bridge = LocatorBridge()
        assert bridge.resolve("NonExistentKey") == "NonExistentKey"

    def test_health_report_structure(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        bridge = LocatorBridge()
        report = bridge.health_report()
        assert "json_locators" in report
        assert "pom_repository" in report
        assert "db_repository" in report
        assert report["json_locators"]["count"] == 2

    def test_singleton_get_bridge(self, locator_dir):
        LocatorManager.load("login", locator_dir)
        from core.locator_bridge import get_bridge
        b1 = get_bridge()
        b2 = get_bridge()
        assert b1 is b2
