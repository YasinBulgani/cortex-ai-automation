"""Code validity scorers — üretilen kodun AST'te geçerli olduğunu test eder.

Kullanım alanı:
    * ``nl_test_generator`` çıktıları (Python pytest / pytest-bdd kodu)
    * TypeScript compile (bu scorer Python için; TS için ayrı node tooling)

Scorer:
    * ``python_ast_valid``     : ``ast.parse(code)`` başarılı mı
    * ``python_has_assert``    : üretilen kod en az bir assert içeriyor mu
    * ``python_has_testid``    : üretilen kod data-testid kullanıyor mu
"""
from __future__ import annotations

import ast
import re
from typing import Any, Dict

from ..schemas import EvalCase, ScorerOutput


def _extract_code(actual: Dict[str, Any]) -> str:
    """Actual'dan kod alanını çıkar. Birkaç farklı anahtar formatına dayanıklı."""
    for key in ("code", "generated_code", "output", "content"):
        val = actual.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


class PythonAstValidScorer:
    name = "python_ast_valid"

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        code = _extract_code(actual)
        if not code:
            return ScorerOutput(
                name=self.name, value=0.0, passed=False,
                details={"error": "no_code"},
            )
        try:
            ast.parse(code)
            return ScorerOutput(name=self.name, value=1.0, passed=True)
        except SyntaxError as exc:
            return ScorerOutput(
                name=self.name, value=0.0, passed=False,
                details={"syntax_error": str(exc), "line": exc.lineno},
            )


class PythonHasAssertScorer:
    """En az bir assert / pytest assertion içeriyor mu?"""

    name = "python_has_assert"
    _PATTERNS = (
        re.compile(r"\bassert\s"),
        re.compile(r"pytest\.raises\("),
        re.compile(r"\.assert_[a-z_]+\("),     # unittest .assert_called, .assertEqual vb.
        re.compile(r"expect\("),               # Playwright-style
    )

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        code = _extract_code(actual)
        if not code:
            return ScorerOutput(name=self.name, value=0.0, passed=False)
        has = any(p.search(code) for p in self._PATTERNS)
        return ScorerOutput(
            name=self.name,
            value=1.0 if has else 0.0,
            passed=has,
            details={"match_count": sum(1 for p in self._PATTERNS if p.search(code))},
        )


class PythonHasTestIdScorer:
    """``data-testid`` veya ``getByTestId`` kullanımı var mı?"""

    name = "python_has_testid"
    _RX = re.compile(r"(data[-_]testid|getByTestId|get_by_test_id)", re.IGNORECASE)

    def score(self, *, case: EvalCase, actual: Dict[str, Any]) -> ScorerOutput:
        code = _extract_code(actual)
        if not code:
            return ScorerOutput(name=self.name, value=0.0, passed=False)
        has = bool(self._RX.search(code))
        return ScorerOutput(
            name=self.name,
            value=1.0 if has else 0.0,
            passed=has,
        )
