"""Locator match scorer — self-heal çıktısı değerlendirmesi.

Heal edilen locator beklenen locator'la tam eşit mi? Tam eşitlik talep etmek
fazla katıdır; çünkü birden fazla semantik-eşdeğer locator geçerlidir.
Bu scorer iki mod destekler:

    * ``locator_exact`` : case.expected["new_locator"] == actual["new_locator"]
    * ``locator_contains_any`` : actual["new_locator"] ∈ case.expected["acceptable_locators"]
"""
from __future__ import annotations

from typing import Any, Dict

from ..schemas import EvalCase, ScorerOutput


def _normalize(loc: str) -> str:
    """Locator string'i normalize — whitespace + tırnak tipleri."""
    if not loc:
        return ""
    s = loc.strip()
    s = s.replace("\"", "'")
    return " ".join(s.split())


class LocatorExactScorer:
    name = "locator_exact"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        expected = _normalize(case.expected.get("new_locator") or "")
        got = _normalize(actual.get("new_locator") or "")
        matched = bool(expected) and expected == got
        return ScorerOutput(
            name=self.name,
            value=1.0 if matched else 0.0,
            passed=matched,
            details={"expected": expected, "actual": got},
        )


class LocatorContainsAnyScorer:
    """Acceptable locator setindeki herhangi biriyle eşleşme."""

    name = "locator_contains_any"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        acceptable = case.expected.get("acceptable_locators") or []
        if not isinstance(acceptable, (list, tuple)):
            return ScorerOutput(
                name=self.name, value=0.0, passed=False,
                details={"error": "expected.acceptable_locators must be list"},
            )
        normalized = [_normalize(str(x)) for x in acceptable]
        got = _normalize(actual.get("new_locator") or "")

        matched = got in normalized
        return ScorerOutput(
            name=self.name,
            value=1.0 if matched else 0.0,
            passed=matched,
            details={
                "actual": got,
                "acceptable_count": len(normalized),
                "matched": matched,
            },
        )
