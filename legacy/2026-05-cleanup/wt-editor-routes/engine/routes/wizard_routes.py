"""
Proje Sihirbazı (Wizard) Routes
- Sayfa keşfi (crawler)
- Selector/XPath keşfi
- Monkey testing
- Otomasyon kodu üretimi
- Doküman analizi
"""
import json
import logging
import os
import random
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify
from config.settings import settings

logger = logging.getLogger(__name__)

wizard_bp = Blueprint("wizard", __name__)


# ═══════════════════════════════════════════════════════════════════════
# 1. Doküman Analizi — AI ile manuel test senaryosu çıkarma
# ═══════════════════════════════════════════════════════════════════════

@wizard_bp.route("/api/wizard/analyze-document", methods=["POST"])
def api_analyze_document():
    """Analiz dokümanından AI ile manuel test senaryoları üretir."""
    data = request.json or {}
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"error": "Analiz metni gereklidir"}), 400

    try:
        from core.ai_engine import AIEngine
        engine = AIEngine()
        manual_tests = engine.extract_manual_tests_from_text(text)
        return jsonify({
            "status": "ok",
            "manual_tests": manual_tests,
            "count": len(manual_tests),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════
# 2. Sayfa Keşfi (Crawler) — Hedef uygulamayı otomatik gezme
# ═══════════════════════════════════════════════════════════════════════

@wizard_bp.route("/api/wizard/crawl", methods=["POST"])
def api_crawl_site():
    """
    Hedef URL'den başlayarak sayfaları keşfeder.
    Linkleri takip eder, her sayfanın elementlerini toplar.
    """
    data = request.json or {}
    start_url = data.get("url", "").strip()
    max_pages = data.get("max_pages", 10)
    credentials = data.get("credentials")

    if not start_url:
        return jsonify({"error": "URL gereklidir"}), 400

    if not start_url.startswith(("http://", "https://")):
        start_url = "https://" + start_url

    try:
        from playwright.sync_api import sync_playwright
        from urllib.parse import urlparse, urljoin

        base_domain = urlparse(start_url).netloc
        visited = set()
        pages_data = []
        to_visit = [start_url]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="tr-TR",
            )
            page = context.new_page()

            # Login if credentials provided
            if credentials and credentials.get("login_url"):
                page.goto(credentials["login_url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)
                if credentials.get("username_selector") and credentials.get("username"):
                    page.fill(credentials["username_selector"], credentials["username"])
                if credentials.get("password_selector") and credentials.get("password"):
                    page.fill(credentials["password_selector"], credentials["password"])
                if credentials.get("submit_selector"):
                    page.click(credentials["submit_selector"])
                    page.wait_for_timeout(2000)

            while to_visit and len(visited) < max_pages:
                url = to_visit.pop(0)
                if url in visited:
                    continue

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1500)
                    visited.add(url)

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
                            .map(a => a.href)
                            .filter(h => h.startsWith('http'));

                        let buttons = [...document.querySelectorAll('button, [role="button"], input[type="submit"]')]
                            .filter(e => window.getComputedStyle(e).display !== 'none')
                            .map(e => ({
                                text: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().substring(0, 60),
                                selector: getSelector(e),
                                xpath: getXPath(e),
                                tag: e.tagName.toLowerCase()
                            })).filter(b => b.text.length > 0);

                        let inputs = [...document.querySelectorAll('input:not([type="hidden"]), textarea, select')]
                            .filter(e => window.getComputedStyle(e).display !== 'none')
                            .map(e => ({
                                label: (e.getAttribute('placeholder') || e.getAttribute('aria-label') || e.name || e.id || '').trim(),
                                type: e.type || e.tagName.toLowerCase(),
                                selector: getSelector(e),
                                xpath: getXPath(e),
                                tag: e.tagName.toLowerCase()
                            }));

                        let headings = [...document.querySelectorAll('h1, h2, h3')]
                            .map(h => h.innerText.trim())
                            .filter(t => t.length > 0);

                        return {
                            title: document.title,
                            headings: headings.slice(0, 10),
                            buttons: buttons.slice(0, 30),
                            inputs: inputs.slice(0, 30),
                            links: [...new Set(links)].slice(0, 50),
                            forms_count: document.querySelectorAll('form').length,
                            tables_count: document.querySelectorAll('table').length,
                        };
                    }
                    """)

                    page_record = {
                        "url": url,
                        "title": page_info.get("title", ""),
                        "headings": page_info.get("headings", []),
                        "buttons": page_info.get("buttons", []),
                        "inputs": page_info.get("inputs", []),
                        "forms_count": page_info.get("forms_count", 0),
                        "tables_count": page_info.get("tables_count", 0),
                        "links_count": len(page_info.get("links", [])),
                    }
                    pages_data.append(page_record)

                    for link in page_info.get("links", []):
                        parsed = urlparse(link)
                        if parsed.netloc == base_domain and link not in visited:
                            clean = link.split("#")[0].split("?")[0]
                            if clean not in visited and clean not in to_visit:
                                to_visit.append(clean)

                except Exception:
                    continue

            browser.close()

        return jsonify({
            "status": "ok",
            "pages": pages_data,
            "visited_count": len(visited),
            "total_buttons": sum(len(p["buttons"]) for p in pages_data),
            "total_inputs": sum(len(p["inputs"]) for p in pages_data),
        })

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ═══════════════════════════════════════════════════════════════════════
# 3. Derinlemesine Selector/XPath Keşfi
# ═══════════════════════════════════════════════════════════════════════

@wizard_bp.route("/api/wizard/discover-selectors", methods=["POST"])
def api_discover_selectors():
    """Tek bir sayfadaki tüm etkileşimli elementleri derinlemesine keşfeder."""
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL gereklidir"}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)

            elements = page.evaluate("""
            () => {
                const getXPath = (el) => {
                    if (el.id) return `//*[@id="${el.id}"]`;
                    let parts = [];
                    let node = el;
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
                        id: el.id || null,
                        name: el.name || null,
                        css: getCSS(el),
                        xpath: getXPath(el),
                        testid: el.getAttribute('data-testid') || null,
                        href: el.getAttribute('href') || null,
                        is_visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    });
                });

                return results;
            }
            """)

            screenshot_b64 = None
            try:
                ss_bytes = page.screenshot(full_page=True)
                import base64
                screenshot_b64 = base64.b64encode(ss_bytes).decode()
            except Exception as exc:
                logger.debug("Wizard keşif ekran görüntüsü alınamadı: %s", exc)

            browser.close()

        return jsonify({
            "status": "ok",
            "url": url,
            "elements": elements,
            "element_count": len(elements),
            "screenshot": screenshot_b64,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════
# 4. Monkey Testing — Rastgele etkileşimle hata avcılığı
# ═══════════════════════════════════════════════════════════════════════

@wizard_bp.route("/api/wizard/monkey-test", methods=["POST"])
def api_monkey_test():
    """
    Sayfada rastgele tıklama, yazma, scroll yaparak hata arar.
    Console hatalarını, çökmeleri, 404'leri yakalar.
    """
    data = request.json or {}
    url = data.get("url", "").strip()
    max_actions = data.get("max_actions", 30)
    credentials = data.get("credentials")

    if not url:
        return jsonify({"error": "URL gereklidir"}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.sync_api import sync_playwright

        console_errors = []
        network_errors = []
        actions_log = []
        screenshots = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="tr-TR",
            )
            page = context.new_page()

            page.on("console", lambda msg: (
                console_errors.append({
                    "type": msg.type,
                    "text": msg.text,
                    "url": page.url,
                    "timestamp": datetime.now().isoformat(),
                }) if msg.type in ("error", "warning") else None
            ))

            page.on("response", lambda res: (
                network_errors.append({
                    "url": res.url,
                    "status": res.status,
                    "page_url": page.url,
                }) if res.status >= 400 else None
            ))

            # Login
            if credentials and credentials.get("login_url"):
                try:
                    page.goto(credentials["login_url"], wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1000)
                    if credentials.get("username_selector") and credentials.get("username"):
                        page.fill(credentials["username_selector"], credentials["username"])
                    if credentials.get("password_selector") and credentials.get("password"):
                        page.fill(credentials["password_selector"], credentials["password"])
                    if credentials.get("submit_selector"):
                        page.click(credentials["submit_selector"])
                        page.wait_for_timeout(2000)
                except Exception as exc:
                    logger.debug("Wizard monkey login adımı atlandı: %s", exc)

            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)

            random_strings = [
                "test", "' OR 1=1 --", "<script>alert(1)</script>",
                "a" * 300, "12345", "test@test.com", "", " ",
                "!@#$%^&*()", "null", "undefined", "-1", "0",
            ]

            for i in range(max_actions):
                try:
                    action_type = random.choice(["click", "click", "click", "fill", "scroll", "navigate"])
                    action_record = {"step": i + 1, "type": action_type, "url": page.url}

                    if action_type == "click":
                        clickables = page.evaluate("""
                        () => {
                            let els = document.querySelectorAll(
                                'button, a[href], [role="button"], [onclick], input[type="submit"]'
                            );
                            return [...els]
                                .filter(e => {
                                    let s = window.getComputedStyle(e);
                                    return s.display !== 'none' && s.visibility !== 'hidden' && e.offsetHeight > 0;
                                })
                                .map((e, i) => ({
                                    index: i,
                                    text: (e.innerText || e.value || '').trim().substring(0, 40),
                                    tag: e.tagName.toLowerCase()
                                }));
                        }
                        """)
                        if clickables:
                            target = random.choice(clickables)
                            action_record["target"] = target["text"] or target["tag"]
                            try:
                                els = page.query_selector_all(
                                    "button, a[href], [role='button'], [onclick], input[type='submit']"
                                )
                                visible = [e for e in els if e.is_visible()]
                                if visible:
                                    chosen = random.choice(visible)
                                    chosen.click(timeout=3000)
                                    action_record["result"] = "clicked"
                                    page.wait_for_timeout(500)
                            except Exception as e:
                                action_record["result"] = f"click_error: {str(e)[:80]}"

                    elif action_type == "fill":
                        inputs = page.query_selector_all("input:not([type='hidden']):not([type='submit']), textarea")
                        visible_inputs = [inp for inp in inputs if inp.is_visible()]
                        if visible_inputs:
                            target_input = random.choice(visible_inputs)
                            random_val = random.choice(random_strings)
                            action_record["value"] = random_val[:30]
                            try:
                                target_input.fill(random_val)
                                action_record["result"] = "filled"
                            except Exception as e:
                                action_record["result"] = f"fill_error: {str(e)[:80]}"

                    elif action_type == "scroll":
                        direction = random.choice(["down", "up"])
                        pixels = random.randint(100, 500)
                        page.evaluate(f"window.scrollBy(0, {pixels if direction == 'down' else -pixels})")
                        action_record["direction"] = direction
                        action_record["pixels"] = pixels
                        action_record["result"] = "scrolled"

                    elif action_type == "navigate":
                        links = page.evaluate("""
                        () => [...document.querySelectorAll('a[href]')]
                            .map(a => a.href)
                            .filter(h => h.startsWith('http') && !h.includes('logout') && !h.includes('signout'))
                        """)
                        if links:
                            link = random.choice(links[:20])
                            action_record["target"] = link[:80]
                            try:
                                page.goto(link, wait_until="domcontentloaded", timeout=10000)
                                action_record["result"] = "navigated"
                                page.wait_for_timeout(800)
                            except Exception as e:
                                action_record["result"] = f"nav_error: {str(e)[:80]}"

                    actions_log.append(action_record)

                except Exception as e:
                    actions_log.append({
                        "step": i + 1,
                        "type": "error",
                        "error": str(e)[:100],
                    })

            # Final screenshot
            try:
                import base64
                ss = page.screenshot(full_page=True)
                screenshots.append(base64.b64encode(ss).decode())
            except Exception as exc:
                logger.debug("Wizard monkey final ekran görüntüsü alınamadı: %s", exc)

            browser.close()

        error_count = len(console_errors) + len(network_errors)
        return jsonify({
            "status": "ok",
            "actions_performed": len(actions_log),
            "actions_log": actions_log,
            "console_errors": console_errors,
            "network_errors": network_errors,
            "error_count": error_count,
            "stability_score": max(0, 100 - (error_count * 5)),
            "screenshots": screenshots[:3],
        })

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ═══════════════════════════════════════════════════════════════════════
# 5. Otomasyon Kodu Üretimi
# ═══════════════════════════════════════════════════════════════════════

@wizard_bp.route("/api/wizard/generate-automation", methods=["POST"])
def api_generate_automation():
    """
    Manuel test senaryolarından + keşfedilen selector'lardan
    Playwright otomasyon kodu ve Gherkin feature dosyaları üretir.
    """
    data = request.json or {}
    scenarios = data.get("scenarios", [])
    selectors = data.get("selectors", [])
    target_url = data.get("url", "")
    project_name = data.get("project_name", "generated")

    if not scenarios:
        return jsonify({"error": "En az bir senaryo gereklidir"}), 400

    try:
        from core.ai_engine import AIEngine
        engine = AIEngine()

        results = {
            "feature_files": [],
            "test_files": [],
            "locator_json": [],
            "page_objects": [],
        }

        selectors_context = ""
        if selectors:
            selectors_context = "\n\nKEŞFEDİLEN ELEMENTLER VE SELECTORLERİ:\n"
            for s in selectors[:50]:
                selectors_context += f"- {s.get('text', '')} => CSS: {s.get('css', '')} | XPath: {s.get('xpath', '')}\n"

        # Generate Gherkin for each scenario
        for i, scenario in enumerate(scenarios):
            title = scenario.get("title", f"Senaryo_{i+1}")
            steps_text = ""
            for step in scenario.get("steps", []):
                steps_text += f"  - Aksiyon: {step.get('action', '')}\n    Beklenen: {step.get('expected', '')}\n"

            requirements = f"Senaryo: {title}\nAdımlar:\n{steps_text}"
            gherkin = engine.generate_gherkin(requirements + selectors_context, target_url)

            results["feature_files"].append({
                "name": f"{project_name}_{i+1}.feature",
                "content": gherkin,
                "scenario_title": title,
            })

            # Generate pytest code
            task = f"'{title}' senaryosunu test et. URL: {target_url}. Adımlar: {steps_text}"
            test_code = engine.generate_test_file(target_url, task, f"{project_name}_{i+1}")
            results["test_files"].append({
                "name": f"test_{project_name}_{i+1}.py",
                "content": test_code,
                "scenario_title": title,
            })

        # Generate locator JSON (NexusQA pattern)
        if selectors:
            locator_entries = []
            for s in selectors:
                entry = {"key": "", "type": "", "value": ""}
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

        return jsonify({"status": "ok", **results})

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ═══════════════════════════════════════════════════════════════════════
# 6. Tam Akış — Tüm adımları tek seferde çalıştır
# ═══════════════════════════════════════════════════════════════════════

@wizard_bp.route("/api/wizard/full-run", methods=["POST"])
def api_wizard_full_run():
    """
    Tüm wizard adımlarını sırayla çalıştırır:
    1. Doküman analizi → Manuel senaryolar
    2. Sayfa crawl
    3. Selector keşfi
    4. Otomasyon kodu üretimi
    """
    data = request.json or {}
    text = data.get("text", "")
    url = data.get("url", "")
    project_name = data.get("project_name", "wizard")
    max_pages = data.get("max_pages", 5)

    results = {"steps": []}

    # Step 1: Document analysis
    if text.strip():
        try:
            from core.ai_engine import AIEngine
            ai = AIEngine()
            manual_tests = ai.extract_manual_tests_from_text(text)
            results["manual_tests"] = manual_tests
            results["steps"].append({"name": "document_analysis", "status": "ok", "count": len(manual_tests)})
        except Exception as e:
            results["steps"].append({"name": "document_analysis", "status": "error", "error": str(e)})
            manual_tests = []
    else:
        manual_tests = []
        results["steps"].append({"name": "document_analysis", "status": "skipped"})

    # Step 2: Crawl
    all_selectors = []
    if url:
        try:
            from playwright.sync_api import sync_playwright
            from urllib.parse import urlparse

            base_domain = urlparse(url).netloc
            visited = set()
            pages_data = []
            to_visit = [url]

            with sync_playwright() as pw:
                br = pw.chromium.launch(headless=True)
                pg = br.new_page(viewport={"width": 1280, "height": 800})

                while to_visit and len(visited) < max_pages:
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
                                    tag: e.tagName.toLowerCase(),
                                    id: e.id || null,
                                    name: e.name || null,
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
        except Exception as e:
            results["steps"].append({"name": "crawl", "status": "error", "error": str(e)})

    return jsonify({"status": "ok", **results})


@wizard_bp.route("/api/wizard/run-nexusqa", methods=["POST"])
def api_run_nexusqa():
    """
    Wizard'da uretilen NexusQA feature dosyalarini gecici artefaktlara yazar
    ve pytest-bdd ile senkron olarak calistirir.
    """
    data = request.json or {}
    features = data.get("features") or []
    url = str(data.get("url", "") or "").strip()
    domain = str(data.get("domain", "default") or "default").strip() or "default"
    browser = str(data.get("browser", "chromium") or "chromium").strip().lower()
    locators = data.get("locators") or []
    test_data = data.get("test_data") or {}

    if browser not in {"chromium", "firefox", "webkit"}:
        browser = "chromium"
    if not isinstance(features, list) or not features:
        return jsonify({"ok": False, "error": "features listesi zorunludur"}), 400

    try:
        from routes.runner_routes import _build_glue_file_content

        run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        safe_env = f"wizard{run_id[-8:]}"
        feature_dir = settings.FEATURES_DIR / "wizard" / run_id
        test_dir = settings.TESTS_DIR / "wizard" / run_id
        feature_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        settings.ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        locator_file = settings.LOCATORS_DIR / f"wizard_{run_id}.json"
        locator_file.write_text(
            json.dumps(locators if isinstance(locators, list) else [], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        data_file = settings.TESTDATA_DIR / f"{domain}-{safe_env}-data.json"
        data_file.write_text(
            json.dumps(test_data if isinstance(test_data, dict) else {}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        glue_paths: list[str] = []
        saved_features: list[str] = []

        for index, feature in enumerate(features, 1):
            title = str(feature.get("title") or f"wizard_scenario_{index}")
            content = str(feature.get("content") or "").strip()
            if not content:
                continue

            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_").lower() or f"scenario_{index}"
            feature_path = feature_dir / f"{index:02d}_{slug}.feature"
            feature_path.write_text(content + "\n", encoding="utf-8")

            glue_path = test_dir / f"test_{feature_path.stem}.py"
            glue_path.write_text(_build_glue_file_content(feature_path.as_posix()), encoding="utf-8")

            glue_paths.append(str(glue_path))
            saved_features.append(str(feature_path.relative_to(settings.BASE_DIR)))

        if not glue_paths:
            return jsonify({"ok": False, "error": "Calistirilabilir feature olusturulamadi"}), 400

        env = os.environ.copy()
        env["BROWSER"] = browser
        env["BASE_URL"] = url or env.get("BASE_URL", settings.BASE_URL)
        env["TEST_DOMAIN"] = domain
        env["TEST_ENV"] = safe_env
        env["HEADLESS"] = env.get("HEADLESS", "true")

        cmd = [
            sys.executable, "-m", "pytest",
            *glue_paths,
            "--alluredir", str(settings.ALLURE_RESULTS_DIR),
            "--tb=short", "-q",
            "--import-mode=importlib",
        ]

        start = time.time()
        proc = subprocess.run(
            cmd,
            cwd=str(settings.BASE_DIR),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
        duration_ms = int((time.time() - start) * 1000)
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()

        passed = 0
        failed = 0
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        if passed_match:
            passed = int(passed_match.group(1))
        if failed_match:
            failed = int(failed_match.group(1))

        return jsonify({
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": output[-8000:] if output else "",
            "passed": passed,
            "failed": failed,
            "duration_ms": duration_ms,
            "domain": domain,
            "env": safe_env,
            "saved_features": saved_features,
            "locator_file": str(locator_file.relative_to(settings.BASE_DIR)),
            "data_file": str(data_file.relative_to(settings.BASE_DIR)),
            "allure_report_url": "/reports/allure-report/",
        })
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "NexusQA koşusu zaman aşımına uğradı (>180s)", "exit_code": -1}), 504
    except Exception as exc:
        logger.exception("Wizard run-nexusqa failed")
        return jsonify({"ok": False, "error": str(exc), "trace": traceback.format_exc()}), 500
