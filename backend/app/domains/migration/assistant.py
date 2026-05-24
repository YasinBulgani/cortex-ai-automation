"""Migration asistanı — Selenium (Java/Python) → TestwrightAI/Playwright DSL.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §6 / E4.4 (L, P3).

Kapsam (Faz A — bu commit):
    * Selenium Java step definitions (Cucumber):
      @Given/@When/@Then pattern → aynı pattern'li Playwright TypeScript
    * Selenium Python (pytest-bdd veya plain):
      @given/@when/@then → pytest-bdd + Playwright Python
    * Katalon Groovy basit adımlar:
      WebUI.click, WebUI.setText, WebUI.verifyElementPresent → DSL eşleşmesi

    Her dönüştürücü "kaba ama çalışan" taslak üretir. Kullanıcı elle
    gözden geçirir; LLM ile zenginleştirme ileride (prompt_shield
    arkasında).

Çıkışlar:
    * MigrationResult — dönüştürülmüş TS/Py kod string'i + rapor
    * unhandled_steps — hangi adımlar eşleşmedi (operatör elle yapacak)

CLI:
    python -m scripts.migrate --source selenium-java --file StepDefs.java
    python -m scripts.migrate --source selenium-py --dir old_steps/
    python -m scripts.migrate --source katalon --file Script.groovy --json

Tasarım:
    * Pure Python + regex — AST overkill; bu bir "assist", %100 doğru olması
      beklenmiyor. %70-80 otomatik + elle tuning modeli.
    * LLM enjekte noktası var (enrich_with_llm=callback). Çağrılmazsa
      regex-only çıktı.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


SourceFramework = Literal["selenium-java", "selenium-py", "katalon", "cypress-e2e"]


# ── Veri tipleri ─────────────────────────────────────────────────────────


@dataclass
class MigratedStep:
    """Tek bir step'in dönüştürülmüş hali."""

    original: str
    gherkin_keyword: str  # Given/When/Then/* (Türkçe Ezeley/Eğer/Ne zaman/O halde desteği yok — EN kabul)
    gherkin_pattern: str
    translated_code: str
    mapped_to_dsl_action: Optional[str] = None
    notes: str = ""


@dataclass
class UnhandledStep:
    original: str
    reason: str
    line_hint: Optional[int] = None


@dataclass
class MigrationResult:
    source_framework: SourceFramework
    source_file: Optional[str] = None
    steps_migrated: int = 0
    steps_total: int = 0
    steps_unhandled: int = 0
    migrated: List[MigratedStep] = field(default_factory=list)
    unhandled: List[UnhandledStep] = field(default_factory=list)
    output_code: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.steps_total == 0:
            return 0.0
        return round(self.steps_migrated / self.steps_total, 4)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        return d


# ── Step pattern tanıyıcılar (ortak) ────────────────────────────────────


# Selenium Java Cucumber: @Given("pattern")
_JAVA_ANNOTATION_RE = re.compile(
    r'@(Given|When|Then|And|But)\s*\(\s*"([^"]+)"\s*\)\s*\n\s*(public\s+)?(?:void|[A-Za-z_][A-Za-z0-9_<>]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(\{)',
    re.MULTILINE,
)

# Selenium Python (plain + pytest-bdd): @when("pattern") def fn(...):
_PY_DECORATOR_RE = re.compile(
    r'@(given|when|then)\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\n\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\):',
    re.MULTILINE,
)

# Katalon Groovy: WebUI.click(findTestObject('Pages/LoginPage/submit'))
_KATALON_ACTION_RE = re.compile(
    r"WebUI\.(click|setText|verifyElementPresent|verifyElementVisible|verifyElementText|navigateToUrl|delay|uploadFile)\s*\(([^)]*)\)",
    re.MULTILINE,
)


# ── Selenium Java -> TS ──────────────────────────────────────────────────


