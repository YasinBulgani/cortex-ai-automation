"""
QualityEvaluator — Sentetik veri kalite metrikleri.

Uc boyutlu degerlendirme:
1. Sadakat (Fidelity): KL divergence, JS distance, KS test, korelasyon farki
2. Faydalilik (Utility): ML utility (Train Synthetic Test Real)
3. Gizlilik (Privacy): DCR skoru (PrivacyGuard'dan)
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """Sentetik verinin orijinale sadakatini ve faydaliligini olcer."""

    # ------------------------------------------------------------------
    # Sadakat (Fidelity) Metrikleri
    # ------------------------------------------------------------------

    def kl_divergence(self, real: pd.Series, synth: pd.Series, bins: int = 50) -> float:
        """Kolon bazli KL Divergence (D_KL(P || Q))."""
        r = real.dropna().values.astype(float)
        s = synth.dropna().values.astype(float)
        if len(r) < 10 or len(s) < 10:
            return float("inf")

        all_vals = np.concatenate([r, s])
        bin_edges = np.histogram_bin_edges(all_vals, bins=bins)

        p, _ = np.histogram(r, bins=bin_edges, density=True)
        q, _ = np.histogram(s, bins=bin_edges, density=True)

        p = p + 1e-10
        q = q + 1e-10
        p = p / p.sum()
        q = q / q.sum()

        return float(np.sum(p * np.log(p / q)))

    def js_distance(self, real: pd.Series, synth: pd.Series, bins: int = 50) -> float:
        """Jensen-Shannon Distance (simetrik, 0-1 arasi)."""
        r = real.dropna().values.astype(float)
        s = synth.dropna().values.astype(float)
        if len(r) < 10 or len(s) < 10:
            return 1.0

        all_vals = np.concatenate([r, s])
        bin_edges = np.histogram_bin_edges(all_vals, bins=bins)

        p, _ = np.histogram(r, bins=bin_edges, density=True)
        q, _ = np.histogram(s, bins=bin_edges, density=True)

        p = p + 1e-10
        q = q + 1e-10
        p = p / p.sum()
        q = q / q.sum()

        m = (p + q) / 2
        jsd = 0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m))
        return float(np.sqrt(max(jsd, 0)))

    def ks_test(self, real: pd.Series, synth: pd.Series) -> dict:
        """Kolmogorov-Smirnov testi — iki dagilimin farki."""
        r = real.dropna().values.astype(float)
        s = synth.dropna().values.astype(float)
        if len(r) < 5 or len(s) < 5:
            return {"statistic": 1.0, "p_value": 0.0, "same_distribution": False}

        stat, p_val = sp_stats.ks_2samp(r, s)
        return {
            "statistic": round(float(stat), 6),
            "p_value": round(float(p_val), 6),
            "same_distribution": bool(p_val > 0.05),
        }

    def correlation_diff(self, real_df: pd.DataFrame, synth_df: pd.DataFrame) -> dict:
        """Korelasyon matrisi farki (Frobenius norm)."""
        common_numeric = []
        for col in real_df.columns:
            if col in synth_df.columns:
                if pd.api.types.is_numeric_dtype(real_df[col]) and pd.api.types.is_numeric_dtype(synth_df[col]):
                    common_numeric.append(col)

        if len(common_numeric) < 2:
            return {"frobenius_norm": 0.0, "columns": [], "message": "Yeterli sayisal kolon yok"}

        real_corr = real_df[common_numeric].corr().values
        synth_corr = synth_df[common_numeric].corr().values

        real_corr = np.nan_to_num(real_corr, 0)
        synth_corr = np.nan_to_num(synth_corr, 0)

        diff = real_corr - synth_corr
        frob = float(np.linalg.norm(diff, "fro"))
        max_possible = float(np.sqrt(2 * len(common_numeric) ** 2))
        normalized = frob / max_possible if max_possible > 0 else 0

        return {
            "frobenius_norm": round(frob, 6),
            "normalized_diff": round(normalized, 6),
            "columns": common_numeric,
            "quality": "excellent" if normalized < 0.05 else
                       "good" if normalized < 0.1 else
                       "fair" if normalized < 0.2 else "poor",
        }

    # ------------------------------------------------------------------
    # Kategorik Karsilastirma
    # ------------------------------------------------------------------

    def categorical_similarity(self, real: pd.Series, synth: pd.Series) -> dict:
        """Kategorik kolon icin frekans benzerlik skoru."""
        real_dist = real.dropna().value_counts(normalize=True)
        synth_dist = synth.dropna().value_counts(normalize=True)

        all_cats = set(real_dist.index) | set(synth_dist.index)
        total_diff = 0.0
        for cat in all_cats:
            r_freq = float(real_dist.get(cat, 0))
            s_freq = float(synth_dist.get(cat, 0))
            total_diff += abs(r_freq - s_freq)

        similarity = max(0, 1 - total_diff / 2)
        return {
            "similarity": round(similarity, 4),
            "total_variation_distance": round(total_diff / 2, 4),
            "unique_in_real": len(real_dist),
            "unique_in_synth": len(synth_dist),
        }

    # ------------------------------------------------------------------
    # ML Utility (TSTR — Train Synthetic, Test Real)
    # ------------------------------------------------------------------

    def ml_utility_tstr(
        self, real_df: pd.DataFrame, synth_df: pd.DataFrame, target_col: str,
    ) -> dict:
        """Sentetik veri ile egitilen modelin gercek veri uzerindeki performansi."""
        try:
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, f1_score, r2_score
            from sklearn.preprocessing import LabelEncoder
        except ImportError:
            return {"error": "scikit-learn yuklu degil"}

        if target_col not in real_df.columns or target_col not in synth_df.columns:
            return {"error": f"Hedef kolon bulunamadi: {target_col}"}

        common_cols = [c for c in real_df.columns if c in synth_df.columns]
        feature_cols = [c for c in common_cols if c != target_col]

        numeric_features = [c for c in feature_cols
                            if pd.api.types.is_numeric_dtype(real_df[c])
                            and pd.api.types.is_numeric_dtype(synth_df[c])]

        if not numeric_features:
            return {"error": "Yeterli sayisal feature yok"}

        real_clean = real_df[numeric_features + [target_col]].dropna()
        synth_clean = synth_df[numeric_features + [target_col]].dropna()

        if len(real_clean) < 20 or len(synth_clean) < 20:
            return {"error": "Yeterli veri yok"}

        is_classification = (
            real_clean[target_col].dtype == "object"
            or real_clean[target_col].nunique() < 20
        )

        if is_classification:
            le = LabelEncoder()
            all_labels = pd.concat([real_clean[target_col], synth_clean[target_col]]).astype(str)
            le.fit(all_labels)
            y_synth = le.transform(synth_clean[target_col].astype(str))
            y_real = le.transform(real_clean[target_col].astype(str))

            model = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
            model.fit(synth_clean[numeric_features].values, y_synth)

            _, X_test, _, y_test = train_test_split(
                real_clean[numeric_features].values, y_real, test_size=0.3, random_state=42,
            )
            y_pred = model.predict(X_test)

            model_real = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
            X_train_r, _, y_train_r, _ = train_test_split(
                real_clean[numeric_features].values, y_real, test_size=0.3, random_state=42,
            )
            model_real.fit(X_train_r, y_train_r)
            y_pred_real = model_real.predict(X_test)

            return {
                "task": "classification",
                "tstr_accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
                "trtr_accuracy": round(float(accuracy_score(y_test, y_pred_real)), 4),
                "tstr_f1": round(float(f1_score(y_test, y_pred, average="weighted")), 4),
                "trtr_f1": round(float(f1_score(y_test, y_pred_real, average="weighted")), 4),
                "utility_ratio": round(
                    float(accuracy_score(y_test, y_pred))
                    / max(float(accuracy_score(y_test, y_pred_real)), 1e-6), 4,
                ),
            }
        else:
            model = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
            model.fit(synth_clean[numeric_features].values, synth_clean[target_col].values)

            _, X_test, _, y_test = train_test_split(
                real_clean[numeric_features].values, real_clean[target_col].values,
                test_size=0.3, random_state=42,
            )
            y_pred = model.predict(X_test)

            return {
                "task": "regression",
                "tstr_r2": round(float(r2_score(y_test, y_pred)), 4),
                "features_used": numeric_features,
            }

    # ------------------------------------------------------------------
    # Kapsamli Kalite Raporu
    # ------------------------------------------------------------------

    def generate_quality_report(
        self, real_df: pd.DataFrame, synth_df: pd.DataFrame,
        target_col: str | None = None,
    ) -> dict:
        """Tum metrikleri birlestiren kalite raporu."""
        report: dict[str, Any] = {
            "real_shape": list(real_df.shape),
            "synth_shape": list(synth_df.shape),
            "column_metrics": {},
            "overall": {},
        }

        kl_scores = []
        js_scores = []
        ks_pass = 0
        ks_total = 0

        common_cols = [c for c in real_df.columns if c in synth_df.columns]

        for col in common_cols:
            col_report: dict[str, Any] = {}

            if pd.api.types.is_numeric_dtype(real_df[col]) and pd.api.types.is_numeric_dtype(synth_df[col]):
                kl = self.kl_divergence(real_df[col], synth_df[col])
                js = self.js_distance(real_df[col], synth_df[col])
                ks = self.ks_test(real_df[col], synth_df[col])

                col_report = {"type": "numeric", "kl_divergence": round(kl, 6), "js_distance": round(js, 6), "ks_test": ks}
                kl_scores.append(kl)
                js_scores.append(js)
                ks_total += 1
                if ks["same_distribution"]:
                    ks_pass += 1
            else:
                cat_sim = self.categorical_similarity(real_df[col], synth_df[col])
                col_report = {"type": "categorical", **cat_sim}

            report["column_metrics"][col] = col_report

        corr_diff = self.correlation_diff(real_df, synth_df)
        report["correlation"] = corr_diff

        avg_kl = float(np.mean(kl_scores)) if kl_scores else 0
        avg_js = float(np.mean(js_scores)) if js_scores else 0
        ks_ratio = ks_pass / max(ks_total, 1)

        fidelity_score = max(0, min(100, 100 - avg_js * 200))

        report["overall"] = {
            "avg_kl_divergence": round(avg_kl, 6),
            "avg_js_distance": round(avg_js, 6),
            "ks_pass_ratio": round(ks_ratio, 4),
            "correlation_quality": corr_diff.get("quality", "unknown"),
            "fidelity_score": round(fidelity_score, 1),
            "grade": "A" if fidelity_score >= 90 else
                     "B" if fidelity_score >= 75 else
                     "C" if fidelity_score >= 60 else
                     "D" if fidelity_score >= 40 else "F",
        }

        if target_col:
            ml_result = self.ml_utility_tstr(real_df, synth_df, target_col)
            report["ml_utility"] = ml_result

        return report
