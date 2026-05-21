"""Playwright MCP — DOM analysis utilities."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def compute_selector_stability(selector_str: str) -> int:
    """
    Rate a selector's stability from 0 (worst) to 5 (best).

    5 = data-testid, role-based
    4 = aria-label, label, id
    3 = placeholder, name
    2 = text-based, simple CSS
    1 = xpath, complex CSS
    0 = unknown / empty
    """
    if not selector_str or not selector_str.strip():
        return 0

    s = selector_str.strip()

    # Tier 5: data-testid or role selectors
    if "data-testid" in s or "data-test-id" in s:
        return 5
    if re.search(r'\brole\s*=', s):
        return 5

    # Tier 4: aria-label, label, id-based
    if "aria-label" in s:
        return 4
    if s.startswith("label=") or s.startswith("label:"):
        return 4
    if re.match(r'^#[\w-]+$', s):
        return 4

    # Tier 3: placeholder, name
    if "placeholder" in s:
        return 3
    if re.search(r'\[name\s*=', s):
        return 3

    # Tier 2: text-based, simple tag/class
    if s.startswith("text=") or s.startswith('"') or s.startswith("'"):
        return 2
    if re.match(r'^[\w-]+$', s):
        return 2  # simple tag name
    if re.match(r'^\.[\w-]+$', s):
        return 2  # single class

    # Tier 1: xpath or complex selectors
    if s.startswith("//") or s.startswith("xpath="):
        return 1
    if s.count(">") > 2 or s.count(" ") > 3:
        return 1  # deeply nested CSS

    # Default: simple CSS
    return 2


async def analyze_element(page: Any, selector: str) -> dict[str, Any]:
    """Get detailed element info: tag, attributes, computed styles, text."""
    js = """
    (selector) => {
        const el = document.querySelector(selector);
        if (!el) return null;
        const style = window.getComputedStyle(el);
        const attrs = {};
        for (const attr of el.attributes) {
            attrs[attr.name] = attr.value;
        }
        const rect = el.getBoundingClientRect();
        return {
            tag: el.tagName.toLowerCase(),
            attributes: attrs,
            text: (el.textContent || '').trim().substring(0, 500),
            inner_html: el.innerHTML.substring(0, 1000),
            computed_styles: {
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                position: style.position,
                color: style.color,
                backgroundColor: style.backgroundColor,
                fontSize: style.fontSize
            },
            bounding_box: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            },
            is_visible: rect.width > 0 && rect.height > 0
                && style.display !== 'none'
                && style.visibility !== 'hidden',
            child_count: el.children.length,
            parent_tag: el.parentElement ? el.parentElement.tagName.toLowerCase() : null
        };
    }
    """
    result = await page.evaluate(js, selector)
    if result is None:
        return {"found": False, "selector": selector}
    result["found"] = True
    result["selector"] = selector
    return result


async def find_similar_elements(page: Any, broken_selector: str) -> list[dict[str, Any]]:
    """
    Find elements that are similar to what a broken selector might have pointed to.
    Analyses the selector to extract hints (tag, id fragments, class names, text).
    """
    # Parse the broken selector for hints
    hints: dict[str, str | None] = {
        "tag": None,
        "id_fragment": None,
        "class_fragment": None,
        "text_hint": None,
        "attr_name": None,
        "attr_value": None,
    }

    s = broken_selector.strip()

    # Extract tag
    tag_match = re.match(r'^(\w+)', s)
    if tag_match and tag_match.group(1) not in ("text", "xpath", "role", "label"):
        hints["tag"] = tag_match.group(1)

    # Extract id
    id_match = re.search(r'#([\w-]+)', s)
    if id_match:
        hints["id_fragment"] = id_match.group(1)

    # Extract class
    class_match = re.search(r'\.([\w-]+)', s)
    if class_match:
        hints["class_fragment"] = class_match.group(1)

    # Extract attribute value
    attr_match = re.search(r'\[(\w[\w-]*)=["\']?([^"\'\]]+)', s)
    if attr_match:
        hints["attr_name"] = attr_match.group(1)
        hints["attr_value"] = attr_match.group(2)

    # Extract text
    text_match = re.search(r'text=["\']?([^"\']+)', s)
    if text_match:
        hints["text_hint"] = text_match.group(1)

    js = """
    (hints) => {
        const results = [];
        const allElements = document.querySelectorAll('*');
        const maxResults = 10;

        for (const el of allElements) {
            if (results.length >= maxResults) break;
            let score = 0;

            // Tag match
            if (hints.tag && el.tagName.toLowerCase() === hints.tag.toLowerCase()) {
                score += 1;
            }

            // ID partial match
            if (hints.id_fragment && el.id && el.id.includes(hints.id_fragment)) {
                score += 3;
            }

            // Class partial match
            if (hints.class_fragment) {
                for (const cls of el.classList) {
                    if (cls.includes(hints.class_fragment)) {
                        score += 2;
                        break;
                    }
                }
            }

            // Attribute match
            if (hints.attr_name && hints.attr_value) {
                const attrVal = el.getAttribute(hints.attr_name);
                if (attrVal && attrVal.includes(hints.attr_value)) {
                    score += 3;
                }
            }

            // Text match
            if (hints.text_hint) {
                const text = (el.textContent || '').trim();
                if (text.toLowerCase().includes(hints.text_hint.toLowerCase())) {
                    score += 2;
                }
            }

            if (score >= 2) {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                const rect = el.getBoundingClientRect();
                results.push({
                    tag: el.tagName.toLowerCase(),
                    attributes: attrs,
                    text: (el.textContent || '').trim().substring(0, 200),
                    bounding_box: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    score: score
                });
            }
        }

        results.sort((a, b) => b.score - a.score);
        return results;
    }
    """
    try:
        return await page.evaluate(js, hints)
    except Exception as exc:
        logger.warning("find_similar_elements hatasi: %s", exc)
        return []


async def suggest_stable_selectors_for_handle(
    page: Any, element_handle: Any
) -> list[str]:
    """Generate stable selector alternatives for an element handle."""
    js = """
    (el) => {
        const suggestions = [];

        // data-testid (best)
        const testid = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
        if (testid) {
            suggestions.push('[data-testid="' + testid + '"]');
        }

        // role + name
        const role = el.getAttribute('role');
        const ariaLabel = el.getAttribute('aria-label');
        if (role && ariaLabel) {
            suggestions.push(el.tagName.toLowerCase() + '[role="' + role + '"][aria-label="' + ariaLabel + '"]');
        } else if (role) {
            suggestions.push(el.tagName.toLowerCase() + '[role="' + role + '"]');
        }

        // aria-label only
        if (ariaLabel) {
            suggestions.push('[aria-label="' + ariaLabel + '"]');
        }

        // id
        if (el.id) {
            suggestions.push('#' + el.id);
        }

        // name attribute
        const name = el.getAttribute('name');
        if (name) {
            suggestions.push(el.tagName.toLowerCase() + '[name="' + name + '"]');
        }

        // placeholder
        const placeholder = el.getAttribute('placeholder');
        if (placeholder) {
            suggestions.push('[placeholder="' + placeholder + '"]');
        }

        // text content (short)
        const text = (el.textContent || '').trim();
        if (text && text.length < 50 && text.length > 0) {
            suggestions.push('text="' + text + '"');
        }

        return suggestions;
    }
    """
    try:
        return await element_handle.evaluate(js)
    except Exception as exc:
        logger.debug("suggest_stable_selectors hata: %s", exc)
        return []


async def suggest_stable_selectors(page: Any, selector: str) -> list[str]:
    """Generate stable selector alternatives for an element found by selector."""
    element = await page.query_selector(selector)
    if element is None:
        return []
    return await suggest_stable_selectors_for_handle(page, element)


def diff_dom_snapshots(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    """
    Compare two DOM snapshots (DOMNode dicts) and find changes.
    Returns a summary of added, removed, and changed nodes.
    """

    def _flatten(node: dict[str, Any] | None, path: str = "") -> dict[str, dict[str, Any]]:
        if node is None:
            return {}
        result: dict[str, dict[str, Any]] = {}
        tag = node.get("tag", "unknown")
        node_id = node.get("attributes", {}).get("id", "")
        testid = node.get("attributes", {}).get("data-testid", "")
        key = f"{path}/{tag}"
        if node_id:
            key += f"#{node_id}"
        elif testid:
            key += f"[{testid}]"

        result[key] = {
            "tag": tag,
            "text": node.get("text"),
            "attributes": node.get("attributes", {}),
        }
        for i, child in enumerate(node.get("children", [])):
            child_path = f"{key}[{i}]"
            result.update(_flatten(child, child_path))
        return result

    before_root = before.get("root") if isinstance(before, dict) else None
    after_root = after.get("root") if isinstance(after, dict) else None

    flat_before = _flatten(before_root)
    flat_after = _flatten(after_root)

    before_keys = set(flat_before.keys())
    after_keys = set(flat_after.keys())

    added = after_keys - before_keys
    removed = before_keys - after_keys
    common = before_keys & after_keys

    changed: list[dict[str, Any]] = []
    for key in common:
        b = flat_before[key]
        a = flat_after[key]
        diffs: dict[str, Any] = {}
        if b.get("text") != a.get("text"):
            diffs["text"] = {"before": b.get("text"), "after": a.get("text")}
        if b.get("attributes") != a.get("attributes"):
            diffs["attributes"] = {
                "before": b.get("attributes"),
                "after": a.get("attributes"),
            }
        if diffs:
            changed.append({"path": key, "changes": diffs})

    return {
        "added": [{"path": k, **flat_after[k]} for k in sorted(added)],
        "removed": [{"path": k, **flat_before[k]} for k in sorted(removed)],
        "changed": changed,
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
        },
    }


async def extract_page_object_hints(page: Any) -> list[dict[str, Any]]:
    """
    Extract data-testid, roles, labels, and other POM-relevant attributes
    from the current page for Page Object Model generation.
    """
    js = """
    () => {
        const results = [];
        const interactiveTags = new Set([
            'a', 'button', 'input', 'select', 'textarea',
            'details', 'dialog', 'summary', 'form'
        ]);

        const allElements = document.querySelectorAll(
            '[data-testid], [data-test-id], [role], [aria-label], ' +
            'button, a, input, select, textarea, [type="submit"], ' +
            '[type="button"], form'
        );

        const seen = new Set();

        for (const el of allElements) {
            if (results.length >= 200) break;

            // Deduplicate by element reference
            const tag = el.tagName.toLowerCase();
            const id = el.id || '';
            const testid = el.getAttribute('data-testid') || el.getAttribute('data-test-id') || '';
            const role = el.getAttribute('role') || '';
            const ariaLabel = el.getAttribute('aria-label') || '';
            const name = el.getAttribute('name') || '';
            const type = el.getAttribute('type') || '';
            const placeholder = el.getAttribute('placeholder') || '';
            const text = (el.textContent || '').trim().substring(0, 100);

            // Create a unique key
            const key = `${tag}|${id}|${testid}|${role}|${name}|${ariaLabel}`;
            if (seen.has(key)) continue;
            seen.add(key);

            const rect = el.getBoundingClientRect();
            const visible = rect.width > 0 && rect.height > 0;
            if (!visible) continue;

            results.push({
                tag: tag,
                id: id || null,
                data_testid: testid || null,
                role: role || null,
                aria_label: ariaLabel || null,
                name: name || null,
                type: type || null,
                placeholder: placeholder || null,
                text: text || null,
                is_interactive: interactiveTags.has(tag) || !!role
            });
        }

        return results;
    }
    """
    try:
        return await page.evaluate(js)
    except Exception as exc:
        logger.warning("extract_page_object_hints hatasi: %s", exc)
        return []
