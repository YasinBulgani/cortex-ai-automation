"""Locator Verification — Playwright ile doğrulama."""
from __future__ import annotations

import asyncio
import logging

from ...schemas.locator import LocatorCandidate

logger = logging.getLogger(__name__)


async def verify_candidate(page, candidate: LocatorCandidate) -> LocatorCandidate:
    try:
        loc = page.locator(candidate.selector)
        candidate.count = await loc.count()
        if candidate.count > 0:
            first = loc.first
            try:
                candidate.is_visible = await first.is_visible()
            except Exception:
                candidate.is_visible = None
            try:
                candidate.is_enabled = await first.is_enabled()
            except Exception:
                candidate.is_enabled = None
    except Exception as exc:
        logger.debug("Verify fail: %s", exc)
        candidate.count = -1
    return candidate


async def verify_batch(
    page, candidates: list[LocatorCandidate], max_concurrency: int = 8
) -> list[LocatorCandidate]:
    sem = asyncio.Semaphore(max_concurrency)

    async def _one(c: LocatorCandidate) -> LocatorCandidate:
        async with sem:
            return await verify_candidate(page, c)

    return await asyncio.gather(*(_one(c) for c in candidates))
