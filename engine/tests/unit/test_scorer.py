"""
engine/evals/scorer.py birim testleri.

Her puanlama kriteri ayrı ayrı test edilir.
Mutation testing (mutmut) hedefi: bu testler bir mutasyonu ≥ %60 oranında yakalamalıdır.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from engine.evals.scorer import (
    ScoreResult,
    score_gherkin,
    score_playwright,
    score_python_test,
)


# ── ScoreResult ────────────────────────────────────────────────────────────────

class TestScoreResult:
    def test_grade_A_at_90(self):
        r = ScoreResult.from_score(90, [], [], {})
        assert r.grade == "A"
        assert r.passed is True

    def test_grade_A_at_100(self):
        assert ScoreResult.from_score(100, [], [], {}).grade == "A"

    def test_grade_B_at_75(self):
        r = ScoreResult.from_score(75, [], [], {})
        assert r.grade == "B"
        assert r.passed is True

    def test_grade_C_at_60(self):
        r = ScoreResult.from_score(60, [], [], {})
        assert r.grade == "C"
        assert r.passed is True

    def test_grade_D_at_59(self):
        r = ScoreResult.from_score(59, [], [], {})
        assert r.grade == "D"
        assert r.passed is False

    def test_grade_F_at_39(self):
        r = ScoreResult.from_score(39, [], [], {})
        assert r.grade == "F"
        assert r.passed is False

    def test_score_clamped_to_100(self):
        r = ScoreResult.from_score(150, [], [], {})
        assert r.score == 100

    def test_score_clamped_to_0(self):
        r = ScoreResult.from_score(-10, [], [], {})
        assert r.score == 0

    def test_to_dict_keys(self):
        r = ScoreResult.from_score(75, ["issue"], ["hint"], {"k": 1})
        d = r.to_dict()
        assert set(d.keys()) == {"score", "grade", "passed", "issues", "suggestions", "details"}
        assert d["score"] == 75
        assert d["issues"] == ["issue"]
        assert d["suggestions"] == ["hint"]


# ── score_gherkin ──────────────────────────────────────────────────────────────

FULL_BDD = """\
@smoke @regression
Feature: Kullanıcı Girişi

  Background:
    Given sistem ayakta

  Scenario: Başarılı giriş
    Given kullanıcı login sayfasındadır
    When kullanıcı geçerli bilgileri girer
    Then kullanıcı yönlendirilmeli

  Scenario: Hatalı şifre ile giriş başarısız olmalı — negatif akış
    Given kullanıcı login sayfasındadır
    When kullanıcı hatalı şifre girer
    Then hata mesajı görünmeli

  Scenario Outline: Geçersiz e-posta formatları reddedilmeli
    Given kullanıcı formdadır
    When kullanıcı "<geçersiz_email>" girer
    Then doğrulama hatası görünmeli

    Examples:
      | geçersiz_email |
      | düz-metin      |
      | @domain.com    |
"""

class TestScoreGherkin:
    def test_full_bdd_scores_above_85(self):
        r = score_gherkin(FULL_BDD)
        assert r.score >= 85, f"Score {r.score} < 85. Issues: {r.issues}"

    def test_empty_text_scores_very_low(self):
        r = score_gherkin("")
        # Boş metin geçmemeli ve düşük puanlamalı (step/senaryo yok)
        assert not r.passed
        assert r.score < 30

    def test_feature_line_adds_10_points(self):
        with_feature = score_gherkin("Feature: Test\nScenario: A\nGiven b\nWhen c\nThen d")
        without_feature = score_gherkin("Scenario: A\nGiven b\nWhen c\nThen d")
        assert with_feature.score > without_feature.score

    def test_missing_feature_line_adds_issue(self):
        r = score_gherkin("Scenario: A\nGiven b\nThen c")
        assert any("Feature" in i for i in r.issues)

    def test_scenario_without_then_is_penalized(self):
        missing_then = "Feature: X\nScenario: A\nGiven b\nWhen c\n"
        with_then = "Feature: X\nScenario: A\nGiven b\nWhen c\nThen d\n"
        assert score_gherkin(with_then).score > score_gherkin(missing_then).score

    def test_missing_then_adds_issue(self):
        r = score_gherkin("Feature: X\nScenario: A\nGiven b\nWhen c\n")
        assert any("Then" in i for i in r.issues)

    def test_negative_scenario_adds_15_points(self):
        with_neg = score_gherkin(FULL_BDD)
        without_neg = score_gherkin("Feature: X\n@smoke\nScenario: A\nGiven b\nWhen c\nThen d\n")
        # FULL_BDD has negative keywords → higher score
        assert with_neg.score >= without_neg.score

    def test_scenario_outline_adds_10_points(self):
        with_outline = score_gherkin(FULL_BDD)
        without_outline = score_gherkin(
            "Feature: X\nScenario: A\nGiven b\nWhen c\nThen d\nnegatif hata"
        )
        # FULL_BDD has outline → higher
        assert with_outline.score >= without_outline.score

    def test_tags_add_10_points(self):
        with_tags = score_gherkin("@smoke\nFeature: X\nScenario: A\nGiven b\nWhen c\nThen d")
        without_tags = score_gherkin("Feature: X\nScenario: A\nGiven b\nWhen c\nThen d")
        assert with_tags.score > without_tags.score

    def test_tags_absence_adds_suggestion(self):
        r = score_gherkin("Feature: X\nScenario: A\nGiven b\nWhen c\nThen d")
        assert any("etiket" in s.lower() or "tag" in s.lower() or "@" in s for s in r.suggestions)

    def test_over_10_scenarios_adds_issue(self):
        many = "Feature: X\n" + "\n".join(
            [f"Scenario: {i}\nGiven b\nWhen c\nThen d" for i in range(12)]
        )
        r = score_gherkin(many)
        assert any("10" in i for i in r.issues)

    def test_turkish_characters_score_bonus(self):
        turkish = "Feature: Giriş Testi\nScenario: Başarılı\nGiven kullanıcı\nThen görünmeli"
        ascii_only = "Feature: Login Test\nScenario: Success\nGiven user\nThen visible"
        assert score_gherkin(turkish).score >= score_gherkin(ascii_only).score

    def test_details_contains_scenario_count(self):
        r = score_gherkin(FULL_BDD)
        assert "scenario_count" in r.details
        assert r.details["scenario_count"] >= 2


# ── score_playwright ───────────────────────────────────────────────────────────

GOOD_PLAYWRIGHT = """\
import { test, expect } from '@playwright/test';

