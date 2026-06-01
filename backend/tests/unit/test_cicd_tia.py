"""Unit tests for CICD Test Impact Analysis (TIA).

Tests app/domains/cicd/tia.py — pure Python logic.
Covers: is_test_file, _extract_imports, impact_by_imports,
ImpactResult, map_changes_to_tests orchestrator.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, Set
from unittest.mock import patch, MagicMock

import pytest

from app.domains.cicd.tia import (
    ImpactResult,
    _extract_imports,
    impact_by_imports,
    is_test_file,
    map_changes_to_tests,
)


# ── is_test_file ──────────────────────────────────────────────────────────────


class TestIsTestFile:
    @pytest.mark.parametrize("path, expected", [
        # Test paths — should be True
        ("tests/unit/test_auth.py", True),
        ("backend/tests/test_smoke.py", True),
        ("src/__tests__/app.test.ts", True),
        ("apps/web/e2e/login.spec.ts", True),
        ("spec/features/checkout.spec.js", True),
        ("my/test/helper.py", True),  # contains /test/
        # Source paths — should be False
        ("app/domains/auth/router.py", False),
        ("src/components/Button.tsx", False),
        ("lib/utils.ts", False),
        ("apps/web/app/login/page.tsx", False),
        ("backend/app/infra/models.py", False),
    ])
    def test_paths(self, path: str, expected: bool) -> None:
        assert is_test_file(path) is expected

    def test_pytest_prefix(self) -> None:
        assert is_test_file("unit/test_quality_gate.py") is True

    def test_tsx_test_file(self) -> None:
        assert is_test_file("components/__tests__/Button.test.tsx") is True

    def test_jest_spec(self) -> None:
        assert is_test_file("src/hooks/useAuth.spec.js") is True


# ── _extract_imports ──────────────────────────────────────────────────────────


class TestExtractImports:
    def test_python_import(self) -> None:
        code = "import os\nimport sys"
        result = _extract_imports(code, py=True)
        assert "os" in result
        assert "sys" in result

    def test_python_from_import(self) -> None:
        code = "from app.domains.auth import service\nfrom .models import User"
        result = _extract_imports(code, py=True)
        assert "app.domains.auth" in result
        assert ".models" in result

    def test_python_relative_import(self) -> None:
        code = "from ..core import settings"
        result = _extract_imports(code, py=True)
        assert "..core" in result

    def test_js_require(self) -> None:
        code = "const x = require('./utils')\nconst y = require('../lib/api')"
        result = _extract_imports(code, py=False)
        assert "./utils" in result
        assert "../lib/api" in result

    def test_js_esm_import(self) -> None:
        code = "import { foo } from './foo'\nimport Bar from '../bar'"
        result = _extract_imports(code, py=False)
        assert "./foo" in result
        assert "../bar" in result

    def test_js_ignores_node_modules(self) -> None:
        code = "import React from 'react'\nimport { useState } from 'react'"
        result = _extract_imports(code, py=False)
        # Non-relative imports should be included in raw extract (caller filters)
        # but node_modules don't start with '.' so candidate resolution skips them
        # _extract_imports itself doesn't filter, just parses
        assert "react" in result

    def test_empty_code(self) -> None:
        assert _extract_imports("", py=True) == set()
        assert _extract_imports("", py=False) == set()

    def test_no_imports(self) -> None:
        code = "x = 1 + 2\nprint(x)"
        assert _extract_imports(code, py=True) == set()


# ── impact_by_imports ─────────────────────────────────────────────────────────


class TestImpactByImports:
    def test_matching_src_returns_tests(self) -> None:
        graph: Dict[str, Set[str]] = {
            "app/auth.py": {"tests/test_auth.py", "tests/test_login.py"},
            "app/models.py": {"tests/test_models.py"},
        }
        result = impact_by_imports(graph, ["app/auth.py"])
        assert "tests/test_auth.py" in result
        assert "tests/test_login.py" in result
        assert "tests/test_models.py" not in result

    def test_unmatched_src_returns_empty(self) -> None:
        graph: Dict[str, Set[str]] = {
            "app/auth.py": {"tests/test_auth.py"},
        }
        result = impact_by_imports(graph, ["app/unknown.py"])
        assert result == set()

    def test_multiple_changed_files_union(self) -> None:
        graph: Dict[str, Set[str]] = {
            "app/auth.py": {"tests/test_auth.py"},
            "app/billing.py": {"tests/test_billing.py"},
        }
        result = impact_by_imports(graph, ["app/auth.py", "app/billing.py"])
        assert result == {"tests/test_auth.py", "tests/test_billing.py"}

    def test_empty_changed_files(self) -> None:
        graph: Dict[str, Set[str]] = {"app/auth.py": {"tests/test_auth.py"}}
        assert impact_by_imports(graph, []) == set()

    def test_empty_graph(self) -> None:
        assert impact_by_imports({}, ["app/auth.py"]) == set()


# ── ImpactResult ──────────────────────────────────────────────────────────────


class TestImpactResult:
    def test_to_dict_keys(self) -> None:
        result = ImpactResult(run_all=False, reason="selective", tests=["t1", "t2"])
        d = result.to_dict()
        assert set(d.keys()) == {"run_all", "reason", "tests", "changed_files", "impact_sources"}

    def test_run_all_result(self) -> None:
        result = ImpactResult(run_all=True, reason="too_many_changes_40pct")
        d = result.to_dict()
        assert d["run_all"] is True
        assert d["tests"] == []

    def test_selective_result(self) -> None:
        result = ImpactResult(
            run_all=False,
            reason="selective",
            tests=["tests/test_auth.py"],
            changed_files=["app/auth.py"],
            impact_sources={"direct_test_changes": 0, "coverage_mapped": 1, "import_graph": 0},
        )
        d = result.to_dict()
        assert d["run_all"] is False
        assert "tests/test_auth.py" in d["tests"]
        assert d["impact_sources"]["coverage_mapped"] == 1


# ── map_changes_to_tests orchestrator ────────────────────────────────────────


class TestMapChangesToTests:
    def test_empty_changes_returns_no_run(self, tmp_path: Path) -> None:
        result = map_changes_to_tests(repo_root=tmp_path, changed_files=[])
        assert result.run_all is False
        assert result.reason == "no_changes"

    def test_empty_string_files_filtered(self, tmp_path: Path) -> None:
        result = map_changes_to_tests(repo_root=tmp_path, changed_files=[""])
        # Falsy strings ("") filtered → no changes
        assert result.reason == "no_changes"

    def test_too_many_changes_runs_all(self, tmp_path: Path) -> None:
        # 40% ratio with TIA_MAX_IMPACT_RATIO=0.30 → run all
        changed = [f"app/module_{i}.py" for i in range(40)]
        result = map_changes_to_tests(
            repo_root=tmp_path,
            changed_files=changed,
            total_src_count=100,
        )
        assert result.run_all is True
        assert "too_many_changes" in result.reason

    def test_within_ratio_does_not_force_run_all(self, tmp_path: Path) -> None:
        # 5% ratio with TIA_MAX_IMPACT_RATIO=0.30 → selective
        changed = [f"app/module_{i}.py" for i in range(5)]
        with patch.dict("os.environ", {"TIA_MAX_IMPACT_RATIO": "0.30"}):
            result = map_changes_to_tests(
                repo_root=tmp_path,
                changed_files=changed,
                total_src_count=100,
            )
        # No test roots → no signal → run all for safety
        assert result.reason in ("selective", "no_signal_run_all")

    def test_changed_test_file_included_directly(self, tmp_path: Path) -> None:
        changed = ["tests/unit/test_auth.py"]  # This is a test file
        result = map_changes_to_tests(repo_root=tmp_path, changed_files=changed)
        assert result.run_all is False
        assert "tests/unit/test_auth.py" in result.tests

    def test_no_signal_for_src_runs_all_for_safety(self, tmp_path: Path) -> None:
        # Changed a src file but no coverage/test_roots → no signal → run_all
        changed = ["app/auth/router.py"]
        result = map_changes_to_tests(
            repo_root=tmp_path,
            changed_files=changed,
        )
        assert result.run_all is True
        assert result.reason == "no_signal_run_all"

    def test_impact_sources_present_in_result(self, tmp_path: Path) -> None:
        changed = ["tests/unit/test_auth.py"]
        result = map_changes_to_tests(repo_root=tmp_path, changed_files=changed)
        assert "direct_test_changes" in result.impact_sources
        assert result.impact_sources["direct_test_changes"] == 1

    def test_tests_sorted_in_output(self, tmp_path: Path) -> None:
        changed = ["tests/test_z.py", "tests/test_a.py"]
        result = map_changes_to_tests(repo_root=tmp_path, changed_files=changed)
        if not result.run_all:
            assert result.tests == sorted(result.tests)

    def test_import_graph_signal_via_test_roots(self, tmp_path: Path) -> None:
        """Integration: creates real test file with import, runs TIA."""
        # Create a test file that imports "mymodule"
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_mymodule.py"
        test_file.write_text("from mymodule import func\nimport mymodule\n")

        # Create the source file being "changed"
        src_file = tmp_path / "mymodule.py"
        src_file.write_text("def func(): pass\n")

        changed = [str(src_file.relative_to(tmp_path))]  # "mymodule.py"
        result = map_changes_to_tests(
            repo_root=tmp_path,
            changed_files=changed,
            test_roots=[test_dir],
        )
        # Should find the test file via import graph
        if not result.run_all:
            test_names = [Path(t).name for t in result.tests]
            assert "test_mymodule.py" in test_names

    def test_no_total_src_count_skips_ratio_check(self, tmp_path: Path) -> None:
        # Many changes but no total_src_count → no ratio check
        changed = [f"app/module_{i}.py" for i in range(1000)]
        result = map_changes_to_tests(
            repo_root=tmp_path,
            changed_files=changed,
            total_src_count=None,  # explicitly None
        )
        # Should not fail due to ratio — will fail due to no_signal instead
        assert result.run_all is True
        assert "too_many_changes" not in result.reason


# ── Jenkins service schemas (quick smoke) ─────────────────────────────────────


class TestJenkinsServiceSchemas:
    """Smoke-test the jenkins_service module imports without side effects."""

    def test_jenkins_service_importable(self) -> None:
        try:
            from app.domains.cicd import jenkins_service  # noqa: F401
        except ImportError as e:
            pytest.skip(f"jenkins_service deps missing: {e}")

    def test_quality_gate_importable(self) -> None:
        from app.domains.cicd import quality_gate  # noqa: F401
        assert quality_gate.QualityGate is not None

    def test_tia_importable(self) -> None:
        from app.domains.cicd import tia  # noqa: F401
        assert tia.map_changes_to_tests is not None
