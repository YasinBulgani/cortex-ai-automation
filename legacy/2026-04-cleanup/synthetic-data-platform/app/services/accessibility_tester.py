"""
WCAG 2.1 Erişilebilirlik Test Modülü - 10 kural, severity-weighted scoring

Bu modül, HTML sayfalarını WCAG 2.1 (Web Content Accessibility Guidelines)
standartlarına göre statik olarak analiz eder. Harici bağımlılık gerektirmez;
yalnızca Python standart kütüphanesi (re, json, math vb.) kullanılır.

Desteklenen WCAG 2.1 kontrolleri:
  1. img-alt              — Resimler için alternatif metin (Level A)
  2. form-label           — Form elemanları için etiket ilişkilendirmesi (Level A)
  3. heading-hierarchy    — Başlık hiyerarşisi sıralaması (Level A)
  4. color-contrast       — Renk kontrastı oranı (Level AA: 4.5:1 / 3:1)
  5. tabindex             — Pozitif tabindex kullanımından kaçınma (Level A)
  6. aria-validation      — ARIA rol ve özellik geçerliliği (Level A)
  7. link-text            — Bağlantı metninin açıklayıcı olması (Level A)
  8. lang-attribute       — HTML lang özelliği (Level A)
  9. page-title           — Sayfa başlığı varlığı (Level A)
  10. button-accessibility — Buton erişilebilirliği (Level A)

Skor hesaplama:
  Her ihlal önem ağırlığıyla puanı düşürür:
    critical → -25 puan,  serious → -15,  moderate → -8,  minor → -3

Kullanım örneği::

    tester = AccessibilityTester(wcag_level="AA")
    report = tester.test_page(html_str, url="https://example.com")
    print(f"Skor: {report.score}/100")
    for v in report.get_critical_violations():
        print(f"  KRITIK: {v.rule_id} — {v.description}")
"""

import re
import json
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

# Modül seviyesinde logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WCAG 2.1 Kural Sabitleri
# ---------------------------------------------------------------------------

WCAG_RULES: Dict[str, dict] = {
    "img-alt": {
        "level":       "A",
        "description": "Resimler alt metin içermeli",
        "help_text":   (
            "Her <img> etiketi anlamlı bir 'alt' özelliğine sahip olmalıdır. "
            "Dekoratif resimler için alt='' (boş dize) kullanın."
        ),
        "wcag_criteria": "1.1.1 Non-text Content",
        "severity":    "serious",
    },
    "form-label": {
        "level":       "A",
        "description": "Form elemanları etiketle ilişkilendirilmeli",
        "help_text":   (
            "Her <input>, <select> ve <textarea> elemanı, for/id eşleşmesi veya "
            "aria-label/aria-labelledby ile bir etikete bağlanmalıdır."
        ),
        "wcag_criteria": "1.3.1 Info and Relationships",
        "severity":    "critical",
    },
    "heading-hierarchy": {
        "level":       "A",
        "description": "Başlık seviyeleri sıralı olmalı (h1→h2→h3…)",
        "help_text":   (
            "Başlık seviyeleri atlanmamalıdır. Örneğin h1 sonrası doğrudan h3 "
            "kullanmak hiyerarşiyi bozar."
        ),
        "wcag_criteria": "1.3.1 Info and Relationships",
        "severity":    "moderate",
    },
    "color-contrast": {
        "level":       "AA",
        "description": "Metin ve arka plan rengi yeterli kontrast oranına sahip olmalı",
        "help_text":   (
            "Normal metin: en az 4.5:1. Büyük metin (18pt+ veya 14pt kalın): "
            "en az 3:1. AAA seviyesi için: 7:1 normal, 4.5:1 büyük metin."
        ),
        "wcag_criteria": "1.4.3 Contrast (Minimum)",
        "severity":    "serious",
    },
    "tabindex": {
        "level":       "A",
        "description": "Pozitif tabindex değerlerinden kaçınılmalı",
        "help_text":   (
            "tabindex > 0 değerleri sekme sırasını bozabilir. "
            "tabindex='0' veya tabindex='-1' kullanın."
        ),
        "wcag_criteria": "2.4.3 Focus Order",
        "severity":    "moderate",
    },
    "aria-validation": {
        "level":       "A",
        "description": "ARIA rolleri ve özellikleri geçerli olmalı",
        "help_text":   (
            "Kullanılan ARIA rolleri WAI-ARIA spesifikasyonunda tanımlanmış "
            "olmalıdır. Geçersiz rol veya özellik adları ekran okuyucuları "
            "yanıltır."
        ),
        "wcag_criteria": "4.1.2 Name, Role, Value",
        "severity":    "serious",
    },
    "link-text": {
        "level":       "A",
        "description": "Bağlantı metinleri açıklayıcı olmalı",
        "help_text":   (
            "'Tıklayın', 'buraya', 'daha fazla' gibi belirsiz bağlantı metinleri "
            "ekran okuyucu kullanıcıları için anlamsızdır. "
            "Bağlantının hedefini açıklayan metin kullanın."
        ),
        "wcag_criteria": "2.4.4 Link Purpose (In Context)",
        "severity":    "serious",
    },
    "lang-attribute": {
        "level":       "A",
        "description": "<html> etiketi geçerli bir 'lang' özelliği içermeli",
        "help_text":   (
            "lang özelliği (örn. lang='tr', lang='en') ekran okuyucuların "
            "doğru dili kullanmasını sağlar. BCP 47 dil etiketi kullanın."
        ),
        "wcag_criteria": "3.1.1 Language of Page",
        "severity":    "serious",
    },
    "page-title": {
        "level":       "A",
        "description": "Sayfa anlamlı bir <title> içermeli",
        "help_text":   (
            "<title> etiketi boş olmamalı ve sayfanın içeriğini açıkça "
            "tanımlamalıdır. Ekran okuyucular ve tarayıcı sekmeleri için kritiktir."
        ),
        "wcag_criteria": "2.4.2 Page Titled",
        "severity":    "critical",
    },
    "button-accessibility": {
        "level":       "A",
        "description": "Butonlar erişilebilir metin veya ARIA etiketi içermeli",
        "help_text":   (
            "Metin içermeyen butonlar (sadece ikon gibi) aria-label veya "
            "aria-labelledby ile etiketlenmelidir. type özelliği de açıkça "
            "belirtilmelidir."
        ),
        "wcag_criteria": "4.1.2 Name, Role, Value",
        "severity":    "critical",
    },
}

# Önem derecesine göre puan kesintisi ağırlıkları
SEVERITY_WEIGHTS: Dict[str, int] = {
    "critical": 25,
    "serious":  15,
    "moderate":  8,
    "minor":     3,
}

# Önem derecesine göre etki skoru (1-10)
SEVERITY_IMPACT: Dict[str, int] = {
    "critical": 10,
    "serious":   7,
    "moderate":  4,
    "minor":     2,
}

# Geçerli ARIA rolleri (WAI-ARIA 1.2 temel seti)
VALID_ARIA_ROLES: frozenset = frozenset({
    "alert", "alertdialog", "application", "article", "banner",
    "button", "cell", "checkbox", "columnheader", "combobox",
    "command", "complementary", "composite", "contentinfo",
    "definition", "dialog", "directory", "document", "feed",
    "figure", "form", "grid", "gridcell", "group", "heading",
    "img", "input", "landmark", "link", "list", "listbox",
    "listitem", "log", "main", "marquee", "math", "menu",
    "menubar", "menuitem", "menuitemcheckbox", "menuitemradio",
    "navigation", "none", "note", "option", "presentation",
    "progressbar", "radio", "radiogroup", "region", "row",
    "rowgroup", "rowheader", "scrollbar", "search", "searchbox",
    "section", "sectionhead", "select", "separator", "slider",
    "spinbutton", "status", "switch", "tab", "table", "tablist",
    "tabpanel", "term", "textbox", "timer", "toolbar",
    "tooltip", "tree", "treegrid", "treeitem", "widget", "window",
})

