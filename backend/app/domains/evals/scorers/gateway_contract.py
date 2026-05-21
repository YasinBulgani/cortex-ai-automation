"""AI Gateway contract scorers.

Bu scorer'lar modelin cevabını "iyi/kötü" diye yargılamaktan çok gateway
sözleşmesini ölçer: içerik geldi mi, JSON modu bozuldu mu, provider/attempt
metadata'sı raporlanıyor mu, latency bütçesi aşılmış mı?
"""
from __future__ import annotations

import json
from typing import Any, Dict

from ..schemas import EvalCase, ScorerOutput


def _content(actual: Dict[str, Any]) -> str:
    value = actual.get("content") or actual.get("output") or actual.get("response") or ""
    return value if isinstance(value, str) else str(value)


class GatewayContentContainsScorer:
    name = "gateway_content_contains"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        content = _content(actual)
        contains_any = case.expected.get("contains_any") or []
        if isinstance(contains_any, str):
            contains_any = [contains_any]
        lowered = content.lower()
        hits = [str(item) for item in contains_any if str(item).lower() in lowered]
        passed = bool(content.strip()) and (not contains_any or bool(hits))
        return ScorerOutput(
            name=self.name,
            value=1.0 if passed else 0.0,
            passed=passed,
            details={
                "content_len": len(content),
                "contains_any": list(contains_any),
                "hits": hits,
            },
        )


class GatewayJsonValidScorer:
    name = "gateway_json_valid"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        if not bool(case.expected.get("json_required", False)):
            return ScorerOutput(
                name=self.name,
                value=1.0,
                passed=True,
                details={"skipped": True},
            )
        content = _content(actual).strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            return ScorerOutput(
                name=self.name,
                value=0.0,
                passed=False,
                details={"error": str(exc), "content_preview": content[:160]},
            )
        return ScorerOutput(
            name=self.name,
            value=1.0,
            passed=True,
            details={"parsed_type": type(parsed).__name__},
        )


class GatewayProviderAllowedScorer:
    name = "gateway_provider_allowed"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        provider = str(actual.get("provider_used") or "")
        allowed = case.expected.get("provider_allowed") or [
            "vllm",
            "ollama",
            "groq",
            "gemini",
            "g4f",
            "cache",
        ]
        allowed_set = {str(item) for item in allowed}
        passed = provider in allowed_set
        return ScorerOutput(
            name=self.name,
            value=1.0 if passed else 0.0,
            passed=passed,
            details={"provider_used": provider, "allowed": sorted(allowed_set)},
        )


class GatewayAttemptsHealthyScorer:
    name = "gateway_attempts_healthy"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        attempts = actual.get("attempts") or []
        if not isinstance(attempts, list):
            attempts = []

        min_attempts = int(case.expected.get("min_attempts", 1))
        require_success = bool(case.expected.get("require_success_attempt", True))
        require_failed_before_success = bool(
            case.expected.get("require_failed_before_success", False)
        )

        success_indexes = [
            idx for idx, item in enumerate(attempts)
            if isinstance(item, dict) and bool(item.get("success"))
        ]
        failed_indexes = [
            idx for idx, item in enumerate(attempts)
            if isinstance(item, dict) and item.get("success") is False
        ]

        enough_attempts = len(attempts) >= min_attempts
        has_success = bool(success_indexes)
        failed_before_success = (
            bool(failed_indexes)
            and bool(success_indexes)
            and min(failed_indexes) < max(success_indexes)
        )

        passed = enough_attempts
        if require_success:
            passed = passed and has_success
        if require_failed_before_success:
            passed = passed and failed_before_success

        return ScorerOutput(
            name=self.name,
            value=1.0 if passed else 0.0,
            passed=passed,
            details={
                "attempt_count": len(attempts),
                "min_attempts": min_attempts,
                "success_count": len(success_indexes),
                "failed_count": len(failed_indexes),
                "failed_before_success": failed_before_success,
            },
        )


class GatewayLatencyBudgetScorer:
    name = "gateway_latency_budget"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        max_latency_ms = int(case.expected.get("max_latency_ms", 30_000))
        try:
            latency_ms = int(actual.get("latency_ms", 0) or 0)
        except (TypeError, ValueError):
            latency_ms = max_latency_ms + 1
        passed = 0 <= latency_ms <= max_latency_ms
        value = 1.0 if passed else max(0.0, min(1.0, max_latency_ms / max(latency_ms, 1)))
        return ScorerOutput(
            name=self.name,
            value=value,
            passed=passed,
            details={"latency_ms": latency_ms, "max_latency_ms": max_latency_ms},
        )
