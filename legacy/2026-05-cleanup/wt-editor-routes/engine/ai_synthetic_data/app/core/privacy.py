"""
PrivacyGuard — Diferansiyel gizlilik, k-anonimlik ve PII maskeleme.

Sentetik verinin gizlilik garantilerini saglayan modul:
- epsilon-DP noise injection (Laplace mekanizmasi)
- k-anonimlik kontrolu
- PII maskeleme (hash, redact, generalize)
- DCR (Distance to Closest Record) risk hesaplama
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PrivacyGuard:
    """Sentetik veri icin gizlilik korumalari."""

    # ------------------------------------------------------------------
    # Diferansiyel Gizlilik (Laplace Mekanizmasi)
    # ------------------------------------------------------------------

    def apply_dp_noise(
        self, df: pd.DataFrame, epsilon: float = 3.0,
        numeric_only: bool = True,
    ) -> pd.DataFrame:
        """Sayisal kolonlara Laplace noise ekle (epsilon-DP)."""
        result = df.copy()

        for col in result.columns:
            if not pd.api.types.is_numeric_dtype(result[col]):
                continue

            series = result[col].dropna()
            if len(series) == 0:
                continue

            sensitivity = float(series.max() - series.min())
            if sensitivity == 0:
                continue

            scale = sensitivity / max(epsilon, 0.01)
            noise = np.random.laplace(loc=0, scale=scale, size=len(result))

            mask = result[col].notna()
            result.loc[mask, col] = result.loc[mask, col] + noise[mask]

        logger.info("DP noise uygulandı: epsilon=%.2f, %d kolon", epsilon, len(result.columns))
        return result

    # ------------------------------------------------------------------
    # k-Anonimlik Kontrolu
    # ------------------------------------------------------------------

    def check_k_anonymity(
        self, df: pd.DataFrame, quasi_identifiers: list[str], k: int = 5,
    ) -> dict:
        """Quasi-identifier kombinasyonlarinin k-anonimlik kontrolu."""
        valid_qi = [q for q in quasi_identifiers if q in df.columns]
        if not valid_qi:
            return {"satisfies_k": True, "k": k, "message": "Quasi-identifier bulunamadi"}

        groups = df.groupby(valid_qi).size()
        min_group = int(groups.min())
        violations = int((groups < k).sum())
        total_groups = len(groups)

        return {
            "satisfies_k": min_group >= k,
            "k_target": k,
            "min_group_size": min_group,
            "violations": violations,
            "total_groups": total_groups,
            "violation_percentage": round(violations / max(total_groups, 1) * 100, 2),
            "quasi_identifiers": valid_qi,
        }

    # ------------------------------------------------------------------
    # PII Maskeleme
    # ------------------------------------------------------------------

    def mask_pii(
        self, df: pd.DataFrame, pii_columns: dict[str, str],
    ) -> pd.DataFrame:
        """PII kolonlarini belirtilen stratejiye gore maskele.

        Args:
            pii_columns: {"kolon_adi": "strateji"} — strateji: hash, redact, generalize, partial
        """
        result = df.copy()

        for col, strategy in pii_columns.items():
            if col not in result.columns:
                continue

            if strategy == "hash":
                result[col] = result[col].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16] if pd.notna(x) else x
                )
            elif strategy == "redact":
                result[col] = "***REDACTED***"
            elif strategy == "partial":
                result[col] = result[col].apply(lambda x: self._partial_mask(x))
            elif strategy == "generalize":
                if pd.api.types.is_numeric_dtype(result[col]):
                    result[col] = self._generalize_numeric(result[col])
                else:
                    result[col] = result[col].apply(
                        lambda x: str(x)[:2] + "***" if pd.notna(x) and len(str(x)) > 2 else x
                    )

        logger.info("PII maskeleme: %d kolon", len(pii_columns))
        return result

    # ------------------------------------------------------------------
    # Privacy Risk — DCR (Distance to Closest Record)
    # ------------------------------------------------------------------

    def compute_dcr(
        self, real_df: pd.DataFrame, synth_df: pd.DataFrame,
        sample_size: int = 1000,
    ) -> dict:
        """Sentetik kayitlarin gercek kayitlara mesafesini hesapla."""
        numeric_cols = []
        for col in real_df.columns:
            if col in synth_df.columns and pd.api.types.is_numeric_dtype(real_df[col]):
                numeric_cols.append(col)

        if not numeric_cols:
            return {"dcr_mean": 1.0, "dcr_min": 1.0, "risk_level": "low", "message": "Sayisal kolon yok"}

        real_vals = real_df[numeric_cols].dropna().values
        synth_vals = synth_df[numeric_cols].dropna().values

        if len(real_vals) == 0 or len(synth_vals) == 0:
            return {"dcr_mean": 1.0, "dcr_min": 1.0, "risk_level": "low"}

        ranges = real_vals.max(axis=0) - real_vals.min(axis=0)
        ranges[ranges == 0] = 1.0
        real_norm = real_vals / ranges
        synth_norm = synth_vals / ranges

        if len(synth_norm) > sample_size:
            indices = np.random.choice(len(synth_norm), sample_size, replace=False)
            synth_sample = synth_norm[indices]
        else:
            synth_sample = synth_norm

        min_distances = []
        for sv in synth_sample:
            dists = np.sqrt(np.sum((real_norm - sv) ** 2, axis=1))
            min_distances.append(float(dists.min()))

        dcr_mean = float(np.mean(min_distances))
        dcr_min = float(np.min(min_distances))
        dcr_p5 = float(np.percentile(min_distances, 5))

        if dcr_p5 < 0.01:
            risk = "critical"
        elif dcr_p5 < 0.05:
            risk = "high"
        elif dcr_p5 < 0.1:
            risk = "medium"
        else:
            risk = "low"

        return {
            "dcr_mean": round(dcr_mean, 6),
            "dcr_min": round(dcr_min, 6),
            "dcr_p5": round(dcr_p5, 6),
            "dcr_p95": round(float(np.percentile(min_distances, 95)), 6),
            "risk_level": risk,
            "sample_size": len(synth_sample),
            "numeric_columns_used": numeric_cols,
        }

    def compute_privacy_report(
        self, real_df: pd.DataFrame, synth_df: pd.DataFrame,
        quasi_identifiers: list[str] | None = None, k: int = 5,
    ) -> dict:
        """Kapsamli gizlilik raporu."""
        dcr = self.compute_dcr(real_df, synth_df)

        k_anon = {"checked": False}
        if quasi_identifiers:
            k_anon = self.check_k_anonymity(synth_df, quasi_identifiers, k)
            k_anon["checked"] = True

        overall_risk = dcr["risk_level"]
        if k_anon.get("checked") and not k_anon.get("satisfies_k", True):
            if overall_risk == "low":
                overall_risk = "medium"

        return {
            "dcr_analysis": dcr,
            "k_anonymity": k_anon,
            "overall_risk": overall_risk,
            "recommendation": self._risk_recommendation(overall_risk),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _partial_mask(value: Any) -> str:
        s = str(value) if pd.notna(value) else ""
        if len(s) <= 4:
            return "****"
        return s[:2] + "*" * (len(s) - 4) + s[-2:]

    @staticmethod
    def _generalize_numeric(series: pd.Series) -> pd.Series:
        """Sayisal degerleri aralik ifadelerine donustur."""
        q = series.quantile([0, 0.25, 0.5, 0.75, 1.0])
        bins = [q[0] - 1, q[0.25], q[0.5], q[0.75], q[1.0] + 1]
        labels = [
            f"{bins[0]:.0f}-{bins[1]:.0f}",
            f"{bins[1]:.0f}-{bins[2]:.0f}",
            f"{bins[2]:.0f}-{bins[3]:.0f}",
            f"{bins[3]:.0f}-{bins[4]:.0f}",
        ]
        return pd.cut(series, bins=bins, labels=labels, include_lowest=True)

    @staticmethod
    def _risk_recommendation(level: str) -> str:
        recs = {
            "critical": "Sentetik veri orijinale cok yakin — epsilon degerini dusurun veya noise artirin",
            "high": "Gizlilik riski yuksek — k-anonimlik kontrolu yapip PII maskeleme uygulayin",
            "medium": "Kabul edilebilir risk — uretim ortami icin uygun, dis paylasimda dikkat",
            "low": "Dusuk risk — dis paylasim icin uygun",
        }
        return recs.get(level, "Bilinmeyen risk seviyesi")
