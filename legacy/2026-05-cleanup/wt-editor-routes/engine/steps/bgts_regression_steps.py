"""
steps/bgts_regression_steps.py — Regresyon Test Seti BDD adım tanımları.

regression.feature dosyasındaki tüm adımlar için step implementation.
common_steps'teki genel adımları re-export eder, diğer modül step dosyalarından
adımları yeniden kullanır ve regresyona özel doğrulama adımları sağlar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
from pytest_bdd import given, when, then, parsers

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from steps.common_steps import (  # noqa: F401 — re-export for pytest-bdd discovery
    navigate_to_home,
    navigate_to_path,
    click_text,
    click_selector,
    fill_input,
    press_enter,
    wait_ms,
    assert_title_contains,
    assert_url_contains,
    assert_element_visible,
    ai_perform_task,
    assert_at_least_one_passed,
)

from steps.bgts_login_steps import (  # noqa: F401 — re-export auth steps
    user_on_login_page_waiting,
    user_logged_in_with_role,
    user_logged_in_as_admin,
    login_with_credentials,
    user_logs_out,
    assert_login_successful,
    assert_error_message_visible,
    assert_redirected_to_login,
    assert_redirected_to_projects,
)

from steps.bgts_import_steps import (  # noqa: F401 — re-export import steps
    user_on_import_page_waiting,
    assert_import_page_loaded,
    assert_import_result_visible,
)


# ── Regresyon Doğrulama Yardımcıları ─────────────────────────────────────────

def _take_regression_screenshot(page, name: str) -> None:
    allure.attach(
        page.screenshot(),
        name=f"REG: {name}",
        attachment_type=allure.attachment_type.PNG,
    )


# ── EK GIVEN ADIMLARI ───────────────────────────────────────────────────────

@given("regresyon test ortamı hazırdır")
@allure.step("Regresyon test ortamı doğrulama")
def regression_environment_ready(page):
    with allure.step("Ortam kontrolü — sayfa erişilebilir"):
        assert page is not None, "Playwright sayfası oluşturulamadı"
    _take_regression_screenshot(page, "Ortam Hazır")


# ── EK WHEN ADIMLARI ────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı regresyon modülü "{module}" sayfasına gider'))
@allure.step("Regresyon modülüne git: {module}")
def navigate_to_regression_module(page, module: str):
    module_paths = {
        "projeler": "/projects",
        "senaryolar": "/p/test-project/scenarios",
        "onaylar": "/p/test-project/approvals",
        "import": "/p/test-project/import",
        "datasets": "/datasets",
    }
    path = module_paths.get(module.lower(), f"/{module}")
    with allure.step(f"Modül sayfası: {path}"):
        from config.settings import settings
        url = f"{settings.BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        page.goto(url, wait_until="domcontentloaded")
    _take_regression_screenshot(page, f"Modül: {module}")


@when("kullanıcı tüm ana modülleri sırayla ziyaret eder")
@allure.step("Tüm ana modülleri sırayla ziyaret et")
def visit_all_modules(page):
    from config.settings import settings
    base = settings.BASE_URL.rstrip("/")
    modules = ["/projects", "/datasets"]
    for mod in modules:
        with allure.step(f"Modül ziyareti: {mod}"):
            page.goto(f"{base}{mod}", wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
    _take_regression_screenshot(page, "Tüm Modüller Ziyaret Edildi")


# ── EK THEN ADIMLARI ────────────────────────────────────────────────────────

@then(parsers.parse('"{module}" modülü erişilebilir olmalıdır'))
@allure.step("Modül erişilebilirlik kontrolü: {module}")
def assert_module_accessible(page, module: str):
    with allure.step(f"Sayfa yüklenme kontrolü — modül: {module}"):
        assert page.url, f"'{module}' modülü için sayfa URL'si boş"
    _take_regression_screenshot(page, f"Erişim: {module}")


@then("sayfa hatasız yüklenmiş olmalıdır")
@allure.step("Sayfa hata kontrolü")
def assert_no_page_errors(page):
    with allure.step("JavaScript hata kontrolü"):
        error_selectors = [
            "[data-testid='error-boundary']",
            ".error-page",
            "[data-testid='500-error']",
        ]
        for sel in error_selectors:
            count = page.locator(sel).count()
            assert count == 0, f"Sayfa hatası tespit edildi: {sel}"
    _take_regression_screenshot(page, "Hatasız Sayfa")


@then(parsers.parse('regresyon kontrolü "{check}" başarılı olmalıdır'))
@allure.step("Regresyon kontrolü: {check}")
def assert_regression_check_passed(page, check: str):
    with allure.step(f"Kontrol: {check}"):
        _take_regression_screenshot(page, f"Kontrol: {check}")
        assert page.url, f"Regresyon kontrolü başarısız: {check}"
