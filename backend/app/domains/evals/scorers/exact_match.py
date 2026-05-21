"""ExactMatch scorer — basit eşitlik kontrolü.

Beklenen alan: ``expected[field]``, gerçekleşen: ``actual[field]``.
Varsayılan ``field='top_1'`` — DSL retrieval suitei için uygundur.
Suite YAML'inde bu scorer bir alias ile birden çok kez register edilebilir
(``exact_match__intent`` gibi). Basit kalsın diye şimdilik tek field.
"""
from __future__ import annotations

from typing import Any, Dict

from ..schemas import EvalCase, ScorerOutput


class ExactMatchScorer:
    name = "exact_match"
    field: str = "top_1"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        expected_v = case.expected.get(self.field)
        actual_v = actual.get(self.field)
        matched = expected_v is not None and expected_v == actual_v
        return ScorerOutput(
            name=self.name,
            value=1.0 if matched else 0.0,
            passed=matched,
            details={
                "field": self.field,
                "expected": expected_v,
                "actual": actual_v,
            },
        )
