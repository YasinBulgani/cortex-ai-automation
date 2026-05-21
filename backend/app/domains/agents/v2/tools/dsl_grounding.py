"""DSL Grounding — packages/dsl/catalog'dan senaryoya aday adım getirir."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_DIR_CANDIDATES = [
    Path("packages/dsl/catalog"),
    Path("/dsl-catalog"),
    Path("../packages/dsl/catalog"),
    Path("../../packages/dsl/catalog"),
]


def _find_catalog() -> Path | None:
    for p in _CATALOG_DIR_CANDIDATES:
        if p.exists() and p.is_dir():
            return p
    return None


_CACHED_STEPS: list[dict] | None = None


def load_dsl_steps() -> list[dict]:
    global _CACHED_STEPS
    if _CACHED_STEPS is not None:
        return _CACHED_STEPS
    catalog = _find_catalog()
    if not catalog:
        _CACHED_STEPS = []
        return _CACHED_STEPS
    steps: list[dict] = []
    try:
        import yaml
        for yaml_file in catalog.glob("**/*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for key in ("steps", "entries", "items", "patterns"):
                        items = data.get(key, [])
                        if isinstance(items, list):
                            steps.extend(items)
                elif isinstance(data, list):
                    steps.extend(data)
            except Exception:
                continue
    except ImportError:
        pass
    _CACHED_STEPS = steps
    logger.info("DSL catalog yüklendi: %d step", len(steps))
    return steps


def ground_steps(query: str, *, top_k: int = 10, min_score: float = 0.25) -> list[str]:
    steps = load_dsl_steps()
    if not steps:
        return []
    q_lower = query.lower()
    q_bigrams = _bigrams(q_lower)
    if not q_bigrams:
        return []
    scored: list[tuple[str, float]] = []
    for step in steps:
        text = _extract_step_text(step)
        if not text:
            continue
        t_bigrams = _bigrams(text.lower())
        if not t_bigrams:
            continue
        inter = len(q_bigrams & t_bigrams)
        union = len(q_bigrams | t_bigrams)
        score = inter / union if union else 0
        if score >= min_score:
            scored.append((text, score))
    scored.sort(key=lambda x: -x[1])
    return [text for text, _ in scored[:top_k]]


def _bigrams(text: str) -> set[str]:
    clean = " ".join(text.split())
    if len(clean) < 2:
        return set()
    return {clean[i : i + 2] for i in range(len(clean) - 1)}


def _extract_step_text(step: dict | str) -> str:
    if isinstance(step, str):
        return step
    if not isinstance(step, dict):
        return ""
    for key in ("pattern", "text", "gherkin", "template", "step", "canonical"):
        v = step.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    name = step.get("name") or step.get("title")
    return name if isinstance(name, str) else ""
