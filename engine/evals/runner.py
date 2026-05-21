"""
Engine Eval Runner — CI gate + nightly regression

Kullanım:
    python engine/evals/runner.py                  # tüm fixtures
    python engine/evals/runner.py --fixtures 01,03 # seçili fixtures
    python engine/evals/runner.py --threshold 60   # custom pass threshold

Çıkış kodları:
    0  — tüm fixture'lar passed (score >= threshold)
    1  — runner hatası (import, dosya bulunamadı vs.)
    2  — gate başarısız (mapping_accuracy < threshold)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
FIXTURES_DIR = ROOT / "fixtures"
REPORTS_DIR = ROOT / "reports"

# Scorer import — engine path'i ayarla
sys.path.insert(0, str(ROOT.parent.parent))
try:
    from engine.evals.scorer import score_gherkin, score_playwright, score_python_test, ScoreResult
except ImportError:
    # Fallback: doğrudan import
    import importlib.util
    spec = importlib.util.spec_from_file_location("scorer", ROOT / "scorer.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    score_gherkin = mod.score_gherkin
    score_playwright = mod.score_playwright
    score_python_test = mod.score_python_test
    ScoreResult = mod.ScoreResult


# ── Fixture loader ────────────────────────────────────────────────────────────

def load_fixtures(fixture_ids: list[str] | None = None) -> list[dict[str, Any]]:
    fixtures = []
    pattern = "*.json"
    for path in sorted(FIXTURES_DIR.glob(pattern)):
        if fixture_ids and path.stem not in fixture_ids:
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        data["_id"] = path.stem
        data["_path"] = str(path)
        fixtures.append(data)
    return fixtures


# ── Scorer dispatcher ─────────────────────────────────────────────────────────

def run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    ftype = fixture.get("type", "gherkin")
    output = fixture.get("output", "")
    expected_min_score = fixture.get("expected_min_score", 60)

    start = time.perf_counter()
    if ftype == "gherkin":
        result: ScoreResult = score_gherkin(output)
    elif ftype == "playwright":
        result = score_playwright(output)
    elif ftype == "python":
        result = score_python_test(output)
    else:
        return {
            "id": fixture["_id"],
            "type": ftype,
            "error": f"Bilinmeyen fixture type: {ftype}",
            "passed": False,
            "score": 0,
        }
    elapsed = (time.perf_counter() - start) * 1000

    passed = result.score >= expected_min_score
    return {
        "id": fixture["_id"],
        "name": fixture.get("name", fixture["_id"]),
        "type": ftype,
        "score": result.score,
        "grade": result.grade,
        "passed": passed,
        "expected_min": expected_min_score,
        "issues": result.issues,
        "suggestions": result.suggestions,
        "details": result.details,
        "elapsed_ms": round(elapsed, 1),
    }


# ── Reporter ──────────────────────────────────────────────────────────────────

def print_report(results: list[dict[str, Any]], threshold: float) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    accuracy = passed / total * 100 if total else 0

    print(f"\n{'='*60}")
    print(f"  Engine Eval Report — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    print(f"{'='*60}")
    print(f"  Fixtures: {total}  |  Passed: {passed}  |  Failed: {total - passed}")
    print(f"  Mapping accuracy: {accuracy:.1f}%  (threshold: {threshold}%)")
    print(f"{'='*60}")

    for r in results:
        status = "✅" if r.get("passed") else "❌"
        err = r.get("error")
        if err:
            print(f"  {status} [{r['id']}] ERROR: {err}")
        else:
            print(f"  {status} [{r['id']}] {r.get('name','')} — score={r['score']} grade={r['grade']} ({r['elapsed_ms']}ms)")
            for issue in r.get("issues", []):
                print(f"       ⚠  {issue}")

    print(f"{'='*60}\n")


def save_report(results: list[dict[str, Any]], threshold: float) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    accuracy = passed / total * 100 if total else 0

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "mapping_accuracy": round(accuracy, 2),
        "threshold": threshold,
        "gate_passed": accuracy >= threshold,
        "results": results,
    }

    # JSON raporu
    json_path = REPORTS_DIR / "latest.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Markdown raporu (CI summary için)
    md_path = REPORTS_DIR / "latest.md"
    lines = [
        f"# Engine Eval Report",
        f"",
        f"**Tarih:** {summary['generated_at']}  ",
        f"**Mapping accuracy:** {accuracy:.1f}%  ",
        f"**Gate:** {'✅ PASS' if summary['gate_passed'] else '❌ FAIL'} (threshold: {threshold}%)  ",
        f"",
        f"| ID | Tür | Skor | Grade | Geçti? | Süre |",
        f"|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r['id']} | — | — | — | ❌ ERROR | — |")
        else:
            tick = "✅" if r["passed"] else "❌"
            lines.append(
                f"| {r['id']} | {r['type']} | {r['score']} | {r['grade']} | {tick} | {r['elapsed_ms']}ms |"
            )

    if any(r.get("issues") for r in results):
        lines += ["", "## Sorunlar", ""]
        for r in results:
            for issue in r.get("issues", []):
                lines.append(f"- **[{r['id']}]** {issue}")

    with md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Engine eval runner")
    parser.add_argument("--fixtures", default="", help="Virgülle ayrılmış fixture id'leri")
    parser.add_argument("--threshold", type=float, default=60.0,
                        help="Minimum mapping accuracy (%) — default: 60")
    parser.add_argument("--json", action="store_true", help="Sadece JSON çıktı")
    args = parser.parse_args()

    fixture_ids = [x.strip() for x in args.fixtures.split(",") if x.strip()] or None
    fixtures = load_fixtures(fixture_ids)

    if not fixtures:
        print("::warning::Hiç fixture bulunamadı — gate pas geçiliyor")
        return 0

    results = [run_fixture(f) for f in fixtures]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results, args.threshold)

    save_report(results, args.threshold)

    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    accuracy = passed / total * 100 if total else 0

    if accuracy < args.threshold:
        print(f"❌ Gate başarısız: accuracy={accuracy:.1f}% < threshold={args.threshold}%", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
