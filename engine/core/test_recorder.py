"""
Test Recorder Modülü
====================
Kullanıcı aksiyonlarını kaydeder ve çeşitli formatlarda kod üretir:
- Playwright Python test kodu
- Cucumber/Gherkin feature dosyası (Mavi Yaka formatında)
- Page Object Model (Java + Python)
- JSON locator dosyası (Mavi Yaka formatında)
"""
from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

# Desteklenen aksiyon tipleri
ACTION_TYPES = {
    "click", "type", "navigate", "scroll", "wait",
    "assert_text", "assert_visible", "assert_url",
    "select", "hover", "press_key", "screenshot",
    "drag_drop", "upload", "clear",
}

# Mavi Yaka domain listesi
NEXUSQA_DOMAINS = ["ark", "ghz", "girit", "hrnexusqa", "pex", "plus"]


# ──────────────────────────────────────────────────────────────────────────────
# Veri Sınıfları
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class RecordedAction:
    """Kayıtlı bir kullanıcı aksiyonu."""
    action_type: str               # click, type, navigate, vs.
    selector: str = ""             # CSS/XPath seçicisi
    value: str = ""                # type için metin, navigate için URL, vs.
    selector_type: str = "css"     # css, xpath, text, testid
    element_name: str = ""         # İnsan okunabilir element adı
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "selector": self.selector,
            "value": self.value,
            "selector_type": self.selector_type,
            "element_name": self.element_name,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RecordedAction":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RecordingSession:
    """Bir kayıt oturumu."""
    name: str
    domain: str = "default"
    base_url: str = ""
    actions: list[RecordedAction] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "base_url": self.base_url,
            "actions": [a.to_dict() for a in self.actions],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "tags": self.tags,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RecordingSession":
        actions = [RecordedAction.from_dict(a) for a in d.get("actions", [])]
        obj = cls(
            name=d["name"],
            domain=d.get("domain", "default"),
            base_url=d.get("base_url", ""),
            actions=actions,
            started_at=d.get("started_at", ""),
            ended_at=d.get("ended_at", ""),
            tags=d.get("tags", []),
            description=d.get("description", ""),
        )
        return obj


# ──────────────────────────────────────────────────────────────────────────────
# Akıllı Seçici Motoru
# ──────────────────────────────────────────────────────────────────────────────
class SmartSelectorEngine:
    """
    DOM element verilerinden en iyi seçiciyi belirler.
    Öncelik sırası: data-testid > id > aria-label > name > class > text > xpath

    LocatorRegistry entegrasyonu: get_best_selector_chain() ile tüm aday
    seçicileri zincir olarak döndürebilir (self-healing desteği).
    """

    PRIORITY = [
        "data-testid",
        "id",
        "aria-label",
        "name",
        "placeholder",
        "type+name",
        "class",
        "text",
        "xpath",
    ]

    @classmethod
    def get_best_selector(cls, element_info: dict) -> tuple[str, str]:
        """
        Element bilgisinden en iyi seçiciyi ve tipini döner.

        Args:
            element_info: {
                tag, id, class, data-testid, aria-label, name,
                placeholder, text, xpath, type
            }

        Returns:
            (selector_value, selector_type)  → ('"#login-btn"', 'css')
        """
        testid = element_info.get("data-testid", "")
        if testid:
            return f'[data-testid="{testid}"]', "css"

        el_id = element_info.get("id", "")
        if el_id:
            return f"#{el_id}", "css"

        aria = element_info.get("aria-label", "")
        if aria:
            return f'[aria-label="{aria}"]', "css"

        name = element_info.get("name", "")
        tag  = element_info.get("tag", "")
        if name and tag:
            return f'{tag}[name="{name}"]', "css"
        elif name:
            return f'[name="{name}"]', "css"

        placeholder = element_info.get("placeholder", "")
        if placeholder:
            return f'[placeholder="{placeholder}"]', "css"

        css_class = element_info.get("class", "")
        if css_class:
            classes = [c for c in css_class.split() if not re.match(r'^(active|focus|hover|is-)', c)]
            if classes and tag:
                return f"{tag}.{classes[0]}", "css"

        text = element_info.get("text", "")
        if text:
            return f'text="{text[:50]}"', "text"

        xpath = element_info.get("xpath", "")
        if xpath:
            return xpath, "xpath"

        return tag or "div", "css"

    @classmethod
    def get_best_selector_chain(cls, element_info: dict) -> list[dict]:
        """
        Element bilgisinden tüm aday seçicileri güven skoru ile döner.
        LocatorRegistry/SelectorChain formatında kullanıma hazırdır.

        Returns:
            [{"type": "testid", "value": "...", "confidence": 1.0, "stable": True}, ...]
        """
        try:
            from core.recording_event import SelectorChainBuilder
            chain = SelectorChainBuilder.build(element_info)
            return chain.to_list()
        except ImportError:
            selector, stype = cls.get_best_selector(element_info)
            return [{"type": stype, "value": selector, "confidence": 0.7, "stable": False}]

    @classmethod
    def to_element_name(cls, element_info: dict) -> str:
        """Element için Python/Java değişken adı üretir."""
        candidates = [
            element_info.get("data-testid", ""),
            element_info.get("id", ""),
            element_info.get("aria-label", ""),
            element_info.get("name", ""),
            element_info.get("placeholder", ""),
            element_info.get("text", ""),
        ]
        name = next((c for c in candidates if c), "element")
        name = re.sub(r"[^a-zA-Z0-9_\s]", "", name)
        name = re.sub(r"\s+", "_", name.strip().lower())
        name = re.sub(r"_+", "_", name)
        if not name or name[0].isdigit():
            name = "el_" + name
        return name[:40] or "element"


