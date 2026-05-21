"""Eval runner + loader + reporting uçtan uca testleri.

``static_fixture`` adapter ile gateway/model bağımlılığı yok; harness'in
kendisini test ediyoruz.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.domains.evals.adapters import register_adapter
from app.domains.evals.loader import load_suite_file, load_suites
from app.domains.evals.reporting import history_report, history_summary, write_reports
from app.domains.evals.runner import run_suite, run_suites
from app.domains.evals.schemas import Suite


def _write_suite(tmp_path: Path, data: dict, filename: str = "x.yaml") -> Path:
    path = tmp_path / filename
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


# ── Loader ──────────────────────────────────────────────────────────────────


def test_loader_minimal(tmp_path: Path) -> None:
    path = _write_suite(
        tmp_path,
        {
            "name": "t",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "cases": [
                {
                    "id": "c1",
                    "inputs": {"_fixture": {"top_1": "x"}},
                    "expected": {"top_1": "x"},
                }
            ],
        },
    )
    suite = load_suite_file(path)
    assert suite.name == "t"
    assert suite.adapter_name == "static_fixture"
    assert len(suite.cases) == 1


def test_loader_rejects_missing_adapter(tmp_path: Path) -> None:
    path = _write_suite(
        tmp_path,
        {
            "name": "t",
            "scorers": ["exact_match"],
            "cases": [{"id": "c1", "inputs": {}, "expected": {}}],
        },
    )
    with pytest.raises(ValueError, match="adapter"):
        load_suite_file(path)


def test_loader_rejects_empty_cases(tmp_path: Path) -> None:
    path = _write_suite(
        tmp_path,
        {
            "name": "t",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "cases": [],
        },
    )
    with pytest.raises(ValueError, match="case"):
        load_suite_file(path)


def test_loader_directory_skips_non_yaml(tmp_path: Path) -> None:
    _write_suite(
        tmp_path,
        {
            "name": "a",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "cases": [
                {
                    "id": "c",
                    "inputs": {"_fixture": {"top_1": "x"}},
                    "expected": {"top_1": "x"},
                }
            ],
        },
        filename="a.yaml",
    )
    (tmp_path / "readme.md").write_text("ignored")
    suites = load_suites(tmp_path)
    assert [s.name for s in suites] == ["a"]


def test_loader_rejects_duplicate_suite_names(tmp_path: Path) -> None:
    base = {
        "name": "same",
        "adapter": "static_fixture",
        "scorers": ["exact_match"],
        "cases": [
            {
                "id": "c",
                "inputs": {"_fixture": {"top_1": "x"}},
                "expected": {"top_1": "x"},
            }
        ],
    }
    _write_suite(tmp_path, base, "a.yaml")
    _write_suite(tmp_path, base, "b.yaml")
    with pytest.raises(ValueError, match="Duplicate"):
        load_suites(tmp_path)


def test_loader_name_filter(tmp_path: Path) -> None:
    _write_suite(
        tmp_path,
        {
            "name": "a",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "cases": [
                {
                    "id": "c",
                    "inputs": {"_fixture": {"top_1": "x"}},
                    "expected": {"top_1": "x"},
                }
            ],
        },
        "a.yaml",
    )
    _write_suite(
        tmp_path,
        {
            "name": "b",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "cases": [
                {
                    "id": "c",
                    "inputs": {"_fixture": {"top_1": "x"}},
                    "expected": {"top_1": "x"},
                }
            ],
        },
        "b.yaml",
    )
    suites = load_suites(tmp_path, names=["b"])
    assert [s.name for s in suites] == ["b"]


# ── Runner ──────────────────────────────────────────────────────────────────


def _build_smoke_suite() -> Suite:
    return Suite.from_dict(
        {
            "name": "inline",
            "adapter": "static_fixture",
            "scorers": ["exact_match", "precision_at_1", "mrr"],
            "thresholds": {
                "mean": {
                    "exact_match": 1.0,
                    "precision_at_1": 1.0,
                    "mrr": 1.0,
                }
            },
            "cases": [
                {
                    "id": "a",
                    "inputs": {
                        "_fixture": {
                            "top_1": "x",
                            "ranked_ids": ["x", "y"],
                        }
                    },
                    "expected": {"top_1": "x", "relevant_ids": ["x"]},
                },
                {
                    "id": "b",
                    "inputs": {
                        "_fixture": {
                            "top_1": "p",
                            "ranked_ids": ["p", "q"],
                        }
                    },
                    "expected": {"top_1": "p", "relevant_ids": ["p"]},
                },
            ],
        }
    )


def test_runner_all_pass() -> None:
    res = run_suite(_build_smoke_suite())
    assert res.passed is True
    assert len(res.cases) == 2
    assert res.aggregate["case_pass_rate"] == 1.0
    assert res.aggregate["mean_exact_match"] == 1.0
    assert res.aggregate["mean_mrr"] == 1.0
    assert res.threshold_failures == []


def test_runner_threshold_failure() -> None:
    suite = Suite.from_dict(
        {
            "name": "fail",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "thresholds": {"mean": {"exact_match": 1.0}},
            "cases": [
                {
                    "id": "a",
                    "inputs": {"_fixture": {"top_1": "x"}},
                    "expected": {"top_1": "x"},
                },
                {
                    "id": "b",
                    "inputs": {"_fixture": {"top_1": "WRONG"}},
                    "expected": {"top_1": "y"},
                },
            ],
        }
    )
    res = run_suite(suite)
    assert res.passed is False
    assert res.count_passed() == 1
    assert any("mean_exact_match" in f for f in res.threshold_failures)


def test_runner_isolates_adapter_errors() -> None:
    # StaticFixture inputs._fixture yoksa ValueError atar → case fail, suite devam
    suite = Suite.from_dict(
        {
            "name": "err",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "cases": [
                {"id": "ok", "inputs": {"_fixture": {"top_1": "x"}}, "expected": {"top_1": "x"}},
                {"id": "bad", "inputs": {}, "expected": {"top_1": "x"}},
            ],
        }
    )
    res = run_suite(suite)
    assert res.cases[0].passed is True
    assert res.cases[1].passed is False
    assert res.cases[1].error is not None


def test_runner_skip_when_adapter_unavailable() -> None:
    class UnavailableAdapter:
        name = "unavailable_adapter_for_test"

        def available(self) -> bool:
            return False

        def run(self, inputs: dict) -> dict:
            raise RuntimeError("should not be called")

    register_adapter(UnavailableAdapter())
    suite = Suite.from_dict(
        {
            "name": "skipme",
            "adapter": "unavailable_adapter_for_test",
            "scorers": ["exact_match"],
            "cases": [
                {"id": "c", "inputs": {"_fixture": {}}, "expected": {}}
            ],
        }
    )
    res = run_suite(suite)
    assert res.passed is True  # skip CI kırmaz
    assert res.aggregate.get("skipped") == 1.0
    assert len(res.cases) == 0


def test_runner_deterministic_case_order() -> None:
    # Parallel çalışsa bile sonuçlar case listesindeki orijinal sırayı korumalı
    suite = _build_smoke_suite()
    res = run_suite(suite, max_workers=4)
    assert [c.case_id for c in res.cases] == ["a", "b"]


# ── Reporting ──────────────────────────────────────────────────────────────


def test_write_reports_produces_json_and_html(tmp_path: Path) -> None:
    results = run_suites([_build_smoke_suite()])
    out = write_reports(results, out_dir=tmp_path)
    assert out.exists()
    json_files = list(out.glob("*.json"))
    assert len(json_files) == 1
    data = json.loads(json_files[0].read_text())
    assert data["suite_name"] == "inline"
    assert data["passed"] is True

    html_file = out / "index.html"
    assert html_file.exists()
    text = html_file.read_text()
    assert "OVERALL PASS" in text
    assert "inline" in text

    summary_file = out / "summary.md"
    assert summary_file.exists()
    summary = summary_file.read_text()
    assert "# Eval Quality Report" in summary
    assert "| inline | PASS | 2/2 | 1.000 |" in summary

    latest_md = tmp_path / "latest.md"
    latest_json = tmp_path / "latest.json"
    assert latest_md.exists()
    assert latest_json.exists()
    assert "inline" in latest_md.read_text()
    latest = json.loads(latest_json.read_text())
    assert latest["suites"][0]["suite_name"] == "inline"


def test_history_summary_flags_failed_latest_run(tmp_path: Path) -> None:
    write_reports(run_suites([_build_smoke_suite()]), out_dir=tmp_path)
    failing_suite = Suite.from_dict(
        {
            "name": "inline",
            "adapter": "static_fixture",
            "scorers": ["exact_match"],
            "thresholds": {"mean": {"exact_match": 1.0}},
            "cases": [
                {
                    "id": "ok",
                    "inputs": {"_fixture": {"top_1": "x"}},
                    "expected": {"top_1": "x"},
                },
                {
                    "id": "bad",
                    "inputs": {"_fixture": {"top_1": "wrong"}},
                    "expected": {"top_1": "y"},
                },
            ],
        }
    )
    write_reports(run_suites([failing_suite]), out_dir=tmp_path)

    rows = history_report(limit=10, base_dir=tmp_path)
    assert len(rows) == 2

    summary = history_summary(limit=10, base_dir=tmp_path, stale_hours=999999)
    assert summary["status"] == "fail"
    assert summary["total_runs"] == 2
    assert summary["latest_pass_rate"] == 0.5
    assert summary["pass_rate_delta"] == -0.5
    assert summary["suite_health"][0]["status"] == "fail"
    assert any(alert["metric"] == "eval_harness" for alert in summary["alerts"])
