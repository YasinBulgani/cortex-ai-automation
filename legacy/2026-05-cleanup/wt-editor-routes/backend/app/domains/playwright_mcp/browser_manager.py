"""Playwright MCP — Thread-safe browser session manager."""
from __future__ import annotations

import asyncio
import base64
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ── Graceful import ──────────────────────────────────────────────────────────
try:
    from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext,
        Page,
        Playwright,
    )

    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_MAX_SESSIONS = 5
_IDLE_TIMEOUT_SEC = 600  # 10 minutes


class PlaywrightNotInstalledError(RuntimeError):
    """Raised when playwright package is not installed."""


class BrowserManager:
    """Manages Playwright browser sessions with async locks and auto-cleanup."""

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._max_sessions = max_sessions
        self._lock = asyncio.Lock()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._playwright: Any | None = None
        self._browser: Any | None = None

    # ── Internal helpers ─────────────────────────────────────────────────

    def _check_available(self) -> None:
        if not _PW_AVAILABLE:
            raise PlaywrightNotInstalledError(
                "playwright paketi kurulu degil. "
                "Kurmak icin: pip install playwright && python -m playwright install chromium"
            )

    async def _ensure_browser(self) -> None:
        """Lazy-init: start browser on first use."""
        self._check_available()
        if self._browser is None or not self._browser.is_connected():
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            logger.info("Playwright Chromium browser baslatildi.")

    async def _cleanup_idle(self) -> list[str]:
        """Close sessions idle longer than timeout. Returns closed session IDs."""
        now = time.time()
        to_close: list[str] = []
        for sid, data in list(self._sessions.items()):
            if now - data["last_active"] > _IDLE_TIMEOUT_SEC:
                to_close.append(sid)
        closed: list[str] = []
        for sid in to_close:
            try:
                await self._close_session_internal(sid)
                closed.append(sid)
            except Exception as exc:
                logger.warning("Idle session %s kapatilirken hata: %s", sid, exc)
        if closed:
            logger.info("Idle session'lar kapatildi: %s", closed)
        return closed

    async def _close_session_internal(self, session_id: str) -> None:
        """Close a session without acquiring lock (caller must hold lock)."""
        data = self._sessions.pop(session_id, None)
        if data is None:
            return
        ctx: Any = data.get("browser_context")
        if ctx is not None:
            try:
                await ctx.close()
            except Exception:
                pass

    def _touch(self, session_id: str) -> None:
        """Update last_active timestamp."""
        if session_id in self._sessions:
            self._sessions[session_id]["last_active"] = time.time()

    def _get_session_data(self, session_id: str) -> dict[str, Any]:
        data = self._sessions.get(session_id)
        if data is None:
            raise KeyError(f"Session bulunamadi: {session_id}")
        self._touch(session_id)
        return data

    # ── Public API ───────────────────────────────────────────────────────

    async def create_session(
        self,
        *,
        owner_user_id: str,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        locale: str = "tr-TR",
        timezone: str = "Europe/Istanbul",
    ) -> dict[str, Any]:
        """Create a new browser session and return session info."""
        self._check_available()
        async with self._lock:
            await self._cleanup_idle()
            if len(self._sessions) >= self._max_sessions:
                raise RuntimeError(
                    f"Maksimum oturum sayisina ulasildi ({self._max_sessions}). "
                    "Once mevcut bir oturumu kapatin."
                )
            await self._ensure_browser()

            session_id = uuid.uuid4().hex[:12]
            ctx = await self._browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                locale=locale,
                timezone_id=timezone,
            )
            page = await ctx.new_page()
            now = time.time()

            self._sessions[session_id] = {
                "browser_context": ctx,
                "page": page,
                "owner_user_id": owner_user_id,
                "created_at": now,
                "last_active": now,
                "headless": headless,
            }
            logger.info("Yeni browser oturumu olusturuldu: %s", session_id)
            return {
                "session_id": session_id,
                "status": "active",
                "current_url": None,
                "created_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)
                ),
                "page_title": None,
                "owner_user_id": owner_user_id,
            }

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Return info about a session."""
        async with self._lock:
            data = self._get_session_data(session_id)
            page: Any = data["page"]
            try:
                url = page.url
                title = await page.title()
            except Exception:
                url = None
                title = None

            idle_sec = time.time() - data["last_active"]
            status = "active" if idle_sec < 60 else "idle"

            return {
                "session_id": session_id,
                "status": status,
                "current_url": url,
                "created_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(data["created_at"])
                ),
                "page_title": title,
                "owner_user_id": data.get("owner_user_id"),
            }

    async def close_session(self, session_id: str) -> None:
        """Close and remove a session."""
        async with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session bulunamadi: {session_id}")
            await self._close_session_internal(session_id)
            logger.info("Session kapatildi: %s", session_id)

    async def list_sessions(self, owner_user_id: str | None = None) -> list[dict[str, Any]]:
        """List all active sessions."""
        async with self._lock:
            await self._cleanup_idle()
            result: list[dict[str, Any]] = []
            for sid, data in self._sessions.items():
                if owner_user_id and data.get("owner_user_id") != owner_user_id:
                    continue
                page: Any = data["page"]
                try:
                    url = page.url
                    title = await page.title()
                except Exception:
                    url = None
                    title = None
                idle_sec = time.time() - data["last_active"]
                status = "active" if idle_sec < 60 else "idle"
                result.append(
                    {
                        "session_id": sid,
                        "status": status,
                        "current_url": url,
                        "created_at": time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ",
                            time.gmtime(data["created_at"]),
                        ),
                        "page_title": title,
                        "owner_user_id": data.get("owner_user_id"),
                    }
                )
            return result

    # ── Navigation ───────────────────────────────────────────────────────

    async def navigate(
        self,
        session_id: str,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """Navigate to a URL. Returns url, title, status_code, load_time_ms."""
        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        start = time.monotonic()
        response = await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        title = await page.title()
        status_code = response.status if response else None

        return {
            "url": page.url,
            "title": title,
            "status_code": status_code,
            "load_time_ms": elapsed_ms,
        }

    # ── Screenshot ───────────────────────────────────────────────────────

    async def screenshot(
        self,
        session_id: str,
        *,
        selector: str | None = None,
        full_page: bool = False,
        fmt: str = "png",
        quality: int = 80,
    ) -> dict[str, Any]:
        """Take a screenshot. Returns base64 image, format, dimensions, url."""
        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        kwargs: dict[str, Any] = {"type": fmt}
        if fmt == "jpeg":
            kwargs["quality"] = quality

        if selector:
            element = await page.query_selector(selector)
            if element is None:
                raise ValueError(f"Element bulunamadi: {selector}")
            raw = await element.screenshot(**kwargs)
            box = await element.bounding_box()
            width = int(box["width"]) if box else 0
            height = int(box["height"]) if box else 0
        else:
            kwargs["full_page"] = full_page
            raw = await page.screenshot(**kwargs)
            vp = page.viewport_size
            width = vp["width"] if vp else 0
            height = vp["height"] if vp else 0

        return {
            "image_base64": base64.b64encode(raw).decode(),
            "format": fmt,
            "width": width,
            "height": height,
            "url": page.url,
        }

    # ── DOM Snapshot ─────────────────────────────────────────────────────

    async def get_dom_snapshot(
        self,
        session_id: str,
        *,
        selector: str | None = None,
        max_depth: int = 5,
        include_styles: bool = False,
        include_hidden: bool = False,
    ) -> dict[str, Any]:
        """Walk the DOM tree and return a serialised DOMNode structure."""
        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        js_walker = """
        (args) => {
            const {rootSelector, maxDepth, includeStyles, includeHidden} = args;
            let count = 0;

            function walk(el, depth) {
                if (!el || depth > maxDepth) return null;
                const style = window.getComputedStyle(el);
                if (!includeHidden && style.display === 'none') return null;
                count++;

                const attrs = {};
                for (const attr of el.attributes || []) {
                    attrs[attr.name] = attr.value;
                }
                const rect = el.getBoundingClientRect();
                const box = {
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                };

                const children = [];
                for (const child of el.children) {
                    const c = walk(child, depth + 1);
                    if (c) children.push(c);
                }

                let text = null;
                if (el.childNodes.length > 0) {
                    const directText = Array.from(el.childNodes)
                        .filter(n => n.nodeType === 3)
                        .map(n => n.textContent.trim())
                        .filter(Boolean)
                        .join(' ');
                    if (directText) text = directText.substring(0, 200);
                }

                return {
                    tag: el.tagName.toLowerCase(),
                    attributes: attrs,
                    text: text,
                    children: children,
                    bounding_box: box
                };
            }

            const root = rootSelector
                ? document.querySelector(rootSelector)
                : document.body;
            if (!root) return {root: null, element_count: 0};
            const tree = walk(root, 0);
            return {root: tree, element_count: count};
        }
        """

        result = await page.evaluate(
            js_walker,
            {
                "rootSelector": selector,
                "maxDepth": max_depth,
                "includeStyles": include_styles,
                "includeHidden": include_hidden,
            },
        )

        title = await page.title()
        return {
            "url": page.url,
            "title": title,
            "root": result.get("root"),
            "element_count": result.get("element_count", 0),
            "snapshot_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # ── Selector Validation ──────────────────────────────────────────────

    async def validate_selectors(
        self,
        session_id: str,
        selectors: list[str],
        *,
        timeout_ms: int = 5000,
    ) -> dict[str, Any]:
        """Validate a list of selectors against the current page."""
        from .dom_analyzer import compute_selector_stability, suggest_stable_selectors_for_handle

        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        results: list[dict[str, Any]] = []
        for sel in selectors:
            try:
                elements = await page.query_selector_all(sel)
                count = len(elements)
                found = count > 0

                tag_name: str | None = None
                attributes: dict[str, str] = {}
                bounding_box: dict[str, float] | None = None
                visible = False
                alternatives: list[str] = []

                if found:
                    first = elements[0]
                    tag_name = await first.evaluate("el => el.tagName.toLowerCase()")
                    attributes = await first.evaluate(
                        "el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))"
                    )
                    box = await first.bounding_box()
                    if box:
                        bounding_box = {
                            k: round(v, 2) for k, v in box.items()
                        }
                        visible = box["width"] > 0 and box["height"] > 0

                    try:
                        alternatives = await suggest_stable_selectors_for_handle(
                            page, first
                        )
                    except Exception:
                        alternatives = []

                stability = compute_selector_stability(sel)

                results.append(
                    {
                        "selector": sel,
                        "found": found,
                        "count": count,
                        "visible": visible,
                        "tag_name": tag_name,
                        "attributes": attributes,
                        "bounding_box": bounding_box,
                        "stability_score": stability,
                        "suggested_alternatives": alternatives,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "selector": sel,
                        "found": False,
                        "count": 0,
                        "visible": False,
                        "tag_name": None,
                        "attributes": {},
                        "bounding_box": None,
                        "stability_score": 0,
                        "suggested_alternatives": [],
                    }
                )
                logger.debug("Selector validation hatasi ('%s'): %s", sel, exc)

        return {
            "results": results,
            "page_url": page.url,
            "validated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # ── Browser Actions ──────────────────────────────────────────────────

    async def execute_action(
        self,
        session_id: str,
        action: str,
        selector: str,
        *,
        value: str | None = None,
        timeout_ms: int = 5000,
    ) -> dict[str, Any]:
        """Execute a browser action on a selector."""
        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        start = time.monotonic()
        error: str | None = None
        success = False

        try:
            if action == "click":
                await page.click(selector, timeout=timeout_ms)
                success = True
            elif action == "fill":
                if value is None:
                    raise ValueError("'fill' aksiyonu icin 'value' gerekli.")
                await page.fill(selector, value, timeout=timeout_ms)
                success = True
            elif action == "select":
                if value is None:
                    raise ValueError("'select' aksiyonu icin 'value' gerekli.")
                await page.select_option(selector, value, timeout=timeout_ms)
                success = True
            elif action == "hover":
                await page.hover(selector, timeout=timeout_ms)
                success = True
            elif action == "press":
                if value is None:
                    raise ValueError("'press' aksiyonu icin 'value' (tus adi) gerekli.")
                await page.press(selector, value, timeout=timeout_ms)
                success = True
            elif action == "scroll":
                element = await page.query_selector(selector)
                if element is None:
                    raise ValueError(f"Element bulunamadi: {selector}")
                delta = int(value) if value else 300
                await element.evaluate(
                    f"el => el.scrollBy(0, {delta})"
                )
                success = True
            elif action == "wait":
                await page.wait_for_selector(selector, timeout=timeout_ms)
                success = True
            else:
                raise ValueError(f"Bilinmeyen aksiyon: {action}")
        except Exception as exc:
            error = str(exc)[:500]
            logger.warning("Action hatasi (%s, %s): %s", action, selector, error)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "action": action,
            "selector": selector,
            "success": success,
            "error": error,
            "duration_ms": elapsed_ms,
            "screenshot_after": None,
        }

    # ── Selector Suggestion ──────────────────────────────────────────────

    async def suggest_selectors(
        self, session_id: str, target_description: str
    ) -> list[dict[str, Any]]:
        """Find best selectors for a target element described in natural language."""
        from .dom_analyzer import extract_page_object_hints, compute_selector_stability

        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        hints = await extract_page_object_hints(page)

        desc_lower = target_description.lower()
        matches: list[dict[str, Any]] = []

        for hint in hints:
            score = 0
            text_val = (hint.get("text") or "").lower()
            label_val = (hint.get("aria_label") or "").lower()
            testid_val = (hint.get("data_testid") or "").lower()
            role_val = (hint.get("role") or "").lower()
            tag_val = (hint.get("tag") or "").lower()

            # Simple keyword matching
            for keyword in desc_lower.split():
                if keyword in text_val:
                    score += 3
                if keyword in label_val:
                    score += 3
                if keyword in testid_val:
                    score += 2
                if keyword in role_val:
                    score += 1
                if keyword in tag_val:
                    score += 1

            if score > 0:
                # Build candidate selectors for this hint
                selectors: list[str] = []
                if hint.get("data_testid"):
                    selectors.append(f'[data-testid="{hint["data_testid"]}"]')
                if hint.get("role"):
                    if hint.get("aria_label"):
                        selectors.append(
                            f'{hint["tag"]}[role="{hint["role"]}"][aria-label="{hint["aria_label"]}"]'
                        )
                    else:
                        selectors.append(
                            f'{hint["tag"]}[role="{hint["role"]}"]'
                        )
                if hint.get("id"):
                    selectors.append(f'#{hint["id"]}')
                if hint.get("aria_label"):
                    selectors.append(f'[aria-label="{hint["aria_label"]}"]')
                if hint.get("text") and len(hint["text"]) < 60:
                    selectors.append(f'text="{hint["text"]}"')

                best_selector = selectors[0] if selectors else f'{hint["tag"]}'
                stability = compute_selector_stability(best_selector)

                matches.append(
                    {
                        "selector": best_selector,
                        "found": True,
                        "count": 1,
                        "visible": True,
                        "tag_name": hint.get("tag"),
                        "attributes": {
                            k: v
                            for k, v in hint.items()
                            if v and k not in ("tag", "text")
                        },
                        "bounding_box": None,
                        "stability_score": stability,
                        "suggested_alternatives": selectors[1:],
                        "_match_score": score,
                    }
                )

        # Sort by match score desc, then stability desc
        matches.sort(key=lambda m: (-m.get("_match_score", 0), -m.get("stability_score", 0)))
        # Remove internal field
        for m in matches:
            m.pop("_match_score", None)

        return matches[:10]

    # ── Heal/Verify ──────────────────────────────────────────────────────

    async def heal_verify(
        self,
        session_id: str,
        original_selector: str,
        healed_selector: str,
        *,
        expected_tag: str | None = None,
        expected_text: str | None = None,
    ) -> dict[str, Any]:
        """Verify that a healed selector correctly replaces the original."""
        async with self._lock:
            data = self._get_session_data(session_id)
        page: Any = data["page"]

        original_found = False
        healed_found = False
        healed_matches = False
        confidence = 0.0
        recommendation = ""

        # Check original
        try:
            el = await page.query_selector(original_selector)
            original_found = el is not None
        except Exception:
            original_found = False

        # Check healed
        try:
            el = await page.query_selector(healed_selector)
            healed_found = el is not None
            if el is not None:
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                text = await el.evaluate("el => (el.textContent || '').trim().substring(0, 200)")

                tag_ok = expected_tag is None or tag == expected_tag.lower()
                text_ok = expected_text is None or expected_text.lower() in text.lower()
                healed_matches = tag_ok and text_ok

                # Confidence calculation
                confidence = 0.5  # base for found
                if tag_ok and expected_tag:
                    confidence += 0.2
                if text_ok and expected_text:
                    confidence += 0.2
                if not original_found:
                    confidence += 0.1  # original is broken, healed works

                from .dom_analyzer import compute_selector_stability
                stability = compute_selector_stability(healed_selector)
                if stability >= 4:
                    confidence = min(confidence + 0.1, 1.0)

        except Exception:
            healed_found = False

        # Recommendation
        if healed_found and healed_matches:
            recommendation = "Healed selector dogru calisiyor. Guncelleme uygulanabilir."
        elif healed_found and not healed_matches:
            recommendation = (
                "Healed selector bir element buluyor ama beklenen "
                "tag/text ile eslesmiyor. Manuel kontrol onerilir."
            )
        elif not healed_found:
            recommendation = "Healed selector da calismadi. Farkli bir strateji deneyin."

        return {
            "original_found": original_found,
            "healed_found": healed_found,
            "healed_matches_expected": healed_matches,
            "confidence": round(confidence, 2),
            "recommendation": recommendation,
        }

    # ── Shutdown ─────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Close all sessions and the browser."""
        async with self._lock:
            for sid in list(self._sessions):
                try:
                    await self._close_session_internal(sid)
                except Exception:
                    pass
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            logger.info("BrowserManager tamamen kapatildi.")
