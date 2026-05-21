"""Browser Tool — Playwright wrapper."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None  # type: ignore


class BrowserSecurityError(RuntimeError):
    pass


def _check_url_allowed(url: str, allowlist: list[str] | None = None) -> None:
    if not allowlist:
        return
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        raise BrowserSecurityError(f"URL parse: {url}")
    for allowed in allowlist:
        a = allowed.lower().strip()
        if a.startswith("*."):
            suffix = a[2:]
            if host == suffix or host.endswith("." + suffix):
                return
        elif host == a:
            return
    raise BrowserSecurityError(f"URL allowlist dışı: {url}")


class BrowserSession:
    def __init__(
        self,
        *,
        headless: bool = True,
        browser_type: str = "chromium",
        viewport: dict[str, int] | None = None,
        user_agent: str | None = None,
        url_allowlist: list[str] | None = None,
        default_timeout_ms: int = 30_000,
    ) -> None:
        self.headless = headless
        self.browser_type = browser_type
        self.viewport = viewport or {"width": 1280, "height": 800}
        self.user_agent = user_agent or "TestwrightAI-Explorer/1.0"
        self.url_allowlist = url_allowlist or []
        self.default_timeout_ms = default_timeout_ms
        self._pw = None
        self._browser = None
        self._context = None

    async def __aenter__(self) -> "BrowserSession":
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright kurulu değil")
        self._pw = await async_playwright().start()
        browser_cls = getattr(self._pw, self.browser_type)
        self._browser = await browser_cls.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            viewport=self.viewport,
            user_agent=self.user_agent,
        )
        self._context.set_default_timeout(self.default_timeout_ms)
        return self

    async def __aexit__(self, *_args) -> None:
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception as exc:
            logger.debug("Browser cleanup: %s", exc)

    async def new_page(self, url: str | None = None):
        if not self._context:
            raise RuntimeError("BrowserSession active değil")
        page = await self._context.new_page()
        if url:
            _check_url_allowed(url, self.url_allowlist)
            await page.goto(url, wait_until="domcontentloaded")
        return page


async def collect_links(page, *, same_origin_only: bool = True) -> list[str]:
    try:
        js = r"""() => {
          const out = new Set();
          document.querySelectorAll('a[href]').forEach(a => {
            try {
              const u = new URL(a.getAttribute('href'), location.href);
              if (u.protocol.startsWith('http')) out.add(u.toString());
            } catch (e) {}
          });
          return [...out];
        }"""
        links = await page.evaluate(js)
    except Exception as exc:
        logger.debug("Link collection fail: %s", exc)
        return []

    if same_origin_only:
        try:
            origin_host = urlparse(page.url).hostname
            links = [l for l in links if urlparse(l).hostname == origin_host]
        except Exception:
            pass
    return list(set(links))
