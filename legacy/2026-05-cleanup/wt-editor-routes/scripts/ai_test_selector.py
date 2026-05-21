#!/usr/bin/env python3
"""
AI Test Selector — CI/CD pipeline için risk tabanlı test seçimi.

Kullanım:
  python scripts/ai_test_selector.py --changed-files "src/auth.py,src/login.tsx" --output-format github-matrix
  python scripts/ai_test_selector.py --changed-files "$(git diff --name-only HEAD~1)" --output-format json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from core.ai_prioritizer import IntelligentTestSelector


def discover_tests(test_dir: str = "e2e") -> list[dict]:
    """E2E + engine test dosyalarını keşfet ve metadata çıkar."""
    repo_root = Path(__file__).resolve().parent.parent
    tests = []

    e2e_base = Path(test_dir)
    if not e2e_base.exists():
        e2e_base = repo_root / test_dir
    if e2e_base.exists():
        for spec in sorted(e2e_base.glob("**/*.spec.ts")):
            name = spec.stem
            content = spec.read_text(encoding="utf-8")

            tags = []
            if "@smoke" in content or "smoke" in name:
                tags.append("@smoke")
            if "@regression" in content or "regression" in name:
                tags.append("@regression")
            if "@critical" in content:
                tags.append("@critical")

            tests.append({
                "id": name,
                "name": spec.name,
                "tags": tags,
                "covers_files": _infer_covered_files(name),
                "step_count": content.count("test(") + content.count("test.step("),
            })

    engine_tests = repo_root / "engine" / "tests"
    if engine_tests.exists():
        for tf in sorted(engine_tests.rglob("test_*.py")):
            name = tf.stem
            tests.append({
                "id": name,
                "name": tf.name,
                "tags": [],
                "covers_files": [str(tf.relative_to(repo_root))],
                "step_count": 5,
            })

    return tests


def _infer_covered_files(test_name: str) -> list[str]:
    """Test adından kapsanan dosyaları çıkar."""
    mapping = {
        "login": ["e2e/pages/login.page.ts", "apps/web/app/login"],
        "projects": ["e2e/pages/projects.page.ts", "apps/web/app/projects"],
        "scenarios": ["e2e/pages/scenarios-list.page.ts", "apps/web/app/scenarios"],
        "scenario-versions": ["e2e/pages/scenario-form.page.ts", "apps/web/app/scenarios"],
        "executions": ["e2e/pages/executions.page.ts", "apps/web/app/executions"],
        "flows": ["e2e/pages/flows.page.ts", "apps/web/app/flows"],
        "approvals": ["e2e/pages/approvals.page.ts", "apps/web/app/approvals"],
        "import": ["e2e/pages/import.page.ts"],
        "regression": ["e2e/pages/regression.page.ts"],
        "smoke": [],
        "navigation": ["e2e/pages/components/sidebar.component.ts"],
        "api-tests": ["backend/", "engine/routes/"],
        "bdd-generate": ["engine/core/ai_bdd/", "engine/routes/ai_generation_routes.py"],
        "integrations": ["apps/web/lib/api.ts", "backend/app/"],
        "requirements": ["apps/web/app/requirements", "e2e/pages/"],
        "schedules": ["apps/web/app/schedules", "backend/app/"],
        "test-data": ["engine/test_data/", "e2e/fixtures/test-data.ts"],
    }
    for key, files in mapping.items():
        if key in test_name:
            return files
    return []


def main():
    parser = argparse.ArgumentParser(description="AI-powered test selector")
    parser.add_argument("--changed-files", required=True, help="Comma-separated changed files")
    parser.add_argument("--threshold", type=float, default=0.30, help="Risk threshold")
    parser.add_argument("--output-format", choices=["json", "github-matrix", "text"], default="json")
    parser.add_argument("--test-dir", default="e2e", help="Test directory")
    args = parser.parse_args()

    changed = [f.strip() for f in args.changed_files.split(",") if f.strip()]
    tests = discover_tests(args.test_dir)

    if not tests:
        print("No tests discovered", file=sys.stderr)
        if args.output_format == "github-matrix":
            print("[]")
        sys.exit(0)

    selector = IntelligentTestSelector(threshold=args.threshold)
    result = selector.select(tests, changed)

    if args.output_format == "github-matrix":
        matrix = selector.to_github_matrix(result)
        print(matrix)
    elif args.output_format == "text":
        print(f"Selected {result.selected_count}/{result.total_tests} tests")
        print(f"Estimated time saved: {result.estimated_time_saved_pct}%")
        for p in result.selected:
            print(f"  ✓ {p.test_name} (risk={p.risk_score:.3f})")
        for p in result.skipped:
            print(f"  ✗ {p.test_name} (risk={p.risk_score:.3f})")
    else:
        output = {
            "selected_count": result.selected_count,
            "total_tests": result.total_tests,
            "time_saved_pct": result.estimated_time_saved_pct,
            "selected": [
                {"name": p.test_name, "risk_score": p.risk_score, "tags": p.tags}
                for p in result.selected
            ],
            "skipped": [
                {"name": p.test_name, "risk_score": p.risk_score}
                for p in result.skipped
            ],
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