# Yaygın adım pattern'lerini Playwright TS + DSL eşleşmesine çevir
# Key: küçük harf normalize edilmiş pattern parçası; Value: (ts_snippet, dsl_action, notes)
_JAVA_STEP_TRANSLATIONS: List[Tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"i\s+(?:navigate|go)\s+to\s+\{string\}", re.I),
        "await page.goto(url);",
        "en_open_url",
    ),
    # Spesifik → genel sırada: "click the button" → "click on" → "click"
    (
        re.compile(r"i\s+click\s+the\s+button\s+\{string\}", re.I),
        "await page.getByRole('button', { name: text }).click();",
        "click_text",
    ),
    (
        re.compile(r"i\s+click(?:\s+on)?\s+.*\{string\}", re.I),
        "await page.getByText(text, { exact: false }).click();",
        "click_text",
    ),
    (
        re.compile(r"i\s+enter\s+\{string\}\s+(?:in|into)(?:\s+the)?\s+(?:input|field)\s+\{string\}", re.I),
        "await page.getByLabel(fieldName).fill(value);",
        "fill_input",
    ),
    (
        re.compile(r"i\s+fill\s+\{string\}", re.I),
        "await page.getByLabel(fieldName).fill(value);",
        "en_fill",
    ),
    (
        re.compile(r"i\s+(check|verify).*visible", re.I),
        "await expect(page.getByText(text)).toBeVisible();",
        None,
    ),
    (
        re.compile(r"i\s+(check|verify).*contains?\s+\{string\}", re.I),
        "await expect(page.getByText(text)).toContainText(text);",
        None,
    ),
    (
        re.compile(r"i\s+wait\s+for\s+\{string\}", re.I),
        "await page.waitForSelector(selector);",
        "en_wait",
    ),
    (
        re.compile(r"i\s+press\s+(?:key\s+)?\{string\}", re.I),
        "await page.keyboard.press(key);",
        "en_press_key",
    ),
    (
        re.compile(r"i\s+select\s+\{string\}", re.I),
        "await page.locator(selector).selectOption(value);",
        "en_select",
    ),
    (
        re.compile(r"i\s+scroll\s+to", re.I),
        "await page.locator(selector).scrollIntoViewIfNeeded();",
        "en_scroll_to",
    ),
    (
        re.compile(r"i\s+upload\s+(?:file\s+)?\{string\}", re.I),
        "await page.locator(selector).setInputFiles(path);",
        "en_upload",
    ),
]


def _translate_step_body(pattern: str) -> Tuple[str, Optional[str]]:
    """Gherkin pattern → TS snippet + DSL action (eşleşme varsa)."""
    for pat, ts, dsl in _JAVA_STEP_TRANSLATIONS:
        if pat.search(pattern):
            return ts, dsl
    # No pattern matched — return a stub that throws at runtime so the developer
    # knows immediately which step needs work (not a silent TODO comment).
    escaped = pattern.replace("'", "\\'")
    return (
        f"throw new Error('MIGRATION_NEEDED: step not auto-translated — "
        f"implement: {escaped}');"
    ), None


def migrate_selenium_java(source: str, *, source_file: Optional[str] = None) -> MigrationResult:
    result = MigrationResult(source_framework="selenium-java", source_file=source_file)
    matches = list(_JAVA_ANNOTATION_RE.finditer(source))
    if not matches:
        result.warnings.append("Hiç @Given/@When/@Then bulunamadı")
        return result

    ts_lines: List[str] = [
        "// Auto-migrated by TestwrightAI migration assistant",
        "// Source: selenium-java cucumber step definitions",
        "// NOTE: Her step manuel review gerektirir (selector'lar, locators, assertions)",
        "",
        "import { test, expect, Page } from '@playwright/test';",
        "",
    ]

    for m in matches:
        keyword = m.group(1)
        pattern = m.group(2)
        func_name = m.group(4)
        result.steps_total += 1

        ts_body, dsl = _translate_step_body(pattern)
        if ts_body.startswith("// TODO"):
            result.steps_unhandled += 1
            result.unhandled.append(
                UnhandledStep(
                    original=f'@{keyword}("{pattern}")',
                    reason="Pattern eşleşmesi yok — manuel migration",
                )
            )
        else:
            result.steps_migrated += 1

        step = MigratedStep(
            original=f'@{keyword}("{pattern}") {func_name}',
            gherkin_keyword=keyword,
            gherkin_pattern=pattern,
            translated_code=ts_body,
            mapped_to_dsl_action=dsl,
            notes=(
                f"// DSL action: {dsl}" if dsl else "// Review — no DSL mapping"
            ),
        )
        result.migrated.append(step)

        ts_lines.append(f"// {keyword}: {pattern}")
        ts_lines.append(
            f"test('{_slugify(func_name)}', async ({{ page }}) => {{\n  {ts_body}\n}});"
        )
        ts_lines.append("")

    result.output_code = "\n".join(ts_lines)
    return result


