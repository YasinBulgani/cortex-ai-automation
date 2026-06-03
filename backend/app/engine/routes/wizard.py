"""
Wizard routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/wizard_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/wizard.py — APIRouter, port 8000 (consolidated)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wizard", tags=["engine", "wizard"])


# ─── Settings stub ───────────────────────────────────────────────────────────

class _Settings:
    BASE_DIR: Path = Path(__file__).resolve().parents[5]
    FEATURES_DIR: Path = BASE_DIR / "features"
    TESTS_DIR: Path = BASE_DIR / "tests"
    LOCATORS_DIR: Path = BASE_DIR / "locators"
    TESTDATA_DIR: Path = BASE_DIR / "testdata"
    ALLURE_RESULTS_DIR: Path = BASE_DIR / "allure-results"
    BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:3000")

_settings = _Settings()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AnalyzeDocumentBody(BaseModel):
    text: str = Field(..., min_length=1)


class CrawlBody(BaseModel):
    url: str = Field(..., min_length=1)
    max_pages: int = 10
    credentials: Optional[dict] = None


class DiscoverSelectorsBody(BaseModel):
    url: str = Field(..., min_length=1)


class MonkeyTestBody(BaseModel):
    url: str = Field(..., min_length=1)
    max_actions: int = 30
    credentials: Optional[dict] = None


class GenerateAutomationBody(BaseModel):
    scenarios: list[dict] = Field(..., min_length=1)
    selectors: list[dict] = Field(default_factory=list)
    url: str = ""
    project_name: str = "generated"


class FullRunBody(BaseModel):
    text: str = ""
    url: str = ""
    project_name: str = "wizard"
    max_pages: int = 5


class WizardFeature(BaseModel):
    title: str = ""
    content: str = ""


class RunNeurexBody(BaseModel):
    features: list[WizardFeature] = Field(..., min_length=1)
    url: str = ""
    domain: str = "default"
    browser: str = "chromium"
    locators: list[Any] = Field(default_factory=list)
    test_data: dict = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# 1. Doküman Analizi
# ═══════════════════════════════════════════════════════════════════════

@router.post("/analyze-document")
def api_analyze_document(body: AnalyzeDocumentBody):
    """Analiz dokümanından AI ile manuel test senaryoları üretir."""
    try:
        from core.ai_engine import get_ai_engine  # type: ignore[import]
        engine = get_ai_engine()
        manual_tests = engine.extract_manual_tests_from_text(body.text)
        return {
            "status": "ok",
            "manual_tests": manual_tests,
            "count": len(manual_tests),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════
# 2. Sayfa Keşfi (Crawler)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/crawl")
def api_crawl_site(body: CrawlBody):
    """Hedef URL'den başlayarak sayfaları keşfeder."""
    from urllib.parse import urlparse

    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]

        base_domain = urlparse(url).netloc
        visited: set[str] = set()
        pages_data: list[dict] = []
        to_visit = [url]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="tr-TR")
            page = context.new_page()

            creds = body.credentials
            if creds and creds.get("login_url"):
                page.goto(creds["login_url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)
                if creds.get("username_selector") and creds.get("username"):
                    page.fill(creds["username_selector"], creds["username"])
                if creds.get("password_selector") and creds.get("password"):
                    page.fill(creds["password_selector"], creds["password"])
                if creds.get("submit_selector"):
                    page.click(creds["submit_selector"])
                    page.wait_for_timeout(2000)

            while to_visit and len(visited) < body.max_pages:
                current = to_visit.pop(0)
                if current in visited:
                    continue
                try:
                    page.goto(current, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1500)
                    visited.add(current)

                    page_info = page.evaluate("""
                    () => {
                        const getSelector = (el) => {
                            if (el.id) return '#' + el.id;
                            if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
                            if (el.getAttribute('data-test-id')) return `[data-test-id="${el.getAttribute('data-test-id')}"]`;
                            if (el.name) return `[name="${el.name}"]`;
                            let s = el.tagName.toLowerCase();
                            if (el.className && typeof el.className === 'string') {
                                let cls = el.className.trim().split(/\\s+/)[0];
                                if (cls && !cls.includes(':')) s += '.' + cls;
                            }
                            return s;
                        };
                        const getXPath = (el) => {
                            if (el.id) return `//*[@id="${el.id}"]`;
                            let parts = [];
                            while (el && el.nodeType === Node.ELEMENT_NODE) {
                                let idx = 0, sib = el;
                                while (sib = sib.previousElementSibling) {
                                    if (sib.tagName === el.tagName) idx++;
                                }
                                let tag = el.tagName.toLowerCase();
                                parts.unshift(idx > 0 ? `${tag}[${idx+1}]` : tag);
                                el = el.parentNode;
                            }
                            return '/' + parts.join('/');
                        };
                        let links = [...document.querySelectorAll('a[href]')]
                            .map(a => a.href).filter(h => h.startsWith('http'));
                        let buttons = [...document.querySelectorAll('button, [role="button"], input[type="submit"]')]
                            .filter(e => window.getComputedStyle(e).display !== 'none')
                            .map(e => ({
                                text: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().substring(0, 60),
                                selector: getSelector(e), xpath: getXPath(e), tag: e.tagName.toLowerCase()
                            })).filter(b => b.text.length > 0);
                        let inputs = [...document.querySelectorAll('input:not([type="hidden"]), textarea, select')]
                            .filter(e => window.getComputedStyle(e).display !== 'none')
                            .map(e => ({
                                label: (e.getAttribute('placeholder') || e.getAttribute('aria-label') || e.name || e.id || '').trim(),
                                type: e.type || e.tagName.toLowerCase(),
                                selector: getSelector(e), xpath: getXPath(e), tag: e.tagName.toLowerCase()
                            }));
                        let headings = [...document.querySelectorAll('h1, h2, h3')]
                            .map(h => h.innerText.trim()).filter(t => t.length > 0);
                        return {
                            title: document.title, headings: headings.slice(0, 10),
                            buttons: buttons.slice(0, 30), inputs: inputs.slice(0, 30),
                            links: [...new Set(links)].slice(0, 50),
                            forms_count: document.querySelectorAll('form').length,
                            tables_count: document.querySelectorAll('table').length,
                        };
                    }
                    """)

                    record = {
                        "url": current,
                        "title": page_info.get("title", ""),
                        "headings": page_info.get("headings", []),
                        "buttons": page_info.get("buttons", []),
                        "inputs": page_info.get("inputs", []),
                        "forms_count": page_info.get("forms_count", 0),
                        "tables_count": page_info.get("tables_count", 0),
                        "links_count": len(page_info.get("links", [])),
                    }
                    pages_data.append(record)

                    for link in page_info.get("links", []):
                        parsed = urlparse(link)
                        if parsed.netloc == base_domain and link not in visited:
                            clean = link.split("#")[0].split("?")[0]
                            if clean not in visited and clean not in to_visit:
                                to_visit.append(clean)
                except Exception:
                    continue

            browser.close()

        return {
            "status": "ok",
            "pages": pages_data,
            "visited_count": len(visited),
            "total_buttons": sum(len(p["buttons"]) for p in pages_data),
            "total_inputs": sum(len(p["inputs"]) for p in pages_data),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(exc), "trace": traceback.format_exc()},
        )


# ═══════════════════════════════════════════════════════════════════════
# 3. Derinlemesine Selector/XPath Keşfi
# ═══════════════════════════════════════════════════════════════════════

@router.post("/discover-selectors")
def api_discover_selectors(body: DiscoverSelectorsBody):
    """Tek bir sayfadaki tüm etkileşimli elementleri derinlemesine keşfeder."""
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            context.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,otf,mp4,webm}",
                lambda route: route.abort(),
            )
            context.route("**/*.{css}", lambda route: route.abort())
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(500)

            elements = page.evaluate("""
            () => {
                const getXPath = (el) => {
                    if (el.id) return `//*[@id="${el.id}"]`;
                    let parts = [], node = el;
                    while (node && node.nodeType === Node.ELEMENT_NODE) {
                        let idx = 0, sib = node;
                        while (sib = sib.previousElementSibling) {
                            if (sib.tagName === node.tagName) idx++;
                        }
                        let tag = node.tagName.toLowerCase();
                        parts.unshift(idx > 0 ? `${tag}[${idx+1}]` : tag);
                        node = node.parentNode;
                    }
                    return '/' + parts.join('/');
                };
                const getCSS = (el) => {
                    if (el.id) return '#' + el.id;
                    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
                    if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
                    if (el.placeholder) return `${el.tagName.toLowerCase()}[placeholder="${el.placeholder}"]`;
                    let s = el.tagName.toLowerCase();
                    if (el.className && typeof el.className === 'string') {
                        let cls = el.className.trim().split(/\\s+/).slice(0, 2).join('.');
                        if (cls) s += '.' + cls;
                    }
                    return s;
                };
                let results = [];
                let query = 'button, a[href], input:not([type="hidden"]), textarea, select, ' +
                            '[role="button"], [role="link"], [role="textbox"], [role="checkbox"], ' +
                            '[role="radio"], [role="tab"], [role="menuitem"], [onclick], ' +
                            'label, [contenteditable="true"]';
                document.querySelectorAll(query).forEach(el => {
                    let style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return;
                    let text = (el.innerText || el.value || el.getAttribute('aria-label') ||
                               el.getAttribute('placeholder') || el.getAttribute('title') || '').trim();
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || el.getAttribute('role') || '',
                        text: text.substring(0, 80),
                        id: el.id || null, name: el.name || null,
                        css: getCSS(el), xpath: getXPath(el),
                        testid: el.getAttribute('data-testid') || null,
                        href: el.getAttribute('href') || null,
                        is_visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    });
                });
                return results;
            }
            """)

            browser.close()

        return {"status": "ok", "url": url, "elements": elements, "element_count": len(elements)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════
# 4. Monkey Testing
# ═══════════════════════════════════════════════════════════════════════

@router.post("/monkey-test")
def api_monkey_test(body: MonkeyTestBody):
    """Sayfada rastgele tıklama, yazma, scroll yaparak hata arar."""
    import base64
    import random
    from datetime import datetime

    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]

        console_errors: list[dict] = []
        network_errors: list[dict] = []
        actions_log: list[dict] = []
        screenshots: list[str] = []

        random_strings = [
            "test", "' OR 1=1 --", "<script>alert(1)</script>",
            "a" * 300, "12345", "test@test.com", "", " ",
            "!@#$%^&*()", "null", "undefined", "-1", "0",
        ]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="tr-TR")
            page = context.new_page()

            page.on("console", lambda msg: console_errors.append({
                "type": msg.type, "text": msg.text,
                "url": page.url, "timestamp": datetime.now().isoformat(),
            }) if msg.type in ("error", "warning") else None)

            page.on("response", lambda res: network_errors.append({
                "url": res.url, "status": res.status, "page_url": page.url,
            }) if res.status >= 400 else None)

            creds = body.credentials
            if creds and creds.get("login_url"):
                try:
                    page.goto(creds["login_url"], wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1000)
                    if creds.get("username_selector") and creds.get("username"):
                        page.fill(creds["username_selector"], creds["username"])
                    if creds.get("password_selector") and creds.get("password"):
                        page.fill(creds["password_selector"], creds["password"])
                    if creds.get("submit_selector"):
                        page.click(creds["submit_selector"])
                        page.wait_for_timeout(2000)
                except Exception as exc:
                    logger.debug("Wizard monkey login adımı atlandı: %s", exc)

            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)

            for i in range(body.max_actions):
                try:
                    action_type = random.choice(["click", "click", "click", "fill", "scroll", "navigate"])
                    record: dict = {"step": i + 1, "type": action_type, "url": page.url}

                    if action_type == "click":
                        els = page.query_selector_all("button, a[href], [role='button'], [onclick], input[type='submit']")
                        visible = [e for e in els if e.is_visible()]
                        if visible:
                            chosen = random.choice(visible)
                            try:
                                record["target"] = (chosen.inner_text() or chosen.evaluate("e => e.tagName"))[:40]
                                chosen.click(timeout=3000)
                                record["result"] = "clicked"
                                page.wait_for_timeout(500)
                            except Exception as e:
                                record["result"] = f"click_error: {str(e)[:80]}"
                    elif action_type == "fill":
                        inputs = page.query_selector_all("input:not([type='hidden']):not([type='submit']), textarea")
                        visible_inputs = [inp for inp in inputs if inp.is_visible()]
                        if visible_inputs:
                            target_input = random.choice(visible_inputs)
                            val = random.choice(random_strings)
                            record["value"] = val[:30]
                            try:
                                target_input.fill(val)
                                record["result"] = "filled"
                            except Exception as e:
                                record["result"] = f"fill_error: {str(e)[:80]}"
                    elif action_type == "scroll":
                        direction = random.choice(["down", "up"])
                        pixels = random.randint(100, 500)
                        page.evaluate(f"window.scrollBy(0, {pixels if direction == 'down' else -pixels})")
                        record.update({"direction": direction, "pixels": pixels, "result": "scrolled"})
                    elif action_type == "navigate":
                        links = page.evaluate("""
                        () => [...document.querySelectorAll('a[href]')]
                            .map(a => a.href)
                            .filter(h => h.startsWith('http') && !h.includes('logout') && !h.includes('signout'))
                        """)
                        if links:
                            link = random.choice(links[:20])
                            record["target"] = link[:80]
                            try:
                                page.goto(link, wait_until="domcontentloaded", timeout=10000)
                                record["result"] = "navigated"
                                page.wait_for_timeout(800)
                            except Exception as e:
                                record["result"] = f"nav_error: {str(e)[:80]}"

                    actions_log.append(record)
                except Exception as e:
                    actions_log.append({"step": i + 1, "type": "error", "error": str(e)[:100]})

            try:
                ss = page.screenshot(full_page=True)
                screenshots.append(base64.b64encode(ss).decode())
            except Exception as exc:
                logger.debug("Wizard monkey final ekran görüntüsü alınamadı: %s", exc)

            browser.close()

        error_count = len(console_errors) + len(network_errors)
        return {
            "status": "ok",
            "actions_performed": len(actions_log),
            "actions_log": actions_log,
            "console_errors": console_errors,
            "network_errors": network_errors,
            "error_count": error_count,
            "stability_score": max(0, 100 - (error_count * 5)),
            "screenshots": screenshots[:3],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(exc), "trace": traceback.format_exc()},
        )