test.describe('Login Akışı', () => {
  test('başarılı giriş', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('test@example.com');
    await page.getByLabel('Şifre').fill('Secret123!');
    await page.getByRole('button', { name: 'Giriş' }).click();
    await expect(page.getByTestId('dashboard')).toBeVisible();
    expect(page.url()).toContain('/projects');
  });
});
"""

class TestScorePlaywright:
    def test_good_playwright_scores_above_70(self):
        r = score_playwright(GOOD_PLAYWRIGHT)
        assert r.score >= 70, f"Score {r.score} < 70. Issues: {r.issues}"

    def test_empty_code_scores_very_low(self):
        r = score_playwright("")
        assert not r.passed
        assert r.score < 30

    def test_missing_test_block_adds_issue(self):
        r = score_playwright("const x = 1;")
        assert any("test()" in i or "test.describe" in i for i in r.issues)

    def test_missing_expect_adds_issue(self):
        code = "test('x', async ({ page }) => { await page.goto('/'); });"
        r = score_playwright(code)
        assert any("expect" in i for i in r.issues)

    def test_expect_count_in_details(self):
        r = score_playwright(GOOD_PLAYWRIGHT)
        assert r.details.get("expect_count", 0) >= 1

    def test_no_semantic_locators_adds_issue(self):
        code = "test('x', async ({ page }) => { expect(page.locator('#id')).toBeVisible(); });"
        r = score_playwright(code)
        assert any("locator" in i.lower() or "semantic" in i.lower() for i in r.issues)

    def test_hardcoded_url_adds_issue(self):
        code = GOOD_PLAYWRIGHT.replace("'/login'", "'https://production.example.com/login'")
        r = score_playwright(code)
        assert any("URL" in i or "url" in i.lower() for i in r.issues)

    def test_no_hardcoded_url_is_clean(self):
        r = score_playwright(GOOD_PLAYWRIGHT)
        assert not any("hardcoded" in i.lower() or "URL" in i for i in r.issues)

    def test_testid_usage_is_rewarded(self):
        with_testid = score_playwright(GOOD_PLAYWRIGHT)
        without_testid = score_playwright(GOOD_PLAYWRIGHT.replace("getByTestId('dashboard')", "locator('div')"))
        assert with_testid.score >= without_testid.score

    def test_test_describe_adds_10_points(self):
        with_describe = score_playwright(GOOD_PLAYWRIGHT)
        without_describe = score_playwright(
            "test('x', async ({ page }) => { await page.goto('/'); expect(page.getByRole('main')).toBeVisible(); });"
        )
        assert with_describe.score > without_describe.score


# ── score_python_test ─────────────────────────────────────────────────────────

GOOD_PYTHON = """\
import pytest

@pytest.mark.smoke
def test_proje_olusturma(client, auth_headers):
    response = client.post("/api/v1/projects/", json={"name": "Test"}, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test"

def test_proje_listesi(client, auth_headers):
    response = client.get("/api/v1/projects/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
"""

class TestScorePythonTest:
    def test_good_python_scores_above_70(self):
        r = score_python_test(GOOD_PYTHON)
        assert r.score >= 70, f"Score {r.score} < 70. Issues: {r.issues}"

    def test_empty_code_scores_low(self):
        r = score_python_test("")
        # Boş kod geçmemeli
        assert not r.passed

    def test_missing_assert_adds_issue(self):
        code = "def test_something():\n    x = 1 + 1\n"
        r = score_python_test(code)
        assert any("assert" in i.lower() for i in r.issues)

    def test_syntax_error_penalized(self):
        bad_code = "def test_foo(:\n    pass\n"
        r = score_python_test(bad_code)
        assert r.score < score_python_test(GOOD_PYTHON).score

    def test_function_naming_convention(self):
        good = score_python_test("def test_something():\n    assert True\n")
        bad = score_python_test("def somethingTest():\n    assert True\n")
        assert good.score >= bad.score

    def test_pytest_marker_rewarded(self):
        with_marker = score_python_test(GOOD_PYTHON)
        without_marker = score_python_test(GOOD_PYTHON.replace("@pytest.mark.smoke\n", ""))
        assert with_marker.score >= without_marker.score

    def test_result_is_score_result_instance(self):
        r = score_python_test(GOOD_PYTHON)
        assert isinstance(r, ScoreResult)
        assert 0 <= r.score <= 100
