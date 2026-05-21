"""
core/locator_bridge.py — Birlesik Locator Cozumleme Koprusu

Iki farkli locator sistemini tek bir arayuz altinda birlestirir:

1. core.locator_manager.LocatorManager (NexusQA pattern)
   - Feature bazli JSON dosyalari (engine/data/locators/*.json)
   - Selenium type -> Playwright cevirici
   - Keyword-driven BDD step'leri icin

2. locators.locator_manager.LocatorManager (POM pattern)
   - locator_repository.json deposu
   - Self-healing, fallback zinciri (test_id -> css -> xpath)
   - Page Object sinflari icin

3. core.db.resolve_locator (DB pattern)
   - SQLite object_repository tablosu
   - Flask UI uzerinden kaydedilen locator'lar

Cozumleme zinciri:
  JSON feature locator -> POM repository -> DB object_repository -> raw selector

Kullanim:
    from core.locator_bridge import LocatorBridge

    bridge = LocatorBridge()
    selector = bridge.resolve("GirisYapButon")
    selector = bridge.resolve("login", "email_input")  # page+element
    health = bridge.health_report()
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LocatorBridge:
    """Tum locator kaynaklarini tek bir arayuz altinda birlestirir."""

    def __init__(self):
        self._json_mgr = None
        self._pom_mgr = None
        self._init_managers()

    def _init_managers(self):
        try:
            from core.locator_manager import LocatorManager as JsonLM
            self._json_mgr = JsonLM
        except ImportError:
            logger.debug("core.locator_manager yuklenemedi")

        try:
            from locators.locator_manager import LocatorManager as PomLM
            self._pom_mgr = PomLM()
        except (ImportError, Exception) as exc:
            logger.debug("locators.locator_manager yuklenemedi: %s", exc)

    def resolve(self, key_or_page: str, element: str = None) -> str:
        """
        Birlesik locator cozumleme.

        Args:
            key_or_page: Locator key (tek arguman) veya page adi (iki arguman)
            element: Element adi (opsiyonel, page+element cozumleme icin)

        Returns:
            Playwright selector string'i

        Cozumleme sirasi:
          1. Eger element verilmisse -> POM repository (page.element)
          2. JSON feature locators (core.locator_manager)
          3. POM repository (tum sayfalarda ara)
          4. DB object_repository
          5. Raw selector (fallback)
        """
        if element:
            return self._resolve_page_element(key_or_page, element)
        return self._resolve_key(key_or_page)

    def _resolve_key(self, key: str) -> str:
        """Tek key ile cozumleme (BDD step'leri icin)."""
        # 1. JSON feature locators
        if self._json_mgr:
            resolved = self._json_mgr.resolve(key)
            if resolved != key:
                logger.debug("JSON resolve: %s -> %s", key, resolved)
                return resolved

        # 2. POM repository (tum sayfalarda ara)
        if self._pom_mgr:
            try:
                for page_name in self._pom_mgr.list_pages():
                    try:
                        return self._pom_mgr.get_locator_with_fallback(page_name, key)
                    except (KeyError, ValueError):
                        continue
            except Exception as exc:
                logger.debug("POM repository taraması: %s", exc)

        # 3. DB object_repository
        try:
            from core.db import resolve_locator as db_resolve
            resolved = db_resolve(key)
            if resolved != key:
                logger.debug("DB resolve: %s -> %s", key, resolved)
                return resolved
        except Exception as exc:
            logger.debug("DB resolve_locator(%s): %s", key, exc)

        # 4. Raw selector
        return key

    def _resolve_page_element(self, page_name: str, element: str) -> str:
        """Page + element cozumleme (Page Object'ler icin)."""
        # POM repository oncelikli
        if self._pom_mgr:
            try:
                return self._pom_mgr.get_locator_with_fallback(page_name, element)
            except (KeyError, ValueError) as exc:
                logger.debug("POM %s.%s: %s", page_name, element, exc)

        # JSON fallback (page_name.element pattern'i dene)
        compound_key = f"{page_name}_{element}"
        return self._resolve_key(compound_key)

    def self_heal(self, key: str, playwright_page: Any, timeout: int = 3000) -> str:
        """
        Self-healing: birden fazla strateji ile locator bulmaya calisir.
        POM repository'nin self_heal yetenegini kullanir.
        """
        if self._pom_mgr:
            for page_name in self._pom_mgr.list_pages():
                try:
                    return self._pom_mgr.self_heal(
                        page_name, key, playwright_page, timeout
                    )
                except (KeyError, LookupError):
                    continue

        return self._resolve_key(key)

    def health_report(self) -> dict[str, Any]:
        """Tum locator kaynaklarinin saglik raporunu doner."""
        report = {
            "json_locators": {
                "loaded": bool(self._json_mgr),
                "count": len(self._json_mgr.keys()) if self._json_mgr else 0,
            },
            "pom_repository": {
                "loaded": bool(self._pom_mgr),
                "pages": self._pom_mgr.list_pages() if self._pom_mgr else [],
            },
            "db_repository": {"available": False, "count": 0},
        }

        try:
            from core.db import get_locators
            db_locs = get_locators()
            report["db_repository"] = {
                "available": True,
                "count": len(db_locs),
            }
        except Exception as exc:
            logger.debug("DB get_locators health_report: %s", exc)

        return report

    def validate_on_page(self, playwright_page: Any, page_name: str = None) -> dict:
        """Locator'larin canli sayfada calisip calismadigini kontrol eder."""
        if self._pom_mgr:
            return self._pom_mgr.validate_locators(playwright_page, page_name)
        return {}


# Singleton instance
_bridge: Optional[LocatorBridge] = None


def get_bridge() -> LocatorBridge:
    """Singleton bridge instance doner."""
    global _bridge
    if _bridge is None:
        _bridge = LocatorBridge()
    return _bridge
