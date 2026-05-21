#!/usr/bin/env python3
"""
metrics.py — Pipeline KPI / dashboard generator.

state.json'u okuyup pipeline sağlığı hakkında markdown veya JSON rapor üretir.

Kullanım:
    python3 scripts/pipeline/metrics.py [--format markdown|json] [--section all|summary|timing|loops|scope]

Metrikler:
    - Throughput (items/week) son 4 hafta
    - Active items by stage (heatmap)
    - Avg duration per stage (bottleneck tespiti)
    - Loop-back rate (hangi aşama en çok geri dönüyor)
    - Confidence distribution (karar kalitesi)
    - Auto-skip oranı (scope disiplini)
    - Items needing human (kritik liste)
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE = REPO_ROOT / "docs" / "ai" / "pipeline" / "state.json"
STAGES_CFG = REPO_ROOT / "docs" / "ai" / "pipeline" / "stages.json"


def parse_iso(ts):
    # type: (Optional[str]) -> Optional[datetime]
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def duration_minutes(start, end):
    # type: (Optional[datetime], Optional[datetime]) -> Optional[float]
    if not start or not end:
        return None
    return (end - start).total_seconds() / 60.0


def fmt_duration(minutes):
    # type: (Optional[float]) -> str
    if minutes is None:
        return "—"
    if minutes < 60:
        return "{:.0f}m".format(minutes)
    hours = minutes / 60
    if hours < 24:
        return "{:.1f}h".format(hours)
    days = hours / 24
    return "{:.1f}d".format(days)


def load_state():
    # type: () -> dict
    if not STATE.exists():
        return {"version": "2.0", "items": [], "next_ids": {}}
    with STATE.open(encoding="utf-8") as f:
        return json.load(f)


def load_stages_cfg():
    # type: () -> dict
    if not STAGES_CFG.exists():
        return {"stages": {}}
    with STAGES_CFG.open(encoding="utf-8") as f:
        return json.load(f)


def compute_kpis(state, stages_cfg):
    # type: (dict, dict) -> dict
    items = state.get("items", [])
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=28)

    kpi = {
        "generated_at": now.isoformat(),
        "total_items": len(items),
        "by_status": defaultdict(int),
        "by_type": defaultdict(int),
        "by_priority": defaultdict(int),
        "by_current_stage": defaultdict(int),
        "needs_human": [],
        "stuck_items": [],  # in_progress > 3 days
        "stage_durations": defaultdict(list),  # {stage: [minutes, ...]}
        "stage_waiting_now": defaultdict(int),
        "loop_back_counts": defaultdict(int),  # {to_stage: count}
        "loop_back_total": 0,
        "skip_counts": defaultdict(int),  # {stage: count of skipped}
        "confidence_samples": {
            "validator": [],
            "approver": [],
            "product_validator": [],
            "code_reviewer": [],
            "security_reviewer": [],
            "a11y_auditor": [],
            "performance_tester": [],
            "observer": [],
        },
        "throughput": {"last_week": 0, "last_month": 0},
        "cycle_times": [],  # pipeline start → retrospective done
    }

    for item in items:
        status = item.get("status", "unknown")
        kpi["by_status"][status] += 1
        kpi["by_type"][item.get("type", "?")] += 1
        kpi["by_priority"][item.get("priority", "medium")] += 1
        kpi["by_current_stage"][item.get("current_stage", "unknown")] += 1

        if item.get("needs_human"):
            kpi["needs_human"].append({
                "id": item["id"],
                "stage": item.get("current_stage"),
                "title": item.get("title", "")[:60],
            })

        # Stuck detection
        for stage_name, stage_data in item.get("stages", {}).items():
            if stage_data.get("status") == "in_progress":
                started = parse_iso(stage_data.get("started_at"))
                if started and (now - started).days >= 3:
                    kpi["stuck_items"].append({
                        "id": item["id"],
                        "stage": stage_name,
                        "days": (now - started).days,
                    })

            # Waiting now
            if stage_data.get("status") == "waiting":
                kpi["stage_waiting_now"][stage_name] += 1

            # Durations (done stages with both timestamps)
            if stage_data.get("status") == "done":
                start = parse_iso(stage_data.get("started_at"))
                end = parse_iso(stage_data.get("completed_at"))
                dur = duration_minutes(start, end)
                if dur is not None and dur >= 0:
                    kpi["stage_durations"][stage_name].append(dur)

            # Skipped
            if stage_data.get("status") == "skipped":
                kpi["skip_counts"][stage_name] += 1

            # Confidence
            approval = stage_data.get("approval") or {}
            conf = approval.get("confidence")
            if isinstance(conf, (int, float)) and stage_name in kpi["confidence_samples"]:
                kpi["confidence_samples"][stage_name].append(float(conf))

        # Loop-backs
        for fb in item.get("feedback_loops", []):
            kpi["loop_back_counts"][fb.get("to_stage", "?")] += 1
            kpi["loop_back_total"] += 1

        # Throughput (based on retrospective done timestamp; fall back to item status done)
        retro = (item.get("stages") or {}).get("retrospective") or {}
        done_at = parse_iso(retro.get("completed_at"))
        if status == "done" and done_at:
            if done_at >= week_ago:
                kpi["throughput"]["last_week"] += 1
            if done_at >= month_ago:
                kpi["throughput"]["last_month"] += 1

            # Cycle time
            analyzer_start = parse_iso(
                (item.get("stages") or {}).get("analyzer", {}).get("started_at")
            )
            if analyzer_start:
                ct_min = duration_minutes(analyzer_start, done_at)
                if ct_min is not None and ct_min > 0:
                    kpi["cycle_times"].append(ct_min)

    # Summary stats
    kpi["stage_stats"] = {}
    for stage, samples in kpi["stage_durations"].items():
        if samples:
            kpi["stage_stats"][stage] = {
                "count": len(samples),
                "avg_min": statistics.mean(samples),
                "median_min": statistics.median(samples),
                "max_min": max(samples),
                "p90_min": sorted(samples)[int(len(samples) * 0.9)] if len(samples) > 1 else samples[0],
            }

    kpi["confidence_stats"] = {}
    for stage, samples in kpi["confidence_samples"].items():
        if samples:
            kpi["confidence_stats"][stage] = {
                "count": len(samples),
                "avg": statistics.mean(samples),
                "min": min(samples),
                "low_confidence_count": sum(1 for c in samples if c < 0.7),
            }

    if kpi["cycle_times"]:
        kpi["cycle_time_stats"] = {
            "count": len(kpi["cycle_times"]),
            "avg_min": statistics.mean(kpi["cycle_times"]),
            "median_min": statistics.median(kpi["cycle_times"]),
            "p90_min": sorted(kpi["cycle_times"])[int(len(kpi["cycle_times"]) * 0.9)] if len(kpi["cycle_times"]) > 1 else kpi["cycle_times"][0],
        }

    # Convert defaultdicts for JSON
    for key in ("by_status", "by_type", "by_priority", "by_current_stage",
                "stage_waiting_now", "loop_back_counts", "skip_counts"):
        kpi[key] = dict(kpi[key])
    kpi["stage_durations"] = {k: v for k, v in kpi["stage_durations"].items()}

    return kpi


def render_markdown(kpi, sections):
    # type: (dict, List[str]) -> str
    out = []

    if "all" in sections or "summary" in sections:
        out.append("# Pipeline Metrics")
        out.append("")
        out.append(f"**Generated:** {kpi['generated_at']}")
        out.append(f"**Total items:** {kpi['total_items']}")
        out.append("")
        out.append("## Summary")
        out.append("")
        out.append("### By Status")
        out.append("")
        out.append("| Status | Count |")
        out.append("|---|---|")
        for s, c in sorted(kpi["by_status"].items(), key=lambda x: -x[1]):
            out.append(f"| {s} | {c} |")
        out.append("")

        out.append("### By Type")
        out.append("")
        out.append("| Type | Count |")
        out.append("|---|---|")
        for t, c in sorted(kpi["by_type"].items(), key=lambda x: -x[1]):
            out.append(f"| {t} | {c} |")
        out.append("")

        out.append("### Throughput")
        out.append("")
        out.append(f"- **Last 7 days:** {kpi['throughput']['last_week']} items completed")
        out.append(f"- **Last 28 days:** {kpi['throughput']['last_month']} items completed")
        out.append("")

        if "cycle_time_stats" in kpi:
            ct = kpi["cycle_time_stats"]
            out.append("### Cycle Time (analyzer → retrospective)")
            out.append("")
            out.append(f"- **Samples:** {ct['count']}")
            out.append(f"- **Median:** {fmt_duration(ct['median_min'])}")
            out.append(f"- **Avg:** {fmt_duration(ct['avg_min'])}")
            out.append(f"- **p90:** {fmt_duration(ct['p90_min'])}")
            out.append("")

    if "all" in sections or "timing" in sections:
        out.append("## Stage Durations (Bottleneck Analysis)")
        out.append("")
        if kpi.get("stage_stats"):
            out.append("| Stage | Samples | Median | Avg | p90 | Max |")
            out.append("|---|---|---|---|---|---|")
            for stage, stats in sorted(
                kpi["stage_stats"].items(), key=lambda x: -x[1]["avg_min"]
            ):
                out.append(
                    f"| {stage} | {stats['count']} | "
                    f"{fmt_duration(stats['median_min'])} | "
                    f"{fmt_duration(stats['avg_min'])} | "
                    f"{fmt_duration(stats['p90_min'])} | "
                    f"{fmt_duration(stats['max_min'])} |"
                )
        else:
            out.append("_No completed stages yet._")
        out.append("")

        # Current waiting stages
        out.append("### Currently Waiting (workload heatmap)")
        out.append("")
        if kpi["stage_waiting_now"]:
            out.append("| Stage | Waiting count |")
            out.append("|---|---|")
            for stage, c in sorted(kpi["stage_waiting_now"].items(), key=lambda x: -x[1]):
                out.append(f"| {stage} | {c} |")
        else:
            out.append("_Hiçbir aşama waiting değil (pipeline boş veya sıfır idle)._")
        out.append("")

    if "all" in sections or "loops" in sections:
        out.append("## Feedback Loops")
        out.append("")
        out.append(f"**Total:** {kpi['loop_back_total']}")
        out.append("")
        if kpi["loop_back_counts"]:
            out.append("| Target stage | Count |")
            out.append("|---|---|")
            for stage, c in sorted(kpi["loop_back_counts"].items(), key=lambda x: -x[1]):
                out.append(f"| {stage} | {c} |")
        else:
            out.append("_No feedback loops._")
        out.append("")

    if "all" in sections or "scope" in sections:
        out.append("## Auto-Skip / Scope Discipline")
        out.append("")
        total_skip = sum(kpi["skip_counts"].values())
        out.append(f"**Total skipped:** {total_skip}")
        out.append("")
        if kpi["skip_counts"]:
            out.append("| Stage | Skipped |")
            out.append("|---|---|")
            for stage, c in sorted(kpi["skip_counts"].items(), key=lambda x: -x[1]):
                out.append(f"| {stage} | {c} |")
        out.append("")

    if "all" in sections or "confidence" in sections:
        out.append("## Confidence Distribution (Decision Quality)")
        out.append("")
        if kpi.get("confidence_stats"):
            out.append("| Stage | Samples | Avg | Min | Low-confidence (<0.7) |")
            out.append("|---|---|---|---|---|")
            for stage, stats in sorted(kpi["confidence_stats"].items()):
                out.append(
                    f"| {stage} | {stats['count']} | "
                    f"{stats['avg']:.2f} | {stats['min']:.2f} | "
                    f"{stats['low_confidence_count']} |"
                )
        else:
            out.append("_No approval decisions logged yet._")
        out.append("")

    if "all" in sections or "alerts" in sections:
        out.append("## Alerts")
        out.append("")
        if kpi["needs_human"]:
            out.append("### ⚠ Needs human intervention")
            out.append("")
            out.append("| ID | Stage | Title |")
            out.append("|---|---|---|")
            for item in kpi["needs_human"]:
                out.append(f"| {item['id']} | {item['stage']} | {item['title']} |")
            out.append("")
        if kpi["stuck_items"]:
            out.append("### ⚠ Stuck (in_progress > 3 days)")
            out.append("")
            out.append("| ID | Stage | Days |")
            out.append("|---|---|---|")
            for item in kpi["stuck_items"]:
                out.append(f"| {item['id']} | {item['stage']} | {item['days']} |")
            out.append("")
        if not kpi["needs_human"] and not kpi["stuck_items"]:
            out.append("_No alerts — all items healthy._")
            out.append("")

    return "\n".join(out)


def render_json(kpi):
    # type: (dict) -> str
    return json.dumps(kpi, indent=2, default=str)


def main():
    # type: () -> int
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument(
        "--section",
        choices=["all", "summary", "timing", "loops", "scope", "confidence", "alerts"],
        default="all",
    )
    args = parser.parse_args()

    try:
        state = load_state()
        stages_cfg = load_stages_cfg()
        kpi = compute_kpis(state, stages_cfg)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(render_json(kpi))
    else:
        sections = ["all"] if args.section == "all" else [args.section]
        print(render_markdown(kpi, sections))

    return 0


if __name__ == "__main__":
    sys.exit(main())
