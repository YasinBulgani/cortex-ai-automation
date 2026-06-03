"""
Otonom Test Keşfi (Autonomous Test Discovery)
═══════════════════════════════════════════════════════════════════════════

Octomind / Checksum tarzı otonom keşif yeteneği. İnsan senaryo yazmadan:

  1. Hedef uygulamayı crawl eder (BFS, aynı domain).
  2. Keşfedilen sayfa yapısını LLM'e verip **kritik kullanıcı akışlarını**
     (login, arama, form gönderimi, CRUD vb.) sentezler.
  3. Her akışı **çalıştırılabilir Neurex Gherkin feature** + DB manuel testine
     dönüştürür. Üretilen feature'lar doğrudan ``/api/wizard/run-neurex`` ile
     koşturulabilir.

Tasarım notları
---------------
* Crawler ``wizard_routes.api_crawl_site`` ile aynı element-çıkarma mantığını
  kullanır (tek kaynak: aynı JS getSelector/getXPath sözleşmesi).
* Akış→Gherkin dönüşümü **deterministik**tir (ikinci bir LLM çağrısı yok):
  LLM yalnızca akışları yapısal JSON olarak sentezler, kod üretimi kurallıdır.
  Bu, "uydurma selector" riskini düşürür ve maliyeti tek çağrıya indirir.
* Tüm LLM erişimi merkezi ``LLMGateway`` üzerinden (PII sanitize + cache +
  bütçe). Doğrudan provider çağrısı yok.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Neurex DSL — generate_gherkin'deki desteklenen adım sözlüğüyle birebir uyumlu.
_NEUREX_DSL_HINT = """Desteklenen Neurex adımları (SADECE bunlara karşılık gelen action'lar üret):
  navigate      → Given kullanıcı "<path>" sayfasındadır
  fill          → When kullanıcı "<selector>" kutusuna "<değer>" yazar
  click         → When kullanıcı "<metin>" metnine tıklar
  press_enter   → When kullanıcı Enter tuşuna basar
  wait          → When kullanıcı "<ms>" milisaniye bekler
  assert_title  → Then sayfa başlığı "<metin>" içermelidir
  assert_url    → Then URL "<metin>" içermelidir
  assert_visible→ Then "<selector>" elementi görünür olmalıdır"""


# ═══════════════════════════════════════════════════════════════════════════
# 1. CRAWL — Hedef uygulamayı otonom gez
# ═══════════════════════════════════════════════════════════════════════════

_PAGE_EXTRACT_JS = r"""
() => {
    const getSelector = (el) => {
        if (el.id) return '#' + el.id;
        if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
        if (el.getAttribute('data-test-id')) return `[data-test-id="${el.getAttribute('data-test-id')}"]`;
        if (el.name) return `[name="${el.name}"]`;
        let s = el.tagName.toLowerCase();
        if (el.className && typeof el.className === 'string') {
            let cls = el.className.trim().split(/\s+/)[0];
            if (cls && !cls.includes(':')) s += '.' + cls;
        }
        return s;
    };
    let links = [...document.querySelectorAll('a[href]')]
        .map(a => a.href).filter(h => h.startsWith('http'));
    let buttons = [...document.querySelectorAll('button, [role="button"], input[type="submit"], a[href]')]
        .filter(e => window.getComputedStyle(e).display !== 'none')
        .map(e => ({
            text: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().substring(0, 50),
            selector: getSelector(e),
        })).filter(b => b.text.length > 0);
    let inputs = [...document.querySelectorAll('input:not([type="hidden"]), textarea, select')]
        .filter(e => window.getComputedStyle(e).display !== 'none')
        .map(e => ({
            label: (e.getAttribute('placeholder') || e.getAttribute('aria-label') || e.name || e.id || '').trim().substring(0, 50),
            type: e.type || e.tagName.toLowerCase(),
            selector: getSelector(e),
        }));
    let headings = [...document.querySelectorAll('h1, h2, h3')]
        .map(h => h.innerText.trim()).filter(t => t.length > 0);
    return {
        title: document.title,
        headings: headings.slice(0, 8),
        buttons: buttons.slice(0, 25),
        inputs: inputs.slice(0, 25),
        links: [...new Set(links)].slice(0, 50),
        forms_count: document.querySelectorAll('form').length,
    };
}
"""


def discover_pages(
    start_url: str,
    max_pages: int = 12,
    credentials: dict | None = None,
) -> list[dict]:
    """Hedef URL'den başlayarak aynı domaindeki sayfaları BFS ile keşfeder.

    Her sayfa için: url, title, headings, buttons[], inputs[], forms_count.
    Görseller/font/CSS engellenerek crawl hızlandırılır.
    """
    from playwright.sync_api import sync_playwright

    if not start_url.startswith(("http://", "https://")):
        start_url = "https://" + start_url

    base_domain = urlparse(start_url).netloc
    visited: set[str] = set()
    pages: list[dict] = []
    frontier: list[str] = [start_url]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800}, locale="tr-TR"
        )
        # Ağır kaynakları engelle → ~3-5x hızlanma
        context.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,otf,mp4,webm}",
            lambda route: route.abort(),
        )
        page = context.new_page()

        if credentials and credentials.get("login_url"):
            try:
                page.goto(credentials["login_url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(800)
                if credentials.get("username_selector") and credentials.get("username"):
                    page.fill(credentials["username_selector"], credentials["username"])
                if credentials.get("password_selector") and credentials.get("password"):
                    page.fill(credentials["password_selector"], credentials["password"])
                if credentials.get("submit_selector"):
                    page.click(credentials["submit_selector"])
                    page.wait_for_timeout(1500)
            except Exception as exc:
                logger.warning("Discovery login adımı atlandı: %s", exc)

        while frontier and len(visited) < max_pages:
            url = frontier.pop(0)
            if url in visited:
                continue
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)
                visited.add(url)
                info = page.evaluate(_PAGE_EXTRACT_JS)
                pages.append({
                    "url": url,
                    "title": info.get("title", ""),
                    "headings": info.get("headings", []),
                    "buttons": info.get("buttons", []),
                    "inputs": info.get("inputs", []),
                    "forms_count": info.get("forms_count", 0),
                })
                for link in info.get("links", []):
                    if urlparse(link).netloc != base_domain:
                        continue
                    clean = link.split("#")[0].split("?")[0]
                    if clean not in visited and clean not in frontier:
                        frontier.append(clean)
            except Exception as exc:
                logger.debug("Discovery sayfa atlandı %s: %s", url, exc)
                continue

        browser.close()

    return pages


# ═══════════════════════════════════════════════════════════════════════════
# 2. SYNTHESIZE — LLM ile kritik akışları çıkar
# ═══════════════════════════════════════════════════════════════════════════

def _pages_digest(pages: list[dict]) -> str:
    """Sayfaları token-ekonomik metin özetine indirger (LLM girdisi)."""
    lines: list[str] = []
    for i, pg in enumerate(pages, 1):
        lines.append(f"### Sayfa {i}: {pg.get('title') or '(başlıksız)'}")
        lines.append(f"URL: {pg['url']}")
        if pg.get("headings"):
            lines.append("Başlıklar: " + ", ".join(pg["headings"][:6]))
        if pg.get("inputs"):
            ins = "; ".join(
                f"{(inp.get('label') or inp.get('type'))} [{inp.get('selector')}]"
                for inp in pg["inputs"][:12]
            )
            lines.append(f"Girdiler: {ins}")
        if pg.get("buttons"):
            btns = "; ".join(
                f"'{b.get('text')}' [{b.get('selector')}]" for b in pg["buttons"][:15]
            )
            lines.append(f"Tıklanabilirler: {btns}")
        lines.append("")
    return "\n".join(lines)


def _repair_json(s: str) -> str:
    """Yerel LLM'lerin sık yaptığı JSON hatalarını onarır (trailing comma vb.)."""
    # `... ,]` / `... ,}` → trailing virgülü sil
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def _loads_tolerant(s: str):
    """json.loads + trailing-comma onarımı fallback'i."""
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return json.loads(_repair_json(s))


def _extract_json(raw: str):
    """LLM çıktısından ilk geçerli JSON değerini çıkarır (markdown + onarım tolere eder).

    Hem nesne ``{...}`` hem dizi ``[...]`` döndürebilir.
    """
    raw = raw.strip()
    # ```json ... ``` bloğunu soy
    fence = re.search(r"```(?:json)?\s*(.+?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return _loads_tolerant(raw)
    except json.JSONDecodeError:
        pass
    # İlk dengeli { ... } veya [ ... ] bloğunu yakala
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = raw.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == open_ch:
                depth += 1
            elif raw[i] == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return _loads_tolerant(raw[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("LLM çıktısından geçerli JSON çıkarılamadı")


def synthesize_flows(
    pages: list[dict],
    base_url: str,
    max_flows: int = 8,
) -> list[dict]:
    """Crawl çıktısından kritik kullanıcı akışlarını LLM ile sentezler.

    Dönüş: her biri ``title, priority, category, tags, steps[]`` içeren akış
    listesi. ``steps`` her adımda ``action, target, value, expected``.
    """
    from services import get_llm_gateway

    digest = _pages_digest(pages)
    system = (
        "Sen kıdemli bir QA otomasyon mimarısın. Sana bir web uygulamasının "
        "crawl ile keşfedilmiş sayfa yapısı verilir. Görevin: gerçek kullanıcıların "
        "izleyeceği EN KRİTİK uçtan uca akışları (login, arama, form gönderimi, "
        "CRUD, navigasyon, checkout vb.) tespit edip yapısal JSON olarak döndürmek. "
        "Yalnızca verilen selector'leri kullan; selector UYDURMA."
    )
    user = f"""Hedef uygulama: {base_url}

{_NEUREX_DSL_HINT}

KEŞFEDİLEN SAYFALAR:
{digest}

GÖREV: En fazla {max_flows} kritik akış üret. SADECE şu JSON şemasını döndür:
{{
  "flows": [
    {{
      "title": "Kısa akış adı",
      "priority": "P1|P2|P3",
      "category": "authentication|search|form|navigation|crud|other",
      "tags": ["@smoke"],
      "steps": [
        {{"action": "navigate", "target": "/login", "value": "", "expected": "Giriş sayfası açılır"}},
        {{"action": "fill", "target": "#user", "value": "test_user", "expected": ""}},
        {{"action": "click", "target": "Giriş Yap", "value": "", "expected": ""}},
        {{"action": "assert_url", "target": "dashboard", "value": "", "expected": "Panoya yönlenir"}}
      ]
    }}
  ]
}}

KURALLAR:
- action SADECE şunlardan biri: navigate, fill, click, press_enter, wait, assert_title, assert_url, assert_visible
- navigate.target göreli path olsun (ör. "/login").
- fill.target bir selector, click.target görünen METİN veya selector olabilir.
- Hassas alanlar için value'da gerçek sır KOYMA; "test_user" / "Passw0rd!" gibi placeholder kullan.
- Her akış en az 2 adım içersin. SADECE JSON döndür, açıklama yazma."""

    gw = get_llm_gateway()
    resp = gw.complete(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    data = _extract_json(resp.content)
    flows = data.get("flows", []) if isinstance(data, dict) else []
    # Hafif doğrulama / normalize
    clean: list[dict] = []
    for fl in flows:
        if not isinstance(fl, dict) or not fl.get("steps"):
            continue
        clean.append({
            "title": str(fl.get("title") or "İsimsiz akış").strip()[:120],
            "priority": str(fl.get("priority") or "P2").strip().upper(),
            "category": str(fl.get("category") or "other").strip(),
            "tags": [str(t) for t in (fl.get("tags") or []) if t],
            "steps": [s for s in fl["steps"] if isinstance(s, dict) and s.get("action")],
        })
    return [f for f in clean if f["steps"]]


# ═══════════════════════════════════════════════════════════════════════════
# 3. GENERATE — Akış → çalıştırılabilir Neurex Gherkin (deterministik)
# ═══════════════════════════════════════════════════════════════════════════

def _q(value: str) -> str:
    """Gherkin içi çift tırnak kaçışı."""
    return str(value).replace('"', "'").strip()


def _rel_path(target: str, base_url: str) -> str:
    """navigate hedefini göreli path'e indirger."""
    target = str(target).strip()
    if target.startswith(("http://", "https://")):
        path = urlparse(target).path or "/"
        return path
    if not target.startswith("/"):
        target = "/" + target
    return target


def flow_to_gherkin(flow: dict, base_url: str) -> str:
    """Yapısal akışı Neurex DSL'ine uygun çalıştırılabilir .feature metnine çevirir."""
    tags = set(flow.get("tags") or [])
    tags.add("@discovery")
    prio = flow.get("priority", "P2")
    if prio:
        tags.add("@" + prio)
    tag_line = " ".join(sorted(tags))

    title = flow["title"]
    lines = [tag_line, f"Feature: {title}", "", f"  Scenario: {title}"]

    has_nav = False
    for step in flow["steps"]:
        action = str(step.get("action", "")).strip().lower()
        target = step.get("target", "")
        value = step.get("value", "")

        if action == "navigate":
            path = _rel_path(target, base_url)
            if path in ("", "/"):
                lines.append("    Given kullanıcı ana sayfadadır")
            else:
                lines.append(f'    Given kullanıcı "{_q(path)}" sayfasındadır')
            has_nav = True
        elif action == "fill":
            lines.append(f'    When kullanıcı "{_q(target)}" kutusuna "{_q(value)}" yazar')
        elif action == "click":
            lines.append(f'    When kullanıcı "{_q(target)}" metnine tıklar')
        elif action == "press_enter":
            lines.append("    When kullanıcı Enter tuşuna basar")
        elif action == "wait":
            ms = re.sub(r"\D", "", str(target or value)) or "1000"
            lines.append(f'    When kullanıcı "{ms}" milisaniye bekler')
        elif action == "assert_title":
            lines.append(f'    Then sayfa başlığı "{_q(target)}" içermelidir')
        elif action == "assert_url":
            lines.append(f'    Then URL "{_q(target)}" içermelidir')
        elif action == "assert_visible":
            lines.append(f'    Then "{_q(target)}" elementi görünür olmalıdır')
        # bilinmeyen action'lar sessizce atlanır

    # navigate yoksa ana sayfayı başa ekle (Neurex senaryosu bir başlangıç ister)
    if not has_nav:
        lines.insert(3, "    Given kullanıcı ana sayfadadır")

    # Güvenlik ağı assertion'ı — en az bir adım yürümeli
    lines.append("    Then en az 1 adım başarılı olmalıdır")
    return "\n".join(lines) + "\n"


def _step_to_text(step: dict) -> tuple[str, str]:
    """DB manuel testi için (action, expected) okunabilir metin döndürür."""
    action = str(step.get("action", "")).strip().lower()
    target = step.get("target", "")
    value = step.get("value", "")
    expected = str(step.get("expected", "") or "").strip()
    mapping = {
        "navigate": f"'{target}' sayfasına git",
        "fill": f"'{target}' alanına '{value}' yaz",
        "click": f"'{target}' öğesine tıkla",
        "press_enter": "Enter tuşuna bas",
        "wait": f"{target or value} ms bekle",
        "assert_title": f"Sayfa başlığı '{target}' içermeli",
        "assert_url": f"URL '{target}' içermeli",
        "assert_visible": f"'{target}' görünür olmalı",
    }
    text = mapping.get(action, f"{action} {target}".strip())
    if not expected:
        expected = mapping.get(action, "Adım başarıyla tamamlanır")
    return text, expected


def persist_flow(flow: dict) -> int:
    """Akışı SQLite manuel test olarak kaydeder (manual_tests + steps). test_id döner."""
    from core import db

    test_id = db.create_manual_test(f"[Keşif] {flow['title']}")
    for step in flow["steps"]:
        action_text, expected = _step_to_text(step)
        db.add_manual_step(test_id, action_text, expected)
    return test_id


# ═══════════════════════════════════════════════════════════════════════════
# 4. ORCHESTRATE — Tam pipeline
# ═══════════════════════════════════════════════════════════════════════════

def run_discovery(
    start_url: str,
    max_pages: int = 12,
    max_flows: int = 8,
    credentials: dict | None = None,
    persist: bool = True,
) -> dict:
    """Otonom keşif pipeline'ı: crawl → akış sentezi → Gherkin + DB.

    Dönüş::

        {
          "base_url": ...,
          "pages_crawled": int,
          "flows": [ { title, priority, category, tags, steps,
                       feature, test_id } ],
          "features": [ { "title": ..., "content": <gherkin> } ],
          "stats": { pages, flows, persisted }
        }
    """
    if not start_url.startswith(("http://", "https://")):
        start_url = "https://" + start_url

    pages = discover_pages(start_url, max_pages=max_pages, credentials=credentials)
    if not pages:
        return {
            "base_url": start_url,
            "pages_crawled": 0,
            "flows": [],
            "features": [],
            "stats": {"pages": 0, "flows": 0, "persisted": 0},
            "warning": "Hiç sayfa keşfedilemedi (erişim/oturum sorunu olabilir).",
        }

    flows = synthesize_flows(pages, start_url, max_flows=max_flows)

    enriched: list[dict] = []
    features: list[dict] = []
    persisted = 0
    for flow in flows:
        feature_text = flow_to_gherkin(flow, start_url)
        flow["feature"] = feature_text
        if persist:
            try:
                flow["test_id"] = persist_flow(flow)
                persisted += 1
            except Exception as exc:
                logger.warning("Akış DB'ye kaydedilemedi (%s): %s", flow["title"], exc)
                flow["test_id"] = None
        enriched.append(flow)
        features.append({"title": flow["title"], "content": feature_text})

    return {
        "base_url": start_url,
        "pages_crawled": len(pages),
        "flows": enriched,
        "features": features,
        "stats": {"pages": len(pages), "flows": len(flows), "persisted": persisted},
    }
