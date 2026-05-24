"""Semantic test case similarity search for the Management domain.

Uses the existing AI Gateway embedding infrastructure to compute cosine
similarity between a natural-language query and all test cases in a project.

Architecture
------------
- No pgvector extension required — vectors are computed in-memory with numpy.
- Embeddings are NOT persisted; they are computed on each request against the
  live case corpus.  For a project with ≤5 000 cases this is fast enough
  (<200 ms per query at bge-m3 inference speed).
- A future migration may add a `title_embedding` column (vector) to
  ``test_management_cases`` for large projects — this module will serve as
  the fallback until then.

Each case is embedded as:
  "{case_key}: {title}. {objective or ''}. Tags: {', '.join(tags)}"

The most informative fields in one compact sentence so the model sees the
full context without truncation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.domains.test_management.models import TestCase

logger = logging.getLogger(__name__)

# ── Types ─────────────────────────────────────────────────────────────────────


@dataclass
class SimilarCaseResult:
    case_id: str
    case_key: str
    title: str
    score: float
    project_id: str
    tags: list[str]
    last_run_status: str | None


# ── Text serialisation ────────────────────────────────────────────────────────


def _case_text(case: TestCase) -> str:
    """Convert a TestCase to a single embed-friendly string."""
    parts = [f"{case.case_key}: {case.title}"]
    if case.objective:
        parts.append(case.objective)
    if case.preconditions:
        parts.append(f"Preconditions: {case.preconditions}")
    tags = case.tags or []
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    return ". ".join(parts)


# ── Embedding helpers ─────────────────────────────────────────────────────────


def _embed(texts: list[str]) -> list[list[float]] | None:
    """Call the AI Gateway to embed a batch of texts.

    Returns None if the gateway is unavailable (soft-fail).
    """
    try:
        from app.domains.ai.gateway_client import gateway_embed

        result: dict[str, Any] = gateway_embed(texts)
        return result.get("vectors")
    except Exception as exc:  # pragma: no cover
        logger.warning("semantic_search: gateway_embed failed — %s", exc)
        return None


def _cosine_similarity(query_vec: list[float], corpus_vecs: list[list[float]]) -> list[float]:
    """Batch cosine similarity between one query vector and N corpus vectors."""
    try:
        import numpy as np

        q = np.array(query_vec, dtype=np.float32)
        c = np.array(corpus_vecs, dtype=np.float32)

        # Normalise
        q_norm = q / (np.linalg.norm(q) + 1e-10)
        c_norms = np.linalg.norm(c, axis=1, keepdims=True) + 1e-10
        c_normalised = c / c_norms

        scores: np.ndarray = c_normalised @ q_norm
        return scores.tolist()
    except ImportError:
        logger.warning("semantic_search: numpy not available — returning zeros")
        return [0.0] * len(corpus_vecs)


# ── Public API ────────────────────────────────────────────────────────────────


def find_similar_cases(
    db: Session,
    project_id: str,
    query: str,
    *,
    k: int = 10,
    min_score: float = 0.30,
    exclude_case_id: str | None = None,
) -> list[SimilarCaseResult]:
    """Find the top-k test cases most semantically similar to `query`.

    Parameters
    ----------
    db:              SQLAlchemy session.
    project_id:      Scope results to this project.
    query:           Natural-language search query.
    k:               Maximum number of results to return.
    min_score:       Minimum cosine similarity threshold (0–1).
    exclude_case_id: Optionally exclude a specific case (e.g. the caller's own).

    Returns
    -------
    List of SimilarCaseResult sorted by descending similarity score.
    Falls back to empty list if the gateway is unavailable.
    """
    t0 = time.perf_counter()

    # 1. Load active cases for the project
    cases: list[TestCase] = (
        db.query(TestCase)
        .filter(
            TestCase.project_id == project_id,
            TestCase.archived == False,  # noqa: E712
        )
        .all()
    )

    if exclude_case_id:
        cases = [c for c in cases if c.id != exclude_case_id]

    if not cases:
        return []

    # 2. Embed query + corpus in one batch
    corpus_texts = [_case_text(c) for c in cases]
    all_texts = [query] + corpus_texts

    vectors = _embed(all_texts)
    if vectors is None:
        logger.warning(
            "semantic_search: embedding unavailable for project %s — returning empty",
            project_id,
        )
        return []

    query_vec = vectors[0]
    corpus_vecs = vectors[1:]

    # 3. Cosine similarity
    scores = _cosine_similarity(query_vec, corpus_vecs)

    # 4. Filter, sort, slice
    ranked: list[tuple[float, TestCase]] = [
        (score, case)
        for score, case in zip(scores, cases)
        if score >= min_score
    ]
    ranked.sort(key=lambda x: x[0], reverse=True)
    ranked = ranked[:k]

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.debug(
        "semantic_search: project=%s query=%r → %d results in %dms",
        project_id,
        query[:60],
        len(ranked),
        elapsed_ms,
    )

    return [
        SimilarCaseResult(
            case_id=case.id,
            case_key=case.case_key,
            title=case.title,
            score=round(score, 4),
            project_id=case.project_id,
            tags=case.tags or [],
            last_run_status=case.last_run_status,
        )
        for score, case in ranked
    ]
