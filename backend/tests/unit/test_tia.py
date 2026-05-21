"""TIA unit testleri — is_test_file, import graph, coverage parser, orchestrator."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.cicd.tia import (
    CoverageMap,
    build_import_graph,
    impact_by_imports,
    is_test_file,
    map_changes_to_tests,
    parse_coverage_xml,
    parse_lcov,
)


# ── is_test_file ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path, expected",
    [
        ("tests/login.spec.ts", True),
        ("src/app/tests/helper.py", True),
        ("e2e/flows.spec.ts", True),
        ("apps/web/__tests__/Home.test.tsx", True),
        ("backend/tests/unit/test_config.py", True),
        ("backend/app/domains/ai/router.py", False),
        ("src/components/Button.tsx", False),
        ("test_not_in_dir.py", True),  # prefix match
        ("readme.md", False),
    ],
)
def test_is_test_file_patterns(path: str, expected: bool) -> None:
    assert is_test_file(path) is expected


# ── Coverage ─────────────────────────────────────────────────────────────


def test_parse_lcov_minimal(tmp_path: Path) -> None:
    (tmp_path / "lcov.info").write_text(
        "TN:\nSF:src/a.py\nDA:1,1\nend_of_record\nSF:src/b.py\nend_of_record\n",
        encoding="utf-8",
    )
    cm = parse_lcov(tmp_path / "lcov.info")
    assert "src/a.py" in cm.src_to_tests
    assert "src/b.py" in cm.src_to_tests


def test_parse_coverage_xml_with_contexts(tmp_path: Path) -> None:
    xml = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="app/foo.py">
          <lines>
            <line number="1" hits="1">
              <contexts>
                <context>tests/test_foo.py::test_one|run</context>
                <context>tests/test_bar.py::test_two|run</context>
              </contexts>
            </line>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
    p = tmp_path / "cov.xml"
    p.write_text(xml, encoding="utf-8")
    cm = parse_coverage_xml(p)
    assert cm.src_to_tests["app/foo.py"] == {"tests/test_foo.py", "tests/test_bar.py"}


def test_parse_coverage_xml_missing_file(tmp_path: Path) -> None:
    cm = parse_coverage_xml(tmp_path / "missing.xml")
    assert cm.src_to_tests == {}


def test_coverage_map_impacted_tests() -> None:
    cm = CoverageMap(
        src_to_tests={
            "app/a.py": {"tests/test_a.py"},
            "app/b.py": {"tests/test_a.py", "tests/test_b.py"},
        }
    )
    hit = cm.impacted_tests(["app/b.py"])
    assert hit == {"tests/test_a.py", "tests/test_b.py"}


# ── Import graph ─────────────────────────────────────────────────────────


def test_import_graph_python_absolute(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "mymod.py").write_text("X = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymod.py").write_text(
        "from app.mymod import X\n\ndef test_x():\n    assert X == 1\n"
    )

    graph = build_import_graph(tmp_path, test_roots=[tmp_path / "tests"])
    assert "app/mymod.py" in graph
    assert "tests/test_mymod.py" in graph["app/mymod.py"]


def test_import_graph_js_relative(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "utils.ts").write_text("export const x = 1;\n")
    (tmp_path / "src" / "__tests__").mkdir()
    (tmp_path / "src" / "__tests__" / "utils.spec.ts").write_text(
        "import { x } from '../utils';\n// test\n"
    )

    graph = build_import_graph(tmp_path, test_roots=[tmp_path / "src"])
    assert "src/utils.ts" in graph
    rel_test = "src/__tests__/utils.spec.ts"
    assert rel_test in graph["src/utils.ts"]


def test_impact_by_imports_basic() -> None:
    graph = {
        "app/a.py": {"tests/test_a.py"},
        "app/b.py": {"tests/test_a.py", "tests/test_b.py"},
    }
    hit = impact_by_imports(graph, ["app/b.py"])
    assert hit == {"tests/test_a.py", "tests/test_b.py"}


# ── map_changes_to_tests orchestrator ───────────────────────────────────


def test_no_changes_returns_empty(tmp_path: Path) -> None:
    r = map_changes_to_tests(repo_root=tmp_path, changed_files=[])
    assert r.run_all is False
    assert r.reason == "no_changes"


def test_direct_test_change_included(tmp_path: Path) -> None:
    r = map_changes_to_tests(
        repo_root=tmp_path,
        changed_files=["tests/test_x.py"],
    )
    assert r.run_all is False
    assert "tests/test_x.py" in r.tests
    assert r.impact_sources["direct_test_changes"] == 1


def test_no_signal_src_change_falls_back_to_run_all(tmp_path: Path) -> None:
    r = map_changes_to_tests(
        repo_root=tmp_path,
        changed_files=["app/unknown.py"],
    )
    assert r.run_all is True
    assert r.reason == "no_signal_run_all"


def test_too_many_changes_runs_all(tmp_path: Path) -> None:
    r = map_changes_to_tests(
        repo_root=tmp_path,
        changed_files=[f"app/f{i}.py" for i in range(40)],
        total_src_count=100,  # 40/100 = 0.40 > default 0.30
    )
    assert r.run_all is True
    assert "too_many_changes" in r.reason


def test_env_override_max_ratio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIA_MAX_IMPACT_RATIO", "0.60")
    r = map_changes_to_tests(
        repo_root=tmp_path,
        changed_files=[f"app/f{i}.py" for i in range(40)],
        total_src_count=100,  # 40/100 = 0.40 < 0.60
    )
    # Run all tetiklenmedi; no signal'den dolayı yine run_all olacak
    # ama reason farklı
    assert r.reason != "too_many_changes_40pct"


def test_full_flow_with_import_graph(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "mod.py").write_text("X = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(
        "from app.mod import X\n\ndef test_one():\n    assert X == 1\n"
    )
    (tmp_path / "tests" / "test_other.py").write_text(
        "def test_other():\n    assert True\n"
    )

    r = map_changes_to_tests(
        repo_root=tmp_path,
        changed_files=["app/mod.py"],
        test_roots=[tmp_path / "tests"],
    )
    assert r.run_all is False
    assert r.tests == ["tests/test_mod.py"]
    assert "tests/test_other.py" not in r.tests
    assert r.impact_sources["import_graph"] == 1


def test_mixed_sources_unioned(tmp_path: Path) -> None:
    # Coverage'dan 1, import'tan 1 farklı test — UNION 2 olmalı
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "mod.py").write_text("X = 1\n")
    (tmp_path / "tests").mkdir()
    # Import eder → import graph'tan yakalanır
    (tmp_path / "tests" / "test_import.py").write_text(
        "from app.mod import X\n\ndef test_x():\n    assert X\n"
    )
    # Direkt import etmez ama coverage rapor bu dosyayı bağlar
    (tmp_path / "tests" / "test_coverage.py").write_text(
        "def test_c():\n    assert True\n"
    )

    xml = """<?xml version="1.0"?>
<coverage>
  <packages><package><classes>
    <class filename="app/mod.py"><lines>
      <line number="1" hits="1"><contexts>
        <context>tests/test_coverage.py::test_c|run</context>
      </contexts></line>
    </lines></class>
  </classes></package></packages>
</coverage>
"""
    (tmp_path / "cov.xml").write_text(xml, encoding="utf-8")

    r = map_changes_to_tests(
        repo_root=tmp_path,
        changed_files=["app/mod.py"],
        coverage_paths=[tmp_path / "cov.xml"],
        test_roots=[tmp_path / "tests"],
    )
    assert r.run_all is False
    assert set(r.tests) == {"tests/test_import.py", "tests/test_coverage.py"}
    assert r.impact_sources["coverage_mapped"] == 1
    assert r.impact_sources["import_graph"] == 1
