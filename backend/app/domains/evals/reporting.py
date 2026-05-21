"""Eval raporlama — JSON (her zaman) + HTML/Markdown özet.

Dosya konumu: ``reports/evals/<timestamp>/<suite>.json`` ve ``index.html``.
Base dir ENV ile override edilebilir (``EVAL_REPORTS_DIR``).

Tasarım:
    * JSON: tam SuiteResult (Pydantic ``.model_dump(mode='json')``)
    * HTML: minimal, bağımsız (CDN yok); scorer bazlı renkli tablo.
    * Markdown: CI step summary ve lokal hızlı okuma için kısa kalite özeti.
    * Exit kod hesabı burada değil — CLI sorumluluğu.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List

from .schemas import SuiteResult

logger = logging.getLogger(__name__)


def _base_dir() -> Path:
    raw = os.environ.get("EVAL_REPORTS_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "reports" / "evals"


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d-%H%M%S")


def _fmt_metric(value: float) -> str:
    return f"{value:.4f}"


def write_reports(
    results: Iterable[SuiteResult],
    *,
    out_dir: Path | None = None,
) -> Path:
    """Tüm suite sonuçlarını diske yaz. Çıkış: kök dizin path'i."""
    results_list: List[SuiteResult] = list(results)
    ts_dir = (out_dir or _base_dir()) / _fmt_ts(datetime.now(timezone.utc))
    ts_dir.mkdir(parents=True, exist_ok=True)

    for res in results_list:
        json_path = ts_dir / f"{res.suite_name}.json"
        try:
            json_path.write_text(
                json.dumps(
                    res.model_dump(mode="json"), ensure_ascii=False, indent=2
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Eval JSON yazılamadı (%s): %s", json_path, exc)

    html_path = ts_dir / "index.html"
    try:
        html_path.write_text(_render_html(results_list), encoding="utf-8")
    except OSError as exc:
        logger.warning("Eval HTML yazılamadı: %s", exc)

    generated_at = datetime.now(timezone.utc)
    markdown = _render_markdown(results_list, generated_at=generated_at)
    md_path = ts_dir / "summary.md"
    try:
        md_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        logger.warning("Eval markdown yazılamadı (%s): %s", md_path, exc)

    latest_md = ts_dir.parent / "latest.md"
    latest_json = ts_dir.parent / "latest.json"
    try:
        latest_md.write_text(markdown, encoding="utf-8")
        latest_json.write_text(
            json.dumps(
                {
                    "generated_at": generated_at.isoformat(),
                    "report_dir": str(ts_dir),
                    "suites": [
                        res.model_dump(mode="json") for res in results_list
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Eval latest özet yazılamadı: %s", exc)

    _append_history(results_list, ts_dir=ts_dir, generated_at=generated_at)
    return ts_dir


def latest_report(*, base_dir: Path | None = None) -> dict[str, Any] | None:
    """Son eval raporunu oku. Rapor yoksa None döner."""
    path = (base_dir or _base_dir()) / "latest.json"
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Eval latest raporu okunamadı (%s): %s", path, exc)
        return None


def history_report(
    *,
    limit: int = 50,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Eval history JSONL dosyasından son N koşumu döndür."""
    path = (base_dir or _base_dir()) / "history.jsonl"
    try:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                rows.append(parsed)
        return rows[-max(1, limit):]
    except OSError as exc:
        logger.warning("Eval history okunamadı (%s): %s", path, exc)
        return []


def history_summary(
    *,
    limit: int = 30,
    base_dir: Path | None = None,
    stale_hours: int = 24,
) -> dict[str, Any]:
    """Dashboard ve quality gate için eval history özetini üret."""
    rows = history_report(limit=limit, base_dir=base_dir)
    latest = rows[-1] if rows else None
    previous = rows[-2] if len(rows) > 1 else None

    if not latest:
        return {
            "status": "unknown",
            "total_runs": 0,
            "latest_generated_at": None,
            "latest_report_dir": None,
            "latest_pass_rate": 0.0,
            "latest_latency_ms": 0,
            "previous_pass_rate": None,
            "pass_rate_delta": None,
            "latency_delta_pct": None,
            "alerts": [
                {
                    "severity": "P2",
                    "metric": "eval_harness",
                    "message": "Henüz eval harness history kaydı yok.",
                }
            ],
            "suite_health": [],
            "runtime_matrix": [],
        }

    latest_pass_rate = _as_float(latest.get("case_pass_rate"))
    latest_latency = _as_int(latest.get("total_latency_ms"))
    previous_pass_rate = (
        _as_float(previous.get("case_pass_rate")) if previous else None
    )
    previous_latency = (
        _as_int(previous.get("total_latency_ms")) if previous else None
    )
    pass_rate_delta = (
        round(latest_pass_rate - previous_pass_rate, 6)
        if previous_pass_rate is not None
        else None
    )
    latency_delta_pct = (
        round((latest_latency - previous_latency) / previous_latency, 6)
        if previous_latency and previous_latency > 0
        else None
    )

    alerts: list[dict[str, Any]] = []
    if not bool(latest.get("overall_passed")):
        alerts.append(
            {
                "severity": "P1",
                "metric": "eval_harness",
                "message": "Son eval harness koşumu başarısız.",
            }
        )
    if pass_rate_delta is not None and pass_rate_delta <= -0.05:
        alerts.append(
            {
                "severity": "P1",
                "metric": "case_pass_rate",
                "message": (
                    "Case pass rate önceki koşuma göre "
                    f"{abs(pass_rate_delta) * 100:.1f} puan düştü."
                ),
            }
        )
    if latency_delta_pct is not None and latency_delta_pct >= 0.25:
        alerts.append(
            {
                "severity": "P2",
                "metric": "latency",
                "message": (
                    "Toplam eval latency önceki koşuma göre "
                    f"%{latency_delta_pct * 100:.1f} arttı."
                ),
            }
        )

    generated_at = _parse_dt(str(latest.get("generated_at") or ""))
    if generated_at:
        age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600
        if age_hours > stale_hours:
            alerts.append(
                {
                    "severity": "P2",
                    "metric": "freshness",
                    "message": f"Son eval koşumu {age_hours:.1f} saat eski.",
                }
            )

    suite_health = _suite_health(rows)
    runtime_matrix = _runtime_matrix(latest_report(base_dir=base_dir))
    has_p1 = any(alert.get("severity") == "P1" for alert in alerts)
    status = "fail" if has_p1 else "warn" if alerts else "pass"

    return {
        "status": status,
        "total_runs": len(rows),
        "latest_generated_at": latest.get("generated_at"),
        "latest_report_dir": latest.get("report_dir"),
        "latest_pass_rate": latest_pass_rate,
        "latest_latency_ms": latest_latency,
        "previous_pass_rate": previous_pass_rate,
        "pass_rate_delta": pass_rate_delta,
        "latency_delta_pct": latency_delta_pct,
        "alerts": alerts,
        "suite_health": suite_health,
        "runtime_matrix": runtime_matrix,
    }


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _suite_health(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_suite: dict[str, dict[str, Any]] = {}
    for row in rows:
        for suite in row.get("suites") or []:
            if not isinstance(suite, dict):
                continue
            name = str(suite.get("name") or "unknown")
            item = by_suite.setdefault(
                name,
                {
                    "name": name,
                    "adapter": str(suite.get("adapter") or "-"),
                    "runs": 0,
                    "passed_runs": 0,
                    "case_pass_rates": [],
                    "latest_passed": False,
                    "latest_case_pass_rate": 0.0,
                    "latest_latency_ms": 0,
                    "latest_threshold_failures": [],
                },
            )
            case_pass_rate = _as_float(suite.get("case_pass_rate"))
            item["runs"] += 1
            item["passed_runs"] += 1 if bool(suite.get("passed")) else 0
            item["case_pass_rates"].append(case_pass_rate)
            item["adapter"] = str(suite.get("adapter") or item["adapter"])
            item["latest_passed"] = bool(suite.get("passed"))
            item["latest_case_pass_rate"] = case_pass_rate
            item["latest_latency_ms"] = _as_int(suite.get("total_latency_ms"))
            failures = suite.get("threshold_failures") or []
            item["latest_threshold_failures"] = (
                failures if isinstance(failures, list) else []
            )

    out: list[dict[str, Any]] = []
    for item in by_suite.values():
        runs = max(1, _as_int(item["runs"], 1))
        pass_rate = item["passed_runs"] / runs
        avg_case = sum(item["case_pass_rates"]) / len(item["case_pass_rates"])
        if not item["latest_passed"]:
            status = "fail"
        elif pass_rate < 1.0 or avg_case < 0.98:
            status = "warn"
        else:
            status = "pass"
        out.append(
            {
                "name": item["name"],
                "adapter": item["adapter"],
                "status": status,
                "runs": item["runs"],
                "pass_rate": round(pass_rate, 6),
                "avg_case_pass_rate": round(avg_case, 6),
                "latest_passed": item["latest_passed"],
                "latest_case_pass_rate": item["latest_case_pass_rate"],
                "latest_latency_ms": item["latest_latency_ms"],
                "latest_threshold_failures": item["latest_threshold_failures"],
            }
        )
    return sorted(out, key=lambda item: (item["status"] != "fail", item["name"]))


def _runtime_matrix(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    counts: dict[tuple[str, str], dict[str, Any]] = {}
    for suite in report.get("suites") or []:
        if not isinstance(suite, dict):
            continue
        for case in suite.get("cases") or []:
            if not isinstance(case, dict):
                continue
            actual = case.get("actual") or {}
            if not isinstance(actual, dict):
                actual = {}
            provider = str(actual.get("provider_used") or "-")
            model = str(actual.get("model_used") or "-")
            attempts = actual.get("attempts") or []
            if not isinstance(attempts, list):
                attempts = []
            item = counts.setdefault(
                (provider, model),
                {"provider": provider, "model": model, "cases": 0, "attempts": 0},
            )
            item["cases"] += 1
            item["attempts"] += len(attempts)
    return sorted(
        counts.values(),
        key=lambda item: (-_as_int(item["cases"]), item["provider"], item["model"]),
    )


def _append_history(
    results: list[SuiteResult],
    *,
    ts_dir: Path,
    generated_at: datetime,
) -> None:
    """Kısa run özetini append-only JSONL history'ye yaz."""
    base = ts_dir.parent
    history_path = base / "history.jsonl"
    total_cases = sum(len(res.cases) for res in results)
    passed_cases = sum(res.count_passed() for res in results)
    total_latency_ms = sum(res.total_latency_ms for res in results)
    row = {
        "generated_at": generated_at.isoformat(),
        "report_dir": str(ts_dir),
        "overall_passed": bool(results) and all(res.passed for res in results),
        "total_suites": len(results),
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "case_pass_rate": round(passed_cases / total_cases, 6) if total_cases else 0.0,
        "total_latency_ms": total_latency_ms,
        "suites": [
            {
                "name": res.suite_name,
                "adapter": res.adapter_name,
                "passed": res.passed,
                "skipped": res.aggregate.get("skipped") == 1.0,
                "cases_total": len(res.cases),
                "cases_passed": res.count_passed(),
                "case_pass_rate": res.aggregate.get("case_pass_rate", 0.0),
                "total_latency_ms": res.total_latency_ms,
                "aggregate": res.aggregate,
                "threshold_failures": res.threshold_failures,
            }
            for res in results
        ],
    }
    try:
        with history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Eval history yazılamadı (%s): %s", history_path, exc)


# ── HTML render (minimal) ────────────────────────────────────────────────


_HTML_HEAD = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Eval Rapor</title>
<style>
  body{font:14px/1.4 system-ui;margin:24px;color:#222}
  h1{margin-top:0}
  table{border-collapse:collapse;margin:12px 0;width:100%}
  th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top}
  th{background:#f5f5f5;font-weight:600}
  .pass{background:#e6f7e6}
  .fail{background:#fde8e8}
  .skip{background:#fff4d6}
  .muted{color:#888}
  .suite{margin-bottom:28px}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600}
  .b-pass{background:#1f8a3d;color:#fff}
  .b-fail{background:#b31313;color:#fff}
  .b-skip{background:#a66b00;color:#fff}
  code{background:#f2f2f2;padding:1px 4px;border-radius:3px}
</style></head><body>
"""

_HTML_TAIL = "</body></html>"


def _suite_badge(res: SuiteResult) -> str:
    if res.aggregate.get("skipped") == 1.0:
        return '<span class="badge b-skip">SKIPPED</span>'
    return (
        '<span class="badge b-pass">PASS</span>'
        if res.passed
        else '<span class="badge b-fail">FAIL</span>'
    )


def _row_class(passed: bool, skipped: bool) -> str:
    if skipped:
        return "skip"
    return "pass" if passed else "fail"


def _render_suite(res: SuiteResult) -> str:
    skipped = res.aggregate.get("skipped") == 1.0
    rows: List[str] = []
    for cr in res.cases:
        score_cells = ", ".join(
            f"<code>{s.name}={_fmt_metric(s.value)}</code>" for s in cr.scores
        )
        err = f"<div class='muted'>hata: {cr.error}</div>" if cr.error else ""
        rows.append(
            f"<tr class='{_row_class(cr.passed, False)}'>"
            f"<td>{cr.case_id}</td>"
            f"<td>{'PASS' if cr.passed else 'FAIL'}</td>"
            f"<td>{score_cells}</td>"
            f"<td class='muted'>{cr.latency_ms} ms</td>"
            f"<td>{err}</td>"
            f"</tr>"
        )

    agg_rows = "".join(
        f"<tr><td>{k}</td><td>{_fmt_metric(v) if isinstance(v, float) else v}</td></tr>"
        for k, v in sorted(res.aggregate.items())
    )
    thresh_list = (
        "<ul>"
        + "".join(f"<li class='muted'>{f}</li>" for f in res.threshold_failures)
        + "</ul>"
        if res.threshold_failures
        else "<p class='muted'>— hiçbir threshold ihlali yok —</p>"
    )

    return (
        f"<section class='suite'>"
        f"<h2>{res.suite_name} {_suite_badge(res)}</h2>"
        f"<p class='muted'>adapter: <code>{res.adapter_name}</code> · "
        f"toplam süre {res.total_latency_ms} ms · "
        f"{res.count_passed()}/{len(res.cases)} case pass</p>"
        f"<h3>Aggregate</h3>"
        f"<table><tr><th>Metrik</th><th>Değer</th></tr>{agg_rows}</table>"
        f"<h3>Threshold</h3>{thresh_list}"
        + (
            "<h3>Cases</h3><table><tr>"
            "<th>ID</th><th>Durum</th><th>Scorer'lar</th><th>Gecikme</th><th>Not</th>"
            f"</tr>{''.join(rows)}</table>"
            if res.cases
            else "<p class='muted'>(hiç case yok / skip)</p>"
        )
        + "</section>"
    )


def _render_html(results: List[SuiteResult]) -> str:
    if not results:
        return _HTML_HEAD + "<p>Hiç suite çalışmadı.</p>" + _HTML_TAIL

    any_fail = any(not r.passed for r in results)
    header_badge = (
        '<span class="badge b-fail">OVERALL FAIL</span>'
        if any_fail
        else '<span class="badge b-pass">OVERALL PASS</span>'
    )
    sections = "\n".join(_render_suite(r) for r in results)
    return (
        _HTML_HEAD
        + f"<h1>Eval Raporu {header_badge}</h1>"
        + f"<p class='muted'>{datetime.now(timezone.utc).isoformat()}</p>"
        + sections
        + _HTML_TAIL
    )


# ── Markdown render ──────────────────────────────────────────────────────


def _md_escape(value: object) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _status_text(res: SuiteResult) -> str:
    if res.aggregate.get("skipped") == 1.0:
        return "SKIP"
    return "PASS" if res.passed else "FAIL"


def _metric_summary(res: SuiteResult) -> str:
    pairs = [
        (key.removeprefix("mean_"), value)
        for key, value in sorted(res.aggregate.items())
        if key.startswith("mean_")
    ]
    if not pairs:
        return "-"
    return ", ".join(f"{name}={float(value):.3f}" for name, value in pairs)


def _case_runtime_summary(actual: dict) -> str:
    provider = actual.get("provider_used") or "-"
    model = actual.get("model_used") or "-"
    attempts = actual.get("attempts") or []
    if not isinstance(attempts, list):
        attempts = []
    return f"{provider} / {model} / attempts={len(attempts)}"


def _render_markdown(
    results: List[SuiteResult],
    *,
    generated_at: datetime | None = None,
) -> str:
    generated_at_iso = (generated_at or datetime.now(timezone.utc)).isoformat()
    overall_passed = bool(results) and all(r.passed for r in results)
    total_cases = sum(len(r.cases) for r in results)
    passed_cases = sum(r.count_passed() for r in results)
    total_latency = sum(r.total_latency_ms for r in results)

    lines: List[str] = [
        "# Eval Quality Report",
        "",
        f"- Generated: `{generated_at_iso}`",
        f"- Overall: **{'PASS' if overall_passed else 'FAIL'}**",
        f"- Cases: **{passed_cases}/{total_cases}**",
        f"- Total latency: **{total_latency} ms**",
        "",
        "## Suites",
        "",
        "| Suite | Status | Cases | Case Pass Rate | Latency | Metrics |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for res in results:
        case_total = len(res.cases)
        pass_rate = res.aggregate.get("case_pass_rate", 0.0)
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_escape(res.suite_name),
                    _status_text(res),
                    f"{res.count_passed()}/{case_total}",
                    f"{float(pass_rate):.3f}",
                    f"{res.total_latency_ms} ms",
                    _md_escape(_metric_summary(res)),
                ]
            )
            + " |"
        )

    failures = [
        f"`{res.suite_name}`: {failure}"
        for res in results
        for failure in res.threshold_failures
        if not str(failure).startswith("SKIPPED:")
    ]
    if failures:
        lines.extend(["", "## Threshold Failures", ""])
        lines.extend(f"- {item}" for item in failures)

    case_rows: List[str] = []
    for res in results:
        for cr in res.cases:
            score_text = ", ".join(
                f"{score.name}={score.value:.3f}" for score in cr.scores
            )
            case_rows.append(
                "| "
                + " | ".join(
                    [
                        _md_escape(res.suite_name),
                        _md_escape(cr.case_id),
                        "PASS" if cr.passed else "FAIL",
                        f"{cr.latency_ms} ms",
                        _md_escape(_case_runtime_summary(cr.actual)),
                        _md_escape(score_text or "-"),
                    ]
                )
                + " |"
            )

    if case_rows:
        lines.extend(
            [
                "",
                "## Cases",
                "",
                "| Suite | Case | Status | Latency | Runtime | Scores |",
                "|---|---|---:|---:|---|---|",
                *case_rows,
            ]
        )

    return "\n".join(lines) + "\n"
