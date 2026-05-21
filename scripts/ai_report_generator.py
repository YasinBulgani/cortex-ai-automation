#!/usr/bin/env python3
"""
AI Report Generator — Test sonuçlarını AI ile zenginleştirerek rapor üretir.

Çıktılar:
  - HTML rapor (dashboard)
  - JSON rapor (API)
  - Markdown rapor (PR comment)
  - AI insights (pattern analiz)
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from core.feedback_loop.collector import ResultCollector
from core.feedback_loop.analyzer import PatternAnalyzer


def generate_markdown_report(output_dir: str = "reports") -> str:
    """Markdown formatında AI test raporu üret."""
    collector = ResultCollector()
    analyzer = PatternAnalyzer()

    history = collector.get_history(limit=10)
    insights = analyzer.analyze(history) if history else []

    lines = [
        "# AI Test Otomasyon Raporu",
        f"\n> Oluşturulma: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## Özet\n",
    ]

    if history:
        latest = history[-1]
        lines.append(f"| Metrik | Değer |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Toplam Test | {latest.get('total', 0)} |")
        lines.append(f"| Başarılı | {latest.get('passed', 0)} |")
        lines.append(f"| Başarısız | {latest.get('failed', 0)} |")
        lines.append(f"| Healed | {latest.get('healed', 0)} |")
        lines.append(f"| Flaky | {latest.get('flaky', 0)} |")
        lines.append(f"| Pass Rate | {latest.get('pass_rate', 0)}% |")
        lines.append(f"| Süre | {latest.get('duration_ms', 0)/1000:.1f}s |")
    else:
        lines.append("Henüz execution verisi yok.")

    if insights:
        lines.append("\n## AI Insights\n")
        for insight in insights:
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
                insight.severity, "⚪"
            )
            lines.append(f"### {icon} {insight.type}")
            lines.append(f"\n{insight.description}\n")
            lines.append(f"**Öneri:** {insight.suggestion}\n")
            if insight.affected_tests:
                lines.append("**Etkilenen testler:**")
                for t in insight.affected_tests[:10]:
                    lines.append(f"  - `{t}`")
            lines.append("")

    if len(history) > 1:
        lines.append("\n## Trend\n")
        lines.append("| Run | Total | Pass | Fail | Healed | Rate |")
        lines.append("|-----|-------|------|------|--------|------|")
        for run in history[-5:]:
            lines.append(
                f"| {run.get('run_id', '?')[:8]} "
                f"| {run.get('total', 0)} "
                f"| {run.get('passed', 0)} "
                f"| {run.get('failed', 0)} "
                f"| {run.get('healed', 0)} "
                f"| {run.get('pass_rate', 0)}% |"
            )

    report = "\n".join(lines)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ai_test_report.md").write_text(report, encoding="utf-8")

    json_report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "history_count": len(history),
        "latest_run": history[-1] if history else None,
        "insights": [
            {
                "type": i.type,
                "severity": i.severity,
                "description": i.description,
                "suggestion": i.suggestion,
                "affected_tests": i.affected_tests,
            }
            for i in insights
        ],
    }
    (out / "ai_test_report.json").write_text(
        json.dumps(json_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return report


def main():
    parser = argparse.ArgumentParser(description="AI test report generator")
    parser.add_argument("--output-dir", default="reports", help="Output directory")
    args = parser.parse_args()

    report = generate_markdown_report(args.output_dir)
    print(report)
    print(f"\nReports saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
