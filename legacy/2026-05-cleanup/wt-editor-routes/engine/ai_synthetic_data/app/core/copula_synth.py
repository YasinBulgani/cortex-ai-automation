"""
CopulaSynthesizer — Gaussian Copula ile korelasyon koruyan sentetik veri.

Sklar teoremi geregince:
1. Her kolonun marjinal dagilimini ayri ogren (CDF donusumu)
2. Uniform [0,1] alaninda korelasyon yapisini ogren (copula)
3. Copula'dan ornekle -> marjinal tersleri ile gercek degerlere dondur

Bu modul SDV'ye bagimli degildir — NumPy/SciPy ile saf implementasyon.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.stats import gaussian_kde, norm

logger = logging.getLogger(__name__)


class CopulaSynthesizer:
    """Gaussian Copula tabanlı korelasyon koruyan tablo sentezleyici."""

    def __init__(self) -> None:
        self._marginals: dict[str, dict] = {}
        self._column_order: list[str] = []
        self._corr_matrix: np.ndarray | None = None
        self._fitted = False

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> None:
        """DataFrame'den marjinal dagilimlari ve copula korelasyonunu ogren."""
        self._column_order = df.columns.tolist()
        uniform_cols: list[np.ndarray] = []

        for col in self._column_order:
            series = df[col]
            marginal = self._fit_marginal(col, series)
            self._marginals[col] = marginal
            uniform_cols.append(marginal["uniform_values"])

        U = np.column_stack(uniform_cols)
        Z = norm.ppf(np.clip(U, 1e-6, 1 - 1e-6))

        self._corr_matrix = np.corrcoef(Z, rowvar=False)
        np.fill_diagonal(self._corr_matrix, 1.0)
        self._corr_matrix = self._nearest_positive_definite(self._corr_matrix)

        self._fitted = True
        logger.info("CopulaSynthesizer fit: %d kolon, corr shape %s",
                     len(self._column_order), self._corr_matrix.shape)

    # ------------------------------------------------------------------
    # Sample
    # ------------------------------------------------------------------

    def sample(self, n: int) -> pd.DataFrame:
        """Korelasyon koruyan n satirlik sentetik veri uret."""
        if not self._fitted:
            raise RuntimeError("Once fit() cagirin")

        Z = np.random.multivariate_normal(
            mean=np.zeros(len(self._column_order)),
            cov=self._corr_matrix,
            size=n,
        )
        U = norm.cdf(Z)

        data: dict[str, list] = {}
        for i, col in enumerate(self._column_order):
            marginal = self._marginals[col]
            data[col] = self._inverse_marginal(marginal, U[:, i])

        return pd.DataFrame(data)

    def conditional_sample(
        self, n: int, conditions: dict[str, Any],
    ) -> pd.DataFrame:
        """Kosullu uretim: belirli kolon degerlerini sabitleyerek ornekle."""
        df = self.sample(n * 3)
        for col, val in conditions.items():
            if col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    median = df[col].median()
                    if val == "high":
                        df = df[df[col] > median]
                    elif val == "low":
                        df = df[df[col] <= median]
                else:
                    df = df[df[col] == val]

        if len(df) >= n:
            return df.head(n).reset_index(drop=True)
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Marjinal Fit / Inverse
    # ------------------------------------------------------------------

    def _fit_marginal(self, col_name: str, series: pd.Series) -> dict:
        """Tek kolon icin marjinal dagilim ogren ve uniform [0,1]'e donustur."""
        clean = series.dropna()

        if pd.api.types.is_numeric_dtype(clean) and clean.nunique() > 10:
            values = clean.values.astype(float)
            try:
                kde = gaussian_kde(values, bw_method="scott")
                cdf_values = np.array([kde.integrate_box_1d(-np.inf, v) for v in values])
            except Exception:
                sorted_vals = np.sort(values)
                ranks = np.searchsorted(sorted_vals, values)
                cdf_values = ranks / len(sorted_vals)

            return {
                "type": "numeric",
                "kde_values": values,
                "min": float(values.min()),
                "max": float(values.max()),
                "uniform_values": np.clip(cdf_values, 1e-6, 1 - 1e-6),
            }
        else:
            cats = clean.value_counts(normalize=True)
            cat_map = {v: i / len(cats) for i, v in enumerate(cats.index)}
            uniform = np.array([cat_map.get(v, 0.5) for v in clean])
            uniform += np.random.uniform(0, 1 / max(len(cats), 1), size=len(uniform))
            uniform = np.clip(uniform, 1e-6, 1 - 1e-6)

            return {
                "type": "categorical",
                "categories": cats.index.tolist(),
                "probabilities": cats.values.tolist(),
                "uniform_values": uniform,
            }

    def _inverse_marginal(self, marginal: dict, u: np.ndarray) -> list:
        """Uniform [0,1] degerlerini orijinal marjinal dagilima dondur."""
        if marginal["type"] == "numeric":
            sorted_vals = np.sort(marginal["kde_values"])
            indices = (u * (len(sorted_vals) - 1)).astype(int)
            indices = np.clip(indices, 0, len(sorted_vals) - 1)
            values = sorted_vals[indices]
            noise = np.random.normal(0, (marginal["max"] - marginal["min"]) * 0.001, len(values))
            values = np.clip(values + noise, marginal["min"], marginal["max"])
            return values.tolist()
        else:
            cats = marginal["categories"]
            probs = marginal["probabilities"]
            cum_probs = np.cumsum(probs)
            result = []
            for val in u:
                idx = np.searchsorted(cum_probs, val)
                idx = min(idx, len(cats) - 1)
                result.append(cats[idx])
            return result

    @staticmethod
    def _nearest_positive_definite(A: np.ndarray) -> np.ndarray:
        """En yakin pozitif tanimli matris (Higham algoritmasi)."""
        B = (A + A.T) / 2
        eigvals, eigvecs = np.linalg.eigh(B)
        eigvals = np.maximum(eigvals, 1e-8)
        result = eigvecs @ np.diag(eigvals) @ eigvecs.T
        result = (result + result.T) / 2
        np.fill_diagonal(result, 1.0)
        return result