# ═══════════════════════════════════════════════════════════════════════
# 5. Otomasyon Kodu Üretimi
# ═══════════════════════════════════════════════════════════════════════

@router.post("/generate-automation")
def api_generate_automation(body: GenerateAutomationBody):
    """Manuel test senaryolarından otomasyon kodu ve Gherkin feature dosyaları üretir."""
    try:
        from core.ai_engine import get_ai_engine  # type: ignore[import]
        engine = get_ai_engine()

        results: dict[str, list] = {
            "feature_files": [], "test_files": [], "locator_json": [], "page_objects": [],
        }

        selectors_context = ""
        if body.selectors:
            selectors_context = "\n\nKEŞFEDİLEN ELEMENTLER VE SELECTORLERİ:\n"
            for s in body.selectors[:50]:
                selectors_context += f"- {s.get('text', '')} => CSS: {s.get('css', '')} | XPath: {s.get('xpath', '')}\n"

        for i, scenario in enumerate(body.scenarios):
            title = scenario.get("title", f"Senaryo_{i+1}")
            steps_text = ""
            for step in scenario.get("steps", []):
                steps_text += f"  - Aksiyon: {step.get('action', '')}\n    Beklenen: {step.get('expected', '')}\n"

            requirements = f"Senaryo: {title}\nAdımlar:\n{steps_text}"
            gherkin = engine.generate_gherkin(requirements + selectors_context, body.url)
            results["feature_files"].append({
                "name": f"{body.project_name}_{i+1}.feature",
                "content": gherkin,
                "scenario_title": title,
            })

            task = f"'{title}' senaryosunu test et. URL: {body.url}. Adımlar: {steps_text}"
            test_code = engine.generate_test_file(body.url, task, f"{body.project_name}_{i+1}")
            results["test_files"].append({
                "name": f"test_{body.project_name}_{i+1}.py",
                "content": test_code,
                "scenario_title": title,
            })

        if body.selectors:
            locator_entries = []
            for s in body.selectors:
                text = s.get("text", "").strip()
                if not text:
                    continue
                key = text.lower().replace(" ", "_").replace(".", "")[:40]
                if s.get("testid"):
                    entry = {"key": key, "type": "testid", "value": s["testid"]}
                elif s.get("id"):
                    entry = {"key": key, "type": "id", "value": s["id"]}
                elif s.get("name"):
                    entry = {"key": key, "type": "name", "value": s["name"]}
                elif s.get("xpath"):
                    entry = {"key": key, "type": "xpath", "value": s["xpath"]}
                else:
                    entry = {"key": key, "type": "css", "value": s.get("css", "")}
                if entry["key"]:
                    locator_entries.append(entry)
            results["locator_json"] = locator_entries

        return {"status": "ok", **results}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(exc), "trace": traceback.format_exc()},
        )