# ── Selenium Python -> pytest-bdd + Playwright ──────────────────────────


_PY_STEP_TRANSLATIONS: List[Tuple[re.Pattern[str], str, Optional[str]]] = [
    (
        re.compile(r"\bvisit[_ ]?url|goto|navigate", re.I),
        "page.goto(url)",
        "en_open_url",
    ),
    (
        re.compile(r"\bclick", re.I),
        "page.get_by_text(text).click()",
        "click_text",
    ),
    (
        re.compile(r"\benter|fill|input", re.I),
        "page.get_by_label(field).fill(value)",
        "fill_input",
    ),
    (
        re.compile(r"\b(verify|assert|expect|see).*visible", re.I),
        "expect(page.get_by_text(text)).to_be_visible()",
        None,
    ),
    (
        re.compile(r"\bwait", re.I),
        "page.wait_for_selector(selector)",
        "en_wait",
    ),
]


def migrate_selenium_py(source: str, *, source_file: Optional[str] = None) -> MigrationResult:
    result = MigrationResult(source_framework="selenium-py", source_file=source_file)
    matches = list(_PY_DECORATOR_RE.finditer(source))
    if not matches:
        result.warnings.append("Hiç @given/@when/@then bulunamadı")
        return result

    py_lines: List[str] = [
        "# Auto-migrated by TestwrightAI migration assistant",
        "# Source: selenium-python cucumber/pytest-bdd steps",
        "from pytest_bdd import given, when, then, scenarios",
        "from playwright.sync_api import Page, expect",
        "",
        "scenarios('../features/migrated.feature')",
        "",
    ]

    for m in matches:
        keyword = m.group(1)
        pattern = m.group(2)
        func_name = m.group(3)
        result.steps_total += 1

        # Default: raise at runtime so the developer knows immediately (not a silent comment)
        escaped_pattern = pattern.replace('"', '\\"')
        translated = f'    raise NotImplementedError("MIGRATION_NEEDED: {escaped_pattern}")'
        dsl = None
        for pat, body, mapped_dsl in _PY_STEP_TRANSLATIONS:
            if pat.search(func_name) or pat.search(pattern):
                translated = f"    {body}"
                dsl = mapped_dsl
                break

        if "TODO" in translated:
            result.steps_unhandled += 1
            result.unhandled.append(
                UnhandledStep(
                    original=f'@{keyword}("{pattern}") def {func_name}',
                    reason="Pattern eşleşmesi yok",
                )
            )
        else:
            result.steps_migrated += 1

        result.migrated.append(
            MigratedStep(
                original=f'@{keyword}("{pattern}") def {func_name}',
                gherkin_keyword=keyword,
                gherkin_pattern=pattern,
                translated_code=translated.strip(),
                mapped_to_dsl_action=dsl,
            )
        )

        py_lines.append(f"@{keyword}('{pattern}')")
        py_lines.append(f"def {func_name}(page: Page):")
        py_lines.append(translated)
        py_lines.append("")

    result.output_code = "\n".join(py_lines)
    return result


# ── Katalon -> TS ──────────────────────────────────────────────────────


_KATALON_TS_MAP = {
    "click": "await page.locator(selector).click();",
    "setText": "await page.locator(selector).fill(value);",
    "verifyElementPresent": "await expect(page.locator(selector)).toBeAttached();",
    "verifyElementVisible": "await expect(page.locator(selector)).toBeVisible();",
    "verifyElementText": "await expect(page.locator(selector)).toHaveText(text);",
    "navigateToUrl": "await page.goto(url);",
    "delay": "await page.waitForTimeout(ms);",
    "uploadFile": "await page.locator(selector).setInputFiles(path);",
}


