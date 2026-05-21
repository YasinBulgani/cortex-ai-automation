"""Retrieval metrikleri: Precision@k, MRR, Recall@k.

Tüm scorer'lar şu sözleşmeyi bekler:

    case.expected["relevant_ids"]  : list[str]   # doğru (relevant) item id'leri
    actual["ranked_ids"]           : list[str]   # SUT'un sıralı çıktısı, top-N

Neden ``top_1`` alanı yok: retrieval senaryosunda sıralı liste tamdır —
``ranked_ids[0]`` top-1 olur, ``exact_match`` bu anlamda ayrı scorer.
Bu scorer'lar kümesel bilgi üstünden çalışır.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ..schemas import EvalCase, ScorerOutput


def _norm_relevant(case: EvalCase) -> List[str]:
    raw = case.expected.get("relevant_ids") or []
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def _norm_ranked(actual: Dict[str, Any]) -> List[str]:
    raw = actual.get("ranked_ids") or []
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


@dataclass
class PrecisionAtKScorer:
    """Precision@k: top-k içinde kaç tanesi relevant?"""

    k: int = 1
    name: str = "precision_at_1"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        relevant = set(_norm_relevant(case))
        ranked = _norm_ranked(actual)
        top_k = ranked[: self.k]
        if not top_k:
            value = 0.0
        else:
            hits = sum(1 for r in top_k if r in relevant)
            value = hits / float(len(top_k))
        # Geçmiş eşiği: default %100 (tam hit). Suite threshold'u
        # ortalamalar üstünden esnek davranabilir.
        return ScorerOutput(
            name=self.name,
            value=value,
            passed=value >= 1.0 if self.k == 1 else value > 0.0,
            details={
                "k": self.k,
                "top_k": top_k,
                "relevant": sorted(relevant),
            },
        )


@dataclass
class MRRScorer:
    """Mean Reciprocal Rank: ilk relevant item'ın 1/rank'i. Yoksa 0.

    Per-case "mean" aslında yok — bu scorer tek case için 1/rank verir.
    Suite aggregate bunların ortalamasını alır → geleneksel MRR.
    """

    name: str = "mrr"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        relevant = set(_norm_relevant(case))
        ranked = _norm_ranked(actual)
        rr = 0.0
        rank_found = 0
        for i, r in enumerate(ranked, start=1):
            if r in relevant:
                rr = 1.0 / i
                rank_found = i
                break
        return ScorerOutput(
            name=self.name,
            value=rr,
            passed=rr > 0.0,
            details={
                "rank_of_first_relevant": rank_found,
                "ranked_len": len(ranked),
            },
        )


@dataclass
class RecallAtKScorer:
    """Recall@k: top-k içindeki relevant sayısı / toplam relevant sayısı."""

    k: int = 5
    name: str = "recall_at_5"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        relevant = set(_norm_relevant(case))
        if not relevant:
            return ScorerOutput(
                name=self.name,
                value=0.0,
                passed=False,
                details={"reason": "relevant_ids boş"},
            )
        ranked = _norm_ranked(actual)[: self.k]
        hits = sum(1 for r in ranked if r in relevant)
        value = hits / float(len(relevant))
        return ScorerOutput(
            name=self.name,
            value=value,
            passed=value >= 1.0,  # tüm relevant'lar top-k'da ise tam geçer
            details={"k": self.k, "hits": hits, "total_relevant": len(relevant)},
        )
