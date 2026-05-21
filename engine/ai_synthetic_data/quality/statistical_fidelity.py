"""
İstatistiksel sadakat metrikleri.

Sentetik verinin orijinal veriye ne kadar benzediğini ölçer.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


@dataclass
class FidelityScore:
    column: str
    metric: str
    score: float
    details: str

    def to_dict(self) -> dict:
        return {"column": self.column, "metric": self.metric, "score": round(self.score, 4), "details": self.details}


class StatisticalFidelity:
    """Orijinal ve sentetik veri arasındaki istatistiksel sadakati ölçer."""

    def compare_distributions(
        self, original: list[dict], synthetic: list[dict], columns: list[str] | None = None
    ) -> list[FidelityScore]:
        if not original or not synthetic:
            return []

        cols = columns or list(original[0].keys())
        scores: list[FidelityScore] = []

        for col in cols:
            orig_vals = [r.get(col) for r in original if r.get(col) is not None]
            syn_vals = [r.get(col) for r in synthetic if r.get(col) is not None]
            if not orig_vals or not syn_vals:
                continue

            is_numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in orig_vals)
            if is_numeric:
                try:
                    scores.append(self._compare_numeric(col, orig_vals, syn_vals))
                except (TypeError, ValueError):
                    scores.append(self._compare_categorical(col, orig_vals, syn_vals))
            else:
                scores.append(self._compare_categorical(col, orig_vals, syn_vals))

        return scores

    @staticmethod
    def _compare_numeric(col: str, orig: list, syn: list) -> FidelityScore:
        o_mean = sum(orig) / len(orig)
        s_mean = sum(syn) / len(syn)
        o_std = (sum((x - o_mean) ** 2 for x in orig) / len(orig)) ** 0.5
        s_std = (sum((x - s_mean) ** 2 for x in syn) / len(syn)) ** 0.5

        mean_diff = abs(o_mean - s_mean) / max(abs(o_mean), 1e-10)
        std_diff = abs(o_std - s_std) / max(o_std, 1e-10)
        score = max(0.0, 1.0 - (mean_diff + std_diff) / 2)

        return FidelityScore(
            column=col,
            metric="numeric_distribution",
            score=score,
            details=f"orig(μ={o_mean:.2f}, σ={o_std:.2f}) vs syn(μ={s_mean:.2f}, σ={s_std:.2f})",
        )

    @staticmethod
    def _compare_categorical(col: str, orig: list, syn: list) -> FidelityScore:
        o_counter = Counter(str(v) for v in orig)
        s_counter = Counter(str(v) for v in syn)
        all_keys = set(o_counter.keys()) | set(s_counter.keys())

        o_total = sum(o_counter.values())
        s_total = sum(s_counter.values())

        kl_div = 0.0
        smoothing = 1e-10
        for key in all_keys:
            p = o_counter.get(key, 0) / o_total
            q = max(s_counter.get(key, 0) / s_total, smoothing)
            if p > 0:
                kl_div += p * math.log(p / q)

        score = max(0.0, 1.0 - min(kl_div, 1.0))

        return FidelityScore(
            column=col,
            metric="categorical_distribution",
            score=score,
            details=f"KL-divergence={kl_div:.4f}, unique_orig={len(o_counter)}, unique_syn={len(s_counter)}",
        )
