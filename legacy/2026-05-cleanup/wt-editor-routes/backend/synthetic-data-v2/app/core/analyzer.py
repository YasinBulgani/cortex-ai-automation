"""
Schema Analyzer — parses CSV/JSON/DB sources and extracts schema structure,
column types, statistical profiles, and potential relationships.
"""
import pandas as pd
import numpy as np
import json
import io
from typing import Optional


class SchemaAnalyzer:
    """Analyzes uploaded data sources and extracts schema metadata."""

    def analyze_csv(self, file_content: bytes, filename: str = "upload.csv") -> dict:
        """Analyze a CSV file and return a complete schema profile."""
        df = pd.read_csv(io.BytesIO(file_content))
        return self._analyze_dataframe(df, filename, source_type="csv")

    def analyze_json(self, file_content: bytes, filename: str = "upload.json") -> dict:
        """Analyze a JSON file (array of objects) and return schema profile."""
        data = json.loads(file_content)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to find the first array value
            for key, val in data.items():
                if isinstance(val, list):
                    df = pd.DataFrame(val)
                    break
            else:
                df = pd.DataFrame([data])
        else:
            raise ValueError("Unsupported JSON structure. Expected array or object.")
        return self._analyze_dataframe(df, filename, source_type="json")

    def analyze_dataframe(self, df: pd.DataFrame, table_name: str) -> dict:
        """Analyze an existing DataFrame."""
        return self._analyze_dataframe(df, table_name, source_type="dataframe")

    def _analyze_dataframe(self, df: pd.DataFrame, source_name: str, source_type: str) -> dict:
        """Core analysis logic for any DataFrame."""
        columns = []
        for col in df.columns:
            col_info = self._profile_column(df, col)
            columns.append(col_info)

        return {
            "table_name": self._clean_table_name(source_name),
            "source_type": source_type,
            "source_info": source_name,
            "row_count": len(df),
            "columns": columns,
            "relationships": [],  # populated by relationship detector
        }

    def _profile_column(self, df: pd.DataFrame, col_name: str) -> dict:
        """Generate a complete statistical profile for a single column."""
        series = df[col_name]
        dtype = str(series.dtype)

        profile = {
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

        # Numeric columns
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
            # Detect if it's likely an ID column
            if profile["unique"] and clean.min() >= 0 and dtype in ("int64", "int32"):
                profile["classification"] = "id"

        # String / Object columns
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

            # Detect ENUM-like columns (low cardinality)
            if series.nunique() <= 20 and unique_ratio < 0.05:
                value_counts = series.value_counts(normalize=True).head(20)
                profile["stats"]["top_values"] = {
                    str(k): round(float(v), 4) for k, v in value_counts.items()
                }
                profile["classification"] = "enum"

        # Datetime columns
        elif pd.api.types.is_datetime64_any_dtype(series):
            clean = series.dropna()
            profile["stats"] = {
                "min_date": str(clean.min()),
                "max_date": str(clean.max()),
            }
            profile["classification"] = "datetime"

        return profile

    def _clean_table_name(self, source_name: str) -> str:
        """Extract a clean table name from a file name."""
        name = source_name.rsplit("/", 1)[-1]  # remove path
        name = name.rsplit(".", 1)[0]  # remove extension
        return name.lower().replace(" ", "_").replace("-", "_")

    def detect_relationships(self, schemas: list[dict]) -> list[dict]:
        """
        Detect potential foreign key relationships between multiple schemas.
        Uses column name matching heuristics.
        """
        relationships = []
        table_columns = {}
        for schema in schemas:
            tname = schema["table_name"]
            table_columns[tname] = {c["name"]: c for c in schema["columns"]}

        for schema in schemas:
            tname = schema["table_name"]
            for col in schema["columns"]:
                col_name = col["name"]
                # Pattern: xxx_id → look for table 'xxx' with column 'id'
                if col_name.endswith("_id") and col_name != "id":
                    ref_table = col_name[:-3]  # remove _id suffix
                    # Check plural forms too
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
