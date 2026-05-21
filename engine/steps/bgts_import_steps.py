"""
steps/bgts_import_steps.py — Dosya İçe Aktarma BDD adım tanımları.

import.feature dosyasındaki tüm adımlar için POM tabanlı step implementation.
common_steps'teki genel adımları re-export eder, ek olarak ImportPage POM'u ile
yüksek seviyeli içe aktarma adımları sağlar.
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
from steps.bgts_login_steps import user_logged_in_as_admin  # noqa: F401 — Background step re-export
from pages.import_page import ImportPage
from locators.locator_manager import LocatorManager
from test_data.fixtures import get_admin_user, get_api_payload


# ── POM Fixture-free Yardımcılar ─────────────────────────────────────────────

def _build_import_page(page, project_id: str = "test-project", base_url: str = "") -> ImportPage:
    return ImportPage(page, project_id=project_id, base_url=base_url)


# ── EK GIVEN ADIMLARI ───────────────────────────────────────────────────────

@given("kullanıcı içe aktarma sayfasında bekliyor")
@allure.step("İçe aktarma sayfasına git ve yüklenmesini bekle")
def user_on_import_page_waiting(page):
    ip = _build_import_page(page)
    ip.goto()
    ip.assert_page_loaded()


@given(parsers.parse('kullanıcı "{project_id}" projesi için içe aktarma sayfasındadır'))
@allure.step("Proje import sayfasına git: {project_id}")
def user_on_project_import_page(page, project_id: str):
    ip = _build_import_page(page, project_id=project_id)
    ip.goto()
    ip.assert_page_loaded()


# ── EK WHEN ADIMLARI ────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{filename}" dosyasını içe aktarma alanına yükler'))
@allure.step("Dosya yükle: {filename}")
def upload_import_file(page, filename: str):
    ip = _build_import_page(page)
    ip.fill_filename(filename)
    ip.upload()


@when("kullanıcı içe aktarma formunu gönderir")
@allure.step("İçe aktarma formunu gönder")
def submit_import_form(page):
    ip = _build_import_page(page)
    ip.upload()


@when(parsers.parse('kullanıcı "{filename}" dosya adını girer'))
@allure.step("Dosya adı gir: {filename}")
def fill_import_filename(page, filename: str):
    ip = _build_import_page(page)
    ip.fill_filename(filename)


# ── EK THEN ADIMLARI ────────────────────────────────────────────────────────

@then("içe aktarma sayfası yüklenmiş olmalıdır")
@allure.step("İçe aktarma sayfası yükleme kontrolü")
def assert_import_page_loaded(page):
    ip = _build_import_page(page)
    ip.assert_page_loaded()
    allure.attach(
        page.screenshot(),
        name="İçe Aktarma Sayfası",
        attachment_type=allure.attachment_type.PNG,
    )


@then("içe aktarma sonucu görünür olmalıdır")
@allure.step("İçe aktarma sonuç kontrolü")
def assert_import_result_visible(page):
    ip = _build_import_page(page)
    ip.assert_result_visible()
    allure.attach(
        page.screenshot(),
        name="İçe Aktarma Sonucu",
        attachment_type=allure.attachment_type.PNG,
    )


@then("içe aktarma formu görünür olmalıdır")
@allure.step("İçe aktarma formu görünürlük kontrolü")
def assert_import_form_visible(page):
    ip = _build_import_page(page)
    ip.assert_page_loaded()
