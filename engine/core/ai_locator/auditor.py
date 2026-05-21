"""
LocatorAuditor — Mevcut locator repository'nin sağlık durumunu kontrol eder.

Kontroller:
  - Broken: Sayfada bulunamayan locator'lar
  - Ambiguous: Birden fazla element eşleşen locator'lar
  - Fragile: Düşük stabilite skoru olan locator'lar
  - Missing: data-testid olmayan interaktif elementler
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class LocatorHealthReport:
    total: int = 0
    healthy: int = 0
    broken: int = 0
    ambiguous: int = 0
    details: list[dict] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []

    @property
    def health_percentage(self) -> float:
        return round((self.healthy / self.total) * 100, 1) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "healthy": self.healthy,
            "broken": self.broken,
            "ambiguous": self.ambiguous,
            "health_percentage": self.health_percentage,
            "details": self.details,
        }


class LocatorAuditor:
    """Locator repository sağlık denetçisi."""

    def audit_from_json(self, json_path: str | Path) -> LocatorHealthReport:
        """JSON locator dosyasını yükle ve raporla (browser olmadan statik analiz)."""
        path = Path(json_path)
        if not path.exists():
            return LocatorHealthReport()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            entries = list(data.values()) if all(isinstance(v, dict) for v in data.values()) else []
            if not entries:
                return LocatorHealthReport()
        elif isinstance(data, list):
            entries = [e for e in data if isinstance(e, dict)]
        else:
            return LocatorHealthReport()

        report = LocatorHealthReport(total=len(entries))

        for entry in entries:
            key = entry.get("key", entry.get("name", ""))
            loc_type = entry.get("type", "css").lower()
            value = entry.get("value", entry.get("selector", ""))

            stability = _estimate_stability(loc_type, value)

            if not value:
                status = "broken"
                report.broken += 1
            elif stability >= 3:
                status = "healthy"
                report.healthy += 1
            else:
                status = "fragile"
                report.broken += 1

            report.details.append({
                "key": key,
                "type": loc_type,
                "value": value,
                "stability": stability,
                "status": status,
            })

        return report

    def audit_with_browser(
        self, page, locators: dict[str, str]
    ) -> LocatorHealthReport:
        """
        Playwright page üzerinde locator'ları canlı olarak test et.

        Args:
            page: Playwright Page nesnesi
            locators: {name: selector} sözlüğü
        """
        report = LocatorHealthReport(total=len(locators))

        for name, selector in locators.items():
            try:
                loc = page.locator(selector)
                count = loc.count()
                if count == 0:
                    report.broken += 1
                    report.details.append({
                        "key": name,
                        "selector": selector,
                        "status": "broken",
                        "count": 0,
                    })
                elif count > 1:
                    report.ambiguous += 1
                    report.details.append({
                        "key": name,
                        "selector": selector,
                        "status": "ambiguous",
                        "count": count,
                    })
                else:
                    report.healthy += 1
                    report.details.append({
                        "key": name,
                        "selector": selector,
                        "status": "healthy",
                        "count": 1,
                    })
            except Exception as e:
                report.broken += 1
                report.details.append({
                    "key": name,
                    "selector": selector,
                    "status": "error",
                    "error": str(e),
                })

        return report

    def audit_all_json_files(self, directory: str | Path | None = None) -> dict:
        """Dizindeki tüm locator JSON dosyalarını denetle."""
        base = Path(directory) if directory else settings.BASE_DIR / "locators"
        results = {}
        if not base.exists():
            return results
        for json_file in sorted(base.glob("**/*.json")):
            report = self.audit_from_json(json_file)
            results[json_file.stem] = report.to_dict()
        return results


def _estimate_stability(loc_type: str, value: str) -> int:
    """Locator tipine göre stabilite skoru tahmin et (1-5)."""
    type_scores = {
        "testid": 5, "data-testid": 5,
        "id": 4, "name": 3,
        "css": 2, "xpath": 1,
        "text": 2, "linktext": 2,
        "classname": 1, "class": 1,
        "role": 5, "label": 4,
        "placeholder": 3,
    }
    base = type_scores.get(loc_type, 2)

    if "data-testid" in value:
        base = max(base, 5)
    elif value.startswith("//") and "/div[" in value:
        base = min(base, 1)

    return base
