"""Unit tests for core/locator_registry.py"""
import json
import tempfile
from pathlib import Path

import pytest

from core.locator_registry import (
    SelectorCandidate,
    SelectorChain,
    LocatorEntry,
    LocatorRegistry,
)


class TestSelectorCandidate:
    def test_to_dict(self):
        c = SelectorCandidate(type="testid", value='[data-testid="btn"]', confidence=1.0, stable=True)
        d = c.to_dict()
        assert d["type"] == "testid"
        assert d["confidence"] == 1.0
        assert d["stable"] is True

    def test_from_dict(self):
        c = SelectorCandidate.from_dict({"type": "css", "value": "#btn", "confidence": 0.9, "stable": True})
        assert c.type == "css"
        assert c.value == "#btn"


class TestSelectorChain:
    def test_sorts_by_confidence(self):
        chain = SelectorChain([
            SelectorCandidate("css", "#btn", 0.5, False),
            SelectorCandidate("testid", '[data-testid="x"]', 1.0, True),
            SelectorCandidate("xpath", "//button", 0.3, False),
        ])
        assert chain.primary.type == "testid"
        assert chain.primary.confidence == 1.0
        assert len(chain.fallbacks) == 2

    def test_empty_chain(self):
        chain = SelectorChain([])
        assert chain.primary is None
        assert chain.fallbacks == []

    def test_add(self):
        chain = SelectorChain([SelectorCandidate("css", "#a", 0.5, False)])
        chain.add(SelectorCandidate("testid", '[data-testid="b"]', 1.0, True))
        assert chain.primary.type == "testid"
        assert len(chain.candidates) == 2

    def test_round_trip(self):
        chain = SelectorChain([
            SelectorCandidate("testid", '[data-testid="x"]', 1.0, True),
            SelectorCandidate("css", "#x", 0.9, True),
        ])
        data = chain.to_list()
        rebuilt = SelectorChain.from_list(data)
        assert len(rebuilt.candidates) == 2
        assert rebuilt.primary.value == '[data-testid="x"]'


class TestLocatorEntry:
    def test_round_trip(self):
        entry = LocatorEntry(
            name="login_btn",
            chain=SelectorChain([SelectorCandidate("testid", '[data-testid="login-btn"]', 1.0, True)]),
            page_url="/login",
            screen="login",
            element_type="button",
        )
        d = entry.to_dict()
        rebuilt = LocatorEntry.from_dict(d)
        assert rebuilt.name == "login_btn"
        assert rebuilt.screen == "login"
        assert len(rebuilt.chain.candidates) == 1


class TestLocatorRegistry:
    def test_register_and_get(self):
        reg = LocatorRegistry()
        chain = SelectorChain([SelectorCandidate("testid", '[data-testid="x"]', 1.0, True)])
        reg.register("test_el", chain, screen="login")
        entry = reg.get("test_el")
        assert entry is not None
        assert entry.screen == "login"

    def test_unregister(self):
        reg = LocatorRegistry()
        chain = SelectorChain([SelectorCandidate("css", "#x", 0.9, True)])
        reg.register("test_el", chain)
        reg.unregister("test_el")
        assert reg.get("test_el") is None

    def test_resolve_without_page(self):
        reg = LocatorRegistry()
        chain = SelectorChain([
            SelectorCandidate("testid", '[data-testid="btn"]', 1.0, True),
            SelectorCandidate("css", "#btn", 0.9, True),
        ])
        reg.register("my_btn", chain)
        result = reg.resolve("my_btn")
        assert result == '[data-testid="btn"]'

    def test_resolve_unknown_returns_name(self):
        reg = LocatorRegistry()
        assert reg.resolve("nonexistent") == "nonexistent"

    def test_get_by_screen(self):
        reg = LocatorRegistry()
        reg.register("a", SelectorChain([SelectorCandidate("css", "#a", 0.9, True)]), screen="login")
        reg.register("b", SelectorChain([SelectorCandidate("css", "#b", 0.9, True)]), screen="projects")
        reg.register("c", SelectorChain([SelectorCandidate("css", "#c", 0.9, True)]), screen="login")
        login_entries = reg.get_by_screen("login")
        assert len(login_entries) == 2

    def test_save_and_load(self):
        reg = LocatorRegistry()
        chain = SelectorChain([SelectorCandidate("testid", '[data-testid="x"]', 1.0, True)])
        reg.register("el", chain, screen="test", page_url="/test")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = Path(f.name)

        reg.save(path)

        reg2 = LocatorRegistry()
        reg2.load(path)
        entry = reg2.get("el")
        assert entry is not None
        assert entry.screen == "test"
        path.unlink()

    def test_stats(self):
        reg = LocatorRegistry()
        reg.register("a", SelectorChain([SelectorCandidate("testid", "x", 1.0, True)]), screen="login")
        reg.register("b", SelectorChain([SelectorCandidate("css", "y", 0.5, False)]), screen="login")
        reg.register("c", SelectorChain([SelectorCandidate("xpath", "z", 0.3, False)]), screen="projects")

        s = reg.stats()
        assert s["total"] == 3
        assert s["by_screen"]["login"] == 2
        assert s["by_screen"]["projects"] == 1
        assert s["fragile_count"] == 2

    def test_all_entries(self):
        reg = LocatorRegistry()
        reg.register("a", SelectorChain([SelectorCandidate("css", "#a", 0.9, True)]))
        reg.register("b", SelectorChain([SelectorCandidate("css", "#b", 0.9, True)]))
        assert len(reg.all_entries) == 2
