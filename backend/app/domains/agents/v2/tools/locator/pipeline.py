"""5-Katmanlı Locator Pipeline Orchestrator."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ...schemas.locator import ElementCard, LocatorCandidate, LocatorSuggestion
from .extraction import extract_elements
from .generation import generate_locators_for_element
from .registry import LocatorRegistry, get_registry, url_pattern
from .scoring import aggregate_score, score_locator
from .snapshot import DOMSnapshot, snapshot_page
from .verification import verify_batch

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    elements_found: int = 0
    candidates_generated: int = 0
    candidates_verified: int = 0
    suggestions_created: int = 0
    registry_hits: int = 0
    registry_new: int = 0
    duration_ms: int = 0
    avg_stability: float = 0.0
    layers_timing_ms: dict[str, int] = field(default_factory=dict)


class LocatorPipeline:
    def __init__(
        self,
        *,
        tenant_id: str,
        project_id: str,
        enable_ai_xpath: bool = False,
        ai_xpath_func: Callable | None = None,
        embed_func: Callable | None = None,
        registry: LocatorRegistry | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.enable_ai_xpath = enable_ai_xpath
        self.ai_xpath_func = ai_xpath_func
        self.embed_func = embed_func
        self.registry = registry or get_registry()

    async def run(
        self,
        page,
        *,
        use_registry_cache: bool = True,
    ) -> tuple[list[LocatorSuggestion], PipelineStats]:
        stats = PipelineStats()
        t_total = time.monotonic()

        t = time.monotonic()
        snapshot = await snapshot_page(page)
        stats.layers_timing_ms["snapshot"] = int((time.monotonic() - t) * 1000)

        t = time.monotonic()
        elements = await extract_elements(page)
        stats.elements_found = len(elements)
        stats.layers_timing_ms["extraction"] = int((time.monotonic() - t) * 1000)

        suggestions = await self._process_elements(
            page=page, elements=elements, snapshot=snapshot,
            stats=stats, use_registry_cache=use_registry_cache,
        )

        stats.duration_ms = int((time.monotonic() - t_total) * 1000)
        stats.suggestions_created = len(suggestions)
        stats.avg_stability = (
            sum(s.stability_score for s in suggestions) / len(suggestions)
            if suggestions else 0.0
        )

        logger.info(
            "Locator pipeline — elements=%d suggestions=%d avg=%.3f duration=%dms",
            stats.elements_found, stats.suggestions_created,
            stats.avg_stability, stats.duration_ms,
        )
        return suggestions, stats

    async def run_offline(
        self,
        elements: list[ElementCard],
        *,
        url: str = "/",
        skip_verification: bool = True,
    ) -> tuple[list[LocatorSuggestion], PipelineStats]:
        stats = PipelineStats()
        t_total = time.monotonic()
        stats.elements_found = len(elements)

        suggestions: list[LocatorSuggestion] = []
        url_pat = url_pattern(url)

        for el in elements:
            candidates = await generate_locators_for_element(el, enable_ai_xpath=False)
            stats.candidates_generated += len(candidates)
            if not candidates:
                continue

            for c in candidates:
                score_locator(c, history_success_rate=None)
            primary, fallbacks = aggregate_score(candidates)
            if not primary:
                continue

            suggestion = LocatorSuggestion(
                element_id=el.fingerprint,
                element_description=el.element_description(),
                primary_strategy=primary.strategy,
                primary_selector=primary.selector,
                primary_playwright_expr=primary.playwright_expr,
                fallbacks=fallbacks,
                stability_score=primary.stability_score,
                verified_on_url=url,
                verified_at=datetime.utcnow(),
            )
            suggestions.append(suggestion)

            self.registry.put(
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                url_pattern=url_pat,
                suggestion=suggestion,
            )
            stats.registry_new += 1

        stats.duration_ms = int((time.monotonic() - t_total) * 1000)
        stats.suggestions_created = len(suggestions)
        stats.avg_stability = (
            sum(s.stability_score for s in suggestions) / len(suggestions)
            if suggestions else 0.0
        )
        return suggestions, stats

    async def _process_elements(
        self,
        *,
        page,
        elements: list[ElementCard],
        snapshot: DOMSnapshot,
        stats: PipelineStats,
        use_registry_cache: bool,
    ) -> list[LocatorSuggestion]:
        url_pat = url_pattern(snapshot.url)
        suggestions: list[LocatorSuggestion] = []

        embedding_map: dict[str, list[float]] = {}
        if self.embed_func:
            try:
                texts = [el.element_description() for el in elements]
                emb = await self.embed_func(texts)
                vectors = emb.get("vectors", []) if isinstance(emb, dict) else []
                for el, vec in zip(elements, vectors):
                    embedding_map[el.fingerprint] = vec
            except Exception as exc:
                logger.debug("Embedding: %s", exc)

        t_gen = time.monotonic()
        t_verify_total = 0.0

        for el in elements:
            cached = None
            if use_registry_cache:
                cached = self.registry.get(
                    tenant_id=self.tenant_id,
                    project_id=self.project_id,
                    url_pattern=url_pat,
                    fingerprint=el.fingerprint,
                )
                if cached and cached.is_fresh():
                    stats.registry_hits += 1
                    suggestions.append(cached.suggestion)
                    continue

            candidates = await generate_locators_for_element(
                el,
                enable_ai_xpath=self.enable_ai_xpath,
                ai_xpath_func=self.ai_xpath_func,
                screenshot=snapshot.screenshot,
            )
            stats.candidates_generated += len(candidates)
            if not candidates:
                continue

            t_v = time.monotonic()
            await verify_batch(page, candidates, max_concurrency=6)
            t_verify_total += time.monotonic() - t_v
            stats.candidates_verified += len(candidates)

            history_rate = cached.success_rate() if cached else None
            for c in candidates:
                score_locator(c, history_success_rate=history_rate)

            primary, fallbacks = aggregate_score(candidates)
            if not primary:
                continue

            suggestion = LocatorSuggestion(
                element_id=el.fingerprint,
                element_description=el.element_description(),
                primary_strategy=primary.strategy,
                primary_selector=primary.selector,
                primary_playwright_expr=primary.playwright_expr,
                fallbacks=fallbacks,
                stability_score=primary.stability_score,
                verified_on_url=snapshot.url,
                verified_at=datetime.utcnow(),
                version=(cached.version + 1) if cached else 1,
            )
            suggestions.append(suggestion)

            self.registry.put(
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                url_pattern=url_pat,
                suggestion=suggestion,
                embedding=embedding_map.get(el.fingerprint),
            )
            if not cached:
                stats.registry_new += 1

        stats.layers_timing_ms["generation_and_verify"] = int(
            (time.monotonic() - t_gen) * 1000
        )
        stats.layers_timing_ms["verify_only"] = int(t_verify_total * 1000)
        return suggestions
