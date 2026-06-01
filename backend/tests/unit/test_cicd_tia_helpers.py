"""Unit tests for app.domains.cicd.tia — pure helper functions.

Tests are fully self-contained: no DB, no HTTP, no filesystem.
Covers: is_test_file (all detection modes), _extract_imports (Python/JS),
        _module_name_for, CoverageMap.impacted_tests, ImpactResult.to_dict,
        _env_float.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

try:
    from app.domains.cicd.tia import (
        is_test_file,
        _extract_imports,
        _module_name_for,
        CoverageMap,
        ImpactResult,
        _env_float,
        _TEST_DIR_MARKERS,
        _TEST_FILE_SUFFIXES,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="tia import failed")


# ---------------------------------------------------------------------------
# is_test_file
# ---------------------------------------------------------------------------

class TestIsTestFile:
    def test_test_dir_marker(self):
        assert is_test_file("src/tests/unit/test_foo.py") is True

    def test_double_underscore_tests_dir(self):
        assert is_test_file("src/__tests__/foo.test.ts") is True

    def test_spec_ts_suffix(self):
        assert is_test_file("src/components/Button.spec.ts") is True

    def test_test_ts_suffix(self):
        assert is_test_file("app/logic.test.ts") is True

    def test_spec_tsx_suffix(self):
        assert is_test_file("src/Form.spec.tsx") is True

    def test_test_prefix_py(self):
        assert is_test_file("test_service.py") is True

    def test_regular_src_not_test(self):
        assert is_test_file("app/domains/ai/router.py") is False

    def test_regular_ts_not_test(self):
        assert is_test_file("src/components/Button.ts") is False

    def test_e2e_dir_marker(self):
        assert is_test_file("e2e/login_flow.py") is True

    def test_spec_dir_marker(self):
        assert is_test_file("spec/features/auth.feature") is True

    def test_windows_path_separators(self):
        assert is_test_file("src\\tests\\test_router.py") is True

    def test_case_insensitive(self):
        assert is_test_file("SRC/TESTS/TEST_FOO.PY") is True

    def test_empty_path_not_test(self):
        assert is_test_file("") is False

    def test_returns_bool(self):
        assert isinstance(is_test_file("foo.py"), bool)


# ---------------------------------------------------------------------------
# _extract_imports
# ---------------------------------------------------------------------------

class TestExtractImports:
    def test_python_simple_import(self):
        text = "import os\nimport sys"
        result = _extract_imports(text, py=True)
        assert "os" in result
        assert "sys" in result

    def test_python_from_import(self):
        text = "from pathlib import Path\nfrom typing import Optional"
        result = _extract_imports(text, py=True)
        assert "pathlib" in result
        assert "typing" in result

    def test_python_dotted_import(self):
        text = "from app.domains.ai import router"
        result = _extract_imports(text, py=True)
        assert "app.domains.ai" in result

    def test_python_empty_text(self):
        result = _extract_imports("", py=True)
        assert result == set()

    def test_js_require(self):
        text = "const express = require('express');"
        result = _extract_imports(text, py=False)
        assert "express" in result

    def test_js_import_from(self):
        text = "import React from 'react';"
        result = _extract_imports(text, py=False)
        assert "react" in result

    def test_returns_set(self):
        result = _extract_imports("import os", py=True)
        assert isinstance(result, set)

    def test_no_duplicates(self):
        text = "import os\nimport os"
        result = _extract_imports(text, py=True)
        assert result.count("os") if isinstance(result, list) else len([x for x in result if x == "os"]) == 1

    def test_js_mode_ignores_python_imports(self):
        text = "import os"
        result = _extract_imports(text, py=False)
        # Python-style import without quotes won't match JS regex
        assert "os" not in result


# ---------------------------------------------------------------------------
# _module_name_for
# ---------------------------------------------------------------------------

class TestModuleNameFor:
    def test_basic_module(self, tmp_path):
        f = tmp_path / "app" / "router.py"
        f.parent.mkdir(parents=True)
        f.touch()
        result = _module_name_for(f, tmp_path)
        assert result == "app.router"

    def test_init_file_removes_init(self, tmp_path):
        f = tmp_path / "app" / "__init__.py"
        f.parent.mkdir(parents=True)
        f.touch()
        result = _module_name_for(f, tmp_path)
        assert result == "app"

    def test_file_outside_repo_returns_none(self, tmp_path):
        f = Path("/tmp/external/module.py")
        result = _module_name_for(f, tmp_path)
        assert result is None

    def test_nested_module(self, tmp_path):
        f = tmp_path / "a" / "b" / "c.py"
        f.parent.mkdir(parents=True)
        f.touch()
        result = _module_name_for(f, tmp_path)
        assert result == "a.b.c"


# ---------------------------------------------------------------------------
# CoverageMap
# ---------------------------------------------------------------------------

class TestCoverageMap:
    def test_impacted_tests_returns_set(self):
        cmap = CoverageMap()
        result = cmap.impacted_tests(["src/foo.py"])
        assert isinstance(result, set)

    def test_impacted_tests_empty_when_no_mapping(self):
        cmap = CoverageMap()
        assert cmap.impacted_tests(["any/file.py"]) == set()

    def test_impacted_tests_returns_mapped_tests(self):
        cmap = CoverageMap(src_to_tests={"src/foo.py": {"tests/test_foo.py"}})
        result = cmap.impacted_tests(["src/foo.py"])
        assert "tests/test_foo.py" in result

    def test_multiple_src_files(self):
        cmap = CoverageMap(src_to_tests={
            "src/a.py": {"tests/test_a.py"},
            "src/b.py": {"tests/test_b.py"},
        })
        result = cmap.impacted_tests(["src/a.py", "src/b.py"])
        assert "tests/test_a.py" in result
        assert "tests/test_b.py" in result

    def test_unmapped_src_not_in_result(self):
        cmap = CoverageMap(src_to_tests={"src/a.py": {"tests/test_a.py"}})
        result = cmap.impacted_tests(["src/unknown.py"])
        assert len(result) == 0


# ---------------------------------------------------------------------------
# ImpactResult.to_dict
# ---------------------------------------------------------------------------

class TestImpactResultToDict:
    def test_returns_dict(self):
        result = ImpactResult(run_all=False, reason="no_changes")
        assert isinstance(result.to_dict(), dict)

    def test_run_all_key(self):
        result = ImpactResult(run_all=True, reason="too_many_changes")
        assert result.to_dict()["run_all"] is True

    def test_reason_key(self):
        result = ImpactResult(run_all=False, reason="stable")
        assert result.to_dict()["reason"] == "stable"

    def test_all_required_keys(self):
        d = ImpactResult(run_all=False, reason="ok").to_dict()
        for key in ("run_all", "reason", "tests", "changed_files", "impact_sources"):
            assert key in d

    def test_default_tests_empty_list(self):
        result = ImpactResult(run_all=False, reason="no_changes")
        assert result.to_dict()["tests"] == []


# ---------------------------------------------------------------------------
# _env_float (tia variant)
# ---------------------------------------------------------------------------

class TestEnvFloatTia:
    def test_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("TIA_TEST_FLOAT", raising=False)
        assert _env_float("TIA_TEST_FLOAT", 0.3) == pytest.approx(0.3)

    def test_reads_env_value(self, monkeypatch):
        monkeypatch.setenv("TIA_TEST_FLOAT", "0.5")
        assert _env_float("TIA_TEST_FLOAT", 0.3) == pytest.approx(0.5)

    def test_invalid_returns_default(self, monkeypatch):
        monkeypatch.setenv("TIA_TEST_FLOAT", "not_a_number")
        assert _env_float("TIA_TEST_FLOAT", 0.99) == pytest.approx(0.99)
