"""
KDE (Kernel Density Estimation) tabanlı sentetik veri üretici.

Orijinal verinin dağılımını KDE ile modelleyerek
istatistiksel olarak gerçekçi sentetik veri üretir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class KDEGeneratorConfig:
    bandwidth: float = 0.5
    kernel: str = "gaussian"
    sample_size: int = 1000


class KDEGenerator:
    """Kernel Density Estimation tabanlı sentetik veri üretici."""

    def __init__(self, config: KDEGeneratorConfig | None = None, seed: int = 42):
        self.config = config or KDEGeneratorConfig()
        self.rng = np.random.RandomState(seed)
        self._fitted_columns: dict[str, Any] = {}

    def fit(self, records: list[dict], numeric_columns: list[str] | None = None):
        """Orijinal veri üzerinde KDE modeli eğitir."""
        if not records:
            return

        all_cols = list(records[0].keys()) if records else []
        num_cols = numeric_columns or [
            c for c in all_cols
            if all(isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool) for r in records[:20] if r.get(c) is not None)
        ]

        for col in num_cols:
            values = np.array([r[col] for r in records if col in r and r[col] is not None], dtype=float)
            if len(values) < 2:
                continue
            from sklearn.neighbors import KernelDensity
            kde = KernelDensity(bandwidth=self.config.bandwidth, kernel=self.config.kernel)
            kde.fit(values.reshape(-1, 1))
            self._fitted_columns[col] = {
                "model": kde,
                "min": float(values.min()),
                "max": float(values.max()),
                "dtype": "int" if all(v == int(v) for v in values) else "float",
            }

    def generate(self, count: int | None = None) -> dict[str, list]:
        """Eğitilmiş KDE modellerinden sentetik değerler üretir."""
        n = count or self.config.sample_size
        result: dict[str, list] = {}

        for col, info in self._fitted_columns.items():
            samples = info["model"].sample(n, random_state=self.rng).flatten()
            samples = np.clip(samples, info["min"], info["max"])
            if info["dtype"] == "int":
                samples = np.round(samples).astype(int)
            result[col] = samples.tolist()

        return result

    @property
    def fitted_columns(self) -> list[str]:
        return list(self._fitted_columns.keys())
