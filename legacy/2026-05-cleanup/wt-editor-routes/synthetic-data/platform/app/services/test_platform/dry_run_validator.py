"""
DryRunValidator — Test Script Syntax ve Locator Doğrulama

Otomasyon scriptlerini gerçekten çalıştırmadan önce:
  - Python syntax kontrolü
  - Import doğrulama
  - Locator kalite skoru
  - Beklenen değer varlığı kontrolü
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationIssue:
    severity: str   # error / warning / info
    line: int
    message: str


@dataclass
class ValidationResult:
    script_id: str
    is_valid: bool
    syntax_ok: bool
    issues: List[ValidationIssue]
    locator_quality_score: float   # 0.0 - 1.0
    suggestions: List[str]
    overall_score: float           # 0.0 - 1.0


class DryRunValidator:
    """
    Test scriptlerini çalıştırmadan analiz eder ve
    kalite skoru üretir.
    """

    # Kötü locator sinyalleri
    _UNSTABLE_PATTERNS = [
        r'By\.XPATH.*position\(\)',
        r'By\.XPATH.*\[last\(\)',
        r'class_name.*btn-\d',
        r'css.*:nth-child',
    ]

    # Gerekli import'lar
    _REQUIRED_IMPORTS = {
        "playwright": ["playwright.sync_api"],
        "selenium": ["selenium.webdriver"],
        "requests": ["requests"],
    }

    def validate(self, script_code: str, framework: str = "playwright") -> ValidationResult:
        """
        Script kodunu doğrular.

        Args:
            script_code: Python kod metni
            framework: playwright / selenium / requests

        Returns:
            ValidationResult
        """
        issues: List[ValidationIssue] = []

        # 1. Syntax kontrolü
        syntax_ok, syntax_issues = self._check_syntax(script_code)
        issues.extend(syntax_issues)

        # 2. Import kontrolü
        issues.extend(self._check_imports(script_code, framework))

        # 3. Locator kalite kontrolü
        locator_score, locator_issues = self._check_locators(script_code)
        issues.extend(locator_issues)

        # 4. Assert varlık kontrolü
        issues.extend(self._check_assertions(script_code))

        # Genel skor
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        overall = max(0.0, 1.0 - (errors * 0.3) - (warnings * 0.1))
        overall = min(overall, locator_score + 0.2)

        suggestions = self._generate_suggestions(issues)

        return ValidationResult(
            script_id="DRY-RUN",
            is_valid=errors == 0 and syntax_ok,
            syntax_ok=syntax_ok,
            issues=issues,
            locator_quality_score=round(locator_score, 2),
            suggestions=suggestions,
            overall_score=round(overall, 2),
        )

    def _check_syntax(self, code: str):
        issues = []
        try:
            ast.parse(code)
            return True, []
        except SyntaxError as e:
            issues.append(ValidationIssue("error", e.lineno or 0, f"Syntax hatası: {e.msg}"))
            return False, issues

    def _check_imports(self, code: str, framework: str):
        issues = []
        required = self._REQUIRED_IMPORTS.get(framework, [])
        for req in required:
            if req not in code:
                issues.append(ValidationIssue(
                    "warning", 1,
                    f"'{req}' import bulunamadı — {framework} testi için gerekli."
                ))
        return issues

    def _check_locators(self, code: str):
        issues = []
        score = 1.0

        for pattern in self._UNSTABLE_PATTERNS:
            if re.search(pattern, code):
                issues.append(ValidationIssue(
                    "warning", 0,
                    f"Kararsız locator tespit edildi: '{pattern}'. data-testid tercih edin."
                ))
                score -= 0.2

        # Olumlu: data-testid kullanımı
        if "data-testid" in code or "get_by_test_id" in code:
            score = min(score + 0.1, 1.0)

        return max(0.0, score), issues

    def _check_assertions(self, code: str):
        issues = []
        has_assert = "assert " in code or "expect(" in code or ".to_have" in code
        if not has_assert:
            issues.append(ValidationIssue(
                "warning", 0,
                "Test içinde doğrulama (assert/expect) bulunamadı — test her zaman geçer görünebilir."
            ))
        return issues

    def _generate_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        suggestions = []
        msgs = [i.message for i in issues]
        if any("assert" in m for m in msgs):
            suggestions.append("Her test adımı sonunda `assert` veya `expect()` kullanın.")
        if any("locator" in m.lower() for m in msgs):
            suggestions.append("HTML element'lerine `data-testid` attribute ekleyin.")
        if any("import" in m.lower() for m in msgs):
            suggestions.append("Gerekli kütüphanelerin requirements.txt'e eklendiğinden emin olun.")
        return suggestions

    def validate(self, script: str) -> dict:
        """
        Script'i doğrula ve sonucu dict olarak döndür.

        Args:
            script: Python otomasyon kodu string olarak.

        Returns:
            Dict with keys:
              - valid (bool): Script geçerli mi?
              - errors (list[str]): Kritik hatalar.
              - warnings (list[str]): Uyarılar.
        """
        result = self.validate_full(script)
        errors = [i.message for i in result.issues if i.severity == "error"]
        warnings = [i.message for i in result.issues if i.severity == "warning"]
        return {
            "valid": result.is_valid,
            "errors": errors,
            "warnings": warnings,
        }

    def validate_full(self, script_code: str, framework: str = "playwright") -> "ValidationResult":
        """
        Script kodunu tam doğrular ve ValidationResult nesnesi döndür.

        Args:
            script_code: Python kod metni.
            framework: playwright / selenium / requests.

        Returns:
            ValidationResult dataclass.
        """
        issues: List[ValidationIssue] = []

        if not script_code or not script_code.strip():
            issues.append(ValidationIssue("error", 0, "Script is empty."))
            return ValidationResult(
                script_id="DRY-RUN",
                is_valid=False,
                syntax_ok=False,
                issues=issues,
                locator_quality_score=0.0,
                suggestions=[],
                overall_score=0.0,
            )

        syntax_ok, syntax_issues = self._check_syntax(script_code)
        issues.extend(syntax_issues)

        if syntax_ok:
            issues.extend(self._check_imports(script_code, framework))
            locator_score, locator_issues = self._check_locators(script_code)
            issues.extend(locator_issues)
            issues.extend(self._check_assertions(script_code))
        else:
            locator_score = 0.0

        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        overall = max(0.0, 1.0 - (errors * 0.3) - (warnings * 0.1))
        overall = min(overall, locator_score + 0.2) if syntax_ok else overall
        suggestions = self._generate_suggestions(issues)

        return ValidationResult(
            script_id="DRY-RUN",
            is_valid=errors == 0 and syntax_ok,
            syntax_ok=syntax_ok,
            issues=issues,
            locator_quality_score=round(locator_score if syntax_ok else 0.0, 2),
            suggestions=suggestions,
            overall_score=round(overall, 2),
        )
