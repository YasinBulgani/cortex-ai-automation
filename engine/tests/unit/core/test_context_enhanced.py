"""
Unit tests for enhanced core.context — GlobalContext with @var and {var} support
"""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.context import GlobalContext


@pytest.fixture(autouse=True)
def clean_context():
    GlobalContext.clear()
    yield
    GlobalContext.clear()


class TestBraceVarSyntax:
    def test_render_brace_var(self):
        GlobalContext.set_value("name", "Yasin")
        assert GlobalContext.render("Merhaba {name}") == "Merhaba Yasin"

    def test_render_multiple_brace_vars(self):
        GlobalContext.set_value("a", "1")
        GlobalContext.set_value("b", "2")
        assert GlobalContext.render("{a} + {b}") == "1 + 2"

    def test_render_missing_brace_var_unchanged(self):
        assert GlobalContext.render("{unknown}") == "{unknown}"


class TestAtVarSyntax:
    def test_render_at_var(self):
        GlobalContext.set_value("username", "admin")
        assert GlobalContext.render("User: @username") == "User: admin"

    def test_render_multiple_at_vars(self):
        GlobalContext.set_value("user", "admin")
        GlobalContext.set_value("pass", "123")
        assert GlobalContext.render("@user:@pass") == "admin:123"

    def test_render_missing_at_var_unchanged(self):
        assert GlobalContext.render("@missing") == "@missing"


class TestMixedSyntax:
    def test_render_both_syntaxes(self):
        GlobalContext.set_value("name", "Yasin")
        GlobalContext.set_value("role", "admin")
        result = GlobalContext.render("{name} is @role")
        assert result == "Yasin is admin"


class TestHasAndAsDict:
    def test_has_returns_true(self):
        GlobalContext.set_value("key", "val")
        assert GlobalContext.has("key") is True

    def test_has_returns_false(self):
        assert GlobalContext.has("nonexistent") is False

    def test_as_dict_returns_copy(self):
        GlobalContext.set_value("x", "1")
        d = GlobalContext.as_dict()
        assert d == {"x": "1"}
        d["y"] = "2"
        assert not GlobalContext.has("y")


class TestNonStringPassthrough:
    def test_render_none(self):
        assert GlobalContext.render(None) is None

    def test_render_int(self):
        assert GlobalContext.render(42) == 42