def migrate_katalon(source: str, *, source_file: Optional[str] = None) -> MigrationResult:
    result = MigrationResult(source_framework="katalon", source_file=source_file)
    matches = list(_KATALON_ACTION_RE.finditer(source))
    if not matches:
        result.warnings.append("Hiç WebUI.* çağrısı bulunamadı")
        return result

    ts_lines: List[str] = [
        "// Auto-migrated from Katalon Groovy",
        "// NOTE: findTestObject('Pages/...') referansları manuel selector'a çevrilmeli",
        "",
        "import { test, expect } from '@playwright/test';",
        "",
        "test('migrated from katalon', async ({ page }) => {",
    ]

    for m in matches:
        action = m.group(1)
        args = m.group(2).strip()
        result.steps_total += 1

        ts = _KATALON_TS_MAP.get(action)
        if ts is None:
            result.steps_unhandled += 1
            result.unhandled.append(
                UnhandledStep(
                    original=f"WebUI.{action}({args})",
                    reason=f"Desteklenmeyen Katalon komutu: {action}",
                )
            )
            ts_lines.append(f"  throw new Error('MIGRATION_NEEDED: WebUI.{action}({args[:60]}...)');")
            continue

        result.steps_migrated += 1
        result.migrated.append(
            MigratedStep(
                original=f"WebUI.{action}(...)",
                gherkin_keyword="When",
                gherkin_pattern=f"WebUI.{action}",
                translated_code=ts,
                notes="Katalon findTestObject ref'leri manuel selector gerekir",
            )
        )
        ts_lines.append(f"  // Kaynak: WebUI.{action}({args[:80]}...)")
        ts_lines.append(f"  {ts}")

    ts_lines.append("});")
    result.output_code = "\n".join(ts_lines)
    return result


# ── Facade ──────────────────────────────────────────────────────────────


def _slugify(s: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = re.sub(r"[_]+", " ", s).lower().strip()
    return re.sub(r"\s+", " ", s)


_MIGRATORS: Dict[str, Callable[[str], MigrationResult]] = {
    "selenium-java": lambda s: migrate_selenium_java(s),
    "selenium-py": lambda s: migrate_selenium_py(s),
    "katalon": lambda s: migrate_katalon(s),
}


def migrate_source(
    framework: SourceFramework, source: str, *, source_file: Optional[str] = None
) -> MigrationResult:
    fn = _MIGRATORS.get(framework)
    if fn is None:
        raise ValueError(
            f"Desteklenmeyen framework: {framework}. Desteklenenler: {sorted(_MIGRATORS)}"
        )
    # Kwarg forwarding — her fonksiyonun farklı signature'ı: ayrı dispatch
    if framework == "selenium-java":
        return migrate_selenium_java(source, source_file=source_file)
    if framework == "selenium-py":
        return migrate_selenium_py(source, source_file=source_file)
    if framework == "katalon":
        return migrate_katalon(source, source_file=source_file)
    raise ValueError(f"Unreachable: {framework}")


def migrate_directory(
    framework: SourceFramework,
    directory: Path,
    *,
    patterns: Optional[Sequence[str]] = None,
) -> List[MigrationResult]:
    """Dizini tara, her dosya için ayrı MigrationResult üret."""
    glob_patterns: Sequence[str] = patterns or _default_patterns(framework)
    results: List[MigrationResult] = []
    for pat in glob_patterns:
        for fp in directory.rglob(pat):
            if not fp.is_file():
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning("dosya okunamadı %s: %s", fp, exc)
                continue
            try:
                rel = str(fp.relative_to(directory))
            except ValueError:
                rel = str(fp)
            results.append(migrate_source(framework, text, source_file=rel))
    return results


def _default_patterns(framework: SourceFramework) -> Sequence[str]:
    if framework == "selenium-java":
        return ("*.java",)
    if framework == "selenium-py":
        return ("*.py",)
    if framework == "katalon":
        return ("*.groovy",)
    return ("*",)
