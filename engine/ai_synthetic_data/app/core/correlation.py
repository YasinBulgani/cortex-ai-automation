"""
CorrelationAnalyzer — Kolonlar arasi bagimliliklari tespit ve raporlama.

Pearson (sayisal), Cramer's V (kategorik) ve kosullu dagilim analizi.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Kolon-kolon korelasyon ve bagimliliklari analiz eder."""

    def compute_correlation_matrix(self, df: pd.DataFrame) -> dict:
        """Hibrit korelasyon matrisi: Pearson (numeric) + Cramer's V (categorical)."""
        cols = df.columns.tolist()
        n = len(cols)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    matrix[i][j] = 1.0
                    continue
                val = self._pairwise_correlation(df[cols[i]], df[cols[j]])
                matrix[i][j] = val
                matrix[j][i] = val

        return {
            "columns": cols,
            "matrix": matrix.tolist(),
            "type": "hybrid_pearson_cramersv",
        }

    def find_strong_correlations(
        self, corr_result: dict, threshold: float = 0.5,
    ) -> list[dict]:
        """Esik degerinin uzerindeki korelasyonlari listele."""
        cols = corr_result["columns"]
        matrix = np.array(corr_result["matrix"])
        strong = []

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                val = abs(matrix[i][j])
                if val >= threshold:
                    strong.append({
                        "column_a": cols[i],
                        "column_b": cols[j],
                        "correlation": round(float(matrix[i][j]), 4),
                        "strength": "very_strong" if val >= 0.8 else "strong",
                    })

        return sorted(strong, key=lambda x: abs(x["correlation"]), reverse=True)

    def detect_conditional_distributions(
        self, df: pd.DataFrame, target_col: str, condition_col: str,
    ) -> dict:
        """Kosul kolonunun degerlerine gore hedef dagilim farklarini tespit et."""
        groups = df.groupby(condition_col)[target_col]
        group_stats = {}

        for name, group in groups:
            series = group.dropna()
            if len(series) < 3:
                continue

            stats: dict[str, Any] = {"count": len(series)}
            if pd.api.types.is_numeric_dtype(series):
                stats.update({
                    "mean": round(float(series.mean()), 4),
                    "std": round(float(series.std()), 4),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "median": float(series.median()),
                })
            else:
                top = series.value_counts(normalize=True).head(5)
                stats["top_values"] = {str(k): round(float(v), 4) for k, v in top.items()}

            group_stats[str(name)] = stats

        means = [s["mean"] for s in group_stats.values() if "mean" in s]
        significant_diff = (max(means) / max(min(means), 1e-9) > 2.0) if len(means) >= 2 else False

        return {
            "target": target_col,
            "condition": condition_col,
            "groups": group_stats,
            "significant_difference": significant_diff,
        }

    def export_correlation_report(self, df: pd.DataFrame) -> dict:
        """Tam korelasyon raporu uret."""
        corr = self.compute_correlation_matrix(df)
        strong = self.find_strong_correlations(corr)

        return {
            "correlation_matrix": corr,
            "strong_correlations": strong,
            "total_columns": len(corr["columns"]),
            "strong_pair_count": len(strong),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _pairwise_correlation(a: pd.Series, b: pd.Series) -> float:
        """Iki kolon arasi korelasyon: Pearson veya Cramer's V."""
        a_num = pd.api.types.is_numeric_dtype(a)
        b_num = pd.api.types.is_numeric_dtype(b)

        if a_num and b_num:
            clean = pd.DataFrame({"a": a, "b": b}).dropna()
            if len(clean) < 3:
                return 0.0
            return float(clean["a"].corr(clean["b"]))

        return CorrelationAnalyzer._cramers_v(a, b)

    @staticmethod
    def _cramers_v(a: pd.Series, b: pd.Series) -> float:
        """Cramer's V — iki kategorik kolon arasi iliski gucu."""
        confusion = pd.crosstab(a, b)
        n = confusion.sum().sum()
        if n == 0:
            return 0.0

        chi2 = 0.0
        row_totals = confusion.sum(axis=1)
        col_totals = confusion.sum(axis=0)
        for i in range(confusion.shape[0]):
            for j in range(confusion.shape[1]):
                expected = row_totals.iloc[i] * col_totals.iloc[j] / n
                if expected > 0:
                    chi2 += (confusion.iloc[i, j] - expected) ** 2 / expected

        k = min(confusion.shape) - 1
        if k <= 0 or n <= 1:
            return 0.0
        return float(np.sqrt(chi2 / (n * k)))
