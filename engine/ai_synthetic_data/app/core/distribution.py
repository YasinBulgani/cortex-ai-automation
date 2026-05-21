"""
DistributionFitter — KDE, GMM ve parametrik dagilim fit/sampling.

Orijinal veriden gercek dagilimi ogrenir ve sentetik ornekler uretir.
"""
from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats as sp_stats
from scipy.stats import gaussian_kde

logger = logging.getLogger(__name__)

CANDIDATE_DISTRIBUTIONS = [
    "norm", "lognorm", "expon", "gamma", "beta",
    "pareto", "uniform", "weibull_min",
]


@dataclass
class FitResult:
    """Tek bir dagilim fit sonucu."""
    distribution_name: str
    params: tuple
    ks_statistic: float
    p_value: float

    def to_dict(self) -> dict:
        return {
            "distribution": self.distribution_name,
            "params": [float(p) for p in self.params],
            "ks_statistic": round(self.ks_statistic, 6),
            "p_value": round(self.p_value, 6),
        }


class DistributionFitter:
    """Veriden dagilim ogrenir, fit eder ve ornekler uretir."""

    # ------------------------------------------------------------------
    # Parametrik Fit
    # ------------------------------------------------------------------

    def fit_best_distribution(self, data: np.ndarray) -> FitResult:
        """Aday dagilimlar arasindan KS testi ile en uygununu sec."""
        clean = data[np.isfinite(data)]
        if len(clean) < 20:
            return FitResult("uniform", (float(clean.min()), float(clean.ptp())), 1.0, 0.0)

        best: FitResult | None = None
        for name in CANDIDATE_DISTRIBUTIONS:
            try:
                dist = getattr(sp_stats, name)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    params = dist.fit(clean)
                ks_stat, p_val = sp_stats.kstest(clean, name, args=params)
                candidate = FitResult(name, params, ks_stat, p_val)
                if best is None or ks_stat < best.ks_statistic:
                    best = candidate
            except Exception:
                continue

        return best or FitResult("norm", (float(clean.mean()), float(clean.std())), 1.0, 0.0)

    def fit_parametric(self, data: np.ndarray, dist_name: str) -> FitResult:
        """Belirli bir dagilimi fit et."""
        clean = data[np.isfinite(data)]
        dist = getattr(sp_stats, dist_name)
        params = dist.fit(clean)
        ks_stat, p_val = sp_stats.kstest(clean, dist_name, args=params)
        return FitResult(dist_name, params, ks_stat, p_val)

    def sample_from_parametric(
        self, dist_name: str, params: tuple, n: int, clip_min: float | None = None, clip_max: float | None = None,
    ) -> np.ndarray:
        """Parametrik dagilimdan n adet ornekle."""
        dist = getattr(sp_stats, dist_name)
        samples = dist.rvs(*params, size=n)
        if clip_min is not None or clip_max is not None:
            samples = np.clip(samples, clip_min, clip_max)
        return samples

    # ------------------------------------------------------------------
    # KDE (Kernel Density Estimation)
    # ------------------------------------------------------------------

    def fit_kde(self, data: np.ndarray, bw_method: str = "scott") -> gaussian_kde:
        """Gaussian KDE modeli olustur."""
        clean = data[np.isfinite(data)]
        if len(clean) < 5:
            raise ValueError("KDE icin en az 5 veri noktasi gerekli")
        return gaussian_kde(clean, bw_method=bw_method)

    def sample_from_kde(
        self, kde_model: gaussian_kde, n: int, clip_min: float | None = None, clip_max: float | None = None,
    ) -> np.ndarray:
        """KDE modelinden n adet ornekle."""
        samples = kde_model.resample(n).flatten()
        if clip_min is not None or clip_max is not None:
            samples = np.clip(samples, clip_min, clip_max)
        return samples

    # ------------------------------------------------------------------
    # GMM (Gaussian Mixture Model)
    # ------------------------------------------------------------------

    def fit_gmm(self, data: np.ndarray, max_components: int = 5) -> dict:
        """BIC ile optimal bilesen sayisini secip GMM fit et."""
        from sklearn.mixture import GaussianMixture

        clean = data[np.isfinite(data)].reshape(-1, 1)
        if len(clean) < 10:
            raise ValueError("GMM icin en az 10 veri noktasi gerekli")

        best_bic = np.inf
        best_model = None
        best_k = 1

        for k in range(1, min(max_components + 1, len(clean))):
            try:
                gmm = GaussianMixture(n_components=k, random_state=42, max_iter=200)
                gmm.fit(clean)
                bic = gmm.bic(clean)
                if bic < best_bic:
                    best_bic = bic
                    best_model = gmm
                    best_k = k
            except Exception:
                break

        return {
            "model": best_model,
            "n_components": best_k,
            "bic": float(best_bic),
            "means": best_model.means_.flatten().tolist() if best_model else [],
            "weights": best_model.weights_.tolist() if best_model else [],
        }

    def sample_from_gmm(
        self, gmm_result: dict, n: int, clip_min: float | None = None, clip_max: float | None = None,
    ) -> np.ndarray:
        """GMM modelinden n adet ornekle."""
        model = gmm_result["model"]
        if model is None:
            return np.random.randn(n)
        samples = model.sample(n)[0].flatten()
        if clip_min is not None or clip_max is not None:
            samples = np.clip(samples, clip_min, clip_max)
        return samples

    # ------------------------------------------------------------------
    # Dagilim Istatistikleri
    # ------------------------------------------------------------------

    @staticmethod
    def compute_distribution_stats(data: np.ndarray) -> dict:
        """Carpiklik, basiklik, normallik testi hesapla."""
        clean = data[np.isfinite(data)]
        if len(clean) < 8:
            return {"skewness": 0.0, "kurtosis": 0.0, "is_normal": False, "shapiro_p": 0.0}

        skew = float(sp_stats.skew(clean))
        kurt = float(sp_stats.kurtosis(clean))

        sample_for_test = clean[:5000] if len(clean) > 5000 else clean
        try:
            _, shapiro_p = sp_stats.shapiro(sample_for_test)
        except Exception:
            shapiro_p = 0.0

        return {
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "is_normal": bool(shapiro_p > 0.05),
            "shapiro_p": round(float(shapiro_p), 6),
        }

    @staticmethod
    def compute_histogram(data: np.ndarray, bins: int = 50) -> dict:
        """Normalize histogram doner."""
        clean = data[np.isfinite(data)]
        counts, bin_edges = np.histogram(clean, bins=bins, density=True)
        return {
            "counts": counts.tolist(),
            "bin_edges": bin_edges.tolist(),
            "bins": bins,
        }

    @staticmethod
    def compute_percentiles(data: np.ndarray) -> dict:
        clean = data[np.isfinite(data)]
        if len(clean) == 0:
            return {}
        return {
            "p1": float(np.percentile(clean, 1)),
            "p5": float(np.percentile(clean, 5)),
            "q1": float(np.percentile(clean, 25)),
            "median": float(np.percentile(clean, 50)),
            "q3": float(np.percentile(clean, 75)),
            "p95": float(np.percentile(clean, 95)),
            "p99": float(np.percentile(clean, 99)),
            "iqr": float(np.percentile(clean, 75) - np.percentile(clean, 25)),
        }
