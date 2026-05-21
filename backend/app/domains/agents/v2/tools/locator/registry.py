"""Katman 5 — Registry Persistence (in-memory; Postgres backend Faz 2'de)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from ...schemas.locator import LocatorSuggestion

logger = logging.getLogger(__name__)


@dataclass
class LocatorRegistryEntry:
    tenant_id: str
    project_id: str
    url_pattern: str
    element_fingerprint: str
    suggestion: LocatorSuggestion
    version: int = 1
    last_verified_at: datetime = field(default_factory=datetime.utcnow)
    verify_success: int = 0
    verify_failure: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    embedding: list[float] | None = None

    def success_rate(self) -> float:
        total = self.verify_success + self.verify_failure
        return (self.verify_success / total) if total else 0.5

    def is_fresh(self, ttl: timedelta = timedelta(hours=24)) -> bool:
        return datetime.utcnow() - self.last_verified_at < ttl


class LocatorRegistry:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str, str, str], LocatorRegistryEntry] = {}

    def _key(self, tenant_id: str, project_id: str, url_pattern: str, fingerprint: str):
        return (tenant_id, project_id, url_pattern, fingerprint)

    def get(
        self,
        *,
        tenant_id: str,
        project_id: str,
        url_pattern: str,
        fingerprint: str,
    ) -> LocatorRegistryEntry | None:
        return self._store.get(self._key(tenant_id, project_id, url_pattern, fingerprint))

    def put(
        self,
        *,
        tenant_id: str,
        project_id: str,
        url_pattern: str,
        suggestion: LocatorSuggestion,
        embedding: list[float] | None = None,
    ) -> LocatorRegistryEntry:
        k = self._key(tenant_id, project_id, url_pattern, suggestion.element_id)
        existing = self._store.get(k)
        if existing:
            if existing.suggestion.primary_selector != suggestion.primary_selector:
                existing.version += 1
                existing.suggestion = suggestion
            existing.last_verified_at = datetime.utcnow()
            if embedding is not None:
                existing.embedding = embedding
            return existing
        entry = LocatorRegistryEntry(
            tenant_id=tenant_id,
            project_id=project_id,
            url_pattern=url_pattern,
            element_fingerprint=suggestion.element_id,
            suggestion=suggestion,
            embedding=embedding,
        )
        self._store[k] = entry
        return entry

    def record_verify(
        self,
        *,
        tenant_id: str,
        project_id: str,
        url_pattern: str,
        fingerprint: str,
        success: bool,
    ) -> None:
        entry = self.get(
            tenant_id=tenant_id, project_id=project_id,
            url_pattern=url_pattern, fingerprint=fingerprint,
        )
        if not entry:
            return
        if success:
            entry.verify_success += 1
        else:
            entry.verify_failure += 1
        entry.last_verified_at = datetime.utcnow()

    def find_similar(
        self,
        *,
        tenant_id: str,
        project_id: str,
        url_pattern: str,
        query_embedding: list[float] | None = None,
        query_description: str | None = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> list[tuple[LocatorRegistryEntry, float]]:
        candidates = [
            e for e in self._store.values()
            if e.tenant_id == tenant_id and e.project_id == project_id
            and e.url_pattern == url_pattern
        ]
        if not candidates:
            return []

        if query_embedding:
            scored = []
            for c in candidates:
                if c.embedding is None:
                    continue
                sim = _cosine(query_embedding, c.embedding)
                if sim >= min_similarity:
                    scored.append((c, sim))
            scored.sort(key=lambda x: -x[1])
            return scored[:top_k]

        if query_description:
            q = query_description.lower()
            scored = [
                (c, _substring_sim(q, c.suggestion.element_description.lower()))
                for c in candidates
            ]
            scored = [(c, s) for c, s in scored if s >= min_similarity]
            scored.sort(key=lambda x: -x[1])
            return scored[:top_k]

        return [(c, 1.0) for c in candidates[:top_k]]

    def stats(self) -> dict[str, Any]:
        return {
            "total_locators": len(self._store),
            "with_embedding": sum(1 for e in self._store.values() if e.embedding),
            "avg_success_rate": (
                sum(e.success_rate() for e in self._store.values()) / len(self._store)
                if self._store else 0.0
            ),
        }

    def clear(self) -> None:
        self._store.clear()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _substring_sim(q: str, target: str) -> float:
    def bigrams(s: str) -> set[str]:
        return {s[i : i + 2] for i in range(len(s) - 1)}
    if not q or not target:
        return 0.0
    a, b = bigrams(q), bigrams(target)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def url_pattern(url: str) -> str:
    import re
    try:
        parsed = urlparse(url)
        path = parsed.path
    except Exception:
        path = url
    path = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/:uuid", path)
    path = re.sub(r"/\d{3,}", "/:id", path)
    return path or "/"


_singleton = LocatorRegistry()


def get_registry() -> LocatorRegistry:
    return _singleton
