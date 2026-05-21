"""Katman 1 — DOM Snapshot."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DOMSnapshot:
    url: str
    title: str
    dom: str
    aria: dict[str, Any] = field(default_factory=dict)
    screenshot: bytes = b""
    viewport: dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 800})
    hash: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    network_idle: bool = False

    def __post_init__(self) -> None:
        if not self.hash and (self.dom or self.url):
            h = hashlib.sha256()
            h.update(self.url.encode("utf-8", errors="ignore"))
            h.update(b"|")
            h.update(self.dom.encode("utf-8", errors="ignore")[:200_000])
            self.hash = h.hexdigest()[:16]

    def dom_size(self) -> int:
        return len(self.dom)

    def has_screenshot(self) -> bool:
        return len(self.screenshot) > 0


async def snapshot_page(
    page,
    *,
    wait_for_network_idle: bool = True,
    wait_timeout_ms: int = 15_000,
    full_page_screenshot: bool = True,
    interesting_only: bool = False,
) -> DOMSnapshot:
    if wait_for_network_idle:
        try:
            await page.wait_for_load_state("networkidle", timeout=wait_timeout_ms)
            network_idle = True
        except Exception:
            network_idle = False
    else:
        network_idle = False

    try:
        aria = await page.accessibility.snapshot(interesting_only=interesting_only)
        aria = aria or {}
    except Exception:
        aria = {}

    try:
        dom = await page.content()
    except Exception:
        dom = ""

    try:
        screenshot = await page.screenshot(type="png", full_page=full_page_screenshot)
    except Exception:
        screenshot = b""

    viewport = {"width": 1280, "height": 800}
    try:
        vp = page.viewport_size
        if vp:
            viewport = {"width": vp.get("width", 1280), "height": vp.get("height", 800)}
    except Exception:
        pass

    try:
        url = page.url
    except Exception:
        url = ""
    try:
        title = await page.title()
    except Exception:
        title = ""

    return DOMSnapshot(
        url=url,
        title=title,
        dom=dom,
        aria=aria,
        screenshot=screenshot,
        viewport=viewport,
        network_idle=network_idle,
    )


def snapshot_from_html(url: str, html: str, title: str = "") -> DOMSnapshot:
    return DOMSnapshot(url=url, title=title, dom=html, network_idle=True)
