"""
KDESynthesizer — KDE bazli gercekci sentetik veri uretimi.

Her sayisal kolon icin Kernel Density Estimation ile orijinal dagilimi
ogrenir ve bu dagilimdan ornekleyerek sentetik veri uretir.
Kosullu uretim (conditional generation) destekler.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from app.core.distribution import DistributionFitter

logger = logging.getLogger(__name__)


class KDESynthesizer:
    """KDE ve tam frekans tabanlı sentetik tablo uretici."""

    def __init__(self) -> None:
        self._fitter = DistributionFitter()
        self._column_models: dict[str, Any] = {}
        self._column_types: dict[str, str] = {}
        self._fitted = False

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> None:
        """DataFrame'deki her kolon icin model ogren."""
        self._column_models.clear()
        self._column_types.clear()

        for col in df.columns:
            series = df[col].dropna()
            if len(series) < 5:
                self._column_types[col] = "constant"
                self._column_models[col] = series.tolist()[:1] or [""]
                continue

            if pd.api.types.is_numeric_dtype(series):
                self._column_types[col] = "numeric"
                try:
                    kde = self._fitter.fit_kde(series.values.astype(float))
                    self._column_models[col] = {
                        "kde": kde,
                        "min": float(series.min()),
                        "max": float(series.max()),
                    }
                except Exception:
                    self._column_models[col] = {
                        "mean": float(series.mean()),
                        "std": float(series.std()),
                        "min": float(series.min()),
                        "max": float(series.max()),
                    }
            else:
                self._column_types[col] = "categorical"
                counts = series.value_counts(normalize=True)
                self._column_models[col] = {
                    "values": counts.index.tolist(),
                    "weights": counts.values.tolist(),
                }

        self._fitted = True
        logger.info("KDESynthesizer fit tamamlandi: %d kolon", len(df.columns))

    # ------------------------------------------------------------------
    # Sample
    # ------------------------------------------------------------------

    def sample(self, n: int) -> pd.DataFrame:
        """Fit edilen modelden n satir sentetik veri uret."""
        if not self._fitted:
            raise RuntimeError("Once fit() cagirin")

        data: dict[str, list] = {}
        for col, ctype in self._column_types.items():
            model = self._column_models[col]

            if ctype == "numeric":
                if "kde" in model:
                    values = self._fitter.sample_from_kde(
                        model["kde"], n, clip_min=model["min"], clip_max=model["max"],
                    )
                else:
                    values = np.random.normal(model["mean"], max(model["std"], 1e-6), n)
                    values = np.clip(values, model["min"], model["max"])
                data[col] = values.tolist()

            elif ctype == "categorical":
                data[col] = np.random.choice(
                    model["values"], size=n, p=model["weights"],
                ).tolist()

            else:
                data[col] = (model * n)[:n]

        return pd.DataFrame(data)

    # ------------------------------------------------------------------
    # Kosullu Uretim
    # ------------------------------------------------------------------

    def fit_conditional(
        self, df: pd.DataFrame, target_col: str, condition_col: str,
    ) -> None:
        """Kosul kolonunun her degeri icin ayri KDE/frekans modeli ogren."""
        self._conditional_models: dict[str, dict] = {}
        groups = df.groupby(condition_col)

        for group_val, group_df in groups:
            series = group_df[target_col].dropna()
            if len(series) < 3:
                continue

            if pd.api.types.is_numeric_dtype(series):
                try:
                    kde = self._fitter.fit_kde(series.values.astype(float))
                    self._conditional_models[str(group_val)] = {
                        "type": "numeric",
                        "kde": kde,
                        "min": float(series.min()),
                        "max": float(series.max()),
                    }
                except Exception:
                    self._conditional_models[str(group_val)] = {
                        "type": "numeric",
                        "mean": float(series.mean()),
                        "std": float(series.std()),
                        "min": float(series.min()),
                        "max": float(series.max()),
                    }
            else:
                counts = series.value_counts(normalize=True)
                self._conditional_models[str(group_val)] = {
                    "type": "categorical",
                    "values": counts.index.tolist(),
                    "weights": counts.values.tolist(),
                }

        logger.info(
            "Kosullu model ogrendi: %s | %s -> %d grup",
            condition_col, target_col, len(self._conditional_models),
        )

    def sample_conditional(
        self, n: int, condition_values: list[str],
    ) -> np.ndarray:
        """Kosul degerlerine gore hedef kolon uret."""
        results = []
        for cv in condition_values:
            model = self._conditional_models.get(str(cv))
            if model is None:
                results.append(np.nan)
                continue

            if model["type"] == "numeric":
                if "kde" in model:
                    val = self._fitter.sample_from_kde(
                        model["kde"], 1, clip_min=model["min"], clip_max=model["max"],
                    )[0]
                else:
                    val = np.clip(
                        np.random.normal(model["mean"], max(model["std"], 1e-6)),
                        model["min"], model["max"],
                    )
                results.append(float(val))
            else:
                val = np.random.choice(model["values"], p=model["weights"])
                results.append(val)

        return np.array(results)
