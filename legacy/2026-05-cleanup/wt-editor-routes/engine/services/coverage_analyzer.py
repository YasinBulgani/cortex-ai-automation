"""
Coverage raporunu analiz edip test önerileri üreten servis.

Düşük coverage alanlarını önceliklendirir ve LLM ile test önerisi üretir.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_SKIP_PATTERNS = {"__pycache__", "migrations", "node_modules", ".venv", "test_", "ai_generated"}


@dataclass
class CoverageGap:
    file_path: str
    uncovered_lines: list[int]
    line_coverage_pct: float
    priority: str  # "critical" | "high" | "medium" | "low"
    suggested_test: str = ""

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "uncovered_lines_count": len(self.uncovered_lines),
            "line_coverage_pct": self.line_coverage_pct,
            "priority": self.priority,
            "suggested_test": self.suggested_test[:500] if self.suggested_test else "",
        }


class CoverageAnalyzer:
    CRITICAL_THRESHOLD = 50.0
    HIGH_THRESHOLD = 70.0
    MEDIUM_THRESHOLD = 85.0

    def __init__(self, gateway: LLMGateway | None = None, model: str | None = None):
        self.gateway = gateway
        self.model = model or "gpt-4o"

    def analyze(
        self,
        coverage_json_path: str | Path = "reports/coverage.json",
        generate_suggestions: bool = False,
    ) -> list[CoverageGap]:
        data = self._load_coverage(_REPO_ROOT / coverage_json_path)
        gaps: list[CoverageGap] = []

        for file_path, info in data.items():
            if any(p in file_path for p in _SKIP_PATTERNS):
                continue

            uncovered = info.get("uncovered_lines", [])
            total = max(info.get("total_lines", 1), 1)
            covered = info.get("covered_lines", 0)
            pct = round((covered / total) * 100, 1)

            if pct >= self.MEDIUM_THRESHOLD:
                continue

            priority = self._determine_priority(pct, file_path)
            suggestion = ""

            if generate_suggestions and self.gateway and priority in ("critical", "high"):
                source = self._read_source(file_path)
                if source:
                    suggestion = self._generate_suggestion(file_path, source, uncovered)

            gaps.append(CoverageGap(
                file_path=file_path,
                uncovered_lines=uncovered,
                line_coverage_pct=pct,
                priority=priority,
                suggested_test=suggestion,
            ))

        gaps.sort(key=lambda g: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(g.priority, 4))
        return gaps

    def save_report(self, gaps: list[CoverageGap], output: str | Path = "reports/coverage-gaps.json"):
        try:
            out = _REPO_ROOT / output
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps([g.to_dict() for g in gaps], indent=2, ensure_ascii=False))
        except OSError as exc:
            logger.warning("Coverage gaps raporu yazılamadı: %s", exc)

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _determine_priority(pct: float, file_path: str) -> str:
        critical_keywords = {"auth", "security", "payment", "transaction", "login"}
        is_critical = any(k in file_path.lower() for k in critical_keywords)
        if pct < 50.0 or is_critical:
            return "critical"
        if pct < 70.0:
            return "high"
        return "medium"

    def _generate_suggestion(self, file_path: str, source: str, uncovered: list[int]) -> str:
        snippets = self._extract_uncovered_snippets(source, uncovered)
        if not snippets:
            return ""
        messages = [
            {"role": "system", "content": "Verilen kaynak kodun test edilmemiş bölümleri için kısa pytest test önerisi üret."},
            {"role": "user", "content": f"Dosya: {file_path}\n\nTest edilmemiş kod:\n{snippets}\n\nKısa test kodu öner."},
        ]
        resp = self.gateway.complete(messages, model=self.model, temperature=0.2, max_tokens=800)
        return resp.content

    @staticmethod
    def _extract_uncovered_snippets(source: str, uncovered: list[int], max_lines: int = 15) -> str:
        lines = source.split("\n")
        parts: list[str] = []
        for ln in uncovered[:max_lines]:
            if 0 < ln <= len(lines):
                start = max(0, ln - 2)
                end = min(len(lines), ln + 1)
                for i in range(start, end):
                    prefix = ">>>" if i + 1 == ln else "   "
                    parts.append(f"{prefix} {i + 1}: {lines[i]}")
                parts.append("---")
        return "\n".join(parts)

    @staticmethod
    def _load_coverage(path: Path) -> dict:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not load coverage JSON %s: %s", path, exc)
        return {}

    @staticmethod
    def _read_source(file_path: str) -> str | None:
        p = _REPO_ROOT / file_path
        if p.exists():
            try:
                return p.read_text(errors="replace")
            except OSError as exc:
                logger.debug("Could not read source %s: %s", p, exc)
        return None
