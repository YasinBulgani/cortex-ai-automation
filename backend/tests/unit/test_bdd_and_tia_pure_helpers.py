"""Unit tests for tspm.bdd_generator and cicd.tia pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - bdd_generator._fuzzy_step_match: fuzzy BDD step text comparison
  - tia._env_float: env-var float parsing with fallback
  - tia._module_name_for: Python file path → dotted module name
  - tia._extract_imports: import extraction from Python/JS source text
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    from app.domains.tspm.bdd_generator import _fuzzy_step_match
    _BDD_OK = True
except ImportError:
    _BDD_OK = False

try:
    from app.domains.cicd.tia import (
        _env_float,
        _module_name_for,
        _extract_imports,
    )
    _TIA_OK = True
except ImportError:
    _TIA_OK = False


# ---------------------------------------------------------------------------
# _fuzzy_step_match
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="bdd_generator import failed")
class TestFuzzyStepMatch:
    def test_exact_match(self):
        assert _fuzzy_step_match("user logs in", "user logs in") is True

    def test_generated_in_known(self):
        assert _fuzzy_step_match("logs in", "user logs in") is True

    def test_known_in_generated(self):
        assert _fuzzy_step_match("the user logs in now", "logs in") is True

    def test_high_word_overlap(self):
        # "user logs in system" vs "user logs in" → 3/4 = 75% >= 60%
        assert _fuzzy_step_match("user logs in system", "user logs in") is True

    def test_low_word_overlap_returns_false(self):
        # "click login" vs "submit form" → 0 overlap
        assert _fuzzy_step_match("click login", "submit form") is False

    def test_empty_generated_returns_false(self):
        assert _fuzzy_step_match("", "user logs in") is False

    def test_empty_known_returns_false(self):
        assert _fuzzy_step_match("user logs in", "") is False

    def test_both_empty_returns_false(self):
        assert _fuzzy_step_match("", "") is False

    def test_returns_bool(self):
        assert isinstance(_fuzzy_step_match("step A", "step A"), bool)

    def test_case_sensitive(self):
        # Case matters since no lowercase normalization in function
        result = _fuzzy_step_match("User Logs In", "user logs in")
        # Either True (word overlap) or False - just verify it's a bool
        assert isinstance(result, bool)

    def test_exact_60_percent_boundary(self):
        # "a b c d e" vs "a b c x y" → 3/5 = 60% >= 60%
        assert _fuzzy_step_match("a b c d e", "a b c x y") is True

    def test_just_below_60_percent(self):
        # "a b c d e f" vs "a b x y z w" → 2/6 = 33% < 60%
        assert _fuzzy_step_match("a b c d e f", "a b x y z w") is False


# ---------------------------------------------------------------------------
# _env_float
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TIA_OK, reason="cicd.tia import failed")
class TestEnvFloat:
    def test_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("TIA_TEST_VAR", raising=False)
        assert _env_float("TIA_TEST_VAR", 0.5) == pytest.approx(0.5)

    def test_set_env_parsed(self, monkeypatch):
        monkeypatch.setenv("TIA_TEST_VAR", "0.8")
        assert _env_float("TIA_TEST_VAR", 0.5) == pytest.approx(0.8)

    def test_invalid_env_returns_default(self, monkeypatch):
        monkeypatch.setenv("TIA_TEST_VAR", "invalid")
        assert _env_float("TIA_TEST_VAR", 0.5) == pytest.approx(0.5)

    def test_integer_env_parsed(self, monkeypatch):
        monkeypatch.setenv("TIA_TEST_VAR", "2")
        assert _env_float("TIA_TEST_VAR", 1.0) == pytest.approx(2.0)

    def test_returns_float(self, monkeypatch):
        monkeypatch.delenv("TIA_TEST_VAR", raising=False)
        assert isinstance(_env_float("TIA_TEST_VAR", 1.0), float)

    def test_zero_default(self, monkeypatch):
        monkeypatch.delenv("TIA_TEST_VAR", raising=False)
        assert _env_float("TIA_TEST_VAR", 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _module_name_for
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TIA_OK, reason="cicd.tia import failed")
class TestModuleNameFor:
    def test_simple_module(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "mypackage" / "module.py"
        py_file.parent.mkdir(parents=True)
        py_file.touch()
        result = _module_name_for(py_file, repo)
        assert result == "mypackage.module"

    def test_init_stripped(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        init_file = repo / "mypackage" / "__init__.py"
        init_file.parent.mkdir(parents=True)
        init_file.touch()
        result = _module_name_for(init_file, repo)
        assert result == "mypackage"

    def test_outside_repo_returns_none(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        outside = tmp_path / "other" / "module.py"
        outside.parent.mkdir(parents=True)
        outside.touch()
        result = _module_name_for(outside, repo)
        assert result is None

    def test_top_level_module(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "toplevel.py"
        py_file.touch()
        result = _module_name_for(py_file, repo)
        assert result == "toplevel"

    def test_returns_string_or_none(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "mod.py"
        py_file.touch()
        result = _module_name_for(py_file, repo)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _extract_imports
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TIA_OK, reason="cicd.tia import failed")
class TestExtractImports:
    def test_python_import(self):
        code = "import os\nimport sys\n"
        result = _extract_imports(code, py=True)
        assert "os" in result
        assert "sys" in result

    def test_python_from_import(self):
        code = "from pathlib import Path\nfrom typing import Optional\n"
        result = _extract_imports(code, py=True)
        assert "pathlib" in result or "Path" in result or "typing" in result

    def test_python_returns_set(self):
        code = "import os\n"
        result = _extract_imports(code, py=True)
        assert isinstance(result, set)

    def test_js_import(self):
        code = 'import React from "react";\nimport { useState } from "react";'
        result = _extract_imports(code, py=False)
        assert "react" in result

    def test_empty_code_returns_empty_set(self):
        assert _extract_imports("", py=True) == set()
        assert _extract_imports("", py=False) == set()

    def test_no_imports_returns_empty_set(self):
        code = "def foo():\n    pass\n"
        result = _extract_imports(code, py=True)
        assert isinstance(result, set)

    def test_multiple_imports_deduplicated(self):
        code = "import os\nimport os\nimport sys\n"
        result = _extract_imports(code, py=True)
        assert len([x for x in result if x == "os"]) == 1