# ──────────────────────────────────────────────────────────────────────────────
# Aksiyon Kaydedici
# ──────────────────────────────────────────────────────────────────────────────
class ActionRecorder:
    """
    Aksiyonları kaydeder ve JSON olarak saklar.
    Playwright sayfa dinleyicileriyle veya manuel eklemeyle kullanılabilir.
    """

    def __init__(self, session_name: str = "", domain: str = "default", base_url: str = ""):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session = RecordingSession(
            name=session_name or f"kayit_{ts}",
            domain=domain if domain in NEXUSQA_DOMAINS else "default",
            base_url=base_url,
        )
        self._start_time = datetime.now().timestamp()

    # ── Temel Aksiyon Ekleyiciler ─────────────────────────────────────────────
    def record(self, action_type: str, selector: str = "", value: str = "",
               selector_type: str = "css", element_info: dict | None = None,
               metadata: dict | None = None) -> RecordedAction:
        """Ham aksiyon kaydeder."""
        ei = element_info or {}
        element_name = SmartSelectorEngine.to_element_name(ei) if ei else (
            re.sub(r"[^a-z0-9_]", "_", selector.lower())[:30] or "element"
        )
        if ei and not selector:
            selector, selector_type = SmartSelectorEngine.get_best_selector(ei)

        action = RecordedAction(
            action_type=action_type,
            selector=selector,
            value=value,
            selector_type=selector_type,
            element_name=element_name,
            timestamp=datetime.now().timestamp() - self._start_time,
            metadata=metadata or {},
        )
        self.session.actions.append(action)
        logger.debug("Aksiyon kaydedildi: %s %s", action_type, selector[:50])
        return action

    def click(self, selector: str = "", element_info: dict | None = None) -> RecordedAction:
        """Click aksiyonu kaydeder."""
        return self.record("click", selector, element_info=element_info)

    def type_text(self, selector: str, text: str, element_info: dict | None = None) -> RecordedAction:
        """Metin yazma aksiyonu kaydeder."""
        return self.record("type", selector, value=text, element_info=element_info)

    def navigate(self, url: str) -> RecordedAction:
        """Navigasyon aksiyonu kaydeder."""
        return self.record("navigate", value=url, element_name="page")

    def scroll(self, selector: str = "", x: int = 0, y: int = 500) -> RecordedAction:
        """Scroll aksiyonu kaydeder."""
        return self.record("scroll", selector, metadata={"x": x, "y": y})

    def wait(self, selector: str = "", duration_ms: int = 1000) -> RecordedAction:
        """Bekleme aksiyonu kaydeder."""
        meta = {"duration_ms": duration_ms} if not selector else {}
        return self.record("wait", selector, metadata=meta)

    def assert_text(self, selector: str, expected: str) -> RecordedAction:
        """Metin doğrulama aksiyonu kaydeder."""
        return self.record("assert_text", selector, value=expected)

    def assert_visible(self, selector: str) -> RecordedAction:
        """Görünürlük doğrulama aksiyonu kaydeder."""
        return self.record("assert_visible", selector)

    def assert_url(self, expected_url: str) -> RecordedAction:
        """URL doğrulama aksiyonu kaydeder."""
        return self.record("assert_url", value=expected_url, element_name="url")

    def select_option(self, selector: str, value: str, element_info: dict | None = None) -> RecordedAction:
        """Select aksiyonu kaydeder."""
        return self.record("select", selector, value=value, element_info=element_info)

    def upload_file(self, selector: str, file_path: str) -> RecordedAction:
        """Dosya yükleme aksiyonu kaydeder."""
        return self.record("upload", selector, value=file_path)

    # ── Oturum Kapatma & Kaydetme ─────────────────────────────────────────────
    def stop(self) -> RecordingSession:
        """Kaydı durdurur."""
        self.session.ended_at = datetime.now().isoformat()
        return self.session

    def save(self, output_path: Path | str | None = None) -> str:
        """Oturumu JSON dosyasına kaydeder."""
        self.session.ended_at = self.session.ended_at or datetime.now().isoformat()
        if output_path is None:
            records_dir = settings.BASE_DIR / "recordings"
            records_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = records_dir / f"{self.session.name}_{ts}.json"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.session.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Kayıt dosyası kaydedildi: %s", output_path)
        return str(output_path)

    @classmethod
    def load(cls, path: Path | str) -> "ActionRecorder":
        """JSON dosyasından kayıt oturumu yükler."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        session = RecordingSession.from_dict(data)
        recorder = cls.__new__(cls)
        recorder.session = session
        recorder._start_time = 0.0
        return recorder


# ──────────────────────────────────────────────────────────────────────────────
# Playwright Python Kod Üretici
# ──────────────────────────────────────────────────────────────────────────────
class CodeGenerator:
    """
    Kayıt oturumundan Playwright Python test kodu üretir.
    pytest + Playwright uyumlu.
    """

    def generate(self, session: RecordingSession, class_name: str = "") -> str:
        """
        Playwright Python test kodunu döner.

        Args:
            session:    Kayıt oturumu
            class_name: Test sınıf adı (boşsa session.name kullanılır)
        """
        cls_name = class_name or self._to_class_name(session.name)
        domain   = session.domain
        base_url = session.base_url

        lines = [
            '"""',
            f'Test: {session.name}',
            f'Domain: {domain}',
            f'Oluşturuldu: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'Açıklama: {session.description}',
            '"""',
            "import pytest",
            "from playwright.sync_api import Page, expect",
            "",
            "",
            f"class {cls_name}:",
            f'    """Mavi Yaka — {domain} domain test sınıfı."""',
            "",
            f"    BASE_URL = {repr(base_url)}",
            "",
        ]

        # Test metodu
        method_name = "test_" + re.sub(r"[^a-z0-9_]", "_", session.name.lower())
        lines += [
            f"    def {method_name}(self, page: Page):",
            f'        """Kayıt oturumundan üretilen test: {session.name}"""',
        ]

        for action in session.actions:
            code = self._action_to_code(action, base_url)
            if code:
                lines.append(f"        {code}")

        lines += ["", ""]
        return "\n".join(lines)

    @staticmethod
    def _to_class_name(name: str) -> str:
        """snake_case veya kebab-case → PascalCase."""
        parts = re.split(r"[_\-\s]+", name)
        return "Test" + "".join(p.capitalize() for p in parts if p)

    @staticmethod
    def _selector_expr(action: RecordedAction) -> str:
        """Seçiciyi Playwright Python ifadesine dönüştürür."""
        sel = action.selector
        stype = action.selector_type
        if stype == "testid":
            tid = sel.replace('[data-testid="', "").rstrip('"]')
            return f'page.get_by_test_id("{tid}")'
        elif stype == "text":
            text = sel.replace('text="', "").rstrip('"')
            return f'page.get_by_text("{text}")'
        elif stype == "xpath":
            return f'page.locator("{sel}")'
        else:
            return f'page.locator("{sel}")'

    def _action_to_code(self, action: RecordedAction, base_url: str = "") -> str:
        """Tek aksiyonu Python satırına dönüştürür."""
        sel_expr = self._selector_expr(action)
        at = action.action_type

        if at == "navigate":
            url = action.value
            if base_url and url.startswith(base_url):
                url_expr = f'self.BASE_URL + "{url[len(base_url):]}"'
            else:
                url_expr = repr(url)
            return f"page.goto({url_expr})"

        elif at == "click":
            return f"{sel_expr}.click()"

        elif at == "type":
            return f"{sel_expr}.fill({repr(action.value)})"

        elif at == "clear":
            return f"{sel_expr}.clear()"

        elif at == "select":
            return f"{sel_expr}.select_option({repr(action.value)})"

        elif at == "scroll":
            y = action.metadata.get("y", 500)
            x = action.metadata.get("x", 0)
            if action.selector:
                return f"{sel_expr}.scroll_into_view_if_needed()"
            else:
                return f"page.evaluate('window.scrollBy({x}, {y})')"

        elif at == "wait":
            if action.selector:
                return f"{sel_expr}.wait_for(state='visible')"
            else:
                ms = action.metadata.get("duration_ms", 1000)
                return f"page.wait_for_timeout({ms})"

        elif at == "assert_text":
            return f"expect({sel_expr}).to_have_text({repr(action.value)})"

        elif at == "assert_visible":
            return f"expect({sel_expr}).to_be_visible()"

        elif at == "assert_url":
            return f"expect(page).to_have_url({repr(action.value)})"

        elif at == "hover":
            return f"{sel_expr}.hover()"

        elif at == "press_key":
            return f"{sel_expr}.press({repr(action.value)})"

        elif at == "upload":
            return f"{sel_expr}.set_input_files({repr(action.value)})"

        elif at == "screenshot":
            name = action.metadata.get("name", "screenshot")
            return f'page.screenshot(path="screenshots/{name}.png")'

        elif at == "drag_drop":
            target = action.metadata.get("target", "")
            return f"{sel_expr}.drag_to(page.locator({repr(target)}))"

        # Fallback: generate a generic interaction comment that is at least
        # syntactically valid Python (playwright wait) so the script runs.
        # The comment documents what was originally recorded for manual review.
        return (
            f"# NOTE: unsupported action type '{at}' — manual implementation needed\n"
            f"# Selector: {action.selector!r}\n"
            f"page.wait_for_timeout(500)  # placeholder: replace with real action"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Cucumber/Gherkin Üretici (Mavi Yaka Formatı)
# ──────────────────────────────────────────────────────────────────────────────
class CucumberGenerator:
    """
    Kayıt oturumundan Mavi Yaka Cucumber/Gherkin feature dosyası üretir.
    """

    TR_KEYWORDS = {
        "navigate": "Kullanıcı {url} sayfasına gider",
        "click":    "Kullanıcı {element} üzerine tıklar",
        "type":     "Kullanıcı {element} alanına \"{value}\" yazar",
        "select":   "Kullanıcı {element} alanından \"{value}\" seçer",
        "assert_text":    "Sayfa \"{value}\" metnini içermelidir",
        "assert_visible": "{element} görünür olmalıdır",
        "assert_url":     "URL \"{value}\" olmalıdır",
        "wait":     "Sistem yanıt vermesini bekler",
        "scroll":   "Kullanıcı sayfayı kaydırır",
        "hover":    "Kullanıcı {element} üzerine gelir",
        "upload":   "Kullanıcı {element} alanına dosya yükler",
        "screenshot": "Ekran görüntüsü alınır",
    }

    def generate(self, session: RecordingSession, feature_title: str = "") -> str:
        """
        Gherkin feature dosyası içeriği döner.
        """
        title = feature_title or session.name
        domain = session.domain
        tags = " ".join(f"@{t}" for t in (session.tags or [domain, "otomasyon"]))
        ts = datetime.now().strftime("%Y-%m-%d")

        lines = [
            f"# Özellik: {title}",
            f"# Domain: {domain}",
            f"# Oluşturuldu: {ts}",
            f"# Açıklama: {session.description}",
            "",
            f"# language: tr",
            "",
            tags,
            f"Özellik: {title}",
            f"  {session.description or domain + ' domain üzerinde ' + title + ' testi'}",
            "",
        ]

        # Background (navigate ile başlıyorsa)
        bg_actions = [a for a in session.actions if a.action_type == "navigate"]
        if bg_actions:
            lines += [
                "  Arka Plan:",
                f"    {self._action_to_step(bg_actions[0], 'Verildiği zaman')}",
                "",
            ]
            remaining = [a for a in session.actions if a != bg_actions[0]]
        else:
            remaining = session.actions

        # Senaryo
        scenario_name = self._to_scenario_name(title)
        lines += [
            f"  @{domain} @smoke",
            f"  Senaryo: {scenario_name}",
        ]

        step_keyword = "Verildiği zaman"
        for i, action in enumerate(remaining):
            step = self._action_to_step(action, step_keyword)
            lines.append(f"    {step}")
            if i == 0:
                step_keyword = "Ve"

        lines += ["", ""]
        return "\n".join(lines)

    def _action_to_step(self, action: RecordedAction, keyword: str = "Ve") -> str:
        """Aksiyonu Gherkin adımına dönüştürür."""
        tmpl = self.TR_KEYWORDS.get(
            action.action_type,
            "Bilinmeyen aksiyon ({action_type}) — manuel adım gerekli",
        )
        element = action.element_name or action.selector[:30]
        value = action.value
        url = action.value if action.action_type == "navigate" else ""

        step = tmpl.format(
            element=element,
            value=value,
            url=url,
            action_type=action.action_type,
        )
        return f"{keyword} {step}"

    @staticmethod
    def _to_scenario_name(name: str) -> str:
        """Makine adını okunabilir Türkçe senaryo adına çevirir."""
        name = re.sub(r"[_\-]", " ", name)
        return name.capitalize()


# ──────────────────────────────────────────────────────────────────────────────
# Page Object Model Üretici
# ──────────────────────────────────────────────────────────────────────────────
class POMGenerator:
    """
    Kayıt oturumundan Page Object Model sınıfı üretir.
    Hem Python hem Java formatında.
    """

    def generate_python(self, session: RecordingSession, class_name: str = "") -> str:
        """Python POM sınıfı üretir."""
        cls_name = class_name or self._to_class_name(session.name) + "Page"
        elements = self._extract_unique_elements(session)
        domain   = session.domain
        base_url = session.base_url

        lines = [
            '"""',
            f'Page Object: {cls_name}',
            f'Domain: {domain}',
            f'Oluşturuldu: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            '"""',
            "from playwright.sync_api import Page, Locator",
            "from core.enhanced_framework import PageObjectBase",
            "",
            "",
            f"class {cls_name}(PageObjectBase):",
            f'    """Mavi Yaka {domain} — {session.name} sayfası."""',
            "",
            f"    URL = {repr(base_url)}",
            "",
            "    # ── Seçiciler ───────────────────────────────────────────────────────────",
        ]

        # Element sabitleri
        for name, (sel, stype) in elements.items():
            const_name = name.upper()
            lines.append(f"    {const_name} = {repr(sel)}")

        lines += [
            "",
            "    def __init__(self, page: Page):",
            "        super().__init__(page)",
            "",
        ]

        # Locator property'leri
        lines.append("    # ── Locator'lar ─────────────────────────────────────────────────────────")
        for name, (sel, stype) in elements.items():
            const_name = name.upper()
            lines += [
                f"    @property",
                f"    def {name}(self) -> Locator:",
                f"        return self.page.locator(self.{const_name})",
                "",
            ]

        # Aksiyon metodları
        lines.append("    # ── Aksiyonlar ─────────────────────────────────────────────────────────")
        method_sets: set[str] = set()
        for action in session.actions:
            if action.action_type == "navigate":
                if "navigate_to" not in method_sets:
                    lines += [
                        "    def navigate_to(self):",
                        '        """Sayfaya gider."""',
                        "        self.page.goto(self.URL)",
                        "",
                    ]
                    method_sets.add("navigate_to")
            elif action.action_type in ("click", "type", "select") and action.element_name:
                method_name = f"{action.action_type}_{action.element_name}"
                if method_name not in method_sets:
                    if action.action_type == "click":
                        lines += [
                            f"    def click_{action.element_name}(self):",
                            f'        """{action.element_name} elementine tıklar."""',
                            f"        self.{action.element_name}.click()",
                            "",
                        ]
                    elif action.action_type == "type":
                        lines += [
                            f"    def fill_{action.element_name}(self, text: str):",
                            f'        """{action.element_name} alanını doldurur."""',
                            f"        self.{action.element_name}.fill(text)",
                            "",
                        ]
                    elif action.action_type == "select":
                        lines += [
                            f"    def select_{action.element_name}(self, value: str):",
                            f'        """{action.element_name} seçim kutusunda seçim yapar."""',
                            f"        self.{action.element_name}.select_option(value)",
                            "",
                        ]
                    method_sets.add(method_name)

        return "\n".join(lines)

    def generate_java(self, session: RecordingSession, class_name: str = "") -> str:
        """Java POM sınıfı üretir (Selenium WebDriver uyumlu)."""
        cls_name = class_name or self._to_class_name(session.name) + "Page"
        elements = self._extract_unique_elements(session)
        domain   = session.domain
        package  = f"com.nexusqa.{domain}.pages"

        lines = [
            f"package {package};",
            "",
            "import org.openqa.selenium.By;",
            "import org.openqa.selenium.WebDriver;",
            "import org.openqa.selenium.WebElement;",
            "import org.openqa.selenium.support.ui.Select;",
            "import org.openqa.selenium.support.ui.WebDriverWait;",
            "import java.time.Duration;",
            "",
            f"/**",
            f" * Page Object: {cls_name}",
            f" * Domain: {domain}",
            f" * Oluşturuldu: {datetime.now().strftime('%Y-%m-%d')}",
            f" */",
            f"public class {cls_name} {{",
            "",
            "    private final WebDriver driver;",
            "    private final WebDriverWait wait;",
            f"    private static final String URL = {json.dumps(session.base_url)};",
            "",
            "    // ── Seçiciler ──────────────────────────────────────────────────────────",
        ]

        for name, (sel, stype) in elements.items():
            by_type = "By.cssSelector" if stype in ("css", "text") else "By.xpath"
            const_name = re.sub(r"([A-Z])", r"_\1", name).upper().lstrip("_")
            lines.append(f"    private static final By {const_name} = {by_type}({json.dumps(sel)});")

        lines += [
            "",
            f"    public {cls_name}(WebDriver driver) {{",
            "        this.driver = driver;",
            "        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));",
            "    }",
            "",
            "    public void navigateTo() {",
            "        driver.get(URL);",
            "    }",
            "",
        ]

        for name, (sel, stype) in elements.items():
            by_type = "By.cssSelector" if stype in ("css", "text") else "By.xpath"
            const_name = re.sub(r"([A-Z])", r"_\1", name).upper().lstrip("_")
            cap_name = name[0].upper() + name[1:]

            lines += [
                f"    public WebElement get{cap_name}() {{",
                f"        return wait.until(d -> d.findElement({const_name}));",
                "    }",
                "",
                f"    public void click{cap_name}() {{",
                f"        get{cap_name}().click();",
                "    }",
                "",
            ]

        lines += ["}", ""]
        return "\n".join(lines)

    @staticmethod
    def _to_class_name(name: str) -> str:
        parts = re.split(r"[_\-\s]+", name)
        return "".join(p.capitalize() for p in parts if p)

    @staticmethod
    def _extract_unique_elements(session: RecordingSession) -> dict[str, tuple[str, str]]:
        """Oturumdaki benzersiz elementleri {element_name: (selector, type)} olarak döner."""
        elements: dict[str, tuple[str, str]] = {}
        for action in session.actions:
            if action.selector and action.element_name and action.action_type != "navigate":
                elements[action.element_name] = (action.selector, action.selector_type)
        return elements


# ──────────────────────────────────────────────────────────────────────────────
# JSON Locator Dosyası Üretici (Mavi Yaka Formatı)
# ──────────────────────────────────────────────────────────────────────────────
class LocatorGenerator:
    """
    Mavi Yaka'nın JSON locator formatında çıktı üretir.
    Format: {"element_name": {"type": "css|xpath", "value": "..."}}
    """

    def generate(self, session: RecordingSession) -> dict:
        """
        JSON locator sözlüğü döner.

        Returns::

            {
              "login_button": {"type": "css", "value": "#login-btn"},
              "username_input": {"type": "css", "value": "[name='username']"},
              ...
            }
        """
        locators: dict[str, dict] = {}
        for action in session.actions:
            if not action.selector or action.action_type == "navigate":
                continue
            name = action.element_name or re.sub(r"[^a-z0-9_]", "_", action.selector.lower())[:30]
            # Tekrarı önle — zaten varsa daha spesifik olanı tercih et
            if name in locators:
                existing = locators[name]["value"]
                # data-testid > id > diğer
                if "data-testid" in action.selector and "data-testid" not in existing:
                    locators[name] = {"type": action.selector_type, "value": action.selector}
            else:
                locators[name] = {
                    "type": action.selector_type,
                    "value": action.selector,
                }
        return locators

    def save(self, session: RecordingSession, output_path: Path | str | None = None) -> str:
        """JSON locator dosyasını kaydeder."""
        locators = self.generate(session)
        if output_path is None:
            domain = session.domain
            loc_dir = settings.BASE_DIR / "locators" / domain
            loc_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r"[^a-z0-9_]", "_", session.name.lower())
            output_path = loc_dir / f"{safe_name}_locators.json"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(locators, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Locator dosyası kaydedildi: %s", output_path)
        return str(output_path)


# ──────────────────────────────────────────────────────────────────────────────
# Test Recorder — Hepsi Bir Arada
# ──────────────────────────────────────────────────────────────────────────────
class TestRecorder:
    """
    Tüm üretici sınıfları bir araya getiren ana sınıf.

    Kullanım::

        recorder = TestRecorder("login_test", domain="ark", base_url="https://ark.example.com")
        recorder.start()
        recorder.navigate("https://ark.example.com/login")
        recorder.click("#login-btn")
        session = recorder.stop()

        # Kod üretimi
        playwright_code = recorder.to_playwright()
        feature_file    = recorder.to_cucumber()
        pom_py          = recorder.to_pom_python()
        pom_java        = recorder.to_pom_java()
        locator_json    = recorder.to_locators()
    """

    def __init__(self, name: str = "", domain: str = "default", base_url: str = ""):
        self.name      = name
        self.domain    = domain
        self.base_url  = base_url
        self._recorder: ActionRecorder | None = None
        self._session: RecordingSession | None = None

        self._code_gen    = CodeGenerator()
        self._cuke_gen    = CucumberGenerator()
        self._pom_gen     = POMGenerator()
        self._loc_gen     = LocatorGenerator()

    # ── Yaşam Döngüsü ────────────────────────────────────────────────────────
    def start(self) -> "TestRecorder":
        """Kaydı başlatır."""
        self._recorder = ActionRecorder(self.name, self.domain, self.base_url)
        return self

    def stop(self) -> RecordingSession:
        """Kaydı durdurur."""
        if self._recorder:
            self._session = self._recorder.stop()
        return self._session

    @property
    def session(self) -> RecordingSession:
        if self._session:
            return self._session
        if self._recorder:
            return self._recorder.session
        raise RuntimeError("Kayıt başlatılmadı. Önce start() çağırın.")

    # ── Aksiyon kısayolları ───────────────────────────────────────────────────
    def navigate(self, url: str):
        self._recorder.navigate(url); return self

    def click(self, selector: str, element_info: dict | None = None):
        self._recorder.click(selector, element_info); return self

    def type_text(self, selector: str, text: str, element_info: dict | None = None):
        self._recorder.type_text(selector, text, element_info); return self

    def scroll(self, selector: str = "", y: int = 500):
        self._recorder.scroll(selector, y=y); return self

    def wait(self, selector: str = "", duration_ms: int = 1000):
        self._recorder.wait(selector, duration_ms); return self

    def assert_text(self, selector: str, expected: str):
        self._recorder.assert_text(selector, expected); return self

    def assert_visible(self, selector: str):
        self._recorder.assert_visible(selector); return self

    def assert_url(self, url: str):
        self._recorder.assert_url(url); return self

    def select_option(self, selector: str, value: str):
        self._recorder.select_option(selector, value); return self

    def add_raw_action(self, action: RecordedAction):
        self._recorder.session.actions.append(action); return self

    # ── Kod Üretimi ───────────────────────────────────────────────────────────
    def to_playwright(self) -> str:
        """Playwright Python test kodu üretir."""
        return self._code_gen.generate(self.session)

    def to_cucumber(self, feature_title: str = "") -> str:
        """Cucumber/Gherkin feature dosyası üretir."""
        return self._cuke_gen.generate(self.session, feature_title)

    def to_pom_python(self) -> str:
        """Python POM sınıfı üretir."""
        return self._pom_gen.generate_python(self.session)

    def to_pom_java(self) -> str:
        """Java POM sınıfı üretir."""
        return self._pom_gen.generate_java(self.session)

    def to_locators(self) -> dict:
        """JSON locator sözlüğü döner."""
        return self._loc_gen.generate(self.session)

    # ── Kaydet / Yükle ────────────────────────────────────────────────────────
    def save_session(self, path: Path | str | None = None) -> str:
        """Oturumu JSON dosyasına kaydeder."""
        return self._recorder.save(path)

    def save_all(self, output_dir: Path | str | None = None) -> dict[str, str]:
        """
        Tüm çıktıları (playwright, feature, pom_py, pom_java, locators, session)
        belirtilen dizine kaydeder.

        Returns:
            {output_type: file_path}
        """
        if output_dir is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = settings.BASE_DIR / "generated" / f"{self.domain}_{self.name}_{ts}"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        safe = re.sub(r"[^a-z0-9_]", "_", self.name.lower())
        results = {}

        # Playwright
        pw_path = output_dir / f"test_{safe}.py"
        pw_path.write_text(self.to_playwright(), encoding="utf-8")
        results["playwright"] = str(pw_path)

        # Feature
        feat_path = output_dir / f"{safe}.feature"
        feat_path.write_text(self.to_cucumber(), encoding="utf-8")
        results["feature"] = str(feat_path)

        # POM Python
        pom_py_path = output_dir / f"{safe}_page.py"
        pom_py_path.write_text(self.to_pom_python(), encoding="utf-8")
        results["pom_python"] = str(pom_py_path)

        # POM Java
        pom_java_path = output_dir / f"{self._pom_gen._to_class_name(self.name)}Page.java"
        pom_java_path.write_text(self.to_pom_java(), encoding="utf-8")
        results["pom_java"] = str(pom_java_path)

        # Locators JSON
        loc_path = output_dir / f"{safe}_locators.json"
        loc_path.write_text(
            json.dumps(self.to_locators(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        results["locators"] = str(loc_path)

        # Session JSON
        sess_path = output_dir / f"{safe}_session.json"
        sess_path.write_text(
            json.dumps(self.session.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        results["session"] = str(sess_path)

        logger.info("Tüm çıktılar kaydedildi: %s", output_dir)
        return results

    @classmethod
    def load_session(cls, path: Path | str) -> "TestRecorder":
        """Kayıtlı oturumu yükler."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        session = RecordingSession.from_dict(data)
        tr = cls(name=session.name, domain=session.domain, base_url=session.base_url)
        tr._session = session
        return tr
