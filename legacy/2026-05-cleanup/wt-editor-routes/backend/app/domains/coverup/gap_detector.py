"""
CoverUp — Coverage gap detector ve risk scorer.

Banking-aware risk scoring:
  - Ödeme/transfer fonksiyonları -> yüksek risk
  - Auth/session fonksiyonları -> yüksek risk
  - KVKK/PII işleyen kodlar -> yüksek risk
  - Hata handler'lar -> orta risk
  - UI helper'lar -> düşük risk
"""
from __future__ import annotations

import fnmatch
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Banking-critical path keywords
_BANKING_CRITICAL_KEYWORDS = (
    "payment",
    "transfer",
    "auth",
    "session",
    "kyc",
    "kvkk",
    "transaction",
    "account",
    "balance",
    "deposit",
    "withdraw",
    "loan",
    "credit",
    "debit",
    "swift",
    "iban",
    "eft",
    "havale",
    "odeme",
    "kredi",
    "hesap",
)


class GapDetector:
    """Coverage gap detector with banking-aware risk scoring."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def detect_gaps(
        report: dict[str, Any],
        focus_paths: list[str] | None = None,
        min_risk: float = 0.3,
        max_targets: int = 50,
    ) -> list[dict[str, Any]]:
        """Detect coverage gaps and return risk-scored targets.

        Args:
            report: Parsed coverage report (from CoverageParser).
            focus_paths: Optional glob patterns to filter files.
            min_risk: Minimum risk score to include (0.0 - 1.0).
            max_targets: Maximum number of targets to return.

        Returns:
            List of gap target dicts sorted by risk_score descending.
        """
        files = report.get("files", [])
        targets: list[dict[str, Any]] = []

        for file_info in files:
            file_path = file_info.get("file_path", "")

            # Apply focus_paths filter
            if focus_paths:
                matched = any(
                    fnmatch.fnmatch(file_path, pattern)
                    for pattern in focus_paths
                )
                if not matched:
                    continue

            # --- Line gaps ---
            missed_lines = file_info.get("missed_line_numbers", [])
            if missed_lines:
                groups = GapDetector.group_consecutive_lines(missed_lines)
                for start, end in groups:
                    score, factors = GapDetector.score_risk(
                        file_path=file_path,
                        line_range=(start, end),
                    )
                    if score >= min_risk:
                        targets.append(
                            {
                                "file_path": file_path,
                                "function_name": None,
                                "start_line": start,
                                "end_line": end,
                                "gap_type": "line",
                                "risk_score": round(score, 3),
                                "risk_factors": factors,
                                "code_snippet": "",
                                "suggestion": _line_suggestion(
                                    file_path, start, end
                                ),
                            }
                        )

            # --- Branch gaps ---
            missed_branch_lines = file_info.get("missed_branch_lines", [])
            if missed_branch_lines:
                branch_groups = GapDetector.group_consecutive_lines(
                    missed_branch_lines
                )
                for start, end in branch_groups:
                    score, factors = GapDetector.score_risk(
                        file_path=file_path,
                        line_range=(start, end),
                    )
                    # Branch gaps get a bonus
                    score = min(score + 0.1, 1.0)
                    factors = factors + ["uncovered_branch"]
                    if score >= min_risk:
                        targets.append(
                            {
                                "file_path": file_path,
                                "function_name": None,
                                "start_line": start,
                                "end_line": end,
                                "gap_type": "branch",
                                "risk_score": round(score, 3),
                                "risk_factors": factors,
                                "code_snippet": "",
                                "suggestion": _branch_suggestion(
                                    file_path, start, end
                                ),
                            }
                        )

            # --- Function gaps ---
            uncovered_fns = file_info.get("uncovered_functions", [])
            for fn_name in uncovered_fns:
                score, factors = GapDetector.score_risk(
                    file_path=file_path,
                    function_name=fn_name,
                )
                if score >= min_risk:
                    targets.append(
                        {
                            "file_path": file_path,
                            "function_name": fn_name,
                            "start_line": 0,
                            "end_line": 0,
                            "gap_type": "function",
                            "risk_score": round(score, 3),
                            "risk_factors": factors,
                            "code_snippet": "",
                            "suggestion": _function_suggestion(
                                file_path, fn_name
                            ),
                        }
                    )

        # Sort by risk descending, then file path for stability
        targets.sort(key=lambda t: (-t["risk_score"], t["file_path"]))
        return targets[:max_targets]

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    @staticmethod
    def score_risk(
        file_path: str,
        function_name: str = "",
        line_range: tuple[int, int] = (0, 0),
    ) -> tuple[float, list[str]]:
        """Banking-aware risk scoring.

        Returns:
            (score, risk_factors) where score is clamped to [0.0, 1.0].
        """
        score = 0.2  # base score
        factors: list[str] = []
        path_lower = file_path.lower()
        fn_lower = function_name.lower()

        # --- Path-based scoring ---

        # High risk: banking-critical paths
        banking_keywords = (
            "payment", "transfer", "auth", "session", "kyc", "kvkk",
            "transaction", "odeme", "havale", "eft",
        )
        for kw in banking_keywords:
            if kw in path_lower or kw in fn_lower:
                score += 0.3
                factors.append(f"banking_critical:{kw}")
                break  # only count once

        # Medium-high: API/endpoint/route
        api_keywords = ("api", "endpoint", "route", "controller", "handler")
        for kw in api_keywords:
            if kw in path_lower:
                score += 0.2
                factors.append(f"api_path:{kw}")
                break

        # Medium: validation/verification logic
        validation_keywords = ("validate", "verify", "check", "sanitize", "guard")
        for kw in validation_keywords:
            if kw in fn_lower or kw in path_lower:
                score += 0.2
                factors.append(f"validation_logic:{kw}")
                break

        # Medium: error handling
        error_keywords = ("error", "exception", "handler", "catch", "fallback")
        for kw in error_keywords:
            if kw in path_lower or kw in fn_lower:
                score += 0.15
                factors.append(f"error_handling:{kw}")
                break

        # PII / KVKK
        pii_keywords = ("pii", "personal", "gdpr", "kvkk", "encrypt", "mask")
        for kw in pii_keywords:
            if kw in path_lower or kw in fn_lower:
                score += 0.25
                factors.append(f"pii_handling:{kw}")
                break

        # Negative: utility/helper paths (lower priority)
        low_keywords = ("util", "helper", "format", "constant", "config", "mock", "stub")
        for kw in low_keywords:
            if kw in path_lower:
                score -= 0.1
                factors.append(f"low_priority:{kw}")
                break

        # Gap size bonus for line ranges
        start, end = line_range
        if end > start:
            gap_size = end - start + 1
            if gap_size > 20:
                score += 0.1
                factors.append(f"large_gap:{gap_size}_lines")
            elif gap_size > 10:
                score += 0.05
                factors.append(f"medium_gap:{gap_size}_lines")

        # Clamp to [0.0, 1.0]
        score = max(0.0, min(1.0, score))
        return round(score, 3), factors

    # ------------------------------------------------------------------
    # Banking critical path detection
    # ------------------------------------------------------------------

    @staticmethod
    def identify_banking_critical_paths(
        files: list[dict[str, Any]],
    ) -> list[str]:
        """Scan file paths for banking keywords and return critical paths with low coverage.

        Returns paths that match banking keywords AND have line_rate < 0.8.
        """
        critical: list[str] = []
        for f in files:
            fp = f.get("file_path", "").lower()
            line_rate = f.get("line_rate", 0.0)
            if line_rate >= 0.8:
                continue
            for kw in _BANKING_CRITICAL_KEYWORDS:
                if kw in fp:
                    critical.append(f.get("file_path", ""))
                    break
        return sorted(critical)

    # ------------------------------------------------------------------
    # Line grouping
    # ------------------------------------------------------------------

    @staticmethod
    def group_consecutive_lines(
        missed_lines: list[int],
    ) -> list[tuple[int, int]]:
        """Group consecutive line numbers into (start, end) tuples.

        Example:
            [1, 2, 3, 7, 8, 15] -> [(1, 3), (7, 8), (15, 15)]
        """
        if not missed_lines:
            return []

        sorted_lines = sorted(set(missed_lines))
        groups: list[tuple[int, int]] = []
        start = sorted_lines[0]
        prev = start

        for ln in sorted_lines[1:]:
            if ln == prev + 1:
                prev = ln
            else:
                groups.append((start, prev))
                start = ln
                prev = ln

        groups.append((start, prev))
        return groups


# ------------------------------------------------------------------
# Suggestion helpers (module-private)
# ------------------------------------------------------------------


def _line_suggestion(file_path: str, start: int, end: int) -> str:
    """Generate a suggestion for uncovered lines."""
    count = end - start + 1
    if count == 1:
        return f"{file_path}:{start} satırı kapsanmamış — bu satırı tetikleyen test ekleyin."
    return (
        f"{file_path}:{start}-{end} ({count} satır) kapsanmamış — "
        f"bu aralığı kapsayan test senaryosu ekleyin."
    )


def _branch_suggestion(file_path: str, start: int, end: int) -> str:
    """Generate a suggestion for uncovered branches."""
    return (
        f"{file_path}:{start}-{end} — dal (branch) kapsanmamış. "
        f"Koşulun her iki yönünü de test eden senaryo ekleyin."
    )


def _function_suggestion(file_path: str, fn_name: str) -> str:
    """Generate a suggestion for uncovered functions."""
    return (
        f"{file_path} — '{fn_name}' fonksiyonu hiç çağrılmamış. "
        f"Bu fonksiyonu doğrudan çağıran birim testi ekleyin."
    )
