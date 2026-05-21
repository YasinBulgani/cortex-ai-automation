"""
SchemaAnalyzer — DataFrame sema analizi, istatistik ve dagilim profilleme.

MVP: min/max/mean/std + top_values (korundu).
v2: dagilim fit, histogram, percentile, skewness/kurtosis eklendi.
"""
import pandas as pd
import numpy as np


class SchemaAnalyzer:
    """Analyze pandas DataFrames to extract schema information, null rates, datatypes, and basic bounds."""

    def analyze_dataframe(self, table_name: str, df: pd.DataFrame) -> dict:
        columns_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            mapped_type = self._map_dtype(dtype)

            non_null_df = df[col].dropna()
            null_count = int(df[col].isna().sum())
            null_rate = null_count / len(df) if len(df) > 0 else 0
            distinct_count = int(non_null_df.nunique())

            stats: dict = {}
            if mapped_type in ["int", "float"]:
                if not non_null_df.empty:
                    stats = {
                        "min": float(non_null_df.min()),
                        "max": float(non_null_df.max()),
                        "mean": float(non_null_df.mean()),
                        "std": float(non_null_df.std()),
                    }
            elif mapped_type in ["string"]:
                if not non_null_df.empty:
                    val_counts = non_null_df.value_counts(normalize=True).head(5)
                    stats["top_values"] = {str(k): float(v) for k, v in val_counts.items()}

            columns_info.append({
                "name": col,
                "dtype": mapped_type,
                "null_rate": round(null_rate, 4),
                "distinct_count": distinct_count,
                "stats": stats,
            })

        return {
            "table_name": table_name,
            "row_count": len(df),
            "columns": columns_info,
        }

    # ------------------------------------------------------------------
    # v2: Gelismis Profilleme
    # ------------------------------------------------------------------

    def analyze_advanced(self, table_name: str, df: pd.DataFrame) -> dict:
        """Temel analiz + dagilim tespiti, histogram, percentile, korelasyon."""
        base = self.analyze_dataframe(table_name, df)

        from app.core.distribution import DistributionFitter
        fitter = DistributionFitter()

        for col_info in base["columns"]:
            col_name = col_info["name"]
            series = df[col_name].dropna()

            if col_info["dtype"] in ("int", "float") and len(series) >= 10:
                arr = series.values.astype(float)

                dist_stats = fitter.compute_distribution_stats(arr)
                col_info["stats"]["skewness"] = dist_stats["skewness"]
                col_info["stats"]["kurtosis"] = dist_stats["kurtosis"]
                col_info["stats"]["is_normal"] = dist_stats["is_normal"]

                best_fit = fitter.fit_best_distribution(arr)
                col_info["stats"]["best_distribution"] = best_fit.distribution_name
                col_info["stats"]["distribution_params"] = [float(p) for p in best_fit.params]
                col_info["stats"]["ks_statistic"] = best_fit.ks_statistic

                hist = fitter.compute_histogram(arr)
                col_info["stats"]["histogram"] = hist

                pcts = fitter.compute_percentiles(arr)
                col_info["stats"]["percentiles"] = pcts

            elif col_info["dtype"] == "string" and len(series) > 0:
                full_counts = series.value_counts(normalize=True)
                col_info["stats"]["all_values"] = {
                    str(k): round(float(v), 6) for k, v in full_counts.items()
                }
                col_info["stats"]["unique_ratio"] = round(
                    col_info["distinct_count"] / len(series), 4,
                )

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            base["correlation_matrix"] = {
                "columns": numeric_cols,
                "values": corr_matrix.values.tolist(),
            }

        return base

    # ------------------------------------------------------------------
    # Yardimcilar
    # ------------------------------------------------------------------

    def _map_dtype(self, dtype: str) -> str:
        if "int" in dtype:
            return "int"
        if "float" in dtype:
            return "float"
        if "datetime" in dtype:
            return "datetime"
        if "bool" in dtype:
            return "boolean"
        return "string"
