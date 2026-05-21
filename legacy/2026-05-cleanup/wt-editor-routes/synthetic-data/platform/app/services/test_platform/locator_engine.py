"""
LocatorEngine — 8 Öncelikli Locator Stratejisi

HTML/DOM analizi yaparak en güvenilir element locator'ını seçer.
Öncelik: data-testid > aria-label > id > name > CSS > XPath > text > class
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class LocatorStrategy(str, Enum):
    DATA_TESTID = "data-testid"
    ARIA_LABEL = "aria-label"
    ID = "id"
    NAME = "name"
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    CLASS = "class"


@dataclass
class Locator:
    strategy: LocatorStrategy
    value: str
    confidence: float       # 0.0 - 1.0
    playwright_syntax: str
    selenium_syntax: str
    is_stable: bool
    fallback_locators: List["Locator"]


class LocatorEngine:
    """
    DOM içeriğini veya element açıklamasını analiz ederek
    en güvenilir locator stratejisini belirler.
    """

    # Strateji güven seviyeleri (yüksek = daha stabil)
    _CONFIDENCE = {
        LocatorStrategy.DATA_TESTID: 0.99,
        LocatorStrategy.ARIA_LABEL: 0.92,
        LocatorStrategy.ID: 0.90,
        LocatorStrategy.NAME: 0.85,
        LocatorStrategy.CSS: 0.75,
        LocatorStrategy.XPATH: 0.65,
        LocatorStrategy.TEXT: 0.60,
        LocatorStrategy.CLASS: 0.40,
    }

    def analyze_element(self, element_description: str, html_snippet: str = "") -> Locator:
        """
        Element açıklaması veya HTML snippet'inden en iyi locator'ı seçer.

        Args:
            element_description: "Login butonu", "Şifre alanı" vb.
            html_snippet: İsteğe bağlı HTML

        Returns:
            Locator: En iyi locator + fallback'ler
        """
        candidates = self._extract_candidates(element_description, html_snippet)
        if not candidates:
            candidates = [self._generate_fallback(element_description)]

        # Güvene göre sırala
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        best = candidates[0]
        best.fallback_locators = candidates[1:3]
        return best

    def _extract_candidates(self, desc: str, html: str) -> List[Locator]:
        """HTML ve açıklamadan locator adaylarını çıkarır."""
        import re
        candidates = []
        desc_lower = desc.lower()

        # data-testid arama
        m = re.search(r'data-testid=["\']([^"\']+)["\']', html)
        if m:
            val = m.group(1)
            candidates.append(self._build(LocatorStrategy.DATA_TESTID, val))

        # id arama
        m = re.search(r'\bid=["\']([^"\']+)["\']', html)
        if m:
            candidates.append(self._build(LocatorStrategy.ID, f"#{m.group(1)}"))

        # aria-label arama
        m = re.search(r'aria-label=["\']([^"\']+)["\']', html)
        if m:
            candidates.append(self._build(LocatorStrategy.ARIA_LABEL, m.group(1)))

        # Açıklama bazlı tahmin
        if any(w in desc_lower for w in ["button", "buton", "btn", "giriş", "kaydet", "login"]):
            candidates.append(self._build(LocatorStrategy.CSS, "button[type='submit']", confidence_override=0.70))
        if any(w in desc_lower for w in ["input", "alan", "field", "şifre", "kullanıcı"]):
            field_type = "password" if "şifre" in desc_lower or "password" in desc_lower else "text"
            candidates.append(self._build(LocatorStrategy.CSS, f"input[type='{field_type}']", confidence_override=0.72))

        return candidates

    def _build(self, strategy: LocatorStrategy, value: str, confidence_override: Optional[float] = None) -> Locator:
        conf = confidence_override or self._CONFIDENCE[strategy]
        pw = self._playwright_syntax(strategy, value)
        sel = self._selenium_syntax(strategy, value)
        return Locator(
            strategy=strategy,
            value=value,
            confidence=conf,
            playwright_syntax=pw,
            selenium_syntax=sel,
            is_stable=conf >= 0.80,
            fallback_locators=[],
        )

    def _generate_fallback(self, desc: str) -> Locator:
        """Hiç locator bulunamazsa XPath metin tabanlı fallback üretir."""
        xpath = f"//*[contains(text(), '{desc[:30]}')]"
        return self._build(LocatorStrategy.XPATH, xpath)

    def _playwright_syntax(self, strategy: LocatorStrategy, value: str) -> str:
        mapping = {
            LocatorStrategy.DATA_TESTID: f'page.get_by_test_id("{value}")',
            LocatorStrategy.ARIA_LABEL: f'page.get_by_label("{value}")',
            LocatorStrategy.ID: f'page.locator("{value}")',
            LocatorStrategy.NAME: f'page.locator("[name=\'{value}\']")',
            LocatorStrategy.CSS: f'page.locator("{value}")',
            LocatorStrategy.XPATH: f'page.locator("{value}")',
            LocatorStrategy.TEXT: f'page.get_by_text("{value}")',
            LocatorStrategy.CLASS: f'page.locator(".{value}")',
        }
        return mapping.get(strategy, f'page.locator("{value}")')

    def _selenium_syntax(self, strategy: LocatorStrategy, value: str) -> str:
        mapping = {
            LocatorStrategy.DATA_TESTID: f'driver.find_element(By.CSS_SELECTOR, "[data-testid=\'{value}\']")',
            LocatorStrategy.ARIA_LABEL: f'driver.find_element(By.XPATH, "//*[@aria-label=\'{value}\']")',
            LocatorStrategy.ID: f'driver.find_element(By.ID, "{value.lstrip("#")}")',
            LocatorStrategy.NAME: f'driver.find_element(By.NAME, "{value}")',
            LocatorStrategy.CSS: f'driver.find_element(By.CSS_SELECTOR, "{value}")',
            LocatorStrategy.XPATH: f'driver.find_element(By.XPATH, "{value}")',
            LocatorStrategy.TEXT: f'driver.find_element(By.XPATH, "//*[contains(text(), \'{value}\')]")',
            LocatorStrategy.CLASS: f'driver.find_element(By.CLASS_NAME, "{value}")',
        }
        return mapping.get(strategy, f'driver.find_element(By.CSS_SELECTOR, "{value}")')

    # ── Public API (dict-based wrapper) ──────────────────────────────────

    def suggest_locators(self, element_info: dict) -> list:
        """
        Element bilgisine göre öncelikli locator listesi öner.

        Args:
            element_info: Element özelliklerini içeren dict.
              Desteklenen anahtarlar:
                - tag (str): HTML tag adı
                - id (str): element id
                - name (str): name attribute
                - text (str): görünür metin
                - aria_label (str): aria-label attribute
                - data_testid (str): data-testid attribute
                - placeholder (str): placeholder attribute
                - css_class (str): CSS sınıfları
                - role (str): ARIA role

        Returns:
            Locator dict'lerinin listesi (strategy, value, priority anahtarlarıyla).
        """
        # HTML snippet'i oluştur
        tag = element_info.get("tag", "div")
        el_id = element_info.get("id", "")
        name = element_info.get("name", "")
        aria_label = element_info.get("aria_label", "")
        data_testid = element_info.get("data_testid", "")
        text = element_info.get("text", "")
        css_class = element_info.get("css_class", "")
        placeholder = element_info.get("placeholder", "")

        html_parts = [f"<{tag}"]
        if el_id:
            html_parts.append(f' id="{el_id}"')
        if name:
            html_parts.append(f' name="{name}"')
        if aria_label:
            html_parts.append(f' aria-label="{aria_label}"')
        if data_testid:
            html_parts.append(f' data-testid="{data_testid}"')
        if placeholder:
            html_parts.append(f' placeholder="{placeholder}"')
        if css_class:
            html_parts.append(f' class="{css_class}"')
        html_parts.append(">")
        if text:
            html_parts.append(text)
        html_parts.append(f"</{tag}>")
        html_snippet = "".join(html_parts)

        # analyze_element ile locator al
        best = self.analyze_element(
            element_description=text or aria_label or tag,
            html_snippet=html_snippet,
        )

        # Locator nesnelerini dict listesine dönüştür
        result = []
        priority = 1

        all_locators = [best] + (best.fallback_locators or [])
        for loc in all_locators:
            result.append({
                "strategy": loc.strategy.value if hasattr(loc.strategy, "value") else loc.strategy,
                "value": loc.value,
                "priority": priority,
            })
            priority += 1

        # Placeholder/name fallback'leri ekle
        if placeholder and not any(placeholder in r["value"] for r in result):
            result.append({
                "strategy": "placeholder",
                "value": placeholder,
                "priority": priority,
            })
            priority += 1

        if not result:
            result.append({
                "strategy": LocatorStrategy.CSS.value,
                "value": tag or "*",
                "priority": 1,
            })

        return result
