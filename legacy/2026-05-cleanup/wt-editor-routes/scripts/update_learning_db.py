#!/usr/bin/env python3
"""
Update Learning DB — Feedback loop veritabanını CI/CD pipeline sonuçlarıyla günceller.

Playwright JSON raporunu okuyarak execution history'ye kaydeder.
Ayrıca RiskScorer geçmişini günceller.
"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from core.feedback_loop.collector import ResultCollector, TestExecutionRecord
from core.feedback_loop.analyzer import PatternAnalyzer
from core.feedback_loop.optimizer import SuiteOptimizer


def _walk_suites(suites: list) -> list[dict]:
    """Recursively walk nested Playwright suite structure."""
    specs = []
    for suite in suites:
        specs.extend(suite.get("specs", []))
        specs.extend(_walk_suites(suite.get("suites", [])))
    return specs


def parse_playwright_results(report_path: str) -> list[TestExecutionRecord]:
    """Playwright JSON raporunu recursive olarak parse et."""
    path = Path(report_path)
    if not path.exists():
        print(f"Report not found: {report_path}", file=sys.stderr)
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    all_specs = _walk_suites(data.get("suites", []))

    for spec in all_specs:
        for test in spec.get("tests", []):
            test_title = test.get("title", spec.get("title", "unknown"))
            for result in test.get("results", []):
                status_map = {
                    "passed": "pass", "failed": "fail",
                    "skipped": "skip", "timedOut": "fail",
                }
                file_stem = Path(spec.get("file", "")).stem
                test_id = file_stem or test_title.replace(" ", "_")

                records.append(TestExecutionRecord(
                    test_id=test_id,
                    test_name=test_title,
                    status=status_map.get(result.get("status", ""), "fail"),
                    duration_ms=result.get("duration", 0),
                    error=str(result.get("error", {}).get("message", ""))[:500] if result.get("error") else "",
                    retry_count=result.get("retry", 0),
                ))
    return records


def update_risk_scorer(records: list[TestExecutionRecord]) -> None:
    """RiskScorer geçmişini test sonuçlarıyla güncelle."""
    try:
        from core.ai_prioritizer.risk_scorer import RiskScorer
        scorer = RiskScorer()
        for record in records:
            scorer.record_result(record.test_id, record.status == "pass")
        print(f"RiskScorer updated with {len(records)} results")
    except Exception as e:
        print(f"RiskScorer update failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Update learning DB from CI results")
    parser.add_argument("--report", default="reports/e2e-results.json", help="Playwright JSON report")
    parser.add_argument("--run-id", default=None, help="Run ID (auto-generated if empty)")
    parser.add_argument("--optimize", action="store_true", help="Run suite optimization")
    args = parser.parse_args()

    run_id = args.run_id or f"run-{uuid.uuid4().hex[:8]}"

    records = parse_playwright_results(args.report)
    if not records:
        print("No test results found to process")
        sys.exit(0)

    collector = ResultCollector()
    collector.record_batch(records)
    summary = collector.finalize_run(run_id)

    print(f"Recorded {summary.total} tests (pass={summary.passed}, fail={summary.failed}, "
          f"healed={summary.healed}, rate={summary.pass_rate}%)")

    update_risk_scorer(records)

    analyzer = PatternAnalyzer()
    history = collector.get_history()
    insights = analyzer.analyze(history)

    if insights:
        print(f"\nAI Insights ({len(insights)}):")
        for insight in insights:
            print(f"  [{insight.severity}] {insight.type}: {insight.description}")

    if args.optimize:
        optimizer = SuiteOptimizer()
        report = optimizer.optimize(history)
        print(f"\nOptimization: {len(report.actions)} actions, "
              f"quality score: {report.quality_score}")
        for action in report.actions:
            tag = "AUTO" if action.auto_applied else "SUGGEST"
            print(f"  [{tag}] {action.action_type}: {action.test_id} — {action.reason}")


if __name__ == "__main__":
    main()
