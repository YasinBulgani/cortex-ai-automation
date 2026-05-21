"""Katman 4 — Stability Scoring."""
from __future__ import annotations

from dataclasses import dataclass

from ...schemas.locator import LocatorCandidate, LocatorStrategy


@dataclass(frozen=True)
class ScoreWeights:
    uniqueness: float = 0.4
    semantic: float = 0.3
    temporal: float = 0.3

    def total(self) -> float:
        return self.uniqueness + self.semantic + self.temporal


DEFAULT_WEIGHTS = ScoreWeights()


def score_locator(
    candidate: LocatorCandidate,
    *,
    history_success_rate: float | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> float:
    uniq_score = _uniqueness_score(candidate.count)
    sem_score = candidate.semantic_strength
    temp_score = history_success_rate if history_success_rate is not None else 0.5

    total = (
        weights.uniqueness * uniq_score
        + weights.semantic * sem_score
        + weights.temporal * temp_score
    )

    candidate.score_breakdown = {
        "uniqueness": round(uniq_score, 3),
        "semantic": round(sem_score, 3),
        "temporal": round(temp_score, 3),
    }
    candidate.stability_score = round(min(max(total, 0.0), 1.0), 3)
    return candidate.stability_score


def _uniqueness_score(count: int) -> float:
    if count == 1:
        return 1.0
    if count == 0:
        return 0.0
    if count == -1:
        return 0.5
    if count == 2:
        return 0.6
    if count == 3:
        return 0.4
    return 0.2


def aggregate_score(
    candidates: list[LocatorCandidate],
) -> tuple[LocatorCandidate | None, list[LocatorCandidate]]:
    if not candidates:
        return None, []

    sorted_c = sorted(candidates, key=lambda c: -c.stability_score)

    primary = None
    for c in sorted_c:
        if c.stability_score >= 0.7 and c.count == 1:
            primary = c
            break

    if primary is None and sorted_c:
        primary = sorted_c[0]

    fallbacks: list[LocatorCandidate] = []
    seen_strategies: set[LocatorStrategy] = set()
    if primary:
        seen_strategies.add(primary.strategy)

    for c in sorted_c:
        if c is primary:
            continue
        if c.stability_score < 0.3:
            continue
        if c.strategy in seen_strategies:
            continue
        fallbacks.append(c)
        seen_strategies.add(c.strategy)
        if len(fallbacks) >= 4:
            break

    return primary, fallbacks
