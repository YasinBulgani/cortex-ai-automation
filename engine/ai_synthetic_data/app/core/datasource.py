"""
DataSourceManager — Dis veritabanlarindan veri cekme ve sema kesfetme.

PostgreSQL, MySQL, SQLite ve diger SQLAlchemy destekli DB'lere
senkron baglanti kurar, tablo listesi/kolon bilgisi/FK iliskileri kesfeder
ve ornekleme ile DataFrame doner.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class DataSourceManager:
    """Dis veritabanlarindan sema kesfetme ve veri ornekleme."""

    def __init__(self) -> None:
        self._engine: Engine | None = None
        self._connection_string: str = ""

    # ------------------------------------------------------------------
    # Baglanti
    # ------------------------------------------------------------------

    def connect(self, connection_string: str) -> dict:
        """Verilen connection string ile veritabanina baglan ve test et."""
        self._connection_string = connection_string
        try:
            self._engine = create_engine(connection_string, pool_pre_ping=True)
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            dialect = self._engine.dialect.name
            logger.info("DB baglantisi basarili: %s", dialect)
            return {
                "status": "connected",
                "dialect": dialect,
                "url": self._mask_password(connection_string),
            }
        except Exception as exc:
            logger.error("DB baglanti hatasi: %s", exc)
            return {"status": "error", "detail": str(exc)}

    def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None

    # ------------------------------------------------------------------
    # Sema Kesfetme
    # ------------------------------------------------------------------

    def list_tables(self) -> list[str]:
        """Veritabanindaki tum tablo adlarini doner."""
        self._ensure_connected()
        insp = inspect(self._engine)
        return insp.get_table_names()

    def discover_schema(self, table_name: str) -> dict:
        """Tablo kolon bilgilerini, PK, FK ve indeksleri kesfeder."""
        self._ensure_connected()
        insp = inspect(self._engine)

        columns = []
        for col in insp.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default")) if col.get("default") else None,
            })

        pk = insp.get_pk_constraint(table_name)
        fks = insp.get_foreign_keys(table_name)
        indexes = insp.get_indexes(table_name)

        foreign_keys = []
        for fk in fks:
            foreign_keys.append({
                "constrained_columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_columns": fk["referred_columns"],
            })

        return {
            "table_name": table_name,
            "columns": columns,
            "primary_key": pk.get("constrained_columns", []) if pk else [],
            "foreign_keys": foreign_keys,
            "indexes": [
                {"name": idx["name"], "columns": idx["column_names"], "unique": idx["unique"]}
                for idx in indexes
            ],
        }

    def discover_relationships(self) -> list[dict]:
        """Tum tablolar arasi FK iliskilerini kesfeder."""
        self._ensure_connected()
        insp = inspect(self._engine)
        relationships = []
        for table in insp.get_table_names():
            for fk in insp.get_foreign_keys(table):
                relationships.append({
                    "child_table": table,
                    "child_columns": fk["constrained_columns"],
                    "parent_table": fk["referred_table"],
                    "parent_columns": fk["referred_columns"],
                })
        return relationships

    # ------------------------------------------------------------------
    # Veri Cekme
    # ------------------------------------------------------------------

    def sample(self, table_name: str, n: int = 5000) -> pd.DataFrame:
        """Tablodan n satir ornekle ve DataFrame olarak don."""
        self._ensure_connected()
        dialect = self._engine.dialect.name

        if dialect == "postgresql":
            pct = min(100, max(1, int(n / self._table_count(table_name) * 100) + 1))
            query = f'SELECT * FROM "{table_name}" TABLESAMPLE BERNOULLI({pct}) LIMIT {n}'
        else:
            query = f"SELECT * FROM `{table_name}` ORDER BY RAND() LIMIT {n}"

        try:
            return pd.read_sql(text(query), self._engine)
        except Exception:
            fallback = f"SELECT * FROM {table_name} LIMIT {n}"
            return pd.read_sql(text(fallback), self._engine)

    def read_table(self, table_name: str) -> pd.DataFrame:
        """Tablonun tamamini oku."""
        self._ensure_connected()
        return pd.read_sql_table(table_name, self._engine)

    def execute_query(self, sql: str) -> pd.DataFrame:
        """Ozel SQL sorgusu calistir ve DataFrame olarak don."""
        self._ensure_connected()
        return pd.read_sql(text(sql), self._engine)

    # ------------------------------------------------------------------
    # Yardimcilar
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._engine:
            raise ConnectionError("Veritabanina bagli degil. Once connect() cagirin.")

    def _table_count(self, table_name: str) -> int:
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar() or 1
        except Exception:
            return 10000

    @staticmethod
    def _mask_password(url: str) -> str:
        """Connection string icindeki parolayi maskeler."""
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)
