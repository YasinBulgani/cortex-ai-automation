"""
Schema Analyzer — CSV/JSON/DataFrame → şema profili.

Platform-v4'ten port edildi (Faz 3.B). Değişiklikler:
    - Import yolları backend'e uyarlandı (dış bağımlılık pandas/numpy).
    - Type hint'ler Python 3.11 syntax'ına çevrildi.
    - Davranış aynı; aynı input → aynı output.
"""
from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd


def _require_pandas():
    """Lazy pandas import — opsiyonel bağımlılık (advanced_generators ile aynı desen)."""
    try:
        import pandas as pd  # type: ignore
        return pd
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "SchemaAnalyzer için pandas gerekli. Kur: pip install pandas"
        ) from exc


class SchemaAnalyzer:
    """Yüklenen veri kaynağını analiz eder, şema metadatasını çıkarır."""

    # ─── Dış arayüz ────────────────────────────────────────────────────────

    def analyze_csv(self, file_content: bytes, filename: str = "upload.csv") -> dict:
        """CSV bytes → tam şema profili."""
        pd = _require_pandas()
        df = pd.read_csv(io.BytesIO(file_content))
        return self._analyze_dataframe(df, filename, source_type="csv")

    def analyze_json(self, file_content: bytes, filename: str = "upload.json") -> dict:
        """JSON bytes (dizi veya dict) → şema profili."""
        pd = _require_pandas()
        data = json.loads(file_content)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # İlk array değeri dene
            for _, val in data.items():
                if isinstance(val, list):
                    df = pd.DataFrame(val)
                    break
            else:
                df = pd.DataFrame([data])
        else:
            raise ValueError("Desteklenmeyen JSON yapısı. Array veya object bekleniyor.")
        return self._analyze_dataframe(df, filename, source_type="json")

    def analyze_dataframe(self, df: "pd.DataFrame", table_name: str) -> dict:
        """Hazır DataFrame için."""
        return self._analyze_dataframe(df, table_name, source_type="dataframe")

    # ─── İç ────────────────────────────────────────────────────────────────

    def _analyze_dataframe(
        self, df: Any, source_name: str, source_type: str
    ) -> dict:
        columns = [self._profile_column(df, col) for col in df.columns]
        return {
            "table_name": self._clean_table_name(source_name),
            "source_type": source_type,
            "source_info": source_name,
            "row_count": len(df),
            "columns": columns,
            "relationships": [],
        }

    def _profile_column(self, df: Any, col_name: str) -> dict:
        """Tek bir kolon için istatistiksel profil üret."""
        pd = _require_pandas()
        series = df[col_name]
        dtype = str(series.dtype)

        profile: dict = {
            "name": col_name,
            "dtype": dtype,
            "classification": "unknown",
            "pii": False,
            "pii_confidence": 0.0,
            "nullable": bool(series.isnull().any()),
            "null_ratio": round(float(series.isnull().mean()), 4),
            "unique": bool(series.nunique() == len(series.dropna())),
            "unique_count": int(series.nunique()),
            "sample_values": [str(v) for v in series.dropna().head(5).tolist()],
            "stats": {},
        }

        # Numerik
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            profile["stats"] = {
                "min": float(clean.min()) if len(clean) else 0,
                "max": float(clean.max()) if len(clean) else 0,
                "mean": round(float(clean.mean()), 2) if len(clean) else 0,
                "median": round(float(clean.median()), 2) if len(clean) else 0,
                "std": round(float(clean.std()), 2) if len(clean) > 1 else 0,
                "q25": round(float(clean.quantile(0.25)), 2) if len(clean) else 0,
                "q75": round(float(clean.quantile(0.75)), 2) if len(clean) else 0,
            }
            # ID adayı: unique, non-negative, int → classification = id
            if profile["unique"] and clean.min() >= 0 and dtype in ("int64", "int32"):
                profile["classification"] = "id"

        # String / Object
        elif pd.api.types.is_string_dtype(series) or dtype == "object":
            clean = series.dropna().astype(str)
            lengths = clean.str.len()
            unique_ratio = series.nunique() / max(len(clean), 1)

            profile["stats"] = {
                "min_length": int(lengths.min()) if len(lengths) else 0,
                "max_length": int(lengths.max()) if len(lengths) else 0,
                "avg_length": round(float(lengths.mean()), 1) if len(lengths) else 0,
                "unique_ratio": round(unique_ratio, 4),
            }

            # ENUM sezgisi: düşük kardinalite
            # Küçük datasetlerde (<50 satır) oran koşulu atlanır — 6 satırda 2 unique değer
            # bile yüksek oran verir ama gerçek bir enum sütunudur.
            is_small_dataset = len(clean) < 50
            if series.nunique() <= 20 and (is_small_dataset or unique_ratio < 0.1):
                value_counts = series.value_counts(normalize=True).head(20)
                profile["stats"]["top_values"] = {
                    str(k): round(float(v), 4) for k, v in value_counts.items()
                }
                profile["classification"] = "enum"

        # Datetime
        elif pd.api.types.is_datetime64_any_dtype(series):
            clean = series.dropna()
            profile["stats"] = {
                "min_date": str(clean.min()),
                "max_date": str(clean.max()),
            }
            profile["classification"] = "datetime"

        return profile

    def _clean_table_name(self, source_name: str) -> str:
        """Dosya adından temiz bir tablo adı üret."""
        name = source_name.rsplit("/", 1)[-1]
        name = name.rsplit(".", 1)[0]
        return name.lower().replace(" ", "_").replace("-", "_")

    # ─── İlişki (FK) tespiti ───────────────────────────────────────────────

    def detect_relationships(self, schemas: list[dict]) -> list[dict]:
        """Çoklu şema arasında heuristik FK tespiti (xxx_id → table 'xxx')."""
        relationships: list[dict] = []
        table_columns: dict[str, dict] = {}
        for schema in schemas:
            tname = schema["table_name"]
            table_columns[tname] = {c["name"]: c for c in schema["columns"]}

        for schema in schemas:
            tname = schema["table_name"]
            for col in schema["columns"]:
                col_name = col["name"]
                # Pattern: xxx_id → table 'xxx' + 'id'
                if col_name.endswith("_id") and col_name != "id":
                    ref_table = col_name[:-3]
                    for candidate in [ref_table, ref_table + "s", ref_table + "es"]:
                        if candidate in table_columns and "id" in table_columns[candidate]:
                            relationships.append({
                                "from_table": tname,
                                "from_column": col_name,
                                "to_table": candidate,
                                "to_column": "id",
                                "confidence": 0.9,
                            })
                            break

        return relationships
