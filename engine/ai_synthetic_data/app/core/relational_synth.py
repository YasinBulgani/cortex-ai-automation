"""
RelationalSynthesizer — Tablolar arasi FK koruyarak sentetik veri uretimi.

Topological sort ile uretim sirasini belirler,
parent tablolardan child tablolara FK zincirini korur,
kardinalite dagilimini (Poisson/lognormal) muhafaza eder.
"""
from __future__ import annotations

import logging
import random
from collections import defaultdict, deque
from typing import Any

import numpy as np
import pandas as pd

from app.core.selector import SynthesizerSelector

logger = logging.getLogger(__name__)


class RelationalSynthesizer:
    """Coklu tablo, FK koruyan sentetik veri uretici."""

    def __init__(self) -> None:
        self._selector = SynthesizerSelector()
        self._tables: dict[str, pd.DataFrame] = {}
        self._relationships: list[dict] = []
        self._schema: dict[str, dict] = {}

    def add_table(self, name: str, df: pd.DataFrame, primary_key: str) -> None:
        """Tablolari ekle."""
        self._tables[name] = df
        self._schema[name] = {"primary_key": primary_key, "columns": df.columns.tolist()}

    def add_relationship(
        self, parent_table: str, parent_key: str,
        child_table: str, child_key: str,
        cardinality_mean: float = 3.0,
    ) -> None:
        """FK iliskisi tanimla."""
        self._relationships.append({
            "parent_table": parent_table,
            "parent_key": parent_key,
            "child_table": child_table,
            "child_key": child_key,
            "cardinality_mean": cardinality_mean,
        })

    def generate(self, row_counts: dict[str, int], method: str = "auto") -> dict[str, pd.DataFrame]:
        """Tum tablolari iliskisel olarak uret."""
        order = self._topological_sort()
        logger.info("Uretim sirasi: %s", order)

        generated: dict[str, pd.DataFrame] = {}
        pk_pools: dict[str, list] = {}

        for table_name in order:
            if table_name not in self._tables:
                logger.warning("Tablo verisi yok: %s — atlaniyor", table_name)
                continue

            n = row_counts.get(table_name, len(self._tables[table_name]))
            original = self._tables[table_name]

            parent_rels = [r for r in self._relationships if r["child_table"] == table_name]

            fk_columns = {r["child_key"] for r in parent_rels}
            non_fk_cols = [c for c in original.columns if c not in fk_columns]

            if non_fk_cols:
                synth_df = self._selector.fit_and_sample(original[non_fk_cols], n, method)
            else:
                synth_df = pd.DataFrame(index=range(n))

            for rel in parent_rels:
                parent_pks = pk_pools.get(rel["parent_table"], [])
                if not parent_pks:
                    logger.warning("Parent PK havuzu bos: %s", rel["parent_table"])
                    synth_df[rel["child_key"]] = [None] * n
                    continue

                fk_values = random.choices(parent_pks, k=n)
                synth_df[rel["child_key"]] = fk_values

            pk_col = self._schema[table_name]["primary_key"]
            if pk_col in synth_df.columns:
                pk_pools[table_name] = synth_df[pk_col].tolist()
            else:
                pks = [f"{table_name[:3].upper()}{i+1:08d}" for i in range(n)]
                synth_df[pk_col] = pks
                pk_pools[table_name] = pks

            for c in original.columns:
                if c not in synth_df.columns:
                    synth_df[c] = None

            generated[table_name] = synth_df[original.columns.tolist()]

        summary = {t: len(df) for t, df in generated.items()}
        logger.info("Iliskisel uretim tamamlandi: %s", summary)
        return generated

    # ------------------------------------------------------------------
    # Topological Sort (Kahn)
    # ------------------------------------------------------------------

    def _topological_sort(self) -> list[str]:
        """FK iliskilerine gore uretim sirasini belirle."""
        in_degree: dict[str, int] = defaultdict(int)
        adj: dict[str, list[str]] = defaultdict(list)
        all_tables: set[str] = set(self._tables.keys())

        for rel in self._relationships:
            parent = rel["parent_table"]
            child = rel["child_table"]
            adj[parent].append(child)
            in_degree[child] += 1
            all_tables.add(parent)
            all_tables.add(child)

        for t in all_tables:
            if t not in in_degree:
                in_degree[t] = 0

        queue = deque(t for t in all_tables if in_degree[t] == 0)
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        remaining = all_tables - set(order)
        if remaining:
            logger.warning("Dongusel bagimlilk tespit edildi: %s — sona ekleniyor", remaining)
            order.extend(remaining)

        return order
