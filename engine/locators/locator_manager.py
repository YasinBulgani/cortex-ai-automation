"""
LocatorManager — Merkezi locator yönetim sınıfı.
JSON tabanlı locator deposundan seçici okur, fallback zinciri ve self-healing destekler.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_REPO_PATH = Path(__file__).parent / "locator_repository.json"

FALLBACK_ORDER = ("test_id", "css", "xpath")


class LocatorManager:
    """
    Merkezi locator yöneticisi.

    JSON deposundan seçici okur ve Page Object'lere sunar.
    - Fallback zinciri: test_id → css → xpath
    - Self-healing: birincil seçici başarısız olduğunda alternatifleri dener
    - Sağlık raporu: hangi locator'ların hâlâ çalıştığını denetler
    """

    def __init__(self, repo_path: str | Path | None = None) -> None:
        self._path = Path(repo_path) if repo_path else _REPO_PATH
        self._data: dict[str, Any] = {}
        self._health: dict[str, dict[str, str]] = {}
        self._load()

    # ── Yükleme ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """JSON deposunu diskten okur."""
        if not self._path.exists():
            logger.warning("Locator deposu bulunamadı: %s", self._path)
            return
        with open(self._path, "r", encoding="utf-8") as fh:
            self._data = json.load(fh)
        logger.info("Locator deposu yüklendi: %d sayfa", len(self._data))

    def reload(self) -> None:
        """Depoyu diskten yeniden okur (çalışma zamanında güncelleme için)."""
        self._load()

    # ── Temel Erişim ──────────────────────────────────────────────────────────

    def get_page(self, page_name: str) -> dict[str, Any]:
        """Belirtilen sayfa tanımını döner."""
        page = self._data.get(page_name)
        if page is None:
            raise KeyError(f"Sayfa bulunamadı: '{page_name}'")
        return page

    def get_element(self, page_name: str, element_name: str) -> dict[str, Any]:
        """Belirtilen element tanımını döner."""
        page = self.get_page(page_name)
        elem = page.get("elements", {}).get(element_name)
        if elem is None:
            raise KeyError(
                f"Element bulunamadı: '{element_name}' (sayfa: '{page_name}')"
            )
        return elem

    def get_locator(
        self,
        page_name: str,
        element_name: str,
        strategy: str = "css",
    ) -> str:
        """
        Tek bir seçici strateji ile locator değerini döner.

        Args:
            page_name: Sayfa adı (ör. "login")
            element_name: Element adı (ör. "email_input")
            strategy: Seçici tipi — "css", "xpath" veya "test_id"

        Returns:
            Seçici string'i. test_id stratejisi için ``[data-testid='...']`` formatı.
        """
        elem = self.get_element(page_name, element_name)
        if strategy == "test_id":
            tid = elem.get("test_id", "")
            if tid:
                return f"[data-testid='{tid}']"
            raise ValueError(
                f"test_id tanımlı değil: {page_name}.{element_name}"
            )
        value = elem.get(strategy)
        if not value:
            raise ValueError(
                f"Strateji '{strategy}' tanımlı değil: {page_name}.{element_name}"
            )
        return value

    def get_locator_with_fallback(
        self,
        page_name: str,
        element_name: str,
    ) -> str:
        """
        Fallback zinciri ile ilk geçerli locator'ı döner.
        Sıra: test_id → css → xpath
        """
        elem = self.get_element(page_name, element_name)
        for strategy in FALLBACK_ORDER:
            try:
                if strategy == "test_id":
                    tid = elem.get("test_id", "")
                    if tid:
                        return f"[data-testid='{tid}']"
                else:
                    val = elem.get(strategy)
                    if val:
                        return val
            except Exception:
                continue
        raise ValueError(
            f"Hiçbir strateji ile locator bulunamadı: {page_name}.{element_name}"
        )

    # ── Self-Healing ──────────────────────────────────────────────────────────

    def self_heal(
        self,
        page_name: str,
        element_name: str,
        playwright_page: Any,
        timeout: int = 3000,
    ) -> str:
        """
        Birincil seçici başarısız olduğunda alternatif seçicileri dener.

        Fallback sırasına göre her seçiciyi kısa timeout ile test eder.
        Çalışan ilk seçiciyi döner ve sonucu sağlık raporuna kaydeder.

        Args:
            page_name: Sayfa adı
            element_name: Element adı
            playwright_page: Playwright Page nesnesi
            timeout: Her deneme için ms cinsinden bekleme süresi

        Returns:
            Çalışan seçici string'i
        """
        elem = self.get_element(page_name, element_name)
        key = f"{page_name}.{element_name}"

        candidates: list[tuple[str, str]] = []
        tid = elem.get("test_id", "")
        if tid:
            candidates.append(("test_id", f"[data-testid='{tid}']"))
        css = elem.get("css", "")
        if css:
            candidates.append(("css", css))
        xpath = elem.get("xpath", "")
        if xpath:
            candidates.append(("xpath", xpath))

        for strategy_name, selector in candidates:
            try:
                loc = playwright_page.locator(selector)
                loc.first.wait_for(state="attached", timeout=timeout)
                self._health[key] = {
                    "status": "ok",
                    "strategy": strategy_name,
                    "selector": selector,
                    "timestamp": datetime.now().isoformat(),
                }
                if strategy_name != "test_id":
                    logger.warning(
                        "Self-heal: %s → birincil (test_id) başarısız, "
                        "'%s' ile bulundu",
                        key,
                        strategy_name,
                    )
                return selector
            except Exception:
                continue

        self._health[key] = {
            "status": "broken",
            "strategy": "none",
            "selector": "",
            "timestamp": datetime.now().isoformat(),
        }
        raise LookupError(
            f"Self-heal başarısız — hiçbir seçici çalışmadı: {key}"
        )

    # ── Doğrulama ─────────────────────────────────────────────────────────────

    def validate_locators(
        self,
        playwright_page: Any,
        page_name: Optional[str] = None,
        timeout: int = 2000,
    ) -> dict[str, dict[str, Any]]:
        """
        Locator'ların canlı sayfada çalışıp çalışmadığını kontrol eder.

        Args:
            playwright_page: Playwright Page nesnesi
            page_name: Belirli bir sayfa için kontrol (None = tümü)
            timeout: Her element için ms bekleme süresi

        Returns:
            ``{sayfa.element: {status, strategies: {css: bool, xpath: bool, test_id: bool}}}``
        """
        pages_to_check = (
            {page_name: self.get_page(page_name)}
            if page_name
            else self._data
        )
        report: dict[str, dict[str, Any]] = {}

        for pname, pdata in pages_to_check.items():
            for ename, edata in pdata.get("elements", {}).items():
                key = f"{pname}.{ename}"
                strategies: dict[str, bool] = {}

                tid = edata.get("test_id", "")
                if tid:
                    strategies["test_id"] = self._probe(
                        playwright_page, f"[data-testid='{tid}']", timeout
                    )
                css = edata.get("css", "")
                if css:
                    strategies["css"] = self._probe(playwright_page, css, timeout)
                xpath = edata.get("xpath", "")
                if xpath:
                    strategies["xpath"] = self._probe(playwright_page, xpath, timeout)

                any_ok = any(strategies.values())
                status = "ok" if any_ok else "broken"
                report[key] = {"status": status, "strategies": strategies}
                self._health[key] = {
                    "status": status,
                    "strategy": next(
                        (s for s, v in strategies.items() if v), "none"
                    ),
                    "selector": "",
                    "timestamp": datetime.now().isoformat(),
                }

        return report

    @staticmethod
    def _probe(playwright_page: Any, selector: str, timeout: int) -> bool:
        """Bir seçicinin sayfada element bulup bulmadığını test eder."""
        try:
            loc = playwright_page.locator(selector)
            loc.first.wait_for(state="attached", timeout=timeout)
            return True
        except Exception:
            return False

    # ── Raporlama ─────────────────────────────────────────────────────────────

    def export_report(self) -> dict[str, Any]:
        """
        Locator sağlık raporunu döner.

        Returns:
            Toplam istatistikler ve element bazında sağlık durumu.
        """
        total = len(self._health)
        ok = sum(1 for v in self._health.values() if v["status"] == "ok")
        broken = sum(1 for v in self._health.values() if v["status"] == "broken")
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_checked": total,
                "healthy": ok,
                "broken": broken,
                "health_rate": round(ok / total * 100, 1) if total else 0.0,
            },
            "details": dict(self._health),
        }

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    def list_pages(self) -> list[str]:
        """Depodaki tüm sayfa adlarını döner."""
        return list(self._data.keys())

    def list_elements(self, page_name: str) -> list[str]:
        """Belirtilen sayfadaki tüm element adlarını döner."""
        return list(self.get_page(page_name).get("elements", {}).keys())

    def get_url_pattern(self, page_name: str) -> str:
        """Sayfanın URL desenini döner."""
        return self.get_page(page_name).get("url_pattern", "")

    def get_description(self, page_name: str, element_name: str) -> str:
        """Element'in Türkçe açıklamasını döner."""
        return self.get_element(page_name, element_name).get("description", "")

    def get_wait_strategy(self, page_name: str, element_name: str) -> str:
        """Element'in bekleme stratejisini döner."""
        return self.get_element(page_name, element_name).get(
            "wait_strategy", "visible"
        )

    def __repr__(self) -> str:
        return (
            f"LocatorManager(pages={len(self._data)}, "
            f"path='{self._path.name}')"
        )
