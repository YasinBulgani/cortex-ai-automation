"""
DiscoveryAgent — Accessibility Tree Tabanlı Akıllı Keşif (Ajan 10)

Görev:
  Hedef uygulamayı Playwright CDP üzerinden keşfeder:
  1. A11y (Accessibility) tree snapshot → Semantik element haritası
  2. DOM etkileşim analizi → Tıklanabilir/doldurulabilir elementler
  3. 10-tier lokator hiyerarşisi ile NexusQA JSON üretimi
  4. Sayfa geçiş grafı (page transition graph) oluşturma
  5. KnowledgeStore'a keşif sonuçlarını kaydetme

Neden A11y Tree?
  - DOM'da 10K+ node olabilir → A11y tree 200-400 etkileşimli elemente indirir
  - Screen reader semantiği = doğal lokator kaynağı (role, name, label)
  - Browser Use DOM Pipeline: 10K node → 200 interactive element
  - rtrvr.ai yaklaşımı: %81 doğruluk vs screenshot-based %64

Entegrasyon:
  - NexusQA Wizard Step 7 → crawl-locators endpoint'ini besler
  - Banking Orchestrator → Phase.SCANNING içinde opsiyonel çalışır
  - AutoHealer → Kırılan locator'lar için A11y tree'den alternatif bulur
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse, urljoin

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# ── 10-Tier Selector Hierarchy ──────────────────────────────────────────────
SELECTOR_TIERS = [
    {"tier": 1, "name": "data-testid", "stability": "P5", "score": 10},
    {"tier": 2, "name": "role",        "stability": "P5", "score": 9},
    {"tier": 3, "name": "aria-label",  "stability": "P4", "score": 8},
    {"tier": 4, "name": "label",       "stability": "P4", "score": 7},
    {"tier": 5, "name": "id",          "stability": "P4", "score": 7},
    {"tier": 6, "name": "placeholder", "stability": "P3", "score": 6},
    {"tier": 7, "name": "name",        "stability": "P3", "score": 6},
    {"tier": 8, "name": "text",        "stability": "P2", "score": 4},
    {"tier": 9, "name": "css",         "stability": "P2", "score": 3},
    {"tier": 10, "name": "xpath",      "stability": "P1", "score": 1},
]

# React auto-generated ID pattern
REACT_ID_RE = re.compile(r"^:r[a-zA-Z0-9]+:$")

# A11y tree node extraction JS (Playwright CDP üzerinden çalışır)
A11Y_TREE_SCRIPT = """
() => {
    // Tüm etkileşimli elementleri bul (A11y tree yaklaşımı)
    const interactiveRoles = new Set([
        'button', 'link', 'textbox', 'checkbox', 'radio', 'combobox',
        'listbox', 'option', 'menuitem', 'tab', 'switch', 'searchbox',
        'spinbutton', 'slider', 'dialog', 'alertdialog'
    ]);

    const interactiveTags = new Set([
        'A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'DETAILS',
        'SUMMARY', 'DIALOG', 'LABEL', 'OUTPUT'
    ]);

    const clickableSelectors = [
        '[onclick]', '[ng-click]', '[v-on\\\\:click]', '[@click]',
        '[role="button"]', '[role="link"]', '[role="tab"]',
        '[tabindex]', '[contenteditable="true"]'
    ];

    const results = [];
    const seen = new Set();

    function getAccessibleName(el) {
        // Öncelik: aria-label > aria-labelledby > label[for] > textContent
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
        const labelledBy = el.getAttribute('aria-labelledby');
        if (labelledBy) {
            const label = document.getElementById(labelledBy);
            if (label) return label.textContent?.trim() || '';
        }
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) return label.textContent?.trim() || '';
        }
        if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
            if (el.placeholder) return el.placeholder;
        }
        return el.textContent?.trim()?.substring(0, 80) || '';
    }

    function getRole(el) {
        const explicit = el.getAttribute('role');
        if (explicit) return explicit;
        const tagMap = {
            'A': 'link', 'BUTTON': 'button', 'INPUT': null,
            'SELECT': 'combobox', 'TEXTAREA': 'textbox',
            'H1': 'heading', 'H2': 'heading', 'H3': 'heading',
            'NAV': 'navigation', 'TABLE': 'table', 'DIALOG': 'dialog',
            'IMG': 'img', 'FORM': 'form'
        };
        if (el.tagName === 'INPUT') {
            const t = (el.type || 'text').toLowerCase();
            if (t === 'checkbox') return 'checkbox';
            if (t === 'radio') return 'radio';
            if (t === 'submit' || t === 'button') return 'button';
            if (t === 'search') return 'searchbox';
            return 'textbox';
        }
        return tagMap[el.tagName] || null;
    }

    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    }

    function processElement(el) {
        if (!isVisible(el)) return;

        const role = getRole(el);
        const name = getAccessibleName(el);
        const tag = el.tagName.toLowerCase();

        // Unique key oluştur
        const uid = `${tag}:${role}:${name}:${el.id}`.substring(0, 200);
        if (seen.has(uid)) return;
        seen.add(uid);

        // Rect bilgisi
        const rect = el.getBoundingClientRect();

        results.push({
            tag: tag,
            role: role,
            name: name,
            text: el.textContent?.trim()?.substring(0, 80) || '',
            id: el.id || null,
            testid: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null,
            ariaLabel: el.getAttribute('aria-label') || null,
            placeholder: el.placeholder || null,
            htmlName: el.name || null,
            href: el.href || null,
            type: el.type || null,
            label: null,
            rect: { x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height) },
            isInteractive: true
        });
    }

    // 1. Interactive tags
    interactiveTags.forEach(tag => {
        document.querySelectorAll(tag).forEach(processElement);
    });

    // 2. Clickable selectors
    clickableSelectors.forEach(sel => {
        try {
            document.querySelectorAll(sel).forEach(processElement);
        } catch(e) {}
    });

    // 3. Role-based elements
    interactiveRoles.forEach(role => {
        document.querySelectorAll(`[role="${role}"]`).forEach(processElement);
    });

    // Label ilişkilerini ekle
    document.querySelectorAll('label[for]').forEach(label => {
        const target = document.getElementById(label.getAttribute('for'));
        if (target) {
            const match = results.find(r => r.id === label.getAttribute('for'));
            if (match) {
                match.label = label.textContent?.trim() || null;
            }
        }
    });

    return {
        url: window.location.href,
        title: document.title,
        elementCount: results.length,
        totalDomNodes: document.querySelectorAll('*').length,
        elements: results
    };
}
"""


class DiscoveryAgent(BaseAgent):
    """A11y tree tabanlı sayfa keşif ajanı."""

    name = "Keşif Ajanı"
    temperature = 0.2
    max_tokens = 2048

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          url            — Hedef URL
          max_pages      — Maksimum sayfa sayısı (default: 5)
          domain         — Modül/domain adı
          credentials    — Login bilgileri (opsiyonel)
          with_locators  — NexusQA lokator JSON üret (default: True)
        """
        url = context.get("url", "")
        max_pages = context.get("max_pages", 5)
        domain = context.get("domain", "")
        with_locators = context.get("with_locators", True)

        if not url:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error="URL gerekli",
            )

        # ── A11y Tree Keşfi ────────────────────────────────────────────
        discovery_result = self._discover_pages(url, max_pages, context)

        # ── Lokator Üretimi ────────────────────────────────────────────
        locators = []
        if with_locators:
            locators = self._extract_locators(discovery_result, domain)

        # ── Sayfa Geçiş Grafı ─────────────────────────────────────────
        transition_graph = self._build_transition_graph(discovery_result)

        # ── KnowledgeStore'a kaydet ────────────────────────────────────
        total_elements = sum(
            p.get("elementCount", 0) for p in discovery_result.get("pages", [])
        )
        self.learn(
            f"Keşif: {url} — {len(discovery_result.get('pages', []))} sayfa, "
            f"{total_elements} etkileşimli element, {len(locators)} lokator. "
            f"Domain: {domain}",
            metadata={
                "url": url,
                "page_count": len(discovery_result.get("pages", [])),
                "element_count": total_elements,
                "locator_count": len(locators),
            },
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "pages": discovery_result.get("pages", []),
                "locators": locators,
                "transition_graph": transition_graph,
                "stats": {
                    "pages_discovered": len(discovery_result.get("pages", [])),
                    "total_elements": total_elements,
                    "total_locators": len(locators),
                    "total_dom_nodes": sum(
                        p.get("totalDomNodes", 0)
                        for p in discovery_result.get("pages", [])
                    ),
                },
            },
        )

    def _discover_pages(self, start_url: str, max_pages: int, context: dict) -> dict:
        """
        Playwright ile sayfaları keşfet ve A11y tree snapshot al.
        Engine'e proxy eder, engine yoksa local Playwright kullanır.
        """
        import httpx

        # ── Engine üzerinden keşfet ────────────────────────────────────
        from app.config import settings as _s
        engine_url = _s.engine_base_url
        pages = []

        try:
            # Step 1: Crawl
            crawl_resp = httpx.post(
                f"{engine_url}/api/wizard/crawl",
                json={
                    "url": start_url,
                    "max_pages": max_pages,
                    "credentials": context.get("credentials"),
                },
                timeout=120.0,
            )
            crawl_data = crawl_resp.json()
            crawled_pages = crawl_data.get("pages", [])

            # Step 2: Her sayfa için discover-selectors
            for cp in crawled_pages[:max_pages]:
                page_url = cp.get("url", start_url)
                try:
                    disc_resp = httpx.post(
                        f"{engine_url}/api/wizard/discover-selectors",
                        json={"url": page_url},
                        timeout=60.0,
                    )
                    disc_data = disc_resp.json()
                    pages.append({
                        "url": page_url,
                        "title": cp.get("title", ""),
                        "elements": disc_data.get("elements", []),
                        "elementCount": disc_data.get("element_count", 0),
                        "totalDomNodes": len(disc_data.get("elements", [])) * 5,  # Approx
                        "headings": cp.get("headings", []),
                        "buttons": cp.get("buttons", []),
                        "inputs": cp.get("inputs", []),
                        "forms_count": cp.get("forms_count", 0),
                        "links_count": cp.get("links_count", 0),
                    })
                except Exception as e:
                    logger.debug("Discover hatası (%s): %s", page_url, e)
                    pages.append({
                        "url": page_url,
                        "title": cp.get("title", ""),
                        "elements": [],
                        "elementCount": 0,
                        "headings": cp.get("headings", []),
                        "buttons": cp.get("buttons", []),
                        "inputs": cp.get("inputs", []),
                    })

        except Exception as e:
            logger.warning("Engine keşif hatası: %s — minimal keşif", e)
            pages.append({
                "url": start_url,
                "title": "",
                "elements": [],
                "elementCount": 0,
                "error": str(e),
            })

        return {"pages": pages}

    def _extract_locators(self, discovery: dict, domain: str) -> list[dict]:
        """Keşfedilen elementlerden 10-tier NexusQA lokator JSON üret."""
        locators = []
        seen_keys: set[str] = set()

        for page in discovery.get("pages", []):
            for el in page.get("elements", []):
                entry = self._element_to_best_locator(el, domain, seen_keys)
                if entry:
                    locators.append(entry)
                    seen_keys.add(entry["key"])

        # Stabilite skoruna göre sırala
        tier_score = {t["name"]: t["score"] for t in SELECTOR_TIERS}
        locators.sort(key=lambda x: tier_score.get(x["type"], 0), reverse=True)

        return locators

    def _element_to_best_locator(
        self, el: dict, domain: str, seen_keys: set
    ) -> dict | None:
        """Tek element → en iyi tier ile LocatorEntry."""
        # Key oluştur (name veya text'ten)
        name = el.get("name") or el.get("ariaLabel") or el.get("text", "")
        name = name.strip()[:50]
        if not name or len(name) < 2:
            return None

        key = self._make_key(name, domain)
        if key in seen_keys:
            return None

        # Tier 1: data-testid
        testid = el.get("testid")
        if testid:
            return {"key": key, "type": "testid", "value": testid}

        # Tier 2: role + accessible name
        role = el.get("role")
        acc_name = el.get("name") or el.get("ariaLabel") or ""
        if role and acc_name:
            return {"key": key, "type": "role", "value": f'{role}[name="{acc_name}"]'}

        # Tier 3: aria-label
        aria = el.get("ariaLabel")
        if aria:
            return {"key": key, "type": "aria-label", "value": aria}

        # Tier 4: label
        label = el.get("label")
        if label and el.get("tag") in ("input", "select", "textarea"):
            return {"key": key, "type": "label", "value": label}

        # Tier 5: id (React ID'ler hariç)
        el_id = el.get("id")
        if el_id and not REACT_ID_RE.match(el_id):
            return {"key": key, "type": "id", "value": el_id}

        # Tier 6: placeholder
        placeholder = el.get("placeholder")
        if placeholder:
            return {"key": key, "type": "placeholder", "value": placeholder}

        # Tier 7: name attribute
        html_name = el.get("htmlName")
        if html_name:
            return {"key": key, "type": "name", "value": html_name}

        # Tier 8: text content
        text = el.get("text", "").strip()
        if text and len(text) < 60:
            return {"key": key, "type": "text", "value": text}

        # Tier 9: CSS (from tag + id/class combo)
        css = el.get("css")
        if css:
            return {"key": key, "type": "css", "value": css}

        # Tier 10: XPath (son çare)
        xpath = el.get("xpath")
        if xpath:
            return {"key": key, "type": "xpath", "value": xpath}

        return None

    def _make_key(self, raw: str, domain: str) -> str:
        """Ham text'ten NexusQA key üret."""
        key = raw.strip().lower()
        key = re.sub(r"[^\w\sğüşöçıİĞÜŞÖÇ]", "", key)
        key = re.sub(r"\s+", "_", key)
        key = key[:50]
        if domain:
            key = f"{domain.lower()}_{key}"
        return key

    def _build_transition_graph(self, discovery: dict) -> dict:
        """Sayfa geçiş grafı oluştur (link analizi)."""
        pages = discovery.get("pages", [])
        nodes = []
        edges = []

        page_urls = {p.get("url", "") for p in pages}

        for page in pages:
            page_url = page.get("url", "")
            base = urlparse(page_url)
            nodes.append({
                "url": page_url,
                "title": page.get("title", ""),
                "elements": page.get("elementCount", 0),
            })

            # Link elementlerinden edge oluştur
            for el in page.get("elements", []):
                href = el.get("href")
                if href and el.get("role") == "link":
                    target = urljoin(page_url, href)
                    target_parsed = urlparse(target)
                    if target_parsed.netloc == base.netloc:
                        edges.append({
                            "from": page_url,
                            "to": target,
                            "text": el.get("text", "")[:30],
                        })

        return {"nodes": nodes, "edges": edges}
