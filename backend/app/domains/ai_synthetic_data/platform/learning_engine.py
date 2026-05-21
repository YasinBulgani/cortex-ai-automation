"""
Continuous Learning Engine — geçmiş üretim verisinden kural iyileştirme önerir.

Platform-v4'ten port edildi (Faz 3.B). Temel akış:
    1. Her kolon için üretilmiş gerçek veri ile mevcut kural konfigünü kıyasla.
    2. %15+ sapma (drift) varsa öneri çıkar.
    3. apply_suggestions ile kurallara işle (`learned=True` işaretlenir).
"""
from __future__ import annotations

import statistics


class LearningEngine:
    """Geçmiş üretim verisinden kural iyileştirme önerileri çıkarır."""

    def analyze_schema(
        self,
        schema: dict,
        rules: list[dict],
        history_previews: list[list[dict]],
    ) -> dict:
        """
        Geçmiş üretim preview'lerini mevcut kural konfigleri ile kıyasla.

        Args:
            schema: Kolon metadatası içeren şema dict'i.
            rules: Mevcut üretim kuralları.
            history_previews: Geçmiş üretim preview'leri listesi (her preview = row dict listesi).

        Returns:
            {"insights": [...], "suggestions": [...], "confidence": float, "status": str, ...}
        """
        if not history_previews:
            return {
                "insights": [], "suggestions": [], "confidence": 0.0, "status": "no_data",
            }

        # Tüm preview satırlarını tek bir listede birleştir
        all_rows: list[dict] = []
        for preview in history_previews:
            if isinstance(preview, list):
                all_rows.extend(preview)

        if not all_rows:
            return {
                "insights": [], "suggestions": [], "confidence": 0.0, "status": "no_data",
            }

        columns = schema.get("columns", [])
        rule_map = {r["column_name"]: r for r in rules}
        insights: list[dict] = []
        suggestions: list[dict] = []

        for col in columns:
            col_name = col["name"]
            dtype = col.get("dtype", "string")
            current_rule = rule_map.get(col_name)

            values = [
                row.get(col_name) for row in all_rows
                if row.get(col_name) is not None
            ]
            if not values:
                continue

            # ─── Numerik ────────────────────────────────────────────────
            if (
                dtype in ("int", "float", "integer", "real", "int64", "float64")
                or self._is_numeric_list(values)
            ):
                try:
                    numeric = [float(v) for v in values if v is not None]
                    if len(numeric) < 5:
                        continue

                    actual_min = min(numeric)
                    actual_max = max(numeric)
                    actual_mean = statistics.mean(numeric)
                    actual_std = statistics.stdev(numeric) if len(numeric) > 1 else 0

                    insights.append({
                        "column": col_name,
                        "type": "numeric",
                        "actual_min": round(actual_min, 2),
                        "actual_max": round(actual_max, 2),
                        "actual_mean": round(actual_mean, 2),
                        "actual_std": round(actual_std, 2),
                        "sample_count": len(numeric),
                    })

                    if current_rule and current_rule["rule_type"] == "range":
                        cfg = current_rule.get("rule_config", {})
                        configured_min = cfg.get("min", 0)
                        configured_max = cfg.get("max", 1000)
                        configured_mean = cfg.get("mean", (configured_min + configured_max) / 2)

                        drift_min = abs(actual_min - configured_min) / max(abs(configured_min), 1)
                        drift_max = abs(actual_max - configured_max) / max(abs(configured_max), 1)
                        drift_mean = abs(actual_mean - configured_mean) / max(abs(configured_mean), 1)

                        if drift_min > 0.15 or drift_max > 0.15 or drift_mean > 0.1:
                            suggestions.append({
                                "column": col_name,
                                "rule_type": "range",
                                "current_config": cfg,
                                "suggested_config": {
                                    "min": round(actual_min * 0.9, 2),
                                    "max": round(actual_max * 1.1, 2),
                                    "mean": round(actual_mean, 2),
                                    "std": round(actual_std, 2),
                                    "distribution": "normal" if actual_std > 0.1 * abs(actual_mean) else "uniform",
                                },
                                "reason": (
                                    f"Gerçek dağılım (ort: {actual_mean:.1f}) "
                                    f"mevcut konfigürasyondan (ort: {configured_mean:.1f}) sapıyor"
                                ),
                                "drift_pct": round(max(drift_min, drift_max, drift_mean) * 100, 1),
                                "confidence": round(min(0.95, 0.5 + len(numeric) / 1000), 2),
                            })

                except (ValueError, TypeError):
                    pass

            # ─── Kategorik / enum ──────────────────────────────────────
            elif dtype in ("string", "object", "text") or col.get("classification") == "enum":
                str_values = [str(v) for v in values if v is not None]
                if len(str_values) < 5:
                    continue

                unique_count = len(set(str_values))

                if unique_count <= 25:
                    freq: dict[str, int] = {}
                    for v in str_values:
                        freq[v] = freq.get(v, 0) + 1
                    total = len(str_values)
                    actual_weights = {
                        k: round(v / total, 4)
                        for k, v in sorted(freq.items(), key=lambda x: -x[1])[:20]
                    }

                    insights.append({
                        "column": col_name,
                        "type": "categorical",
                        "unique_count": unique_count,
                        "top_values": actual_weights,
                        "sample_count": len(str_values),
                    })

                    if current_rule and current_rule["rule_type"] == "enum":
                        cfg = current_rule.get("rule_config", {})
                        current_values = set(cfg.get("values", []))
                        new_values = set(actual_weights.keys())

                        if new_values - current_values or (
                            len(current_values) > 0 and len(new_values) != len(current_values)
                        ):
                            suggestions.append({
                                "column": col_name,
                                "rule_type": "enum",
                                "current_config": cfg,
                                "suggested_config": {
                                    "values": list(actual_weights.keys()),
                                    "weights": list(actual_weights.values()),
                                },
                                "reason": (
                                    f"Gerçek dağılımda {len(new_values)} benzersiz değer var, "
                                    f"mevcut listede {len(current_values)}"
                                ),
                                "drift_pct": round(
                                    len(new_values - current_values) / max(len(new_values), 1) * 100, 1
                                ),
                                "confidence": round(min(0.9, 0.4 + len(str_values) / 500), 2),
                            })

        # Genel güven skoru
        if suggestions:
            overall_confidence = round(
                statistics.mean([s["confidence"] for s in suggestions]), 2
            )
        elif insights:
            overall_confidence = round(min(0.7, 0.3 + len(all_rows) / 1000), 2)
        else:
            overall_confidence = 0.0

        return {
            "status": "analyzed",
            "sample_rows": len(all_rows),
            "insights": insights,
            "suggestions": suggestions,
            "confidence": overall_confidence,
            "message": (
                f"{len(all_rows)} satır analiz edildi. "
                f"{len(suggestions)} iyileştirme önerisi bulundu."
            ),
        }

    def apply_suggestions(
        self, rules: list[dict], suggestions: list[dict]
    ) -> list[dict]:
        """Önerileri mevcut kurallara uygular; `learned=True` işaretler."""
        rule_map = {r["column_name"]: dict(r) for r in rules}

        for suggestion in suggestions:
            col = suggestion["column"]
            if col in rule_map:
                rule_map[col]["rule_config"] = suggestion["suggested_config"]
                rule_map[col]["rule_type"] = suggestion["rule_type"]
                rule_map[col]["learned"] = True

        return list(rule_map.values())

    # ─── İç yardımcılar ────────────────────────────────────────────────────

    @staticmethod
    def _is_numeric_list(values: list) -> bool:
        """Örnek değerlerin en az %80'i numerik mi?"""
        if not values:
            return False
        numeric_count = 0
        sample = values[:20]
        for v in sample:
            try:
                float(v)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        return numeric_count / min(len(values), 20) >= 0.8