# ═══════════════════════════════════════════════════════════════════════
# 6. Tam Akış
# ═══════════════════════════════════════════════════════════════════════

@router.post("/full-run")
def api_wizard_full_run(body: FullRunBody):
    """Tüm wizard adımlarını sırayla çalıştırır."""
    from urllib.parse import urlparse

    results: dict[str, Any] = {"steps": []}
    manual_tests: list = []

    if body.text.strip():
        try:
            from core.ai_engine import get_ai_engine  # type: ignore[import]
            ai = get_ai_engine()
            manual_tests = ai.extract_manual_tests_from_text(body.text)
            results["manual_tests"] = manual_tests
            results["steps"].append({"name": "document_analysis", "status": "ok", "count": len(manual_tests)})
        except Exception as exc:
            results["steps"].append({"name": "document_analysis", "status": "error", "error": str(exc)})
    else:
        results["steps"].append({"name": "document_analysis", "status": "skipped"})

    all_selectors: list = []
    if body.url:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import]

            url = body.url
            base_domain = urlparse(url).netloc
            visited: set[str] = set()
            pages_data: list[dict] = []
            to_visit = [url]

            with sync_playwright() as pw:
                br = pw.chromium.launch(headless=True)
                pg = br.new_page(viewport={"width": 1280, "height": 800})

                while to_visit and len(visited) < body.max_pages:
                    current = to_visit.pop(0)
                    if current in visited:
                        continue
                    try:
                        pg.goto(current, wait_until="domcontentloaded", timeout=15000)
                        pg.wait_for_timeout(1500)
                        visited.add(current)

                        info = pg.evaluate("""() => {
                            let links = [...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => h.startsWith('http'));
                            let els = [...document.querySelectorAll('button, input:not([type="hidden"]), textarea, select, a[href], [role="button"]')]
                                .filter(e => { let s = window.getComputedStyle(e); return s.display !== 'none'; })
                                .map(e => ({
                                    text: (e.innerText || e.value || e.placeholder || e.getAttribute('aria-label') || '').trim().substring(0, 60),
                                    tag: e.tagName.toLowerCase(), id: e.id || null, name: e.name || null,
                                    css: e.id ? '#'+e.id : e.tagName.toLowerCase(),
                                }));
                            return { title: document.title, links, elements: els };
                        }""")

                        pages_data.append({"url": current, "title": info["title"], "element_count": len(info["elements"])})
                        all_selectors.extend(info.get("elements", []))

                        for link in info.get("links", []):
                            parsed = urlparse(link)
                            if parsed.netloc == base_domain and link not in visited:
                                clean = link.split("#")[0].split("?")[0]
                                if clean not in visited and clean not in to_visit:
                                    to_visit.append(clean)
                    except Exception:
                        continue
                br.close()

            results["pages"] = pages_data
            results["steps"].append({"name": "crawl", "status": "ok", "pages_found": len(pages_data)})
        except Exception as exc:
            results["steps"].append({"name": "crawl", "status": "error", "error": str(exc)})

    return {"status": "ok", **results}