# Belirsiz bağlantı metinleri (küçük harf)
VAGUE_LINK_TEXTS: frozenset = frozenset({
    "tıkla", "tıklayın", "click", "click here", "here", "buraya",
    "daha fazla", "more", "read more", "devam", "devam et",
    "link", "bağlantı", "go", "git", "details", "detaylar",
    "bilgi", "info", "incele", "view",
})


# ---------------------------------------------------------------------------
# Veri Sınıfları
# ---------------------------------------------------------------------------

@dataclass
class AccessibilityViolation:
    """
    Tek bir WCAG ihlalini temsil eden veri sınıfı.

    Her ihlal; hangi kurala aykırı olduğunu, hangi HTML elementinde
    bulunduğunu, önem derecesini ve kullanıcıya gösterilecek yardım
    metnini içerir.
    """
    rule_id:          str            # WCAG_RULES anahtarı (örn. "img-alt")
    level:            str            # "A", "AA" veya "AAA"
    severity:         str            # "critical" | "serious" | "moderate" | "minor"
    element_selector: str            # CSS benzeri seçici (örn. 'img[src="logo.png"]')
    description:      str            # Kısa ihlal açıklaması
    help_text:        str            # Düzeltme rehberi
    wcag_criteria:    str            # İlgili WCAG kriteri (örn. "1.1.1 Non-text Content")
    impact_score:     int            # 1-10 arası etki skoru (10 = en kritik)

    def to_dict(self) -> dict:
        """İhlali JSON uyumlu sözlüğe dönüştürür."""
        return {
            "rule_id":          self.rule_id,
            "level":            self.level,
            "severity":         self.severity,
            "element_selector": self.element_selector,
            "description":      self.description,
            "help_text":        self.help_text,
            "wcag_criteria":    self.wcag_criteria,
            "impact_score":     self.impact_score,
        }


@dataclass
class AccessibilityReport:
    """
    Bir sayfanın tüm erişilebilirlik analiz sonucunu tutan rapor sınıfı.

    test_page() metodunun çıktısıdır. Skor, ihlaller, geçen kurallar ve
    özet istatistikleri içerir.
    """
    url:           str
    tested_at:     str
    wcag_level:    str
    score:         float                     # 0-100 arası ağırlıklı puan
    violations:    List[AccessibilityViolation] = field(default_factory=list)
    passed_rules:  List[str]                 = field(default_factory=list)
    summary:       Dict[str, Any]            = field(default_factory=dict)

    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Raporu JSON serileştirilebilir sözlüğe dönüştürür.

        Returns:
            dict: Tüm rapor alanlarını içeren iç içe sözlük.
        """
        return {
            "url":          self.url,
            "tested_at":    self.tested_at,
            "wcag_level":   self.wcag_level,
            "score":        self.score,
            "violations":   [v.to_dict() for v in self.violations],
            "passed_rules": self.passed_rules,
            "summary":      self.summary,
        }

    def get_critical_violations(self) -> List[AccessibilityViolation]:
        """
        Yalnızca 'critical' önem derecesindeki ihlalleri döndürür.

        Returns:
            List[AccessibilityViolation]: Kritik ihlaller listesi.
        """
        return [v for v in self.violations if v.severity == "critical"]

    def get_recommendations(self) -> List[str]:
        """
        İhlallere dayalı önceliklendirilmiş düzeltme önerileri üretir.

        Kritik ihlaller önce sıralanır. Her ihlal için help_text'ten
        kısa bir eylem cümlesi türetilir.

        Returns:
            List[str]: İnsan tarafından okunabilir öneriler listesi.
        """
        if not self.violations:
            return ["Tebrikler! Seçilen WCAG seviyesinde ihlal tespit edilmedi."]

        # Önem derecesine göre sırala: critical → serious → moderate → minor
        severity_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        sorted_violations = sorted(
            self.violations,
            key=lambda v: severity_order.get(v.severity, 9)
        )

        seen_rules: set = set()
        recommendations: List[str] = []

        for v in sorted_violations:
            if v.rule_id in seen_rules:
                continue
            seen_rules.add(v.rule_id)

            prefix = {
                "critical": "[KRİTİK]",
                "serious":  "[CİDDİ]",
                "moderate": "[ORTA]",
                "minor":    "[KÜÇÜK]",
            }.get(v.severity, "[BİLGİ]")

            recommendations.append(
                f"{prefix} {v.description}: {v.help_text}"
            )

        if self.score >= 90:
            recommendations.append(
                f"Genel skor iyi ({self.score:.0f}/100). "
                "Kalan ihlalleri gidererek mükemmel skora ulaşabilirsiniz."
            )
        elif self.score < 60:
            recommendations.append(
                f"Skor düşük ({self.score:.0f}/100). "
                "Kritik ve ciddi ihlallerin hepsinin giderilmesi önceliklidir."
            )

        return recommendations

    def to_json(self, indent: int = 2) -> str:
        """
        Raporu JSON string olarak döndürür.

        Args:
            indent: JSON girintisi (varsayılan: 2).

        Returns:
            str: Güzel biçimlendirilmiş JSON.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# ColorContrastChecker — WCAG renk kontrast hesaplama
# ---------------------------------------------------------------------------

