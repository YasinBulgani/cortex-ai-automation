"""Katman 2 — Element Extraction."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Iterable

from ...schemas.locator import ElementCard

logger = logging.getLogger(__name__)


EXTRACTION_JS = r"""
() => {
  const SELECTORS = [
    'button', 'a[href]', 'input:not([type=hidden])',
    'select', 'textarea',
    '[role="button"]', '[role="link"]', '[role="textbox"]',
    '[role="checkbox"]', '[role="radio"]', '[role="tab"]',
    '[role="menuitem"]', '[role="option"]',
    '[onclick]', '[data-testid]', '[data-test]', '[data-qa]', '[data-cy]'
  ];
  const HASH_CLASS_RE = /^(css-[a-z0-9]+|jsx-[a-z0-9]+|_[a-zA-Z0-9]{5,}|sc-[a-z0-9]+|emotion-[a-z0-9]+)$/;

  function stableClasses(el) {
    return [...el.classList].filter(c => !HASH_CLASS_RE.test(c));
  }
  function visibleText(el) {
    const txt = (el.innerText || el.value || el.textContent || '').trim();
    return txt.length > 200 ? txt.slice(0, 200) : txt;
  }
  function xpathOf(el) {
    if (el.id && !/^[0-9]/.test(el.id)) return `//*[@id="${el.id}"]`;
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1) {
      let idx = 1;
      let sib = cur.previousElementSibling;
      while (sib) { if (sib.tagName === cur.tagName) idx++; sib = sib.previousElementSibling; }
      parts.unshift(`${cur.tagName.toLowerCase()}[${idx}]`);
      cur = cur.parentElement;
    }
    return '/' + parts.join('/');
  }
  function parentContext(el) {
    const container = el.closest('form, [role="dialog"], [role="main"], section, article, nav, header, footer');
    if (!container) return null;
    const id = container.id;
    const label = container.getAttribute('aria-label');
    const name = container.getAttribute('name');
    if (id) return `${container.tagName.toLowerCase()}#${id}`;
    if (label) return `${container.tagName.toLowerCase()}[aria-label="${label}"]`;
    if (name) return `${container.tagName.toLowerCase()}[name="${name}"]`;
    return container.tagName.toLowerCase();
  }
  function fingerprintOf(el, role, ariaLabel, text, testid, parent) {
    const parts = [
      el.tagName.toLowerCase(), testid || '', role || '',
      ariaLabel || '', (text || '').slice(0, 40), parent || '',
    ].join('|');
    let h = 0;
    for (let i = 0; i < parts.length; i++) {
      h = ((h << 5) - h) + parts.charCodeAt(i);
      h |= 0;
    }
    return 'el_' + (h >>> 0).toString(16);
  }

  const nodes = [...document.querySelectorAll(SELECTORS.join(','))];
  const seen = new WeakSet();
  const out = [];

  nodes.forEach((el, i) => {
    if (seen.has(el)) return;
    seen.add(el);
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    const style = window.getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') return;

    const ariaLabel = el.getAttribute('aria-label');
    const role = el.getAttribute('role') || el.tagName.toLowerCase();
    const text = visibleText(el);
    const testid = el.getAttribute('data-testid') || el.getAttribute('data-test')
                || el.getAttribute('data-qa') || el.getAttribute('data-cy');
    const parent = parentContext(el);
    const fp = fingerprintOf(el, role, ariaLabel, text, testid, parent);

    out.push({
      idx: i,
      tag: el.tagName.toLowerCase(),
      visible_text: text,
      role: role,
      aria_label: ariaLabel,
      placeholder: el.getAttribute('placeholder'),
      title: el.getAttribute('title'),
      testid: testid,
      element_id: el.id || null,
      class_list: stableClasses(el),
      href: el.href || null,
      type: el.type || null,
      name: el.name || null,
      value: (el.value && typeof el.value === 'string') ? el.value.slice(0, 100) : null,
      required: !!el.required,
      disabled: !!el.disabled,
      bbox: [r.x, r.y, r.width, r.height],
      parent_context: parent,
      xpath_raw: xpathOf(el),
      fingerprint: fp,
    });
  });

  return out;
}
"""


async def extract_elements(page) -> list[ElementCard]:
    try:
        raw = await page.evaluate(EXTRACTION_JS)
    except Exception as exc:
        logger.error("Extraction JS: %s", exc)
        return []
    cards: list[ElementCard] = []
    for row in raw or []:
        try:
            bbox = row.get("bbox")
            if bbox and isinstance(bbox, list) and len(bbox) == 4:
                row["bbox"] = tuple(bbox)
            cards.append(ElementCard(**row))
        except Exception as exc:
            logger.debug("Card parse skip: %s", exc)
    return cards


_HASH_CLASS_RE = re.compile(
    r"^(css-[a-z0-9]+|jsx-[a-z0-9]+|_[a-zA-Z0-9]{5,}|sc-[a-z0-9]+|emotion-[a-z0-9]+)$"
)


def _stable_classes(cls_attr: str | None) -> list[str]:
    if not cls_attr:
        return []
    return [c for c in cls_attr.split() if c and not _HASH_CLASS_RE.match(c)]


def _fingerprint_for(
    tag: str, testid: str | None, role: str | None,
    aria: str | None, text: str | None, parent: str | None,
) -> str:
    key = "|".join([tag or "", testid or "", role or "", aria or "", (text or "")[:40], parent or ""])
    h = hashlib.md5(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]  # nosec B324
    return f"el_{h}"


def extract_from_html(html: str) -> list[ElementCard]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("bs4 yok")
        return []

    soup = BeautifulSoup(html, "html.parser")
    selectors = [
        "button", "a[href]", "input:not([type=hidden])",
        "select", "textarea",
        "[role]", "[onclick]", "[data-testid]", "[data-test]", "[data-qa]",
    ]
    found: list = []
    for sel in selectors:
        try:
            found.extend(soup.select(sel))
        except Exception:
            continue

    cards: list[ElementCard] = []
    seen_ids = set()
    for i, el in enumerate(found):
        try:
            tag = el.name
            testid = (
                el.get("data-testid") or el.get("data-test")
                or el.get("data-qa") or el.get("data-cy")
            )
            role = el.get("role") or tag
            aria_label = el.get("aria-label")
            text = (el.get_text(strip=True) or el.get("value", ""))[:200]
            cls_list = _stable_classes(" ".join(el.get("class", [])))

            parent = None
            for parent_tag_name in ("form", "dialog", "section", "nav", "main", "article"):
                parent_tag = el.find_parent(parent_tag_name)
                if parent_tag:
                    pid = parent_tag.get("id")
                    plabel = parent_tag.get("aria-label")
                    if pid:
                        parent = f"{parent_tag_name}#{pid}"
                    elif plabel:
                        parent = f'{parent_tag_name}[aria-label="{plabel}"]'
                    else:
                        parent = parent_tag_name
                    break

            fp = _fingerprint_for(tag, testid, role, aria_label, text, parent)
            if fp in seen_ids:
                continue
            seen_ids.add(fp)

            cards.append(ElementCard(
                idx=i,
                tag=tag,
                visible_text=text,
                role=role,
                aria_label=aria_label,
                placeholder=el.get("placeholder"),
                title=el.get("title"),
                testid=testid,
                element_id=el.get("id"),
                class_list=cls_list,
                href=el.get("href"),
                type=el.get("type"),
                name=el.get("name"),
                value=el.get("value"),
                required=el.get("required") is not None,
                disabled=el.get("disabled") is not None,
                parent_context=parent,
                xpath_raw="",
                fingerprint=fp,
            ))
        except Exception as exc:
            logger.debug("HTML skip: %s", exc)
    return cards
