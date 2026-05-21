"""
Rule Engine — infers business rules from analyzed schema columns.
Generates range constraints, enum distributions, dependencies, and temporal ordering.
"""
from typing import Optional


class RuleEngine:
    """Infers generation rules from column statistics and classification."""

    def infer_rules(self, schema: dict) -> list[dict]:
        """
        Analyze a classified schema and produce a list of generation rules
        for every column.
        """
        rules = []
        columns = schema.get("columns", [])

        for col in columns:
            col_rules = self._infer_column_rules(col, columns)
            rules.extend(col_rules)

        # Temporal ordering rules
        rules.extend(self._infer_temporal_rules(columns))

        return rules

    def _infer_column_rules(self, col: dict, all_columns: list) -> list[dict]:
        """Infer rules for a single column."""
        col_name = col["name"]
        classification = col.get("classification", "unknown")
        stats = col.get("stats", {})
        rules = []

        # ── Faker-based rule ────────────────────────────────────────────────
        faker_config = col.get("faker_config")
        if faker_config:
            rules.append({
                "column_name": col_name,
                "rule_type": "faker",
                "rule_config": faker_config,
            })
            return rules  # Faker handles it, no need for other rules

        # ── Numeric range rule ──────────────────────────────────────────────
        if "min" in stats and "max" in stats:
            config = {
                "min": stats["min"],
                "max": stats["max"],
            }
            if "mean" in stats and "std" in stats:
                config["distribution"] = "normal"
                config["mean"] = stats["mean"]
                config["std"] = stats["std"]
            else:
                config["distribution"] = "uniform"

            rules.append({
                "column_name": col_name,
                "rule_type": "range",
                "rule_config": config,
            })

        # ── Enum rule (categorical) ─────────────────────────────────────────
        elif classification == "enum" and "top_values" in stats:
            values = list(stats["top_values"].keys())
            weights = list(stats["top_values"].values())
            rules.append({
                "column_name": col_name,
                "rule_type": "enum",
                "rule_config": {
                    "values": values,
                    "weights": weights,
                },
            })

        # ── ID / Sequential rule ────────────────────────────────────────────
        elif classification == "id":
            rules.append({
                "column_name": col_name,
                "rule_type": "sequential",
                "rule_config": {
                    "start": int(stats.get("min", 1)),
                    "step": 1,
                },
            })

        # ── Datetime rule ───────────────────────────────────────────────────
        elif classification == "datetime":
            rules.append({
                "column_name": col_name,
                "rule_type": "date_range",
                "rule_config": {
                    "start_date": stats.get("min_date", "2020-01-01"),
                    "end_date": stats.get("max_date", "2025-12-31"),
                },
            })

        # ── Fallback: random string based on observed lengths ───────────────
        elif "min_length" in stats:
            rules.append({
                "column_name": col_name,
                "rule_type": "random_string",
                "rule_config": {
                    "min_length": stats["min_length"],
                    "max_length": stats["max_length"],
                },
            })

        # ── Null injection rule ─────────────────────────────────────────────
        null_ratio = col.get("null_ratio", 0)
        if null_ratio > 0:
            rules.append({
                "column_name": col_name,
                "rule_type": "nullable",
                "rule_config": {
                    "null_ratio": null_ratio,
                },
            })

        return rules

    def _infer_temporal_rules(self, columns: list) -> list[dict]:
        """Infer temporal ordering rules (e.g., created_at < updated_at)."""
        rules = []
        datetime_cols = [c for c in columns if c.get("classification") == "datetime"]
        date_names = [c["name"] for c in datetime_cols]

        # Common temporal pairs
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
