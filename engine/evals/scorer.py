"""
Engine — LLM Çıktı Kalite Skoru

Her generator (BDD, Playwright, AssertionEngine vb.) çıktısını
0–100 arasında skorlayarak kaliteyi ölçer.

Scorer'lar kural tabanlıdır (hızlı, LLM gerektirmiyor).
LLM-assisted scoring ileride eklenebilir (pahalı, yavaş).

Kullanım:
    from engine.evals.scorer import score_gherkin, score_playwright, ScoreResult

    result = score_gherkin(feature_text)
    print(result.score, result.issues)
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    score: int                       # 0–100
    grade: str                       # A / B / C / D / F
    passed: bool                     # score >= 60
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    @classmethod
    def from_score(cls, score: int, issues: list[str], suggestions: list[str], details: dict) -> "ScoreResult":
        grade = (
            "A" if score >= 90 else
            "B" if score >= 75 else
            "C" if score >= 60 else
            "D" if score >= 40 else
            "F"
        )
        return cls(
            score=max(0, min(100, score)),
            grade=grade,
            passed=score >= 60,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "grade": self.grade,
            "passed": self.passed,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "details": self.details,
        }


# ── Gherkin Scorer ───────────────────────────────────────────────────────────

def score_gherkin(feature_text: str) -> ScoreResult:
    """
    Gherkin feature dosyasını skorla.

    Kriterler (toplam 100 puan):
    - Feature satırı var mı?           (10p)
    - En az 1 senaryo var mı?          (10p)
    - Senaryo başına Then var mı?      (20p)
    - Negatif senaryo var mı?          (15p)
    - Scenario Outline kullanımı       (10p)
    - Step sayısı makul mu? (≤10)      (10p)
    - Türkçe başlıklar mı?             (10p)
    - Tag kullanımı var mı?            (10p)
    - Max 10 senaryo sınırı            (5p)
    """
    issues: list[str] = []
    suggestions: list[str] = []
    score = 0
    details: dict = {}

    # Feature satırı
    has_feature = "Feature:" in feature_text
    if has_feature:
        score += 10
    else:
        issues.append("'Feature:' satırı bulunamadı")

    # Senaryo sayısı
    scenario_count = len(re.findall(r"Scenario(?:\s+Outline)?:", feature_text))
    details["scenario_count"] = scenario_count
    if scenario_count >= 1:
        score += 10
    else:
        issues.append("En az 1 senaryo olmalı")

    if scenario_count > 10:
        issues.append(f"Senaryo sayısı ({scenario_count}) max 10'u aşıyor")
    else:
        score += 5

    # Her senaryo Then içeriyor mu?
    scenarios = re.split(r"Scenario(?:\s+Outline)?:", feature_text)
    then_missing = 0
    for block in scenarios[1:]:
        if "Then" not in block:
            then_missing += 1
    details["scenarios_missing_then"] = then_missing
    if then_missing == 0 and scenario_count > 0:
        score += 20
    elif then_missing > 0:
        issues.append(f"{then_missing} senaryo 'Then' (assertion) içermiyor")
        score += max(0, 20 - then_missing * 5)

    # Negatif senaryo
    negative_keywords = ["negatif", "hatalı", "geçersiz", "başarısız", "yanlış",
                         "hata", "invalid", "negative", "fail", "error"]
    has_negative = any(kw in feature_text.lower() for kw in negative_keywords)
    details["has_negative_scenarios"] = has_negative
    if has_negative:
        score += 15
    else:
        suggestions.append("Negatif test senaryoları ekleyin (geçersiz giriş, hata durumları)")

    # Scenario Outline kullanımı
    has_outline = "Scenario Outline:" in feature_text
    details["has_scenario_outline"] = has_outline
    if has_outline:
        score += 10
    else:
        suggestions.append("Parametreli testler için 'Scenario Outline' + 'Examples' kullanın")

    # Step sayısı (senaryo başına ortalama)
    step_keywords = re.findall(r"^\s*(Given|When|Then|And|But)\s", feature_text, re.MULTILINE)
    avg_steps = len(step_keywords) / max(scenario_count, 1)
    details["avg_steps_per_scenario"] = round(avg_steps, 1)
    if avg_steps <= 10:
        score += 10
    else:
        issues.append(f"Senaryo başına ortalama {avg_steps:.1f} adım — max 10 önerilir")

    # Türkçe başlık kontrolü (Türkçe karakterler veya Türkçe kelimeler)
    turkish_chars = re.search(r"[çğışöüÇĞİŞÖÜ]", feature_text)
    turkish_words = re.search(r"\b(kullanıcı|giriş|sayfa|test|senaryosu|işlemi)\b", feature_text, re.IGNORECASE)
    if turkish_chars or turkish_words:
        score += 10
    else:
        suggestions.append("Senaryo başlıklarını Türkçe yazın")

    # Tag kullanımı
    has_tags = "@" in feature_text
    details["has_tags"] = has_tags
    if has_tags:
        score += 10
    else:
        suggestions.append("Senaryolara @smoke, @regression gibi etiketler ekleyin")

    return ScoreResult.from_score(score, issues, suggestions, details)


# ── Playwright / Python Kod Scorer ───────────────────────────────────────────

def score_playwright(code: str) -> ScoreResult:
    """
    Playwright TypeScript test kodunu skorla.

    Kriterler (toplam 100 puan):
    - Syntax geçerli mi? (JS/TS için basit kontrol)  (20p)
    - En az 1 expect() var mı?                        (20p)
    - getByRole/getByLabel/getByText kullanımı         (15p)
    - page.goto() var mı?                              (10p)
    - test.describe var mı?                            (10p)
    - Hardcoded URL/veri yok mu?                       (10p)
    - await kullanımı doğru mu?                        (10p)
    - data-testid kullanımı                            (5p)
    """
    issues: list[str] = []
    suggestions: list[str] = []
    score = 0
    details: dict = {}

    # Temel Playwright yapısı kontrolü
    has_test = "test(" in code or "test.describe" in code
    if has_test:
        score += 20
    else:
        issues.append("'test()' veya 'test.describe' bloğu bulunamadı")

    # expect() assertion
    expect_count = len(re.findall(r"expect\(", code))
    details["expect_count"] = expect_count
    if expect_count >= 1:
        score += 20
    else:
        issues.append("Hiç 'expect()' assertion bulunamadı")

    if expect_count == 0:
        suggestions.append("En az 1 expect() assertion ekleyin")
    elif expect_count == 1:
        suggestions.append("Daha kapsamlı doğrulama için birden fazla expect() ekleyin")

    # Semantic locator kullanımı
    semantic_locators = len(re.findall(r"getBy(?:Role|Label|Text|Placeholder|AltText|Title)\(", code))
    details["semantic_locator_count"] = semantic_locators
    if semantic_locators >= 1:
        score += 15
    else:
        issues.append("Semantic locator bulunamadı (getByRole, getByLabel, getByText)")
        suggestions.append("CSS selector yerine getByRole/getByLabel/getByText kullanın")

    # page.goto()
    if "page.goto(" in code:
        score += 10
    else:
        suggestions.append("Test başlangıcında page.goto() ile URL'ye git")

    # test.describe
    if "test.describe" in code:
        score += 10
    else:
        suggestions.append("İlgili testleri test.describe() bloğunda gruplandırın")

    # Hardcoded değer kontrolü (localhost hariç)
    hardcoded_urls = re.findall(r"https?://(?!localhost)[a-zA-Z0-9.-]+", code)
    details["hardcoded_urls"] = hardcoded_urls
    if not hardcoded_urls:
        score += 10
    else:
        issues.append(f"Hardcoded URL bulundu: {hardcoded_urls[:2]}")
        suggestions.append("URL'leri environment variable veya base URL config'inden alın")

    # await kullanımı
    async_calls = re.findall(r"(?:click|fill|goto|press|type|check|uncheck|selectOption)\(", code)
    awaited_calls = re.findall(r"await\s+\w+\.(?:click|fill|goto|press|type|check|uncheck|selectOption)\(", code)
    details["async_calls"] = len(async_calls)
    details["awaited_calls"] = len(awaited_calls)
    if async_calls and len(awaited_calls) >= len(async_calls) * 0.8:
        score += 10
    elif async_calls:
        missing = len(async_calls) - len(awaited_calls)
        issues.append(f"{missing} async çağrı 'await' eksik olabilir")

    # data-testid kullanımı
    if "data-testid" in code or "getByTestId" in code:
        score += 5
    else:
        suggestions.append("Kararlı locator için data-testid attribute'u kullanın")

    return ScoreResult.from_score(score, issues, suggestions, details)


def score_python_test(code: str) -> ScoreResult:
    """
    Python pytest test kodunu skorla.

    Kriterler (toplam 100 puan):
    - Python syntax geçerli mi?          (25p)
    - En az 1 assert var mı?             (25p)
    - test_ prefix'li fonksiyon var mı?  (20p)
    - Fixture kullanımı                  (15p)
    - Docstring var mı?                  (10p)
    - Parametrize kullanımı              (5p)
    """
    issues: list[str] = []
    suggestions: list[str] = []
    score = 0
    details: dict = {}

    # Python syntax
    try:
        ast.parse(code)
        score += 25
        details["syntax_valid"] = True
    except SyntaxError as exc:
        issues.append(f"Python syntax hatası: {exc}")
        details["syntax_valid"] = False

    # Assert sayısı
    assert_count = len(re.findall(r"\bassert\s+", code))
    details["assert_count"] = assert_count
    if assert_count >= 2:
        score += 25
    elif assert_count == 1:
        score += 15
        suggestions.append("Daha kapsamlı doğrulama için birden fazla assert ekleyin")
    else:
        issues.append("Hiç 'assert' ifadesi bulunamadı")

    # test_ fonksiyonlar
    test_funcs = re.findall(r"def\s+(test_\w+)", code)
    details["test_function_count"] = len(test_funcs)
    if test_funcs:
        score += 20
    else:
        issues.append("'test_' ile başlayan fonksiyon bulunamadı")

    # Fixture kullanımı
    fixtures = re.findall(r"@pytest\.fixture|def\s+\w+\(.*\bfixture\b", code)
    if fixtures or re.search(r"def test_\w+\([^)]+\)", code):
        score += 15
    else:
        suggestions.append("Test bağımlılıkları için pytest fixture kullanın")

    # Docstring
    if '"""' in code or "'''" in code:
        score += 10
    else:
        suggestions.append("Test fonksiyonlarına docstring ekleyin")

    # Parametrize
    if "@pytest.mark.parametrize" in code:
        score += 5
    else:
        suggestions.append("Birden fazla değer testi için @pytest.mark.parametrize kullanın")

    return ScoreResult.from_score(score, issues, suggestions, details)


# ── Toplu Skorlama ───────────────────────────────────────────────────────────

def score_pipeline_output(pipeline_outputs: dict[str, str]) -> dict[str, ScoreResult]:
    """
    Pipeline çıktılarını toplu skorla.

    Args:
        pipeline_outputs: {"step_name": "output_text", ...}

    Returns:
        {"step_name": ScoreResult, ...}
    """
    results: dict[str, ScoreResult] = {}

    if "generate_gherkin" in pipeline_outputs:
        results["generate_gherkin"] = score_gherkin(pipeline_outputs["generate_gherkin"])

    if "generate_playwright" in pipeline_outputs:
        results["generate_playwright"] = score_playwright(pipeline_outputs["generate_playwright"])

    if "generate_java_steps" in pipeline_outputs:
        results["generate_java_steps"] = score_python_test(pipeline_outputs.get("generate_java_steps", ""))

    return results
