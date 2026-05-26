"""
tests/unit/test_registry_routes.py
====================================
Locator Registry blueprint (/api/registry/…) için birim testler.

Dış bağımlılıklar (LocatorRegistry singleton, config.settings) monkeypatching
ile izole edilir; her test temiz bir singleton ile başlar.
"""
from __future__ import annotations

import importlib
import sys
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

class _FakeEntry:
    """Minimal LocatorEntry stub."""

    def __init__(self, name: str, screen: str = ""):
        self.name = name
        self.screen = screen

    def to_dict(self):
        return {"name": self.name, "screen": self.screen}


class _FakeRegistry:
    """In-memory LocatorRegistry stub."""

    def __init__(self):
        self._store: dict[str, _FakeEntry] = {}
        self.heal_log: list = []

    @property
    def all_entries(self):
        return list(self._store.values())

    def get(self, name: str):
        return self._store.get(name)

    def get_by_screen(self, screen: str):
        return [e for e in self._store.values() if e.screen == screen]

    def register(self, name, chain=None, page_url="", screen="", element_type="", metadata=None):
        self._store[name] = _FakeEntry(name, screen)

    def unregister(self, name: str):
        self._store.pop(name, None)

    def sync_from_db(self):
        pass

    def sync_to_db(self):
        pass

    def load(self, path):
        pass

    def stats(self):
        return {"total": len(self._store)}

    def resolve(self, name: str):
        entry = self._store.get(name)
        return entry.name if entry else None


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def registry_client(monkeypatch, tmp_path):
    """Flask test client with registry stubs injected."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-internal")

    # Reset module caches so the blueprint re-imports cleanly
    for mod in list(sys.modules.keys()):
        if "registry_routes" in mod or mod == "app":
            sys.modules.pop(mod, None)

    fake_reg = _FakeRegistry()

    # Patch singleton getter used inside registry_routes
    import routes.registry_routes as rr
    monkeypatch.setattr(rr, "_registry", fake_reg)
    monkeypatch.setattr(rr, "_get_registry", lambda: fake_reg)

    # Stub settings so BASE_DIR exists
    import config.settings as cs
    monkeypatch.setattr(cs.settings, "BASE_DIR", tmp_path, raising=False)

    # Stub SelectorChain / SelectorCandidate imports used by create_entry
    import types
    fake_lrmod = types.ModuleType("core.locator_registry")

    class _SC:
        @staticmethod
        def from_dict(d):
            return d

    class _Chain:
        def __init__(self, candidates):
            self._candidates = candidates

        def to_list(self):
            return list(self._candidates)

    fake_lrmod.SelectorCandidate = _SC
    fake_lrmod.SelectorChain = _Chain
    fake_lrmod.LocatorRegistry = _FakeRegistry
    fake_lrmod.LocatorEntry = _FakeEntry
    sys.modules["core.locator_registry"] = fake_lrmod

    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client, fake_reg


# ── GET /api/registry/entries ─────────────────────────────────────────────────

def test_list_entries_empty(registry_client):
    """Empty registry returns ok=True with empty entries list."""
    client, _ = registry_client
    r = client.get("/api/registry/entries")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["entries"] == []
    assert data["count"] == 0


def test_list_entries_with_data(registry_client):
    """Registry with entries returns all of them."""
    client, reg = registry_client
    reg._store["btn_login"] = _FakeEntry("btn_login", "login")
    reg._store["btn_logout"] = _FakeEntry("btn_logout", "home")

    r = client.get("/api/registry/entries")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["count"] == 2
    names = {e["name"] for e in data["entries"]}
    assert names == {"btn_login", "btn_logout"}


def test_list_entries_filter_by_screen(registry_client):
    """?screen= filter returns only matching entries."""
    client, reg = registry_client
    reg._store["btn_login"] = _FakeEntry("btn_login", "login")
    reg._store["btn_logout"] = _FakeEntry("btn_logout", "home")

    r = client.get("/api/registry/entries?screen=login")
    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 1
    assert data["entries"][0]["name"] == "btn_login"


def test_list_entries_filter_screen_no_match(registry_client):
    """?screen= with no matching entries returns empty list."""
    client, reg = registry_client
    reg._store["btn_login"] = _FakeEntry("btn_login", "login")

    r = client.get("/api/registry/entries?screen=unknown")
    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 0
    assert data["entries"] == []


# ── GET /api/registry/entries/<name> ─────────────────────────────────────────

def test_get_entry_not_found_returns_404(registry_client):
    """Getting a non-existent entry returns 404."""
    client, _ = registry_client
    r = client.get("/api/registry/entries/nonexistent")
    assert r.status_code == 404
    data = r.get_json()
    assert data["ok"] is False


def test_get_entry_found_returns_data(registry_client):
    """Getting an existing entry returns its data."""
    client, reg = registry_client
    reg._store["input_username"] = _FakeEntry("input_username", "login")

    r = client.get("/api/registry/entries/input_username")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["entry"]["name"] == "input_username"


# ── POST /api/registry/entries ────────────────────────────────────────────────

def test_create_entry_missing_name_returns_400(registry_client):
    """POST without name field returns 400."""
    client, _ = registry_client
    r = client.post(
        "/api/registry/entries",
        json={"chain": [{"type": "testid", "value": "x"}]},
        content_type="application/json",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert data["ok"] is False


def test_create_entry_missing_chain_returns_400(registry_client):
    """POST without chain field returns 400."""
    client, _ = registry_client
    r = client.post(
        "/api/registry/entries",
        json={"name": "btn_submit"},
        content_type="application/json",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert data["ok"] is False


def test_create_entry_success(registry_client):
    """POST with valid payload registers entry and returns ok=True."""
    client, reg = registry_client
    payload = {
        "name": "btn_submit",
        "chain": [{"type": "testid", "value": "submit-btn", "confidence": 1.0, "stable": True}],
        "screen": "checkout",
    }
    r = client.post("/api/registry/entries", json=payload, content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["name"] == "btn_submit"
    # Entry should now exist in the registry
    assert "btn_submit" in reg._store


def test_create_entry_empty_body_returns_400(registry_client):
    """POST with empty body returns 400 (no name)."""
    client, _ = registry_client
    r = client.post("/api/registry/entries", json={}, content_type="application/json")
    assert r.status_code == 400


# ── DELETE /api/registry/entries/<name> ──────────────────────────────────────

def test_delete_entry_success(registry_client):
    """DELETE removes entry and returns ok=True."""
    client, reg = registry_client
    reg._store["btn_delete_me"] = _FakeEntry("btn_delete_me")

    r = client.delete("/api/registry/entries/btn_delete_me")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert "btn_delete_me" not in reg._store


def test_delete_nonexistent_entry_returns_ok(registry_client):
    """DELETE on non-existent entry still returns ok (unregister is idempotent)."""
    client, _ = registry_client
    r = client.delete("/api/registry/entries/does_not_exist")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── POST /api/registry/sync-db ────────────────────────────────────────────────

def test_sync_db_from_db_direction(registry_client):
    """sync-db with direction=from_db returns ok."""
    client, _ = registry_client
    r = client.post(
        "/api/registry/sync-db",
        json={"direction": "from_db"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["direction"] == "from_db"


def test_sync_db_to_db_direction(registry_client):
    """sync-db with direction=to_db returns ok."""
    client, _ = registry_client
    r = client.post(
        "/api/registry/sync-db",
        json={"direction": "to_db"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


def test_sync_db_default_direction(registry_client):
    """sync-db with no direction defaults to from_db."""
    client, _ = registry_client
    r = client.post("/api/registry/sync-db", json={}, content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── POST /api/registry/save ───────────────────────────────────────────────────

def test_save_registry_returns_ok(registry_client, tmp_path):
    """save endpoint returns ok with the path used."""
    client, _ = registry_client
    save_path = str(tmp_path / "out.json")
    r = client.post(
        "/api/registry/save",
        json={"path": save_path},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── GET /api/registry/stats ───────────────────────────────────────────────────

def test_registry_stats_returns_ok(registry_client):
    """stats endpoint returns ok with stats dict."""
    client, reg = registry_client
    reg._store["a"] = _FakeEntry("a")
    reg._store["b"] = _FakeEntry("b")

    r = client.get("/api/registry/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert "stats" in data


# ── GET /api/registry/heal-log ────────────────────────────────────────────────

def test_heal_log_empty(registry_client):
    """heal-log returns empty list when no healing has occurred."""
    client, _ = registry_client
    r = client.get("/api/registry/heal-log")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["log"] == []
    assert data["count"] == 0


# ── POST /api/registry/bulk-import ───────────────────────────────────────────

def test_bulk_import_success(registry_client):
    """bulk-import with valid entries returns imported count."""
    client, reg = registry_client
    payload = {
        "entries": {
            "btn_a": {"name": "btn_a", "chain": [], "page_url": "", "screen": "", "element_type": "", "metadata": None},
            "btn_b": {"name": "btn_b", "chain": [], "page_url": "", "screen": "", "element_type": "", "metadata": None},
        }
    }

    import types

    class _FakeLocatorEntry:
        def __init__(self, name):
            self.name = name
            self.chain = None
            self.page_url = ""
            self.screen = ""
            self.element_type = ""
            self.metadata = None

        @classmethod
        def from_dict(cls, d):
            return cls(d["name"])

    sys.modules["core.locator_registry"].LocatorEntry = _FakeLocatorEntry

    r = client.post("/api/registry/bulk-import", json=payload, content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["imported"] == 2