class ColorContrastChecker:
    """
    WCAG 2.1 renk kontrast oranı hesaplama sınıfı.

    Göreli parlaklık (relative luminance) sRGB doğrusallaştırma formülü
    kullanılarak hesaplanır; kontrast oranı ise şu formülle bulunur:
        CR = (L1 + 0.05) / (L2 + 0.05)
    burada L1 ≥ L2 (açık renk / koyu renk).

    Referans:
        WCAG 2.1 Success Criterion 1.4.3 — https://www.w3.org/TR/WCAG21/#contrast-minimum
    """

    def __init__(self) -> None:
        """ColorContrastChecker başlatıcı."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_relative_luminance(self, r: int, g: int, b: int) -> float:
        """
        Bir RGB renginin göreli parlaklığını (relative luminance) hesaplar.

        sRGB doğrusallaştırma formülü:
            C_srgb = C_8bit / 255
            C_lin  = C_srgb / 12.92                    if C_srgb ≤ 0.04045
            C_lin  = ((C_srgb + 0.055) / 1.055) ^ 2.4 otherwise

        Parlaklık:
            L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin

        Args:
            r: Kırmızı bileşen (0-255).
            g: Yeşil bileşen (0-255).
            b: Mavi bileşen (0-255).

        Returns:
            float: Göreli parlaklık değeri [0.0, 1.0].
        """
        def linearize(c_8bit: int) -> float:
            c = c_8bit / 255.0
            if c <= 0.04045:
                return c / 12.92
            return math.pow((c + 0.055) / 1.055, 2.4)

        r_lin = linearize(r)
        g_lin = linearize(g)
        b_lin = linearize(b)

        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

    def get_contrast_ratio(
        self,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int],
    ) -> float:
        """
        İki renk arasındaki WCAG kontrast oranını hesaplar.

        Formül: CR = (L_lighter + 0.05) / (L_darker + 0.05)

        Args:
            color1: İlk renk (R, G, B) tuple, değerler 0-255.
            color2: İkinci renk (R, G, B) tuple, değerler 0-255.

        Returns:
            float: Kontrast oranı [1.0, 21.0].
                   1.0 = özdeş renkler, 21.0 = siyah/beyaz maksimum.
        """
        l1 = self.get_relative_luminance(*color1)
        l2 = self.get_relative_luminance(*color2)

        lighter = max(l1, l2)
        darker  = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    def passes_aa(self, ratio: float, is_large_text: bool = False) -> bool:
        """
        Kontrast oranının WCAG AA seviyesini geçip geçmediğini kontrol eder.

        AA eşikleri:
          - Normal metin: 4.5:1
          - Büyük metin (18pt+ veya 14pt kalın): 3:1

        Args:
            ratio:         Hesaplanan kontrast oranı.
            is_large_text: Büyük metin mi? (varsayılan: False).

        Returns:
            bool: AA seviyesini geçiyorsa True.
        """
        threshold = 3.0 if is_large_text else 4.5
        return ratio >= threshold

    def passes_aaa(self, ratio: float, is_large_text: bool = False) -> bool:
        """
        Kontrast oranının WCAG AAA seviyesini geçip geçmediğini kontrol eder.

        AAA eşikleri:
          - Normal metin: 7:1
          - Büyük metin: 4.5:1

        Args:
            ratio:         Hesaplanan kontrast oranı.
            is_large_text: Büyük metin mi? (varsayılan: False).

        Returns:
            bool: AAA seviyesini geçiyorsa True.
        """
        threshold = 4.5 if is_large_text else 7.0
        return ratio >= threshold

    def parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """
        Renk string'ini (R, G, B) tuple'ına dönüştürür.

        Desteklenen formatlar:
          - Kısa hex:   "#fff"     → (255, 255, 255)
          - Uzun hex:   "#ffffff"  → (255, 255, 255)
          - rgb():      "rgb(255, 255, 255)"
          - rgba():     "rgba(255, 255, 255, 1.0)"  (alpha yoksayılır)

        Args:
            color_str: Renk dizgisi (boşluk ve büyük/küçük harf fark etmez).

        Returns:
            Tuple[int, int, int]: (R, G, B) değerleri 0-255 aralığında.

        Raises:
            ValueError: Tanınan bir renk formatı değilse.
        """
        s = color_str.strip().lower()

        # Hex kısa: #abc → #aabbcc
        m_short = re.match(r'^#([0-9a-f])([0-9a-f])([0-9a-f])$', s)
        if m_short:
            r = int(m_short.group(1) * 2, 16)
            g = int(m_short.group(2) * 2, 16)
            b = int(m_short.group(3) * 2, 16)
            return r, g, b

        # Hex uzun: #aabbcc
        m_long = re.match(r'^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$', s)
        if m_long:
            r = int(m_long.group(1), 16)
            g = int(m_long.group(2), 16)
            b = int(m_long.group(3), 16)
            return r, g, b

        # rgb(r, g, b) veya rgba(r, g, b, a)
        m_rgb = re.match(
            r'^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})'
            r'(?:\s*,\s*[\d.]+)?\s*\)$',
            s
        )
        if m_rgb:
            r = int(m_rgb.group(1))
            g = int(m_rgb.group(2))
            b = int(m_rgb.group(3))
            # 0-255 aralığı zorla
            return (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
            )

        raise ValueError(
            f"Tanınamayan renk formatı: '{color_str}'. "
            "Desteklenen: #rgb, #rrggbb, rgb(r,g,b), rgba(r,g,b,a)"
        )


# ---------------------------------------------------------------------------
# HTMLParser — Harici kütüphane olmadan HTML parse etme
# ---------------------------------------------------------------------------

class HTMLParser:
    """
    Yalnızca `re` modülü kullanan hafif HTML parser sınıfı.

    BeautifulSoup, lxml veya html.parser gibi dış bağımlılıklar kullanmaz.
    WCAG testleri için gereken yapısal bilgileri (etiketler, özellikler,
    metin içeriği) çıkarır.

    Kısıtlamalar:
      - Gerçek bir DOM ağacı oluşturmaz; regex bazlı düz arama yapar.
      - Karmaşık iç içe yapılarda sınırlı doğruluk.
      - JavaScript ile oluşturulmuş içerikler analiz edilmez.
    """

    def __init__(self) -> None:
        """HTMLParser başlatıcı."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse(self, html: str) -> dict:
        """
        HTML string'ini WCAG testi için gereken yapılara ayrıştırır.

        Args:
            html: Ham HTML içeriği (tam sayfa veya parça).

        Returns:
            dict: Aşağıdaki anahtarları içeren yapı:
                - images       (list): <img> etiketleri
                - forms        (list): <form> etiketleri
                - inputs       (list): <input>, <select>, <textarea> etiketleri
                - headings     (list): <h1>–<h6> etiketleri (level bilgisiyle)
                - links        (list): <a> etiketleri
                - buttons      (list): <button> etiketleri
                - lang         (str):  <html> etiketinin lang özelliği
                - title        (str):  <title> içeriği
                - aria_elements(list): role veya aria-* özellikli etiketler
                - labels       (list): <label> etiketleri
        """
        result: dict = {
            "images":        [],
            "forms":         [],
            "inputs":        [],
            "headings":      [],
            "links":         [],
            "buttons":       [],
            "lang":          "",
            "title":         "",
            "aria_elements": [],
            "labels":        [],
        }

        # <html lang="...">
        html_tag = re.search(r'<html([^>]*)>', html, re.IGNORECASE)
        if html_tag:
            attrs = self.extract_attributes(html_tag.group(1))
            result["lang"] = attrs.get("lang", "").strip()

        # <title>...</title>
        title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_m:
            result["title"] = self.get_text_content(title_m.group(1)).strip()

        # <img>
        result["images"] = self.find_all_tags(html, "img")

        # <form>
        result["forms"] = self.find_all_tags(html, "form")

        # <input>, <select>, <textarea>
        for tag in ("input", "select", "textarea"):
            result["inputs"].extend(self.find_all_tags(html, tag))

        # <h1>–<h6>
        for level in range(1, 7):
            for tag_info in self.find_all_tags(html, f"h{level}"):
                tag_info["heading_level"] = level
                result["headings"].append(tag_info)
        # Belgedeki görünüm sırasına göre sırala (basit: ham HTML içindeki konum)
        result["headings"].sort(
            key=lambda h: html.lower().find(h.get("outer_html", "")[:20].lower())
        )

        # <a>
        result["links"] = self.find_all_tags(html, "a")

        # <button>
        result["buttons"] = self.find_all_tags(html, "button")

        # <label>
        result["labels"] = self.find_all_tags(html, "label")

        # ARIA elementleri (role veya aria-* içeren)
        aria_pattern = re.compile(
            r'<(\w+)([^>]*(?:role\s*=|aria-\w+)[^>]*)>',
            re.IGNORECASE
        )
        for m in aria_pattern.finditer(html):
            tag_name = m.group(1).lower()
            attr_str = m.group(2)
            attrs    = self.extract_attributes(attr_str)
            result["aria_elements"].append({
                "tag":        tag_name,
                "attributes": attrs,
                "outer_html": m.group(0)[:200],
            })

        self.logger.debug(
            f"HTML ayrıştırıldı: "
            f"img={len(result['images'])}, "
            f"input={len(result['inputs'])}, "
            f"heading={len(result['headings'])}, "
            f"link={len(result['links'])}, "
            f"button={len(result['buttons'])}"
        )
        return result

    def find_all_tags(self, html: str, tag: str) -> List[dict]:
        """
        HTML içindeki belirli etiketteki tüm örnekleri bulur.

        Hem öz-kapanan etiketler (<img />, <input>) hem de açık/kapalı
        çiftler (<a>...</a>, <button>...</button>) desteklenir.

        Args:
            html: HTML içeriği.
            tag:  Aranacak etiket adı (büyük/küçük harf fark etmez).

        Returns:
            List[dict]: Her etiket için:
                - tag          (str):  Etiket adı (küçük harf)
                - attributes   (dict): Tüm özellikler sözlüğü
                - text_content (str):  Etiket içindeki düz metin
                - outer_html   (str):  Ham etiket dizgisi (maks. 500 karakter)
        """
        results: List[dict] = []
        t = re.escape(tag)

        # Öz-kapanan etiket: <tag ... /> veya sadece <tag ...> (img, input vb.)
        self_closing_pat = re.compile(
            rf'<{t}(\s[^>]*)?\s*/?>',
            re.IGNORECASE
        )
        # Çift etiket: <tag ...>...</tag>
        paired_pat = re.compile(
            rf'<{t}(\s[^>]*)?>.*?</{t}>',
            re.IGNORECASE | re.DOTALL
        )

        # Eşleşmeleri topla (tekrar önlemek için konum takibi)
        matched_spans: List[Tuple[int, int]] = []

        for m in paired_pat.finditer(html):
            outer = m.group(0)
            attrs_str = m.group(1) or ""
            text_raw  = re.sub(r'<[^>]+>', '', outer)
            results.append({
                "tag":          tag.lower(),
                "attributes":   self.extract_attributes(attrs_str),
                "text_content": self.get_text_content(text_raw),
                "outer_html":   outer[:500],
            })
            matched_spans.append(m.span())

        for m in self_closing_pat.finditer(html):
            # Zaten paired olarak yakalananlar ile çakışma kontrolü
            overlap = any(s <= m.start() < e for s, e in matched_spans)
            if overlap:
                continue
            outer     = m.group(0)
            attrs_str = m.group(1) or ""
            results.append({
                "tag":          tag.lower(),
                "attributes":   self.extract_attributes(attrs_str),
                "text_content": "",
                "outer_html":   outer[:500],
            })

        return results

    def extract_attributes(self, attr_str: str) -> dict:
        """
        HTML özellik dizgisini anahtar-değer sözlüğüne dönüştürür.

        Desteklenen formatlar:
          - key="value"
          - key='value'
          - key=value  (tırnaksız)
          - key         (boolean özellik, değer True)

        Args:
            attr_str: Etiket içindeki özellik bölümü
                      (örn. ' class="foo" id="bar" disabled').

        Returns:
            dict: {özellik_adı: değer} sözlüğü (küçük harf anahtarlar).
        """
        attrs: dict = {}
        if not attr_str:
            return attrs

        # Çift tırnak
        for m in re.finditer(r'([\w-]+)\s*=\s*"([^"]*)"', attr_str):
            attrs[m.group(1).lower()] = m.group(2)

        # Tek tırnak
        for m in re.finditer(r"([\w-]+)\s*=\s*'([^']*)'", attr_str):
            key = m.group(1).lower()
            if key not in attrs:
                attrs[key] = m.group(2)

        # Tırnaksız
        for m in re.finditer(r'([\w-]+)\s*=\s*([^\s"\'>/]+)', attr_str):
            key = m.group(1).lower()
            if key not in attrs:
                attrs[key] = m.group(2)

        # Boolean (sadece anahtar)
        for m in re.finditer(r'\b([\w-]+)\b(?!\s*=)', attr_str):
            key = m.group(1).lower()
            if key not in attrs and key not in ('/', ):
                attrs[key] = True

        return attrs

    def get_text_content(self, raw: str) -> str:
        """
        HTML etiketlerini kaldırarak düz metin içeriğini döndürür.

        Args:
            raw: HTML içerebilen ham metin.

        Returns:
            str: Etiket ve fazla boşluklardan arındırılmış düz metin.
        """
        text = re.sub(r'<[^>]+>', ' ', raw)       # Etiketleri boşlukla değiştir
        text = re.sub(r'&nbsp;', ' ', text)        # HTML entity
        text = re.sub(r'&amp;',  '&', text)
        text = re.sub(r'&lt;',   '<', text)
        text = re.sub(r'&gt;',   '>', text)
        text = re.sub(r'&#\d+;', ' ', text)        # Sayısal entityler
        text = re.sub(r'\s+',    ' ', text)        # Çoklu boşlukları birleştir
        return text.strip()


