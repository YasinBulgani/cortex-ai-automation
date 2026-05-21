#!/usr/bin/env python3
"""
Locator Health Check — Kırılgan locator tespiti ve registry sağlık raporu.

Kullanım:
    python scripts/locator_health_check.py [--url URL] [--registry PATH] [--output PATH]

Fonksiyonlar:
    1. Registry'deki tüm entry'leri yükler
    2. Her entry için primary selector'ın DOM'da bulunup bulunmadığını kontrol eder
    3. Kırılgan (fragile) locator'ları raporlar
    4. data-testid coverage oranını hesaplar
    5. JSON/text rapor üretir
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class LocatorHealthResult:
    name: str
    screen: str
    primary_type: str
    primary_value: str
    is_stable: bool
    chain_length: int
    has_testid: bool
    dom_found: bool | None = None  # None = not checked (no browser)
    status: str = ""  # healthy | fragile | broken | unchecked

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "screen": self.screen,
            "primary_type": self.primary_type,
            "primary_value": self.primary_value,
            "is_stable": self.is_stable,
            "chain_length": self.chain_length,
            "has_testid": self.has_testid,
            "dom_found": self.dom_found,
            "status": self.status,
        }


@dataclass
class HealthReport:
    timestamp: str = ""
    url_checked: str = ""
    total: int = 0
    healthy: int = 0
    fragile: int = 0
    broken: int = 0
    unchecked: int = 0
    testid_coverage: float = 0.0
    results: list[LocatorHealthResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "url_checked": self.url_checked,
            "total": self.total,
            "healthy": self.healthy,
            "fragile": self.fragile,
            "broken": self.broken,
            "unchecked": self.unchecked,
            "testid_coverage_pct": round(self.testid_coverage, 1),
            "results": [r.to_dict() for r in self.results],
        }


def analyze_registry(registry_path: str | Path) -> list[LocatorHealthResult]:
    """Registry JSON'dan statik analiz yapar."""
    path = Path(registry_path)
    if not path.exists():
        logger.error("Registry dosyası bulunamadı: %s", path)
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    results = []

    for name, entry in data.items():
        chain = entry.get("chain", [])
        primary = chain[0] if chain else {}
        has_testid = any(c.get("type") == "testid" for c in chain)
        is_stable = primary.get("stable", False)
        primary_type = primary.get("type", "unknown")
        primary_value = primary.get("value", "")

        if has_testid and is_stable:
            status = "healthy"
        elif has_testid:
            status = "healthy"
        elif is_stable:
            status = "fragile"
        else:
            status = "fragile"

        results.append(LocatorHealthResult(
            name=name,
            screen=entry.get("screen", ""),
            primary_type=primary_type,
            primary_value=primary_value,
            is_stable=is_stable,
            chain_length=len(chain),
            has_testid=has_testid,
            status=status,
        ))

    return results


def check_dom(results: list[LocatorHealthResult], url: str) -> list[LocatorHealthResult]:
    """Playwright ile canlı DOM kontrolü yapar."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright yüklü değil, DOM kontrolü atlanıyor.")
        return results

    pages_checked: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for result in results:
            page_url = f"{url}{result.primary_value}" if result.primary_value.startswith("/") else url
            target_url = url

            try:
                if target_url not in pages_checked:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=15_000)
                    page.wait_for_timeout(1000)
                    pages_checked.add(target_url)

                count = page.locator(result.primary_value).count()
                result.dom_found = count > 0
                if result.dom_found:
                    result.status = "healthy"
                else:
                    result.status = "broken" if result.has_testid else "fragile"
            except Exception:
                result.dom_found = None
                result.status = "unchecked"

        browser.close()

    return results


def generate_report(results: list[LocatorHealthResult], url: str = "") -> HealthReport:
    """Sonuçlardan rapor üretir."""
    total = len(results)
    healthy = sum(1 for r in results if r.status == "healthy")
    fragile = sum(1 for r in results if r.status == "fragile")
    broken = sum(1 for r in results if r.status == "broken")
    unchecked = sum(1 for r in results if r.status == "unchecked")
    testid_count = sum(1 for r in results if r.has_testid)
    testid_coverage = (testid_count / total * 100) if total > 0 else 0.0

    return HealthReport(
        timestamp=datetime.now().isoformat(),
        url_checked=url,
        total=total,
        healthy=healthy,
        fragile=fragile,
        broken=broken,
        unchecked=unchecked,
        testid_coverage=testid_coverage,
        results=results,
    )


def print_report(report: HealthReport):
    """Terminale renkli rapor basar."""
    print("\n" + "=" * 60)
    print("  LOCATOR HEALTH CHECK RAPORU")
    print("=" * 60)
    print(f"  Tarih:              {report.timestamp}")
    print(f"  URL:                {report.url_checked or 'Statik analiz'}")
    print(f"  Toplam Locator:     {report.total}")
    print(f"  Saglıklı:           {report.healthy}")
    print(f"  Kırılgan:           {report.fragile}")
    print(f"  Bozuk:              {report.broken}")
    print(f"  Kontrol Edilemedi:  {report.unchecked}")
    print(f"  data-testid Kapsam: %{report.testid_coverage:.1f}")
    print("=" * 60)

    if report.fragile > 0 or report.broken > 0:
        print("\n  SORUNLU LOCATOR'LAR:")
        print("-" * 60)
        for r in report.results:
            if r.status in ("fragile", "broken"):
                icon = "!!" if r.status == "broken" else "!"
                testid_flag = "[testid: YOK]" if not r.has_testid else ""
                print(f"  [{icon}] {r.name} ({r.screen})")
                print(f"       Primary: {r.primary_type} = {r.primary_value}")
                print(f"       Chain: {r.chain_length} aday | Stable: {r.is_stable} {testid_flag}")
                print()

    by_screen: dict[str, int] = {}
    for r in report.results:
        screen = r.screen or "unknown"
        by_screen[screen] = by_screen.get(screen, 0) + 1
    print("\n  EKRAN BAZLI DAGITIM:")
    print("-" * 60)
    for screen, count in sorted(by_screen.items()):
        testid_in_screen = sum(1 for r in report.results if r.screen == screen and r.has_testid)
        print(f"  {screen:20s}  {count:3d} locator  ({testid_in_screen} testid)")

    print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Locator Health Check")
    parser.add_argument("--registry", default=str(ROOT / "locators" / "default" / "bgts_locators.json"))
    parser.add_argument("--url", default="", help="Canlı DOM kontrolü için URL")
    parser.add_argument("--output", default="", help="JSON rapor çıktı yolu")
    args = parser.parse_args()

    results = analyze_registry(args.registry)
    if not results:
        logger.error("Registry boş veya okunamadı.")
        sys.exit(1)

    if args.url:
        results = check_dom(results, args.url)

    report = generate_report(results, args.url)
    print_report(report)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Rapor kaydedildi: %s", out)


if __name__ == "__main__":
    main()
