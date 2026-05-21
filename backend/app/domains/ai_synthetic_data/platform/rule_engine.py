"""
Rule Engine — sınıflandırılmış şemadan iş kuralı çıkarır.

Platform-v4'ten port edildi (Faz 3.B).

Üretilen kural türleri:
    - faker        → ColumnClassifier'ın Faker eşlemesini kullan
    - range        → min/max/mean/std ile numerik
    - enum         → kategorik değer-ağırlık
    - sequential   → artan ID
    - date_range   → tarih aralığı
    - random_string→ uzunluk aralığı
    - nullable     → null enjeksiyon oranı
    - temporal_order→ created_at < updated_at gibi sıralama
"""
from __future__ import annotations


class RuleEngine:
    """Kolon istatistikleri ve sınıflandırmadan üretim kuralları çıkarır."""

    def infer_rules(self, schema: dict) -> list[dict]:
        """Tüm şema için kural listesi üret."""
        rules: list[dict] = []
        columns = schema.get("columns", [])

        for col in columns:
            rules.extend(self._infer_column_rules(col, columns))

        # Tablo seviyesi temporal sıralama
        rules.extend(self._infer_temporal_rules(columns))

        return rules

    # ─── İç ────────────────────────────────────────────────────────────────

    def _infer_column_rules(self, col: dict, all_columns: list) -> list[dict]:
        col_name = col["name"]
        classification = col.get("classification", "unknown")
        stats = col.get("stats", {})
        rules: list[dict] = []

        # Faker temelli — varsa diğerlerini atla
        faker_config = col.get("faker_config")
        if faker_config:
            rules.append({
                "column_name": col_name,
                "rule_type": "faker",
                "rule_config": faker_config,
            })
            return rules

        # Numerik range
        if "min" in stats and "max" in stats:
            config: dict = {"min": stats["min"], "max": stats["max"]}
            if "mean" in stats and "std" in stats:
                config["distribution"] = "normal"
                config["mean"] = stats["mean"]
                config["std"] = stats["std"]
            else:
                config["distribution"] = "uniform"
                config["mean"] = stats.get("mean", (stats["min"] + stats["max"]) / 2)
                config["std"] = stats.get("std", (stats["max"] - stats["min"]) / 4)

            rules.append({
                "column_name": col_name,
                "rule_type": "range",
                "rule_config": config,
            })

        # Enum
        elif classification == "enum" and "top_values" in stats:
            values = list(stats["top_values"].keys())
            weights = list(stats["top_values"].values())
            rules.append({
                "column_name": col_name,
                "rule_type": "enum",
                "rule_config": {"values": values, "weights": weights},
            })

        # ID / sequential
        elif classification == "id":
            rules.append({
                "column_name": col_name,
                "rule_type": "sequential",
                "rule_config": {"start": int(stats.get("min", 1)), "step": 1},
            })

        # Datetime
        elif classification == "datetime":
            rules.append({
                "column_name": col_name,
                "rule_type": "date_range",
                "rule_config": {
                    "start_date": stats.get("min_date", "2020-01-01"),
                    "end_date": stats.get("max_date", "2025-12-31"),
                },
            })

        # Fallback: string uzunluk
        elif "min_length" in stats:
            rules.append({
                "column_name": col_name,
                "rule_type": "random_string",
                "rule_config": {
                    "min_length": stats["min_length"],
                    "max_length": stats["max_length"],
                },
            })

        # Nullable
        null_ratio = col.get("null_ratio", 0)
        if null_ratio > 0:
            rules.append({
                "column_name": col_name,
                "rule_type": "nullable",
                "rule_config": {"null_ratio": null_ratio},
            })

        return rules

    def _infer_temporal_rules(self, columns: list) -> list[dict]:
        """created_at < updated_at gibi klasik çiftler için sıralama kuralı."""
        rules: list[dict] = []
        datetime_cols = [c for c in columns if c.get("classification") == "datetime"]
        date_names = {c["name"] for c in datetime_cols}

        temporal_pairs = [
            ("created_at", "updated_at"),
            ("open_date", "close_date"),
            ("start_date", "end_date"),
            ("acilis_tarihi", "kapanis_tarihi"),
        ]

        for before, after in temporal_pairs:
            if before in date_names and after in date_names:
                rules.append({
                    "column_name": after,
                    "rule_type": "temporal_order",
                    "rule_config": {
                        "after_column": before,
                        "min_offset_days": 1,
                        "max_offset_days": 365,
                    },
                })

        return rules
