"""ai_test_generator — self-refine + validation (Dalga 2)."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from services.ai_test_generator import AITestGenerator, GeneratedTest


@dataclass
class _FakeLLMResponse:
    content: str
    model: str = "gpt-4o"
    tokens_used: int = 100
    cached: bool = False
    cost_usd: float = 0.0
    latency_ms: int = 100


# ── fixture ──────────────────────────────────────────────────────────────
def _make_gateway(responses):
    """responses: ardışık LLMResponse.content listeleri."""
    mock = MagicMock()
    call_count = {"n": 0}

    def _complete(*args, **kwargs):
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        return _FakeLLMResponse(content=responses[idx])

    mock.complete.side_effect = _complete
    return mock


# ── helpers ─────────────────────────────────────────────────────────────
GOOD_PYTEST = """\
```python
from playwright.sync_api import Page, expect

def test_login(page: Page):
    page.get_by_test_id("login-input-username").fill("ali")
    page.get_by_test_id("login-btn-submit").click()
    expect(page.get_by_test_id("dashboard-header")).to_be_visible()
```
"""

BAD_NO_ASSERT = """\
```python
from playwright.sync_api import Page

def test_login(page: Page):
    page.get_by_test_id("login-btn-submit").click()
```
"""

BAD_SYNTAX = """\
```python
def foo(:
    pass
```
"""


class TestHappyPath:
    def test_first_attempt_succeeds(self):
        gateway = _make_gateway([GOOD_PYTEST])
        gen = AITestGenerator(gateway, model="gpt-4o-mini", max_refine=2)
        result = gen.generate_from_requirement("login akışı", framework="pytest")

        assert result.validation_passed is True
        assert result.validation_errors == []
        assert result.refine_iterations == 0
        assert gateway.complete.call_count == 1
        assert "get_by_test_id" in result.code
        assert "expect(" in result.code


class TestRefineLoop:
    def test_refines_until_valid(self):
        """İlk deneme assert'siz → refine → doğru kod dön."""
        gateway = _make_gateway([BAD_NO_ASSERT, GOOD_PYTEST])
        gen = AITestGenerator(gateway, model="gpt-4o-mini", max_refine=2)
        result = gen.generate_from_requirement("login", framework="pytest")

        assert result.validation_passed is True
        assert result.refine_iterations == 1
        assert gateway.complete.call_count == 2

    def test_gives_up_after_max_refine(self):
        """3 deneme hepsi kötü → son hatalı çıktıyı dön."""
        gateway = _make_gateway([BAD_SYNTAX, BAD_SYNTAX, BAD_SYNTAX])
        gen = AITestGenerator(gateway, model="gpt-4o-mini", max_refine=2)
        result = gen.generate_from_requirement("login", framework="pytest")

        assert result.validation_passed is False
        assert result.refine_iterations == 2
        assert gateway.complete.call_count == 3  # 1 ilk + 2 refine

    def test_max_refine_zero_no_retry(self):
        gateway = _make_gateway([BAD_NO_ASSERT])
        gen = AITestGenerator(gateway, model="gpt-4o-mini", max_refine=0)
        result = gen.generate_from_requirement("login", framework="pytest")

        # max_refine=0 → ilk deneme + refine=0; başarısız ama refine yapılmadı
        assert result.refine_iterations == 0
        assert result.validation_passed is False
        assert gateway.complete.call_count == 1


class TestValidation:
    def test_empty_code_fails(self):
        errors = AITestGenerator._validate_code("", "pytest")
        assert any("boş" in e for e in errors)

    def test_missing_testid_fails_ui(self):
        code = "def test_x():\n    assert 1 == 1"
        errors = AITestGenerator._validate_code(code, "pytest")
        assert any("data-testid" in e for e in errors)

    def test_missing_assert_fails_ui(self):
        code = "def test_x():\n    x = get_by_test_id('btn')"
        errors = AITestGenerator._validate_code(code, "pytest")
        assert any("assertion" in e.lower() for e in errors)

    def test_valid_pytest_passes(self):
        code = "def test_x(page):\n    page.get_by_test_id('btn').click()\n    assert page"
        errors = AITestGenerator._validate_code(code, "pytest")
        assert errors == []

    def test_playwright_ts_not_python_parsed(self):
        """TS framework için Python AST hatası rapor edilmemeli."""
        ts_code = "test('login', async ({ page }) => { await expect(page.getByTestId('x')).toBeVisible(); })"
        errors = AITestGenerator._validate_code(ts_code, "playwright-ts")
        assert errors == []  # assert + testid var


class TestPageObjectScanning:
    def test_extracts_python_methods(self, tmp_path):
        # Geçici POM dosyası oluştur
        pom_file = tmp_path / "LoginPage.py"
        pom_file.write_text(
            "class LoginPage:\n"
            "    def __init__(self): pass\n"
            "    def enter_credentials(self, u, p): pass\n"
            "    def submit(self): pass\n"
            "    def _private(self): pass\n"
        )
        methods = AITestGenerator._extract_methods(pom_file, framework="pytest")
        assert "enter_credentials()" in methods
        assert "submit()" in methods
        # private / dunder dahil edilmemeli
        assert "_private()" not in methods
        assert "__init__()" not in methods


class TestCodeExtraction:
    def test_single_block(self):
        raw = "Some prose\n```python\ndef x(): pass\n```\nMore prose"
        out = AITestGenerator._extract_code_blocks(raw)
        assert out == "def x(): pass"

    def test_no_fence_returns_raw(self):
        raw = "plain text no fences"
        out = AITestGenerator._extract_code_blocks(raw)
        assert out == raw

    def test_multiple_blocks_joined(self):
        raw = "```\npart1\n```\n```\npart2\n```"
        out = AITestGenerator._extract_code_blocks(raw)
        assert "part1" in out
        assert "part2" in out
