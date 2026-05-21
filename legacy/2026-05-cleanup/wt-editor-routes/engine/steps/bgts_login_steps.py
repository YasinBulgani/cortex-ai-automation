"""
steps/bgts_login_steps.py — Kimlik Doğrulama BDD adım tanımları.

login.feature dosyasındaki tüm adımlar için POM tabanlı step implementation.
common_steps'teki genel adımları re-export eder, ek olarak LoginPage POM'u ile
yüksek seviyeli kimlik doğrulama adımları sağlar.
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
)
from pages.login_page import LoginPage
from locators.locator_manager import LocatorManager
from test_data.fixtures import get_admin_user, get_user_by_role


# ── POM Fixture-free Yardımcılar ─────────────────────────────────────────────

def _build_login_page(page, base_url: str = "") -> LoginPage:
    return LoginPage(page, locator_manager=LocatorManager(), base_url=base_url)


# ── EK GIVEN ADIMLARI ───────────────────────────────────────────────────────

@given("kullanıcı giriş sayfasında bekliyor")
@allure.step("Giriş sayfasına git ve yüklenmesini bekle")
def user_on_login_page_waiting(page):
    lp = _build_login_page(page)
    lp.navigate_to_login()
    lp.assert_page_loaded()


@given(parsers.parse('kullanıcı "{role}" rolüyle giriş yapmıştır'))
@allure.step("Rolüne göre giriş yap: {role}")
def user_logged_in_with_role(page, role: str):
    user = get_user_by_role(role)
    lp = _build_login_page(page)
    lp.login(user["email"], user["password"])
    with allure.step(f"Giriş doğrula — rol: {role}"):
        assert lp.is_logged_in(), f"'{role}' rolü ile giriş başarısız"


@given("kullanıcı admin olarak giriş yapmıştır")
@allure.step("Admin olarak giriş yap")
def user_logged_in_as_admin(page):
    admin = get_admin_user()
    lp = _build_login_page(page)
    lp.login(admin["email"], admin["password"])
    with allure.step("Admin giriş doğrulama"):
        assert lp.is_logged_in(), "Admin girişi başarısız"


# ── EK WHEN ADIMLARI ────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{email}" e-postası ve "{password}" parolası ile giriş yapar'))
@allure.step("E-posta ve parola ile giriş: {email}")
def login_with_credentials(page, email: str, password: str):
    lp = _build_login_page(page)
    lp.login(email, password)


@when("kullanıcı oturumu kapatır")
@allure.step("Oturumu kapat")
def user_logs_out(page):
    lp = _build_login_page(page)
    lp.logout()


@when("kullanıcı giriş formunu boş bırakıp gönderir")
@allure.step("Boş form gönder")
def submit_empty_login_form(page):
    lp = _build_login_page(page)
    lp.navigate_to_login()
    lp.submit_button.click()


# ── EK THEN ADIMLARI ────────────────────────────────────────────────────────

@then("kullanıcı başarıyla giriş yapmış olmalıdır")
@allure.step("Başarılı giriş doğrula")
def assert_login_successful(page):
    lp = _build_login_page(page)
    with allure.step("Giriş kontrolü — URL /projects içermeli"):
        assert lp.is_logged_in(), (
            "Giriş başarısız — URL /projects'e yönlenmedi"
        )
    allure.attach(
        page.screenshot(),
        name="Giriş Sonrası",
        attachment_type=allure.attachment_type.PNG,
    )


@then("hata mesajı görünür olmalıdır")
@allure.step("Hata mesajı görünürlük kontrolü")
def assert_error_message_visible(page):
    lp = _build_login_page(page)
    lp.assert_error_visible()
    msg = lp.get_error_message()
    with allure.step(f"Hata mesajı: {msg}"):
        assert msg, "Hata mesajı boş — element görünür ama içerik yok"


@then("kullanıcı giriş sayfasına yönlendirilmelidir")
@allure.step("Login sayfasına yönlendirme kontrolü")
def assert_redirected_to_login(page):
    with allure.step("URL /login içermeli"):
        assert "/login" in page.url, (
            f"Giriş sayfasına yönlendirilmedi. Mevcut URL: {page.url}"
        )


@then("kullanıcı projeler sayfasına yönlendirilmelidir")
@allure.step("Projeler sayfasına yönlendirme kontrolü")
def assert_redirected_to_projects(page):
    with allure.step("URL /projects içermeli"):
        assert "/projects" in page.url, (
            f"Projeler sayfasına yönlendirilmedi. Mevcut URL: {page.url}"
        )


@then("giriş formu görünür olmalıdır")
@allure.step("Giriş formu görünürlük kontrolü")
def assert_login_form_visible(page):
    lp = _build_login_page(page)
    lp.assert_page_loaded()
