#!/usr/bin/env python3
"""
Locator Coverage Analyzer
==========================
Next.js TSX dosyalarındaki data-testid kullanımını analiz eder.

Çıktılar:
- Ekran bazlı testid envanteri
- data-testid olmayan interaktif elementler
- Kapsam yüzdesi

Kullanım:
    python scripts/locator_coverage.py [--web-dir PATH] [--output PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEB = ROOT.parent / "apps" / "web"


@dataclass
class PageAnalysis:
    file: str
    screen: str
    testids: list[str] = field(default_factory=list)
    interactive_without_testid: list[str] = field(default_factory=list)
    total_interactive: int = 0
    covered: int = 0

    @property
    def coverage_pct(self) -> float:
        return (self.covered / self.total_interactive * 100) if self.total_interactive > 0 else 100.0

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "screen": self.screen,
            "testids": self.testids,
            "interactive_without_testid": self.interactive_without_testid,
            "total_interactive": self.total_interactive,
            "covered": self.covered,
            "coverage_pct": round(self.coverage_pct, 1),
        }


INTERACTIVE_PATTERNS = [
    r'<button\b',
    r'<Button\b',
    r'<input\b',
    r'<Input\b',
    r'<select\b',
    r'<textarea\b',
    r'<a\b',
    r'<Link\b',
    r'<form\b',
]

TESTID_RE = re.compile(r'data-testid[=]"([^"]+)"')
INTERACTIVE_RE = re.compile("|".join(INTERACTIVE_PATTERNS), re.IGNORECASE)
ELEMENT_BLOCK_RE = re.compile(r'<(\w+)\b([^>]*?)(?:/>|>)', re.DOTALL)


def analyze_file(filepath: Path, web_root: Path) -> PageAnalysis:
    """Tek bir TSX dosyasını analiz eder."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    rel_path = str(filepath.relative_to(web_root))

    screen = _path_to_screen(rel_path)

    testids = TESTID_RE.findall(content)

    interactive_elements = []
    missing_testid = []

    for match in ELEMENT_BLOCK_RE.finditer(content):
        tag = match.group(1)
        attrs = match.group(2)

        if tag.lower() not in (
            "button", "input", "select", "textarea", "a", "form",
        ) and tag not in ("Button", "Input", "Link"):
            continue

        interactive_elements.append(tag)
        if "data-testid" not in attrs:
            context = _extract_context(tag, attrs)
            missing_testid.append(context)

    return PageAnalysis(
        file=rel_path,
        screen=screen,
        testids=testids,
        interactive_without_testid=missing_testid,
        total_interactive=len(interactive_elements),
        covered=len(interactive_elements) - len(missing_testid),
    )


def _path_to_screen(rel_path: str) -> str:
    """Dosya yolundan ekran adını çıkarır."""
    parts = rel_path.replace("\\", "/").split("/")
    if "page.tsx" in parts[-1]:
        meaningful = [p for p in parts if p not in (
            "app", "(dashboard)", "page.tsx", "p", "[projectId]",
        )]
        return "/".join(meaningful[-2:]) if len(meaningful) >= 2 else meaningful[-1] if meaningful else "root"
    return parts[-1].replace(".tsx", "")


def _extract_context(tag: str, attrs: str) -> str:
    """Element için kısa tanımlayıcı çıkarır."""
    placeholders = re.findall(r'placeholder="([^"]*)"', attrs)
    labels = re.findall(r'aria-label="([^"]*)"', attrs)
    ids = re.findall(r'\bid="([^"]*)"', attrs)
    names = re.findall(r'\bname="([^"]*)"', attrs)
    types = re.findall(r'\btype="([^"]*)"', attrs)

    identifier = ""
    if ids:
        identifier = f"id={ids[0]}"
    elif placeholders:
        identifier = f"placeholder={placeholders[0]}"
    elif labels:
        identifier = f"aria-label={labels[0]}"
    elif names:
        identifier = f"name={names[0]}"
    elif types:
        identifier = f"type={types[0]}"

    return f"<{tag} {identifier}>" if identifier else f"<{tag}>"


def run_analysis(web_dir: Path) -> list[PageAnalysis]:
    """Tüm TSX sayfalarını analiz eder."""
    results = []
    app_dir = web_dir / "app"
    components_dir = web_dir / "components"

    for tsx in sorted(app_dir.rglob("page.tsx")):
        result = analyze_file(tsx, web_dir)
        if result.total_interactive > 0 or result.testids:
            results.append(result)

    for tsx in sorted(components_dir.rglob("*.tsx")):
        result = analyze_file(tsx, web_dir)
        if result.total_interactive > 0 or result.testids:
            results.append(result)

    return results


def print_report(results: list[PageAnalysis]):
    """Terminale rapor basar."""
    total_elements = sum(r.total_interactive for r in results)
    total_covered = sum(r.covered for r in results)
    total_testids = sum(len(r.testids) for r in results)
    overall_pct = (total_covered / total_elements * 100) if total_elements > 0 else 0

    print("\n" + "=" * 70)
    print("  DATA-TESTID COVERAGE RAPORU")
    print("=" * 70)
    print(f"  Toplam Sayfa:           {len(results)}")
    print(f"  Toplam İnteraktif:      {total_elements}")
    print(f"  data-testid Kapsam:     {total_covered}/{total_elements} (%{overall_pct:.1f})")
    print(f"  Toplam Benzersiz testid:{total_testids}")
    print("=" * 70)

    print(f"\n  {'Sayfa':<40s} {'Eleman':>8s} {'Kapsam':>8s} {'%':>6s}")
    print("  " + "-" * 64)
    for r in sorted(results, key=lambda x: x.coverage_pct):
        icon = "OK" if r.coverage_pct >= 80 else "!!" if r.coverage_pct < 50 else "! "
        print(f"  [{icon}] {r.screen:<36s} {r.total_interactive:>8d} {r.covered:>8d} {r.coverage_pct:>5.1f}%")

    missing_pages = [r for r in results if r.interactive_without_testid]
    if missing_pages:
        print(f"\n  TESTID EKSİK ELEMENTLER:")
        print("  " + "-" * 64)
        for r in missing_pages:
            if r.interactive_without_testid:
                print(f"\n  {r.screen} ({r.file}):")
                for elem in r.interactive_without_testid[:10]:
                    print(f"    - {elem}")
                if len(r.interactive_without_testid) > 10:
                    print(f"    ... ve {len(r.interactive_without_testid) - 10} adet daha")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="data-testid Coverage Analyzer")
    parser.add_argument("--web-dir", default=str(DEFAULT_WEB))
    parser.add_argument("--output", default="", help="JSON rapor çıktı yolu")
    args = parser.parse_args()

    web_dir = Path(args.web_dir)
    if not web_dir.exists():
        print(f"Web dizini bulunamadı: {web_dir}", file=sys.stderr)
        sys.exit(1)

    results = run_analysis(web_dir)
    print_report(results)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "total_pages": len(results),
            "total_interactive": sum(r.total_interactive for r in results),
            "total_covered": sum(r.covered for r in results),
            "pages": [r.to_dict() for r in results],
        }
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Rapor kaydedildi: {out}")


if __name__ == "__main__":
    main()