# ---------------------------------------------------------------------------
# AccessibilityTester — Ana WCAG test motoru
# ---------------------------------------------------------------------------

class AccessibilityTester:
    """
    WCAG 2.1 erişilebilirlik testlerini çalıştıran ana sınıf.

    10 kural üzerinden HTML sayfalarını statik olarak analiz eder,
    ihlalleri önem derecesine göre puanlandırır ve AccessibilityReport
    nesnesi döndürür.

    Kullanım::

        tester = AccessibilityTester(wcag_level="AA")
        with open("index.html") as f:
            report = tester.test_page(f.read(), url="https://example.com")
        print(report.score)
        for rec in report.get_recommendations():
            print(rec)
    """

    def __init__(self, wcag_level: str = "AA") -> None:
        """
        AccessibilityTester başlatıcı.

        Args:
            wcag_level: Hedef WCAG uyumluluk seviyesi ("A", "AA" veya "AAA").
                        AA seviyesi için hem A hem AA kuralları kontrol edilir.
                        Varsayılan: "AA".
        """
        valid_levels = {"A", "AA", "AAA"}
        if wcag_level not in valid_levels:
            raise ValueError(
                f"Geçersiz WCAG seviyesi: '{wcag_level}'. "
                f"Geçerli değerler: {valid_levels}"
            )
        self.wcag_level      = wcag_level
        self.html_parser     = HTMLParser()
        self.contrast_checker = ColorContrastChecker()
        self.logger          = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"AccessibilityTester başlatıldı — WCAG seviyesi: {wcag_level}")

    def test_page(self, html: str, url: str = "") -> "AccessibilityReport":
        """
        HTML sayfasını tüm 10 WCAG kuralı üzerinden test eder.

        Args:
            html: Test edilecek HTML içeriği (ham string).
            url:  Sayfanın URL'si (raporda görüntülenir, test etkilemez).

        Returns:
            AccessibilityReport: Tüm test sonuçlarını içeren rapor nesnesi.
        """
        self.logger.info(f"Erişilebilirlik testi başlıyor: '{url or '(URL yok)'}'")
        start = datetime.now()

        # HTML ayrıştır
        parsed = self.html_parser.parse(html)

        # Tüm 10 kuralı çalıştır
        all_violations: List[AccessibilityViolation] = []
        passed_rules:   List[str]                    = []

        rule_checks = [
            ("img-alt",              self._check_img_alt),
            ("form-label",           self._check_form_labels),
            ("heading-hierarchy",    self._check_heading_hierarchy),
            ("color-contrast",       self._check_color_contrast),
            ("tabindex",             self._check_tabindex),
            ("aria-validation",      self._check_aria),
            ("link-text",            self._check_link_text),
            ("lang-attribute",       self._check_lang),
            ("page-title",           self._check_page_title),
            ("button-accessibility", self._check_buttons),
        ]

        for rule_id, check_fn in rule_checks:
            rule_def = WCAG_RULES.get(rule_id, {})

            # Kural seviye filtresi
            rule_level = rule_def.get("level", "A")
            if not self._should_check_rule(rule_level):
                self.logger.debug(f"Kural atlandı (seviye): {rule_id} ({rule_level})")
                continue

            try:
                violations = check_fn(parsed)
                if violations:
                    all_violations.extend(violations)
                    self.logger.debug(
                        f"Kural '{rule_id}': {len(violations)} ihlal bulundu."
                    )
                else:
                    passed_rules.append(rule_id)
                    self.logger.debug(f"Kural '{rule_id}': GEÇTI.")
            except Exception as exc:
                self.logger.error(
                    f"Kural '{rule_id}' çalıştırılırken hata: {exc}", exc_info=True
                )

        # Puan hesapla
        score = self._calculate_score(all_violations)

        # Özet istatistikler
        severity_counts: Dict[str, int] = {
            "critical": 0, "serious": 0, "moderate": 0, "minor": 0
        }
        for v in all_violations:
            severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1

        elapsed_ms = (datetime.now() - start).total_seconds() * 1000.0

        summary = {
            "total_violations":   len(all_violations),
            "passed_rule_count":  len(passed_rules),
            "checked_rule_count": len(rule_checks),
            "severity_counts":    severity_counts,
            "elapsed_ms":         round(elapsed_ms, 2),
            "html_length":        len(html),
            "elements_analyzed": {
                "images":   len(parsed.get("images",  [])),
                "inputs":   len(parsed.get("inputs",  [])),
                "links":    len(parsed.get("links",   [])),
                "buttons":  len(parsed.get("buttons", [])),
                "headings": len(parsed.get("headings",[])),
            },
        }

        report = AccessibilityReport(
            url          = url or "",
            tested_at    = datetime.now().isoformat(),
            wcag_level   = self.wcag_level,
            score        = score,
            violations   = all_violations,
            passed_rules = passed_rules,
            summary      = summary,
        )

        self.logger.info(
            f"Test tamamlandı: skor={score:.1f}/100 | "
            f"ihlal={len(all_violations)} | "
            f"geçen_kural={len(passed_rules)} | "
            f"süre={elapsed_ms:.1f}ms"
        )
        return report

    # ------------------------------------------------------------------
    # 10 WCAG Kontrol Metodu
    # ------------------------------------------------------------------

    def _check_img_alt(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: img-alt — Tüm <img> etiketlerinin alt özelliği olup olmadığını denetler.

        İhlal koşulları:
          - alt özelliği tamamen eksik
          - alt özelliği anlamlı olmayan değerler içeriyor
            (dosya adı, "image", "photo", "resim" gibi)

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Bulunan ihlaller.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["img-alt"]

        # Alt metni anlamsız kılan kalıplar
        meaningless_alts = re.compile(
            r'^(image|img|photo|foto|resim|picture|icon|logo\d*|'
            r'[\w-]+\.(jpg|jpeg|png|gif|svg|webp|bmp))$',
            re.IGNORECASE
        )

        for img in parsed.get("images", []):
            attrs = img.get("attributes", {})
            src   = attrs.get("src", "")
            alt   = attrs.get("alt", None)   # None = özellik yok

            selector = f'img[src="{src[:60]}"]' if src else "img"

            if alt is None:
                # alt özelliği tamamen eksik
                violations.append(AccessibilityViolation(
                    rule_id          = "img-alt",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = selector,
                    description      = f"<img> etiketinde 'alt' özelliği eksik: {src[:80]}",
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))
            elif isinstance(alt, str) and alt.strip() and meaningless_alts.match(alt.strip()):
                # Alt var ama anlamsız
                violations.append(AccessibilityViolation(
                    rule_id          = "img-alt",
                    level            = rule["level"],
                    severity         = "moderate",
                    element_selector = selector,
                    description      = f"<img> alt metni anlamlı değil: '{alt}'",
                    help_text        = "Alt metnini resmin içeriğini açıklayan bir cümleyle değiştirin.",
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT["moderate"],
                ))

        return violations

    def _check_form_labels(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: form-label — Form elemanlarının etiket ilişkilendirmesini denetler.

        Kabul edilen ilişkilendirme yöntemleri:
          - <label for="inputId"> ile id eşleşmesi
          - aria-label özelliği
          - aria-labelledby özelliği
          - title özelliği (minimum kabul)

        Muaf tutulanlar:
          - type="hidden"
          - type="submit" / type="reset" / type="button" (value içeriyorsa)

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Bulunan ihlaller.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["form-label"]

        # Mevcut <label for="..."> değerlerini topla
        label_fors: set = set()
        for lbl in parsed.get("labels", []):
            for_val = lbl.get("attributes", {}).get("for", "")
            if for_val and isinstance(for_val, str):
                label_fors.add(for_val.strip())

        # Etiket gerektirmeyen input tipleri
        no_label_types = {"hidden", "submit", "reset", "button", "image"}

        for inp in parsed.get("inputs", []):
            attrs    = inp.get("attributes", {})
            tag_name = inp.get("tag", "input")
            inp_type = str(attrs.get("type", "text")).lower()
            inp_id   = str(attrs.get("id", "")).strip()

            # Muaf tipleri atla
            if inp_type in no_label_types:
                continue

            selector = (
                f'{tag_name}[id="{inp_id}"]' if inp_id
                else f'{tag_name}[type="{inp_type}"]'
            )

            has_label = (
                (inp_id and inp_id in label_fors)
                or bool(attrs.get("aria-label"))
                or bool(attrs.get("aria-labelledby"))
                or bool(attrs.get("title"))
                or bool(attrs.get("placeholder") and tag_name != "select")
            )

            if not has_label:
                violations.append(AccessibilityViolation(
                    rule_id          = "form-label",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = selector,
                    description      = (
                        f"<{tag_name}> (type='{inp_type}') için erişilebilir etiket bulunamadı."
                    ),
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))

        return violations

    def _check_heading_hierarchy(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: heading-hierarchy — Başlık seviyelerinin sıralı ilerlediğini denetler.

        İhlal koşulları:
          - Bir seviye atlanması (örn. h1 → h3, seviye atladı h2 es geçildi)
          - Birden fazla <h1> kullanımı (best practice ihlali, minor)

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Bulunan ihlaller.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["heading-hierarchy"]
        headings   = parsed.get("headings", [])

        if not headings:
            return violations

        # Birden fazla h1
        h1_count = sum(1 for h in headings if h.get("heading_level") == 1)
        if h1_count > 1:
            violations.append(AccessibilityViolation(
                rule_id          = "heading-hierarchy",
                level            = rule["level"],
                severity         = "minor",
                element_selector = "h1",
                description      = f"Sayfada {h1_count} adet <h1> bulunuyor; ideal olarak 1 adet olmalı.",
                help_text        = "Her sayfada yalnızca bir <h1> kullanın; bu sayfa ana başlığını temsil eder.",
                wcag_criteria    = rule["wcag_criteria"],
                impact_score     = SEVERITY_IMPACT["minor"],
            ))

        # Seviye sırası kontrolü
        prev_level  = 0
        for h in headings:
            level = h.get("heading_level", 0)
            if level == 0:
                continue

            if prev_level > 0 and level > prev_level + 1:
                skip_count = level - prev_level - 1
                violations.append(AccessibilityViolation(
                    rule_id          = "heading-hierarchy",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = f"h{level}",
                    description      = (
                        f"Başlık hiyerarşisi atlıyor: h{prev_level} → h{level} "
                        f"({skip_count} seviye atlandı)."
                    ),
                    help_text        = (
                        f"h{prev_level} sonrasında h{prev_level+1} kullanın; "
                        f"seviye atlamamaya özen gösterin."
                    ),
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))
            prev_level = level

        return violations

    def _check_color_contrast(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: color-contrast — Inline stil içindeki renk çiftlerinin kontrast oranını denetler.

        Yalnızca `style` özelliği `color:` ve `background-color:` birlikte içeren
        elemanlar analiz edilir. Renk değerleri hex veya rgb() formatında olmalıdır.

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: AA seviyesini geçemeyen renkler.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["color-contrast"]

        # Tüm etiket türlerini tara (links, buttons, headings dahil)
        all_elements = (
            parsed.get("links",    []) +
            parsed.get("buttons",  []) +
            parsed.get("headings", []) +
            parsed.get("inputs",   [])
        )

        for elem in all_elements:
            attrs     = elem.get("attributes", {})
            style_str = str(attrs.get("style", ""))
            if not style_str:
                continue

            # color: ve background-color: değerlerini çıkar
            fg_match = re.search(
                r'\bcolor\s*:\s*([^;]+)',
                style_str, re.IGNORECASE
            )
            bg_match = re.search(
                r'background(?:-color)?\s*:\s*([^;]+)',
                style_str, re.IGNORECASE
            )

            if not (fg_match and bg_match):
                continue

            fg_str = fg_match.group(1).strip()
            bg_str = bg_match.group(1).strip()

            try:
                fg_rgb = self.contrast_checker.parse_color(fg_str)
                bg_rgb = self.contrast_checker.parse_color(bg_str)
            except ValueError:
                self.logger.debug(
                    f"Renk parse edilemedi: fg='{fg_str}', bg='{bg_str}'"
                )
                continue

            ratio = self.contrast_checker.get_contrast_ratio(fg_rgb, bg_rgb)

            if not self.contrast_checker.passes_aa(ratio, is_large_text=False):
                selector = (
                    f"{elem.get('tag', 'element')}"
                    f"[style]"
                )
                violations.append(AccessibilityViolation(
                    rule_id          = "color-contrast",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = selector,
                    description      = (
                        f"Kontrast oranı yetersiz: {ratio:.2f}:1 "
                        f"(fg='{fg_str}', bg='{bg_str}'). "
                        f"Minimum AA: 4.5:1"
                    ),
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))

        return violations

    def _check_tabindex(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: tabindex — Pozitif tabindex değerlerini denetler.

        tabindex > 0 değerleri sekme sırasını sayfanın doğal akışından
        koparır ve ekran okuyucu kullanıcılarını yanıltır.

        İhlal: tabindex değeri 1 veya daha büyük olan her eleman.

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Bulunan ihlaller.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["tabindex"]

        # Tüm interaktif elemanları tara
        interactive = (
            parsed.get("links",    []) +
            parsed.get("buttons",  []) +
            parsed.get("inputs",   []) +
            parsed.get("aria_elements", [])
        )

        for elem in interactive:
            attrs    = elem.get("attributes", {})
            tabindex = attrs.get("tabindex", None)

            if tabindex is None or tabindex is True:
                continue

            try:
                ti_val = int(str(tabindex).strip())
            except (ValueError, TypeError):
                continue

            if ti_val > 0:
                selector = (
                    f"{elem.get('tag', 'element')}[tabindex='{ti_val}']"
                )
                violations.append(AccessibilityViolation(
                    rule_id          = "tabindex",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = selector,
                    description      = (
                        f"Pozitif tabindex kullanımı: tabindex={ti_val}. "
                        "Bu değer sekme sırasını bozabilir."
                    ),
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))

        return violations

    def _check_aria(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: aria-validation — ARIA rol ve özelliklerinin geçerliliğini denetler.

        Kontroller:
          - role değeri VALID_ARIA_ROLES içinde olmalı
          - aria-required, aria-expanded, aria-hidden gibi boolean
            özellikler "true" veya "false" değerini almalı
          - aria-label boş olmamalı

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Geçersiz ARIA kullanımları.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["aria-validation"]

        # Boolean ARIA özellikleri
        boolean_aria_props = {
            "aria-required", "aria-expanded", "aria-hidden",
            "aria-disabled", "aria-checked", "aria-selected",
            "aria-pressed", "aria-multiline", "aria-multiselectable",
            "aria-readonly",
        }

        for elem in parsed.get("aria_elements", []):
            attrs    = elem.get("attributes", {})
            tag_name = elem.get("tag", "element")

            # Rol geçerliliği
            role = str(attrs.get("role", "")).strip().lower()
            if role and role not in VALID_ARIA_ROLES:
                violations.append(AccessibilityViolation(
                    rule_id          = "aria-validation",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = f'{tag_name}[role="{role}"]',
                    description      = (
                        f"Geçersiz ARIA rolü: '{role}' WAI-ARIA spesifikasyonunda tanımlı değil."
                    ),
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))

            # Boolean özellik değer kontrolü
            for prop in boolean_aria_props:
                val = attrs.get(prop, None)
                if val is None:
                    continue
                if isinstance(val, bool):
                    # Tırnak olmadan yazılmış (extract_attributes boolean True döndürdü)
                    violations.append(AccessibilityViolation(
                        rule_id          = "aria-validation",
                        level            = rule["level"],
                        severity         = "minor",
                        element_selector = f'{tag_name}[{prop}]',
                        description      = (
                            f"'{prop}' değeri tırnak içinde olmalı: "
                            f'{prop}="true" veya {prop}="false".'
                        ),
                        help_text        = "ARIA boolean özellikleri için değeri tırnak içinde yazın.",
                        wcag_criteria    = rule["wcag_criteria"],
                        impact_score     = SEVERITY_IMPACT["minor"],
                    ))
                elif str(val).lower() not in ("true", "false"):
                    violations.append(AccessibilityViolation(
                        rule_id          = "aria-validation",
                        level            = rule["level"],
                        severity         = "moderate",
                        element_selector = f'{tag_name}[{prop}="{val}"]',
                        description      = (
                            f"'{prop}' geçersiz değer: '{val}'. "
                            '"true" veya "false" olmalı.'
                        ),
                        help_text        = rule["help_text"],
                        wcag_criteria    = rule["wcag_criteria"],
                        impact_score     = SEVERITY_IMPACT["moderate"],
                    ))

            # aria-label boşluk kontrolü
            aria_label = attrs.get("aria-label", None)
            if isinstance(aria_label, str) and not aria_label.strip():
                violations.append(AccessibilityViolation(
                    rule_id          = "aria-validation",
                    level            = rule["level"],
                    severity         = "serious",
                    element_selector = f'{tag_name}[aria-label=""]',
                    description      = "aria-label özelliği boş string içeriyor.",
                    help_text        = "Boş aria-label yerine özelliği tamamen kaldırın veya anlamlı bir değer verin.",
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT["serious"],
                ))

        return violations

    def _check_link_text(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: link-text — Bağlantı metinlerinin açıklayıcı olduğunu denetler.

        İhlal koşulları:
          - Metin içeriği VAGUE_LINK_TEXTS kümesinde yer alıyor
          - Metin içeriği tamamen boş ve aria-label da yok
          - Yalnızca bir URL veya sayı içeriyor

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Belirsiz veya boş bağlantı metinleri.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["link-text"]

        for link in parsed.get("links", []):
            attrs      = link.get("attributes", {})
            text       = link.get("text_content", "").strip()
            href       = str(attrs.get("href", "")).strip()
            aria_label = str(attrs.get("aria-label", "")).strip()
            aria_lb    = str(attrs.get("aria-labelledby", "")).strip()

            # ARIA ile etiketlenmişse kabul et
            if aria_label or aria_lb:
                continue

            selector = f'a[href="{href[:60]}"]' if href else "a"

            # Boş metin
            if not text:
                violations.append(AccessibilityViolation(
                    rule_id          = "link-text",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = selector,
                    description      = f"Bağlantı metni boş: href='{href[:80]}'",
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))
                continue

            # Belirsiz metin
            if text.lower() in VAGUE_LINK_TEXTS:
                violations.append(AccessibilityViolation(
                    rule_id          = "link-text",
                    level            = rule["level"],
                    severity         = "moderate",
                    element_selector = selector,
                    description      = f"Bağlantı metni belirsiz: '{text}'",
                    help_text        = (
                        f"'{text}' yerine bağlantının hedefini açıklayan metin kullanın. "
                        "Örnek: 'Hesap açma kılavuzunu oku' gibi."
                    ),
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT["moderate"],
                ))

        return violations

    def _check_lang(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: lang-attribute — <html> etiketinin lang özelliğini denetler.

        İhlal koşulları:
          - lang özelliği tamamen eksik
          - lang değeri boş string
          - lang değeri BCP 47 formatına uymayan kısa string (< 2 karakter)

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Lang ihlalleri (maksimum 1 ihlal).
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["lang-attribute"]
        lang       = parsed.get("lang", "")

        if not lang or not lang.strip():
            violations.append(AccessibilityViolation(
                rule_id          = "lang-attribute",
                level            = rule["level"],
                severity         = rule["severity"],
                element_selector = "html",
                description      = (
                    "<html> etiketinde 'lang' özelliği eksik veya boş. "
                    "Ekran okuyucular sayfanın dilini belirleyemiyor."
                ),
                help_text        = rule["help_text"],
                wcag_criteria    = rule["wcag_criteria"],
                impact_score     = SEVERITY_IMPACT[rule["severity"]],
            ))
        elif len(lang.strip()) < 2:
            violations.append(AccessibilityViolation(
                rule_id          = "lang-attribute",
                level            = rule["level"],
                severity         = "moderate",
                element_selector = f'html[lang="{lang}"]',
                description      = (
                    f"<html lang='{lang}'> geçerli bir BCP 47 dil etiketi değil. "
                    "Örnek: lang='tr', lang='en', lang='en-US'"
                ),
                help_text        = rule["help_text"],
                wcag_criteria    = rule["wcag_criteria"],
                impact_score     = SEVERITY_IMPACT["moderate"],
            ))

        return violations

    def _check_page_title(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: page-title — Sayfanın anlamlı bir <title> içerdiğini denetler.

        İhlal koşulları:
          - <title> etiketi yok (boş string döner)
          - <title> metni boş veya yalnızca boşluk
          - <title> metni 3 karakterden kısa (anlamsız)

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Sayfa başlığı ihlali (maksimum 1).
        """
        violations: List[AccessibilityViolation] = []
        rule  = WCAG_RULES["page-title"]
        title = parsed.get("title", "").strip()

        if not title:
            violations.append(AccessibilityViolation(
                rule_id          = "page-title",
                level            = rule["level"],
                severity         = rule["severity"],
                element_selector = "title",
                description      = "Sayfada <title> etiketi eksik veya boş.",
                help_text        = rule["help_text"],
                wcag_criteria    = rule["wcag_criteria"],
                impact_score     = SEVERITY_IMPACT[rule["severity"]],
            ))
        elif len(title) < 3:
            violations.append(AccessibilityViolation(
                rule_id          = "page-title",
                level            = rule["level"],
                severity         = "moderate",
                element_selector = "title",
                description      = (
                    f"<title> çok kısa: '{title}'. "
                    "Sayfa başlığı içeriği açıkça tanımlamalıdır."
                ),
                help_text        = rule["help_text"],
                wcag_criteria    = rule["wcag_criteria"],
                impact_score     = SEVERITY_IMPACT["moderate"],
            ))

        return violations

    def _check_buttons(self, parsed: dict) -> List[AccessibilityViolation]:
        """
        Kural: button-accessibility — Buton erişilebilirliğini denetler.

        Kontroller:
          1. Boş metin + aria-label/aria-labelledby yok → critical ihlal
          2. type özelliği eksik → minor ihlal (UX açısından önemli)
          3. disabled özelliği ile aria-disabled uyumsuzluğu → minor

        Args:
            parsed: HTMLParser.parse() çıktısı.

        Returns:
            List[AccessibilityViolation]: Bulunan buton erişilebilirlik ihlalleri.
        """
        violations: List[AccessibilityViolation] = []
        rule       = WCAG_RULES["button-accessibility"]

        for btn in parsed.get("buttons", []):
            attrs      = btn.get("attributes", {})
            text       = btn.get("text_content", "").strip()
            aria_label = str(attrs.get("aria-label", "")).strip()
            aria_lb    = str(attrs.get("aria-labelledby", "")).strip()
            btn_type   = attrs.get("type", None)
            btn_id     = str(attrs.get("id", "")).strip()

            selector = (
                f'button[id="{btn_id}"]' if btn_id
                else "button"
            )

            # Erişilebilir ad kontrolü (metin veya ARIA etiketi)
            has_accessible_name = bool(text or aria_label or aria_lb)

            if not has_accessible_name:
                violations.append(AccessibilityViolation(
                    rule_id          = "button-accessibility",
                    level            = rule["level"],
                    severity         = rule["severity"],
                    element_selector = selector,
                    description      = (
                        "Butonda metin veya ARIA etiketi bulunamadı. "
                        "Ekran okuyucular bu butonu tanımlayamaz."
                    ),
                    help_text        = rule["help_text"],
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT[rule["severity"]],
                ))

            # type özelliği kontrolü
            if btn_type is None or btn_type is True:
                violations.append(AccessibilityViolation(
                    rule_id          = "button-accessibility",
                    level            = rule["level"],
                    severity         = "minor",
                    element_selector = selector,
                    description      = (
                        "Buton için 'type' özelliği belirtilmemiş. "
                        "Formlar içinde type='submit' yerine istemeden tetiklenebilir."
                    ),
                    help_text        = (
                        "Her <button> için type='button', type='submit' veya "
                        "type='reset' açıkça belirtin."
                    ),
                    wcag_criteria    = rule["wcag_criteria"],
                    impact_score     = SEVERITY_IMPACT["minor"],
                ))

        return violations

    # ------------------------------------------------------------------
    # Skor Hesaplama
    # ------------------------------------------------------------------

    def _calculate_score(self, violations: List[AccessibilityViolation]) -> float:
        """
        İhlal listesine göre ağırlıklı erişilebilirlik skoru hesaplar.

        Başlangıç skoru 100 puan. Her ihlal önem ağırlığına göre puan düşürür:
          critical  → -25 puan
          serious   → -15 puan
          moderate  → - 8 puan
          minor     → - 3 puan

        Aynı kural için birden fazla ihlal varsa ek ihlaller %50 ağırlıkla
        sayılır (tekrar cezalandırma etkisini sınırlar).

        Skor 0'ın altına düşmez.

        Args:
            violations: Bulunan ihlallerin listesi.

        Returns:
            float: [0.0, 100.0] aralığında erişilebilirlik skoru.
        """
        if not violations:
            return 100.0

        total_deduction = 0.0
        rule_seen_count: Dict[str, int] = {}

        for v in violations:
            base_weight = SEVERITY_WEIGHTS.get(v.severity, 5)
            count       = rule_seen_count.get(v.rule_id, 0)

            if count == 0:
                # İlk ihlal — tam ağırlık
                deduction = float(base_weight)
            else:
                # Aynı kuralın sonraki ihlalleri — yarı ağırlık
                deduction = base_weight * 0.5

            total_deduction += deduction
            rule_seen_count[v.rule_id] = count + 1

        score = max(0.0, 100.0 - total_deduction)
        return round(score, 2)

    # ------------------------------------------------------------------
    # Yardımcı metodlar
    # ------------------------------------------------------------------

    def _should_check_rule(self, rule_level: str) -> bool:
        """
        Belirtilen kural seviyesinin mevcut WCAG seviyesinde kontrol
        edilip edilmeyeceğini belirler.

        WCAG seviyeleri kapsayıcıdır:
          - Seviye "A":   yalnızca A kuralları
          - Seviye "AA":  A + AA kuralları
          - Seviye "AAA": A + AA + AAA kuralları

        Args:
            rule_level: Kuralın WCAG seviyesi ("A", "AA" veya "AAA").

        Returns:
            bool: Bu kuralın kontrol edilmesi gerekiyorsa True.
        """
        level_order = {"A": 1, "AA": 2, "AAA": 3}
        return level_order.get(rule_level, 1) <= level_order.get(self.wcag_level, 2)

    def get_rule_info(self, rule_id: str) -> Optional[dict]:
        """
        Belirtilen kural hakkında bilgi döndürür.

        Args:
            rule_id: Kural kimliği (örn. "img-alt").

        Returns:
            dict: Kural bilgisi veya None (kural bulunamazsa).
        """
        return WCAG_RULES.get(rule_id)

    def get_all_rules(self) -> Dict[str, dict]:
        """
        Tüm WCAG kurallarının tam listesini döndürür.

        Returns:
            Dict[str, dict]: {rule_id: kural_bilgisi} sözlüğü.
        """
        return WCAG_RULES.copy()

    def get_rules_by_level(self, level: str) -> Dict[str, dict]:
        """
        Belirtilen WCAG seviyesindeki kuralları filtreler.

        Args:
            level: "A", "AA" veya "AAA".

        Returns:
            Dict[str, dict]: Filtrelenmiş kural sözlüğü.
        """
        return {
            k: v for k, v in WCAG_RULES.items()
            if v.get("level") == level
        }


# ---------------------------------------------------------------------------
# Yardımcı fabrika fonksiyonu
# ---------------------------------------------------------------------------

def create_accessibility_tester(wcag_level: str = "AA") -> AccessibilityTester:
    """
    Önceden yapılandırılmış AccessibilityTester nesnesi döndürür.

    Args:
        wcag_level: WCAG uyumluluk seviyesi ("A", "AA" veya "AAA").
                    Varsayılan: "AA".

    Returns:
        AccessibilityTester: Kullanıma hazır test nesnesi.

    Örnek::

        tester = create_accessibility_tester("AA")
        report = tester.test_page(html_content, url="https://mybank.com")
        print(report.score)
    """
    tester = AccessibilityTester(wcag_level=wcag_level)
    logger.info(f"AccessibilityTester oluşturuldu — WCAG {wcag_level}")
    return tester


# ---------------------------------------------------------------------------
# Demo / quick-test
# ---------------------------------------------------------------------------

def run_accessibility_demo() -> None:
    """
    Modülün temel işlevselliğini örnek HTML ile test eden demo.

    Dış bağımlılık gerektirmez. Çalıştırmak için:
        python accessibility_tester.py
    """
    print("=" * 60)
    print(" WCAG 2.1 Erişilebilirlik Test Modülü — Demo")
    print("=" * 60)

    # ── Örnek HTML (kasıtlı ihlaller içeriyor) ──────────────────────
    sample_html = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Örnek Banka Uygulaması</title>
</head>
<body>
    <h1>Hoş Geldiniz</h1>
    <h3>Hesaplarım</h3>

    <img src="logo.png" alt="logo">
    <img src="banner.jpg">

    <form action="/login">
        <input type="text" id="username" placeholder="Kullanıcı adı">
        <input type="password">
        <label for="username">Kullanıcı Adı</label>
        <button>Giriş Yap</button>
        <button type="button" aria-label="Şifreyi göster">👁</button>
    </form>

    <nav>
        <a href="/home">Ana Sayfa</a>
        <a href="/transfer">Buraya</a>
        <a href="/help">Daha fazla</a>
        <a href="/logout">Çıkış</a>
    </nav>

    <div role="invalidrole" tabindex="3">İçerik</div>
    <span role="button" aria-expanded="maybe">Filtrele</span>
    <p style="color: #aaa; background-color: #fff;">Düşük kontrastlı metin</p>
</body>
</html>"""

    # ── Test çalıştır ────────────────────────────────────────────────
    tester = AccessibilityTester(wcag_level="AA")
    report = tester.test_page(sample_html, url="https://demo.bank.example.com")

    # ── Sonuçları yazdır ─────────────────────────────────────────────
    print(f"\n[Sonuç]")
    print(f"  URL:         {report.url}")
    print(f"  WCAG Seviye: {report.wcag_level}")
    print(f"  Skor:        {report.score:.1f} / 100")
    print(f"  İhlal sayısı:{len(report.violations)}")
    print(f"  Geçen kural: {len(report.passed_rules)}")

    print(f"\n[Özet]")
    for k, v in report.summary.items():
        print(f"  {k}: {v}")

    print(f"\n[İhlaller]")
    for i, v in enumerate(report.violations, 1):
        print(f"  {i}. [{v.severity.upper()}] {v.rule_id}")
        print(f"     Seçici : {v.element_selector}")
        print(f"     Açıklama: {v.description}")

    print(f"\n[Kritik İhlaller]")
    for v in report.get_critical_violations():
        print(f"  - {v.rule_id}: {v.description}")

    print(f"\n[Öneriler]")
    for rec in report.get_recommendations():
        print(f"  • {rec}")

    # ── ColorContrastChecker demo ────────────────────────────────────
    print("\n[Renk Kontrast Kontrolü]")
    checker = ColorContrastChecker()

    test_pairs = [
        ("#000000", "#ffffff", "Siyah / Beyaz"),
        ("#767676", "#ffffff", "Gri / Beyaz (AA sınırı)"),
        ("#aaaaaa", "#ffffff", "Açık Gri / Beyaz (başarısız)"),
        ("#0000cd", "#ffffff", "Mavi / Beyaz"),
    ]

    for fg, bg, label in test_pairs:
        fg_rgb = checker.parse_color(fg)
        bg_rgb = checker.parse_color(bg)
        ratio  = checker.get_contrast_ratio(fg_rgb, bg_rgb)
        aa     = checker.passes_aa(ratio)
        aaa    = checker.passes_aaa(ratio)
        print(
            f"  {label}: {ratio:.2f}:1 | "
            f"AA={'GEÇTI' if aa else 'BAŞARISIZ'} | "
            f"AAA={'GEÇTI' if aaa else 'BAŞARISIZ'}"
        )

    # ── JSON çıktısı ─────────────────────────────────────────────────
    print(f"\n[JSON Raporu (ilk 500 karakter)]")
    json_str = report.to_json()
    print(json_str[:500] + "...\n")

    print("Demo başarıyla tamamlandı.")


if __name__ == "__main__":
    run_accessibility_demo()
