"""Katman 3 — Multi-Strategy Locator Generation."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from ...schemas.locator import ElementCard, LocatorCandidate, LocatorStrategy

logger = logging.getLogger(__name__)


def escape_css(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\A ")


def escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def escape_regex(value: str) -> str:
    return re.sub(r"[.*+?^${}()|[\]\\]", r"\\\g<0>", value).replace("/", r"\/")


def strategy_testid(el: ElementCard) -> LocatorCandidate | None:
    if not el.testid:
        return None
    return LocatorCandidate(
        strategy=LocatorStrategy.TESTID,
        selector=f'[data-testid="{escape_css(el.testid)}"]',
        playwright_expr=f'page.getByTestId("{escape_text(el.testid)}")',
        semantic_strength=1.0,
    )


def strategy_role_name(el: ElementCard) -> LocatorCandidate | None:
    name = (el.aria_label or el.visible_text or el.placeholder or "").strip()
    if not name or len(name) > 80:
        return None
    role = el.role or el.tag
    role_normalized = _normalize_role(role, el.tag)
    if not role_normalized:
        return None
    return LocatorCandidate(
        strategy=LocatorStrategy.ROLE_NAME,
        selector=f'role={role_normalized}[name="{escape_css(name)}"]',
        playwright_expr=f'page.getByRole("{role_normalized}", {{ name: /{escape_regex(name)}/i }})',
        semantic_strength=0.9,
    )


def strategy_text(el: ElementCard) -> LocatorCandidate | None:
    text = (el.visible_text or "").strip()
    if not text or len(text) > 60 or len(text) < 2:
        return None
    return LocatorCandidate(
        strategy=LocatorStrategy.TEXT,
        selector=f'text="{escape_css(text)}"',
        playwright_expr=f'page.getByText("{escape_text(text)}", {{ exact: false }})',
        semantic_strength=0.75,
    )


def strategy_css_semantic(el: ElementCard) -> LocatorCandidate | None:
    if not el.class_list:
        return None
    classes = el.class_list[:2]
    if not classes:
        return None
    parent_part = f"{el.parent_context} " if el.parent_context else ""
    css = f"{parent_part}{el.tag}.{'.'.join(classes)}"
    attrs_parts: list[str] = []
    if el.type:
        attrs_parts.append(f'[type="{escape_css(el.type)}"]')
    if el.name:
        attrs_parts.append(f'[name="{escape_css(el.name)}"]')
    if attrs_parts:
        css = f"{css}{''.join(attrs_parts)}"
    return LocatorCandidate(
        strategy=LocatorStrategy.CSS_SEMANTIC,
        selector=css,
        playwright_expr=f'page.locator("{escape_text(css)}")',
        semantic_strength=0.6,
    )


def strategy_id_fallback(el: ElementCard) -> LocatorCandidate | None:
    if not el.element_id:
        return None
    if re.match(r"^[a-zA-Z]+-?[0-9a-f]{8,}$", el.element_id):
        return None
    return LocatorCandidate(
        strategy=LocatorStrategy.CSS_SEMANTIC,
        selector=f'#{el.element_id}',
        playwright_expr=f'page.locator("#{escape_text(el.element_id)}")',
        semantic_strength=0.7,
    )


_TAG_TO_ROLE = {
    "a": "link", "button": "button", "input": None,
    "select": "combobox", "textarea": "textbox", "img": "img",
    "h1": "heading", "h2": "heading", "h3": "heading",
    "h4": "heading", "h5": "heading", "h6": "heading",
    "nav": "navigation", "main": "main", "form": "form",
}

_VALID_PLAYWRIGHT_ROLES = {
    "alert", "alertdialog", "application", "article", "banner", "blockquote",
    "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox",
    "complementary", "contentinfo", "definition", "deletion", "dialog", "directory",
    "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell",
    "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem",
    "log", "main", "marquee", "math", "meter", "menu", "menubar", "menuitem",
    "menuitemcheckbox", "menuitemradio", "navigation", "none", "note", "option",
    "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region",
    "row", "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator",
    "slider", "spinbutton", "status", "strong", "subscript", "superscript", "switch",
    "tab", "table", "tablist", "tabpanel", "term", "textbox", "time", "timer",
    "toolbar", "tooltip", "tree", "treegrid", "treeitem",
}


def _normalize_role(role: str, tag: str) -> str | None:
    if not role:
        return None
    r = role.lower().strip()
    if r in _VALID_PLAYWRIGHT_ROLES:
        return r
    fb = _TAG_TO_ROLE.get(tag.lower())
    if fb:
        return fb
    if tag.lower() == "input":
        return "textbox"
    return None


async def generate_locators_for_element(
    element: ElementCard,
    *,
    enable_ai_xpath: bool = False,
    ai_xpath_func=None,
    screenshot: bytes | None = None,
) -> list[LocatorCandidate]:
    candidates: list[LocatorCandidate] = []

    for strat_func in (strategy_testid, strategy_role_name, strategy_text,
                        strategy_id_fallback, strategy_css_semantic):
        try:
            c = strat_func(element)
            if c:
                candidates.append(c)
        except Exception as exc:
            logger.debug("Strategy %s skip: %s", strat_func.__name__, exc)

    if enable_ai_xpath and ai_xpath_func and not any(
        c.strategy == LocatorStrategy.TESTID and c.semantic_strength >= 0.95
        for c in candidates
    ):
        try:
            xpath = await ai_xpath_func(element, screenshot)
            if xpath:
                candidates.append(LocatorCandidate(
                    strategy=LocatorStrategy.XPATH_AI,
                    selector=f"xpath={xpath}",
                    playwright_expr=f'page.locator("xpath={escape_text(xpath)}")',
                    semantic_strength=0.5,
                ))
        except Exception as exc:
            logger.warning("AI XPath: %s", exc)

    return candidates


async def generate_locators_batch(
    elements: list[ElementCard],
    *,
    enable_ai_xpath: bool = False,
    ai_xpath_func=None,
    max_concurrency: int = 10,
) -> dict[str, list[LocatorCandidate]]:
    sem = asyncio.Semaphore(max_concurrency)

    async def _one(el: ElementCard) -> tuple[str, list[LocatorCandidate]]:
        async with sem:
            cs = await generate_locators_for_element(
                el, enable_ai_xpath=enable_ai_xpath, ai_xpath_func=ai_xpath_func
            )
            return (el.fingerprint, cs)

    results = await asyncio.gather(*(_one(el) for el in elements))
    return {fp: cs for fp, cs in results}
