"""
Accessibility (Erişilebilirlik) Test Modülü
===========================================
WCAG 2.1 AA/AAA uyumluluk testleri.
10 kural, severity-weighted scoring (0-100), HTML rapor üretimi.
axe-core opsiyonel entegrasyon, fallback olarak kendi kuralları.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Opsiyonel bağımlılıklar ────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from config.settings import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Veri Sınıfları
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class A11yViolation:
    """Tek bir erişilebilirlik ihlali."""
    rule_id: str
    description: str
    severity: str          # critical | serious | moderate | minor
    wcag_criteria: str     # örn. "1.1.1", "1.4.3"
    element: str = ""      # HTML seçici veya snippet
    help_url: str = ""
    impact: str = ""


@dataclass
class A11yResult:
    """Bir sayfa için tüm erişilebilirlik sonuçları."""
    url: str
    score: float = 0.0
    violations: list[A11yViolation] = field(default_factory=list)
    warnings: list[A11yViolation] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    page_title: str = ""
    wcag_level: str = "AA"
    error: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# WCAG Kural Tanımları
# ──────────────────────────────────────────────────────────────────────────────
WCAG_RULES: dict[str, dict] = {
    "img-alt": {
        "description": "Resimlerin alt metni olmalı (WCAG 1.1.1)",
        "wcag": "1.1.1",
        "severity": "critical",
        "weight": 15,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content",
    },
    "form-label": {
        "description": "Form girişlerinin etiketleri olmalı (WCAG 1.3.1)",
        "wcag": "1.3.1",
        "severity": "critical",
        "weight": 14,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships",
    },
    "heading-hierarchy": {
        "description": "Başlık hiyerarşisi doğru sırada olmalı (WCAG 1.3.1)",
        "wcag": "1.3.1",
        "severity": "moderate",
        "weight": 8,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships",
    },
    "color-contrast-aa": {
        "description": "Metin kontrast oranı AA: en az 4.5:1 (WCAG 1.4.3)",
        "wcag": "1.4.3",
        "severity": "serious",
        "weight": 13,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum",
    },
    "color-contrast-aaa": {
        "description": "Metin kontrast oranı AAA: en az 7:1 (WCAG 1.4.6)",
        "wcag": "1.4.6",
        "severity": "minor",
        "weight": 5,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/contrast-enhanced",
    },
    "tabindex": {
        "description": "tabindex değerleri 0 veya negatif olmalı (WCAG 2.4.3)",
        "wcag": "2.4.3",
        "severity": "serious",
        "weight": 10,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/focus-order",
    },
    "aria-validation": {
        "description": "ARIA rol ve öznitelikleri geçerli olmalı (WCAG 4.1.2)",
        "wcag": "4.1.2",
        "severity": "serious",
        "weight": 11,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value",
    },
    "link-text": {
        "description": "Bağlantılar açıklayıcı metin içermeli (WCAG 2.4.4)",
        "wcag": "2.4.4",
        "severity": "serious",
        "weight": 10,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context",
    },
    "lang-attribute": {
        "description": "HTML lang özniteliği tanımlanmalı (WCAG 3.1.1)",
        "wcag": "3.1.1",
        "severity": "moderate",
        "weight": 7,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/language-of-page",
    },
    "page-title": {
        "description": "Sayfa başlığı tanımlı ve açıklayıcı olmalı (WCAG 2.4.2)",
        "wcag": "2.4.2",
        "severity": "moderate",
        "weight": 7,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/page-titled",
    },
    "button-accessibility": {
        "description": "Butonların erişilebilir adı olmalı (WCAG 4.1.2)",
        "wcag": "4.1.2",
        "severity": "critical",
        "weight": 12,
        "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value",
    },
}

# Toplam maksimum ağırlık (skor normalizasyonu için)
MAX_WEIGHT = sum(r["weight"] for r in WCAG_RULES.values())

# Boş/anlamsız link metinleri
MEANINGLESS_LINK_TEXTS = {
    "click here", "here", "more", "read more", "link", "tıklayın",
    "buraya tıklayın", "devamı", "daha fazla", "→", ">>",
}

# Geçersiz ARIA rolleri (temsili liste)
INVALID_ARIA_ROLES = {
    "none-existing-role", "foobar", "datepicker", "popup",
}


# ──────────────────────────────────────────────────────────────────────────────
# HTML Ayrıştırma Yardımcıları (regex tabanlı, bağımsız)
# ──────────────────────────────────────────────────────────────────────────────
class HtmlAnalyzer:
    """
    Hafif HTML ayrıştırıcı.
    BeautifulSoup bağımlılığı olmadan regex ile temel kontroller yapar.
    Playwright'ın evaluate() ile alınan DOM snapshot üzerinde çalışır.
    """

    @staticmethod
    def extract_elements(html: str, tag: str, attrs: str = "") -> list[str]:
        """Belirtilen etikete ait tüm elementleri döner."""
        pattern = rf"<{tag}(?:\s[^>]*)?" + attrs + r"[^>]*>"
        return re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

    @staticmethod
    def get_attr(tag_str: str, attr: str) -> str | None:
        """Bir etiketten öznitelik değerini çeker."""
        pattern = rf'{attr}\s*=\s*["\']([^"\']*)["\']'
        m = re.search(pattern, tag_str, re.IGNORECASE)
        return m.group(1) if m else None

    @staticmethod
    def has_attr(tag_str: str, attr: str) -> bool:
        """Etikette öznitelik var mı kontrol eder."""
        return bool(re.search(rf'\b{attr}\b', tag_str, re.IGNORECASE))

    @staticmethod
    def get_inner_text(html: str, tag_str: str) -> str:
        """Bir etiketin metin içeriğini alır."""
        # Etiket başını bul, ardından kapanışa kadar içeriği al
        tag_name = re.match(r"<(\w+)", tag_str)
        if not tag_name:
            return ""
        name = tag_name.group(1)
        idx = html.find(tag_str)
        if idx == -1:
            return ""
        close_tag = f"</{name}>"
        end_idx = html.find(close_tag, idx)
        if end_idx == -1:
            return ""
        inner = html[idx + len(tag_str):end_idx]
        # HTML etiketlerini temizle
        return re.sub(r"<[^>]+>", "", inner).strip()


# ──────────────────────────────────────────────────────────────────────────────
# 10 WCAG Kural Kontrol Fonksiyonları
# ──────────────────────────────────────────────────────────────────────────────
class WCAGRuleEngine:
    """Her WCAG kuralı için kontrol metodunu barındırır."""

    def __init__(self, dom_data: dict):
        """
        Args:
            dom_data: Playwright evaluate ile alınan DOM analiz verisi.
                      Anahtarlar: images, inputs, headings, links, buttons,
                                  lang, title, tabindex_elements, aria_elements
        """
        self.data = dom_data

    # ── Kural 1: img-alt ─────────────────────────────────────────────────────
    def check_img_alt(self) -> list[A11yViolation]:
        violations = []
        for img in self.data.get("images", []):
            alt = img.get("alt")
            src = img.get("src", "")[:80]
            role = img.get("role", "")
            # Dekoratif img (role=presentation veya alt="") → sorun değil
            if role in ("presentation", "none") or alt == "":
                continue
            if alt is None:
                violations.append(A11yViolation(
                    rule_id="img-alt",
                    description=f"img elementinde alt özniteliği eksik: src={src}",
                    severity=WCAG_RULES["img-alt"]["severity"],
                    wcag_criteria=WCAG_RULES["img-alt"]["wcag"],
                    element=f'<img src="{src}">',
                    help_url=WCAG_RULES["img-alt"]["help_url"],
                ))
        return violations

    # ── Kural 2: form-label ───────────────────────────────────────────────────
    def check_form_label(self) -> list[A11yViolation]:
        violations = []
        for inp in self.data.get("inputs", []):
            itype = inp.get("type", "text").lower()
            if itype in ("hidden", "submit", "button", "image", "reset"):
                continue
            has_label = inp.get("has_label", False)
            aria_label = inp.get("aria_label", "")
            aria_labelledby = inp.get("aria_labelledby", "")
            title = inp.get("title", "")
            if not (has_label or aria_label or aria_labelledby or title):
                name = inp.get("name", "?")
                violations.append(A11yViolation(
                    rule_id="form-label",
                    description=f"Form girişi etiketsiz: name={name}, type={itype}",
                    severity=WCAG_RULES["form-label"]["severity"],
                    wcag_criteria=WCAG_RULES["form-label"]["wcag"],
                    element=f'<input type="{itype}" name="{name}">',
                    help_url=WCAG_RULES["form-label"]["help_url"],
                ))
        return violations

    # ── Kural 3: heading-hierarchy ────────────────────────────────────────────
    def check_heading_hierarchy(self) -> list[A11yViolation]:
        violations = []
        headings = self.data.get("headings", [])
        levels = [int(h["level"]) for h in headings if "level" in h]
        prev = 0
        for i, lvl in enumerate(levels):
            if prev > 0 and lvl > prev + 1:
                violations.append(A11yViolation(
                    rule_id="heading-hierarchy",
                    description=f"Başlık atlaması: h{prev} → h{lvl} (sıralama bozuk)",
                    severity=WCAG_RULES["heading-hierarchy"]["severity"],
                    wcag_criteria=WCAG_RULES["heading-hierarchy"]["wcag"],
                    element=f"h{lvl}",
                    help_url=WCAG_RULES["heading-hierarchy"]["help_url"],
                ))
            prev = lvl
        return violations

    # ── Kural 4 & 5: color-contrast ───────────────────────────────────────────
    def check_color_contrast(self) -> list[A11yViolation]:
        """
        Gerçek renk analizi Playwright CSS hesabı gerektirir.
        Dom verisi içindeki contrast_ratio değerlerini kontrol eder.
        """
        violations = []
        for elem in self.data.get("contrast_elements", []):
            ratio = elem.get("contrast_ratio", 999)
            text = (elem.get("text", "") or "")[:40]
            element_str = elem.get("selector", "")

            if ratio < 4.5:
                violations.append(A11yViolation(
                    rule_id="color-contrast-aa",
                    description=f"Kontrast oranı AA eşiğinin altında: {ratio:.2f}:1 (minimum 4.5:1) — '{text}'",
                    severity=WCAG_RULES["color-contrast-aa"]["severity"],
                    wcag_criteria=WCAG_RULES["color-contrast-aa"]["wcag"],
                    element=element_str,
                    help_url=WCAG_RULES["color-contrast-aa"]["help_url"],
                ))
            elif ratio < 7.0:
                violations.append(A11yViolation(
                    rule_id="color-contrast-aaa",
                    description=f"Kontrast oranı AAA eşiğinin altında: {ratio:.2f}:1 (minimum 7:1) — '{text}'",
                    severity=WCAG_RULES["color-contrast-aaa"]["severity"],
                    wcag_criteria=WCAG_RULES["color-contrast-aaa"]["wcag"],
                    element=element_str,
                    help_url=WCAG_RULES["color-contrast-aaa"]["help_url"],
                ))
        return violations

    # ── Kural 6: tabindex ────────────────────────────────────────────────────
    def check_tabindex(self) -> list[A11yViolation]:
        violations = []
        for elem in self.data.get("tabindex_elements", []):
            ti = elem.get("tabindex")
            selector = elem.get("selector", "")
            try:
                ti_int = int(ti)
                if ti_int > 0:
                    violations.append(A11yViolation(
                        rule_id="tabindex",
                        description=f"tabindex={ti_int} pozitif değer; odak sırasını bozar",
                        severity=WCAG_RULES["tabindex"]["severity"],
                        wcag_criteria=WCAG_RULES["tabindex"]["wcag"],
                        element=selector,
                        help_url=WCAG_RULES["tabindex"]["help_url"],
                    ))
            except (TypeError, ValueError):
                pass
        return violations

    # ── Kural 7: aria-validation ─────────────────────────────────────────────
    def check_aria(self) -> list[A11yViolation]:
        violations = []
        for elem in self.data.get("aria_elements", []):
            role = elem.get("role", "")
            aria_hidden = elem.get("aria_hidden", "")
            selector = elem.get("selector", "")
            aria_label = elem.get("aria_label", "")
            aria_required = elem.get("aria_required", "")

            # Geçersiz rol
            if role and role in INVALID_ARIA_ROLES:
                violations.append(A11yViolation(
                    rule_id="aria-validation",
                    description=f"Geçersiz ARIA rolü: role='{role}'",
                    severity=WCAG_RULES["aria-validation"]["severity"],
                    wcag_criteria=WCAG_RULES["aria-validation"]["wcag"],
                    element=selector,
                    help_url=WCAG_RULES["aria-validation"]["help_url"],
                ))

            # aria-hidden="true" olan focusable element
            if aria_hidden == "true" and elem.get("focusable"):
                violations.append(A11yViolation(
                    rule_id="aria-validation",
                    description="aria-hidden='true' olan element odaklanabilir durumda",
                    severity="serious",
                    wcag_criteria="4.1.2",
                    element=selector,
                    help_url=WCAG_RULES["aria-validation"]["help_url"],
                ))

            # aria-required değeri geçersiz
            if aria_required and aria_required not in ("true", "false"):
                violations.append(A11yViolation(
                    rule_id="aria-validation",
                    description=f"aria-required geçersiz değer: '{aria_required}' (true/false olmalı)",
                    severity="moderate",
                    wcag_criteria="4.1.2",
                    element=selector,
                    help_url=WCAG_RULES["aria-validation"]["help_url"],
                ))
        return violations

    # ── Kural 8: link-text ───────────────────────────────────────────────────
    def check_link_text(self) -> list[A11yViolation]:
        violations = []
        for link in self.data.get("links", []):
            text = (link.get("text") or "").strip().lower()
            href = link.get("href", "")[:60]
            aria_label = link.get("aria_label", "")
            title = link.get("title", "")

            # Aria-label veya title varsa sorun yok
            if aria_label or title:
                continue

            if not text:
                violations.append(A11yViolation(
                    rule_id="link-text",
                    description=f"Bağlantıda metin yok: href={href}",
                    severity=WCAG_RULES["link-text"]["severity"],
                    wcag_criteria=WCAG_RULES["link-text"]["wcag"],
                    element=f'<a href="{href}">',
                    help_url=WCAG_RULES["link-text"]["help_url"],
                ))
            elif text in MEANINGLESS_LINK_TEXTS:
                violations.append(A11yViolation(
                    rule_id="link-text",
                    description=f"Bağlantı metni anlamsız: '{text}' href={href}",
                    severity="moderate",
                    wcag_criteria=WCAG_RULES["link-text"]["wcag"],
                    element=f'<a href="{href}">{text}</a>',
                    help_url=WCAG_RULES["link-text"]["help_url"],
                ))
        return violations

    # ── Kural 9: lang-attribute ──────────────────────────────────────────────
    def check_lang(self) -> list[A11yViolation]:
        lang = self.data.get("html_lang", "")
        if not lang:
            return [A11yViolation(
                rule_id="lang-attribute",
                description="<html> elementinde lang özniteliği eksik",
                severity=WCAG_RULES["lang-attribute"]["severity"],
                wcag_criteria=WCAG_RULES["lang-attribute"]["wcag"],
                element="<html>",
                help_url=WCAG_RULES["lang-attribute"]["help_url"],
            )]
        # Geçersiz dil kodu kontrolü
        if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', lang):
            return [A11yViolation(
                rule_id="lang-attribute",
                description=f"<html lang='{lang}'> değeri BCP 47 formatında değil",
                severity="minor",
                wcag_criteria=WCAG_RULES["lang-attribute"]["wcag"],
                element=f'<html lang="{lang}">',
                help_url=WCAG_RULES["lang-attribute"]["help_url"],
            )]
        return []

    # ── Kural 10: page-title ─────────────────────────────────────────────────
    def check_page_title(self) -> list[A11yViolation]:
        title = (self.data.get("page_title") or "").strip()
        if not title:
            return [A11yViolation(
                rule_id="page-title",
                description="<title> elementi eksik veya boş",
                severity=WCAG_RULES["page-title"]["severity"],
                wcag_criteria=WCAG_RULES["page-title"]["wcag"],
                element="<title>",
                help_url=WCAG_RULES["page-title"]["help_url"],
            )]
        if len(title) < 5:
            return [A11yViolation(
                rule_id="page-title",
                description=f"Sayfa başlığı çok kısa: '{title}'",
                severity="minor",
                wcag_criteria=WCAG_RULES["page-title"]["wcag"],
                element=f"<title>{title}</title>",
                help_url=WCAG_RULES["page-title"]["help_url"],
            )]
        return []

    # ── Kural 11: button-accessibility ───────────────────────────────────────
    def check_buttons(self) -> list[A11yViolation]:
        violations = []
        for btn in self.data.get("buttons", []):
            text = (btn.get("text") or "").strip()
            aria_label = btn.get("aria_label", "")
            title = btn.get("title", "")
            selector = btn.get("selector", "")
            if not text and not aria_label and not title:
                violations.append(A11yViolation(
                    rule_id="button-accessibility",
                    description="Butonun erişilebilir adı yok (text/aria-label/title eksik)",
                    severity=WCAG_RULES["button-accessibility"]["severity"],
                    wcag_criteria=WCAG_RULES["button-accessibility"]["wcag"],
                    element=selector,
                    help_url=WCAG_RULES["button-accessibility"]["help_url"],
                ))
        return violations

    # ── Tümünü çalıştır ───────────────────────────────────────────────────────
    def run_all(self, wcag_level: str = "AA") -> dict:
        """
        Tüm kuralları çalıştırır.
        Returns:
            {violations: [], warnings: [], passes: [], score: float}
        """
        all_violations: list[A11yViolation] = []
        passes: list[str] = []

        rule_checks = {
            "img-alt":              self.check_img_alt,
            "form-label":           self.check_form_label,
            "heading-hierarchy":    self.check_heading_hierarchy,
            "color-contrast":       self.check_color_contrast,
            "tabindex":             self.check_tabindex,
            "aria-validation":      self.check_aria,
            "link-text":            self.check_link_text,
            "lang-attribute":       self.check_lang,
            "page-title":           self.check_page_title,
            "button-accessibility": self.check_buttons,
        }

        for rule_id, check_fn in rule_checks.items():
            viols = check_fn()
            if viols:
                all_violations.extend(viols)
            else:
                passes.append(rule_id)

        # AAA seviyesinde değilse AAA ihlallerini warnings'a taşı
        violations, warnings = [], []
        for v in all_violations:
            if wcag_level == "AA" and v.rule_id == "color-contrast-aaa":
                warnings.append(v)
            else:
                violations.append(v)

        # Ağırlıklı skor hesaplama
        penalized_weight = 0
        for v in violations:
            rule_key = v.rule_id
            if rule_key not in WCAG_RULES:
                # color-contrast-aa → color-contrast-aa anahtarı
                rule_key = rule_key.rsplit("-", 1)[0] if "-" in rule_key else rule_key
            penalized_weight += WCAG_RULES.get(rule_key, {}).get("weight", 5)

        score = max(0.0, 100.0 - (penalized_weight / MAX_WEIGHT * 100))

        return {
            "violations": violations,
            "warnings": warnings,
            "passes": passes,
            "score": round(score, 2),
        }


# ──────────────────────────────────────────────────────────────────────────────
# DOM Veri Toplayıcı (Playwright)
# ──────────────────────────────────────────────────────────────────────────────
DOM_ANALYSIS_SCRIPT = """
() => {
  const result = {
    html_lang: document.documentElement.lang || "",
    page_title: document.title || "",
    images: [],
    inputs: [],
    headings: [],
    links: [],
    buttons: [],
    tabindex_elements: [],
    aria_elements: [],
    contrast_elements: [],
  };

  // Resimler
  document.querySelectorAll("img").forEach(img => {
    result.images.push({
      alt: img.hasAttribute("alt") ? img.getAttribute("alt") : null,
      src: img.src ? img.src.substring(0, 100) : "",
      role: img.getAttribute("role") || ""
    });
  });

  // Form girişleri
  document.querySelectorAll("input, select, textarea").forEach(inp => {
    const id = inp.id;
    result.inputs.push({
      type: inp.type || "text",
      name: inp.name || inp.id || "",
      has_label: id ? !!document.querySelector(`label[for="${id}"]`) : false,
      aria_label: inp.getAttribute("aria-label") || "",
      aria_labelledby: inp.getAttribute("aria-labelledby") || "",
      title: inp.title || ""
    });
  });

  // Başlıklar
  document.querySelectorAll("h1,h2,h3,h4,h5,h6").forEach(h => {
    result.headings.push({ level: parseInt(h.tagName.substring(1)), text: h.innerText.substring(0, 60) });
  });

  // Bağlantılar
  document.querySelectorAll("a[href]").forEach(a => {
    result.links.push({
      text: a.innerText || a.textContent || "",
      href: a.href ? a.href.substring(0, 80) : "",
      aria_label: a.getAttribute("aria-label") || "",
      title: a.title || ""
    });
  });

  // Butonlar
  document.querySelectorAll("button, [role='button'], input[type='button'], input[type='submit']").forEach(btn => {
    result.buttons.push({
      text: btn.innerText || btn.value || btn.textContent || "",
      aria_label: btn.getAttribute("aria-label") || "",
      title: btn.title || "",
      selector: btn.tagName.toLowerCase() + (btn.id ? "#" + btn.id : "")
    });
  });

  // tabindex
  document.querySelectorAll("[tabindex]").forEach(el => {
    result.tabindex_elements.push({
      tabindex: el.getAttribute("tabindex"),
      selector: el.tagName.toLowerCase() + (el.id ? "#" + el.id : "")
    });
  });

  // ARIA elementleri
  document.querySelectorAll("[role], [aria-hidden], [aria-required], [aria-label]").forEach(el => {
    const tag = el.tagName.toLowerCase();
    const focusable = el.tabIndex >= 0;
    result.aria_elements.push({
      role: el.getAttribute("role") || "",
      aria_hidden: el.getAttribute("aria-hidden") || "",
      aria_required: el.getAttribute("aria-required") || "",
      aria_label: el.getAttribute("aria-label") || "",
      focusable: focusable,
      selector: tag + (el.id ? "#" + el.id : "")
    });
  });

  // Kontrast: metin elementleri (kısmi analiz — computed style)
  const textElems = document.querySelectorAll("p, span, h1, h2, h3, h4, h5, h6, li, td, a, button, label");
  let count = 0;
  textElems.forEach(el => {
    if (count >= 50) return; // Performans için sınırla
    const style = window.getComputedStyle(el);
    const fg = style.color;
    const bg = style.backgroundColor;
    if (!fg || !bg || bg === "rgba(0, 0, 0, 0)") return;
    // Basit renk ayrıştırma (rgb/rgba)
    const parseRgb = (s) => {
      const m = s.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
      return m ? [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])] : null;
    };
    const relLum = (rgb) => {
      if (!rgb) return 0;
      const c = rgb.map(v => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    };
    const fgRgb = parseRgb(fg);
    const bgRgb = parseRgb(bg);
    if (!fgRgb || !bgRgb) return;
    const l1 = relLum(fgRgb), l2 = relLum(bgRgb);
    const lighter = Math.max(l1, l2), darker = Math.min(l1, l2);
    const ratio = (lighter + 0.05) / (darker + 0.05);
    if (ratio < 7.1) {
      result.contrast_elements.push({
        text: (el.innerText || "").substring(0, 40),
        contrast_ratio: Math.round(ratio * 100) / 100,
        selector: el.tagName.toLowerCase() + (el.id ? "#" + el.id : ""),
        fg, bg
      });
      count++;
    }
  });

  return result;
}
"""


# ──────────────────────────────────────────────────────────────────────────────
# Ana Erişilebilirlik Test Sınıfı
# ──────────────────────────────────────────────────────────────────────────────
class AccessibilityTester:
    """
    Web sayfaları için WCAG 2.1 erişilebilirlik testi.

    Kullanım::

        tester = AccessibilityTester(wcag_level="AA")
        result = tester.test_url("https://example.com")
        report = tester.generate_report(result)
    """

    def __init__(
        self,
        wcag_level: str = "AA",
        browser_type: str = "chromium",
        headless: bool = True,
        ignore_rules: list[str] | None = None,
        timeout: int = 30_000,
        use_axe: bool = False,
    ):
        """
        Args:
            wcag_level:   "AA" veya "AAA"
            browser_type: Playwright tarayıcı tipi
            headless:     Headless mod
            ignore_rules: Atlanacak kural ID'leri
            timeout:      Sayfa yükleme timeout (ms)
            use_axe:      axe-core entegrasyonu kullan (Playwright gerekir)
        """
        self.wcag_level   = wcag_level.upper()
        self.browser_type = browser_type
        self.headless     = headless
        self.ignore_rules = set(ignore_rules or [])
        self.timeout      = timeout
        self.use_axe      = use_axe and HAS_PLAYWRIGHT

    # ── DOM Verisi Topla ─────────────────────────────────────────────────────
    def _collect_dom_data(self, page: "Page") -> dict:
        """Playwright page nesnesinden DOM analiz verisi toplar."""
        try:
            return page.evaluate(DOM_ANALYSIS_SCRIPT)
        except Exception as exc:
            logger.warning("DOM analizi hatası: %s", exc)
            return {}

    # ── URL'yi Test Et ───────────────────────────────────────────────────────
    def test_url(
        self,
        url: str,
        wait_for: str | None = None,
        wait_ms: int = 1000,
    ) -> A11yResult:
        """
        Verilen URL'yi Playwright ile açıp erişilebilirlik testini çalıştırır.

        Args:
            url:      Test edilecek URL
            wait_for: Bekleme CSS seçicisi
            wait_ms:  Ekstra bekleme süresi (ms)

        Returns:
            A11yResult nesnesi
        """
        if not HAS_PLAYWRIGHT:
            result = A11yResult(url=url)
            result.error = "Playwright yüklü değil: pip install playwright && playwright install"
            return result

        with sync_playwright() as pw:
            launcher = getattr(pw, self.browser_type)
            browser  = launcher.launch(headless=self.headless)
            ctx      = browser.new_context()
            page     = ctx.new_page()
            page.set_default_timeout(self.timeout)
            try:
                page.goto(url)
                if wait_for:
                    page.wait_for_selector(wait_for, timeout=10_000)
                page.wait_for_timeout(wait_ms)
                return self.test_page(page, url=url)
            except Exception as exc:
                logger.error("URL test hatası [%s]: %s", url, exc)
                result = A11yResult(url=url)
                result.error = str(exc)
                return result
            finally:
                ctx.close()
                browser.close()

    # ── Page Nesnesini Test Et ────────────────────────────────────────────────
    def test_page(self, page: "Page", url: str = "") -> A11yResult:
        """
        Açık bir Playwright Page nesnesi üzerinde erişilebilirlik testini çalıştırır.

        Returns:
            A11yResult nesnesi
        """
        dom_data = self._collect_dom_data(page)
        result   = A11yResult(url=url or page.url)
        result.page_title = dom_data.get("page_title", "")
        result.wcag_level = self.wcag_level

        # axe-core entegrasyonu
        if self.use_axe:
            try:
                axe_results = self._run_axe(page)
                result.violations = axe_results.get("violations", [])
                result.passes     = axe_results.get("passes", [])
                result.score      = axe_results.get("score", 0.0)
                return result
            except Exception as axe_err:
                logger.warning("axe-core çalıştırılamadı, fallback kullanılıyor: %s", axe_err)

        # Kendi kural motoru
        engine = WCAGRuleEngine(dom_data)
        engine_result = engine.run_all(wcag_level=self.wcag_level)

        # ignore_rules filtreleme
        violations = [v for v in engine_result["violations"] if v.rule_id not in self.ignore_rules]
        warnings   = [w for w in engine_result["warnings"]   if w.rule_id not in self.ignore_rules]

        result.violations = violations
        result.warnings   = warnings
        result.passes     = engine_result["passes"]
        result.score      = engine_result["score"]

        return result

    # ── axe-core Çalıştır ─────────────────────────────────────────────────────
    def _run_axe(self, page: "Page") -> dict:
        """axe-core'u sayfaya inject eder ve çalıştırır."""
        # axe-core CDN'den yükle
        page.evaluate("""
            async () => {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                document.head.appendChild(script);
                await new Promise(r => script.onload = r);
            }
        """)
        page.wait_for_timeout(500)
        axe_raw = page.evaluate("async () => await axe.run()")
        violations = []
        for v in axe_raw.get("violations", []):
            for node in v.get("nodes", []):
                violations.append(A11yViolation(
                    rule_id=v["id"],
                    description=v.get("description", ""),
                    severity=v.get("impact", "moderate"),
                    wcag_criteria=", ".join(
                        t.get("data", "") for t in v.get("tags", []) if "wcag" in t.get("data", "")
                    ),
                    element=node.get("html", "")[:100],
                    help_url=v.get("helpUrl", ""),
                ))
        passes = [p["id"] for p in axe_raw.get("passes", [])]
        score = max(0.0, 100.0 - len(violations) * 3)
        return {"violations": violations, "passes": passes, "score": score}

    # ── Rapor Üretimi ─────────────────────────────────────────────────────────
    def generate_report(
        self,
        result: A11yResult,
        output_path: Path | str | None = None,
        include_warnings: bool = True,
    ) -> str:
        """
        A11yResult'tan HTML rapor üretir.

        Returns:
            HTML rapor dosyasının yolu
        """
        if output_path is None:
            reports_dir = settings.REPORTS_DIR / "accessibility"
            reports_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"a11y_report_{ts}.html"
        output_path = Path(output_path)

        severity_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        sorted_viols = sorted(result.violations, key=lambda v: severity_order.get(v.severity, 9))

        # İhlal satırları
        rows = ""
        for v in sorted_viols:
            sev_cls = {
                "critical": "badge-red", "serious": "badge-orange",
                "moderate": "badge-yellow", "minor": "badge-blue"
            }.get(v.severity, "badge-blue")
            rows += f"""
            <tr>
              <td><code>{v.rule_id}</code></td>
              <td><span class="badge {sev_cls}">{v.severity.upper()}</span></td>
              <td>{v.wcag_criteria}</td>
              <td>{v.description}</td>
              <td><code class="elem">{v.element[:80]}</code></td>
            </tr>"""

        # Uyarı satırları
        warn_rows = ""
        if include_warnings:
            for w in result.warnings:
                warn_rows += f"""
                <tr>
                  <td><code>{w.rule_id}</code></td>
                  <td><span class="badge badge-gray">UYARI</span></td>
                  <td>{w.wcag_criteria}</td>
                  <td>{w.description}</td>
                  <td><code class="elem">{w.element[:80]}</code></td>
                </tr>"""

        score_color = "#22c55e" if result.score >= 80 else ("#f59e0b" if result.score >= 50 else "#ef4444")

        passes_html = "".join(
            f'<span class="pass-badge">{p}</span>' for p in result.passes
        )

        # Uyarı bölümü (içiçe f-string sorununu önlemek için ayrı değişkende)
        if include_warnings and warn_rows:
            warnings_section = (
                f'<section>\n  <h2>Uyarılar ({len(result.warnings)})</h2>\n'
                f'  <table>\n    <thead><tr><th>Kural</th><th>Tip</th>'
                f'<th>WCAG</th><th>Açıklama</th><th>Element</th></tr></thead>\n'
                f'    <tbody>{warn_rows}</tbody>\n  </table>\n</section>\n'
            )
        else:
            warnings_section = ""

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Erişilebilirlik Raporu — {result.url[:60]}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}
  header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 24px 32px; }}
  header h1 {{ font-size: 1.4rem; color: #f8fafc; }}
  header p  {{ color: #94a3b8; font-size: 0.85rem; margin-top: 6px; word-break: break-all; }}
  .score-box {{ display: inline-block; padding: 8px 20px; border-radius: 12px;
               font-size: 2rem; font-weight: 700; margin-top: 12px;
               border: 2px solid {score_color}; color: {score_color}; }}
  .score-lbl {{ font-size: 0.75rem; color: #94a3b8; margin-left: 6px; vertical-align: middle; }}
  section {{ padding: 20px 32px; }}
  section h2 {{ font-size: 1rem; color: #94a3b8; margin-bottom: 12px;
               text-transform: uppercase; letter-spacing: 0.05em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid #1e293b; font-size: 0.83rem; }}
  th {{ background: #1e293b; color: #94a3b8; font-weight: 600; }}
  code {{ background: #1e293b; padding: 2px 6px; border-radius: 4px; font-size: 0.78rem; color: #7dd3fc; }}
  .elem {{ color: #fda4af; }}
  .badge {{ padding: 2px 8px; border-radius: 99px; font-size: 0.7rem; font-weight: 700; }}
  .badge-red    {{ background: #450a0a; color: #fca5a5; }}
  .badge-orange {{ background: #431407; color: #fdba74; }}
  .badge-yellow {{ background: #422006; color: #fde68a; }}
  .badge-blue   {{ background: #0c1a2e; color: #93c5fd; }}
  .badge-gray   {{ background: #1e293b; color: #94a3b8; }}
  .pass-badge {{ display: inline-block; margin: 3px; padding: 2px 9px; border-radius: 99px;
                background: #052e16; color: #86efac; font-size: 0.72rem; }}
  .passes-grid {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }}
  footer {{ text-align: center; padding: 20px; color: #475569; font-size: 0.8rem; }}
</style>
</head>
<body>
<header>
  <h1>♿ Erişilebilirlik Test Raporu</h1>
  <p>{result.url}</p>
  <p style="margin-top:8px;">
    Sayfa Başlığı: <strong>{result.page_title}</strong> &nbsp;|&nbsp;
    WCAG Seviye: <strong>{result.wcag_level}</strong> &nbsp;|&nbsp;
    {result.timestamp}
  </p>
  <div style="margin-top:12px;">
    <span class="score-box">{result.score}</span>
    <span class="score-lbl">/ 100 Puan</span>
  </div>
</header>

<section>
  <h2>İhlaller ({len(result.violations)})</h2>
  <table>
    <thead>
      <tr><th>Kural</th><th>Önem</th><th>WCAG</th><th>Açıklama</th><th>Element</th></tr>
    </thead>
    <tbody>{rows or '<tr><td colspan="5" style="text-align:center;color:#22c55e">İhlal bulunamadı ✓</td></tr>'}</tbody>
  </table>
</section>

{warnings_section}

<section>
  <h2>Geçen Kurallar ({len(result.passes)})</h2>
  <div class="passes-grid">{passes_html}</div>
</section>

<footer>Mavi Yaka Test Altyapısı — Accessibility Module &nbsp;|&nbsp; {result.timestamp}</footer>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")
        logger.info("Erişilebilirlik raporu üretildi: %s", output_path)
        return str(output_path)

    # ── JSON Rapor ────────────────────────────────────────────────────────────
    def to_dict(self, result: A11yResult) -> dict:
        """A11yResult'ı API'ye uygun dict'e çevirir."""
        return {
            "url": result.url,
            "score": result.score,
            "wcag_level": result.wcag_level,
            "page_title": result.page_title,
            "timestamp": result.timestamp,
            "violation_count": len(result.violations),
            "warning_count": len(result.warnings),
            "pass_count": len(result.passes),
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "description": v.description,
                    "severity": v.severity,
                    "wcag_criteria": v.wcag_criteria,
                    "element": v.element,
                    "help_url": v.help_url,
                }
                for v in result.violations
            ],
            "warnings": [
                {
                    "rule_id": w.rule_id,
                    "description": w.description,
                    "severity": w.severity,
                    "wcag_criteria": w.wcag_criteria,
                }
                for w in result.warnings
            ],
            "passes": result.passes,
            "error": result.error,
        }