# ═══════════════════════════════════════════════════════════════════════
# 7. Neurex Koşusu
# ═══════════════════════════════════════════════════════════════════════

@router.post("/run-neurex")
def api_run_neurex(body: RunNeurexBody):
    """Wizard'da üretilen Neurex feature dosyalarını çalıştırır."""
    from datetime import datetime

    browser = body.browser.lower()
    if browser not in {"chromium", "firefox", "webkit"}:
        browser = "chromium"

    try:
        from routes.runner_routes import _build_glue_file_content  # type: ignore[import]

        run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        safe_env = f"wizard{run_id[-8:]}"
        feature_dir = _settings.FEATURES_DIR / "wizard" / run_id
        test_dir = _settings.TESTS_DIR / "wizard" / run_id
        feature_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        _settings.ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        locator_file = _settings.LOCATORS_DIR / f"wizard_{run_id}.json"
        locator_file.write_text(
            json.dumps(body.locators, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        data_file = _settings.TESTDATA_DIR / f"{body.domain}-{safe_env}-data.json"
        data_file.write_text(
            json.dumps(body.test_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        glue_paths: list[str] = []
        saved_features: list[str] = []

        for index, feature in enumerate(body.features, 1):
            title = str(feature.title or f"wizard_scenario_{index}")
            content = str(feature.content or "").strip()
            if not content:
                continue

            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_").lower() or f"scenario_{index}"
            feature_path = feature_dir / f"{index:02d}_{slug}.feature"
            feature_path.write_text(content + "\n", encoding="utf-8")

            glue_path = test_dir / f"test_{feature_path.stem}.py"
            glue_path.write_text(_build_glue_file_content(feature_path.as_posix()), encoding="utf-8")

            glue_paths.append(str(glue_path))
            saved_features.append(str(feature_path.relative_to(_settings.BASE_DIR)))

        if not glue_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Çalıştırılabilir feature oluşturulamadı",
            )

        env = os.environ.copy()
        env["BROWSER"] = browser
        env["BASE_URL"] = body.url or env.get("BASE_URL", _settings.BASE_URL)
        env["TEST_DOMAIN"] = body.domain
        env["TEST_ENV"] = safe_env
        env["HEADLESS"] = env.get("HEADLESS", "true")

        cmd = [
            sys.executable, "-m", "pytest",
            *glue_paths,
            "--alluredir", str(_settings.ALLURE_RESULTS_DIR),
            "--tb=short", "-q", "--import-mode=importlib",
        ]

        start = time.time()
        proc = subprocess.run(
            cmd, cwd=str(_settings.BASE_DIR), capture_output=True,
            text=True, timeout=180, env=env,
        )
        duration_ms = int((time.time() - start) * 1000)
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()

        passed = 0
        failed = 0
        if m := re.search(r"(\d+)\s+passed", output):
            passed = int(m.group(1))
        if m := re.search(r"(\d+)\s+failed", output):
            failed = int(m.group(1))

        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": output[-8000:] if output else "",
            "passed": passed, "failed": failed,
            "duration_ms": duration_ms,
            "domain": body.domain, "env": safe_env,
            "saved_features": saved_features,
            "locator_file": str(locator_file.relative_to(_settings.BASE_DIR)),
            "data_file": str(data_file.relative_to(_settings.BASE_DIR)),
            "allure_report_url": "/reports/allure-report/",
        }
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Neurex koşusu zaman aşımına uğradı (>180s)",
        )
    except Exception as exc:
        logger.exception("Wizard run-neurex failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(exc), "trace": traceback.format_exc()},
        )
