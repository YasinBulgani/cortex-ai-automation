"""
İlişkisel bütünlük (FK) sağlayıcı.

Bağımsız olarak üretilmiş tablolar arasında
foreign key tutarlılığı sağlar.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class FKRelation:
    parent_table: str
    parent_key: str
    child_table: str
    child_fk: str
    cardinality: str = "1:N"  # "1:1" | "1:N"


class RelationalLinker:
    """Tablolar arası FK bütünlüğü sağlar."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def link(
        self,
        tables: dict[str, list[dict]],
        relations: list[FKRelation],
    ) -> dict[str, list[dict]]:
        """Tabloları FK ilişkilerine göre bağlar."""
        linked = {name: [dict(r) for r in records] for name, records in tables.items()}

        for rel in relations:
            parent_records = linked.get(rel.parent_table, [])
            child_records = linked.get(rel.child_table, [])

            if not parent_records or not child_records:
                continue

            parent_ids = [r[rel.parent_key] for r in parent_records if rel.parent_key in r]
            if not parent_ids:
                continue

            for child in child_records:
                child[rel.child_fk] = self._rng.choice(parent_ids)

            linked[rel.child_table] = child_records

        return linked

    @staticmethod
    def validate(
        tables: dict[str, list[dict]],
        relations: list[FKRelation],
    ) -> list[dict]:
        """FK bütünlüğünü doğrular. İhlalleri döndürür."""
        violations: list[dict] = []

        for rel in relations:
            parent_records = tables.get(rel.parent_table, [])
            child_records = tables.get(rel.child_table, [])

            parent_ids = {str(r.get(rel.parent_key)) for r in parent_records}
            orphans = [
                r for r in child_records
                if str(r.get(rel.child_fk)) not in parent_ids
            ]

            if orphans:
                violations.append({
                    "relation": f"{rel.parent_table}.{rel.parent_key} → {rel.child_table}.{rel.child_fk}",
                    "orphan_count": len(orphans),
                    "total_children": len(child_records),
                    "integrity_pct": round((1 - len(orphans) / max(len(child_records), 1)) * 100, 1),
                })

        return violations
