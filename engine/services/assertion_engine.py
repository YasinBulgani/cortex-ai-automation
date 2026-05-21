"""
Mevcut testlerdeki eksik assertion'ları tespit eden ve öneren servis.

Test fonksiyonlarını AST ile analiz eder, az assertion'lı testler için
LLM ile anlamlı assertion önerileri üretir.
"""
from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from ._base_generator import refine_generate
from .llm_gateway import LLMGateway
from .prompt_loader import get_engine_prompt

logger = logging.getLogger(__name__)
ASSERTION_SYSTEM_PROMPT = get_engine_prompt("assertion_analyzer")


@dataclass
class AssertionSuggestion:
    test_file: str
    test_name: str
    current_assertion_count: int
    suggested_assertions: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "test_file": self.test_file,
            "test_name": self.test_name,
            "current_assertion_count": self.current_assertion_count,
            "suggested_assertions": self.suggested_assertions,
            "rationale": self.rationale[:500],
        }


class AssertionEngine:
    """Eksik assertion tespiti ve öneri üretimi."""

    MIN_ASSERTIONS = 2

    def __init__(self, gateway: LLMGateway, model: str | None = None):
        self.gateway = gateway
        self.model = model or "gpt-4o"

    def analyze_file(self, file_path: str | Path) -> list[AssertionSuggestion]:
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            source = path.read_text(errors="replace")
        except OSError:
            return []
        functions = self._extract_test_functions(source)

        suggestions: list[AssertionSuggestion] = []
        for func_name, func_body in functions:
            asserts = self._count_assertions(func_body)
            if asserts < self.MIN_ASSERTIONS:
                suggestion = self._suggest(str(file_path), func_name, func_body, asserts)
                if suggestion:
                    suggestions.append(suggestion)
        return suggestions

    # ── extraction ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_test_functions(source: str) -> list[tuple[str, str]]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        results: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                segment = ast.get_source_segment(source, node)
                if segment:
                    results.append((node.name, segment))
        return results

    @staticmethod
    def _count_assertions(func_body: str) -> int:
        patterns = [
            r"\bassert\s+",
            r"\bexpect\(",
            r"\bassertEqual\(",
            r"\bassertTrue\(",
            r"\bassertFalse\(",
            r"\bassertIn\(",
            r"\bassertRaises\(",
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, func_body))
        return count

    # ── LLM suggestion ──────────────────────────────────────────────────────

    def _suggest(self, file_path: str, func_name: str, func_body: str, current_count: int) -> AssertionSuggestion | None:
        messages = [
            {
                "role": "system",
                "content": ASSERTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"Dosya: {file_path}\nTest: {func_name}\nMevcut assertion sayısı: {current_count}\n\nKod:\n{func_body[:2000]}",
            },
        ]

        def _validate(output: str) -> list[str]:
            suggestions = re.findall(r"(?:assert\s+.+|expect\(.+\)\..+)", output)
            if not suggestions:
                return ["Çıktıda hiç assert veya expect ifadesi bulunamadı"]
            return []

        content, _, _ = refine_generate(
            call_fn=lambda msgs: self.gateway.complete(
                msgs, model=self.model, temperature=0.2, max_tokens=600
            ).content,
            messages=messages,
            validate_fn=_validate,
            refine_prompt=(
                "Önceki yanıtta assertion örneği bulunamadı.\n"
                "Lütfen her satırda bir tane olmak üzere 'assert ...' veya 'expect(...)...' "
                "formatında assertion önerileri yaz."
            ),
            max_refine=1,
            tag="AssertionEngine",
        )

        suggested = re.findall(r"(?:assert\s+.+|expect\(.+\)\..+)", content)
        if suggested:
            return AssertionSuggestion(
                test_file=file_path,
                test_name=func_name,
                current_assertion_count=current_count,
                suggested_assertions=suggested[:5],
                rationale=content,
            )
        return None
