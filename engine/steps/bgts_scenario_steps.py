"""
steps/bgts_scenario_steps.py — Senaryo Yönetimi BDD adım tanımları.

scenarios.feature dosyasındaki tüm adımlar için POM tabanlı step implementation.
ScenariosListPage ve ScenarioFormPage POM'ları kullanır.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
from pytest_bdd import given, when, then, parsers

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from steps.common_steps import (  # noqa: F401
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
from pages.scenarios_page import ScenariosListPage, ScenarioFormPage
from locators.locator_manager import LocatorManager
from test_data.fixtures import get_test_scenarios, get_scenarios_by_project


def _scenarios_list(page, project_id: str = "test-project") -> ScenariosListPage:
    return ScenariosListPage(page, project_id=project_id, locator_manager=LocatorManager())


def _scenario_form(page, project_id: str = "test-project") -> ScenarioFormPage:
    return ScenarioFormPage(page, project_id=project_id, locator_manager=LocatorManager())


# ── GIVEN ────────────────────────────────────────────────────────────────────

@given("kullanıcı senaryo listesini görüntülüyor")
@allure.step("Senaryo listesine git")
def user_viewing_scenario_list(page):
    sl = _scenarios_list(page)
    sl.goto()
    sl.assert_page_loaded()


@given("kullanıcı yeni senaryo formunda")
@allure.step("Yeni senaryo formuna git")
def user_on_new_scenario_form(page):
    sf = _scenario_form(page)
    sf.goto_new()


# ── WHEN — Arama ve Filtreleme ───────────────────────────────────────────────

@when(parsers.parse('kullanıcı senaryoları "{query}" ile arar'))
@allure.step("Senaryo ara: {query}")
def search_scenarios(page, query: str):
    sl = _scenarios_list(page)
    sl.search(query)
    page.wait_for_timeout(500)


@when(parsers.parse('kullanıcı senaryoları "{priority}" önceliğine göre filtreler'))
@allure.step("Öncelik filtresi: {priority}")
def filter_by_priority(page, priority: str):
    sl = _scenarios_list(page)
    sl.filter_by_priority(priority)


@when(parsers.parse('kullanıcı senaryoları "{scenario_type}" türüne göre filtreler'))
@allure.step("Tür filtresi: {scenario_type}")
def filter_by_type(page, scenario_type: str):
    sl = _scenarios_list(page)
    sl.filter_by_type(scenario_type)


# ── WHEN — CRUD ──────────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{title}" başlıklı senaryo oluşturur'))
@allure.step("Senaryo oluştur: {title}")
def create_scenario(page, title: str):
    sf = _scenario_form(page)
    sf.create_scenario(title)


@when(parsers.parse('kullanıcı "{scenario_id}" senaryosunu düzenler'))
@allure.step("Senaryoyu düzenle: {scenario_id}")
def edit_scenario_step(page, scenario_id: str):
    sl = _scenarios_list(page)
    sl.click_scenario(scenario_id)
    page.get_by_text("Düzenle", exact=False).first.click()


@when(parsers.parse('kullanıcı "{scenario_id}" senaryosunu siler'))
@allure.step("Senaryoyu sil: {scenario_id}")
def delete_scenario_step(page, scenario_id: str):
    sl = _scenarios_list(page)
    sl.delete_scenario(scenario_id)


# ── WHEN — Toplu İşlemler ───────────────────────────────────────────────────

@when("kullanıcı tüm senaryoları seçer")
@allure.step("Tüm senaryoları seç")
def select_all_scenarios(page):
    page.locator("[data-testid='select-all-checkbox']").click()


@when("kullanıcı seçili senaryoları toplu siler")
@allure.step("Toplu silme işlemi")
def bulk_delete_scenarios(page):
    page.get_by_text("Toplu Sil", exact=False).first.click()
    page.get_by_text("Onayla", exact=False).first.click()


# ── WHEN — BDD Üretimi ──────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{text}" metni ile BDD senaryosu üretir'))
@allure.step("BDD senaryo üret: {text}")
def generate_bdd_scenario(page, text: str):
    page.get_by_text("BDD Üret", exact=False).first.click()
    page.locator("[data-testid='analysis-text']").fill(text)
    page.get_by_text("Üret", exact=False).first.click()
    page.wait_for_timeout(5000)


@when("kullanıcı üretilen senaryoları kaydeder")
@allure.step("Üretilen senaryoları kaydet")
def save_generated_scenarios(page):
    page.get_by_text("Tümünü Kaydet", exact=False).first.click()


# ── WHEN — Detay & Versiyon ─────────────────────────────────────────────────

@when("kullanıcı senaryo detayını görüntüler")
@allure.step("Senaryo detayını aç")
def view_scenario_detail(page):
    page.locator("[data-testid='scenario-row']").first.click()


@when("kullanıcı versiyon geçmişini açar")
@allure.step("Versiyon geçmişi aç")
def view_version_history(page):
    page.get_by_text("Versiyon Geçmişi", exact=False).first.click()


# ── THEN ─────────────────────────────────────────────────────────────────────

@then("senaryo tablosu görünür olmalıdır")
@allure.step("Senaryo tablosu görünürlük kontrolü")
def assert_scenario_table_visible(page):
    assert page.locator("[data-testid='scenario-table']").is_visible(), (
        "Senaryo tablosu görünür değil"
    )
    allure.attach(
        page.screenshot(),
        name="Senaryo Tablosu",
        attachment_type=allure.attachment_type.PNG,
    )


@then(parsers.parse('senaryo sayısı en az {count:d} olmalıdır'))
@allure.step("Senaryo sayısı kontrolü: en az {count}")
def assert_scenario_count(page, count: int):
    sl = _scenarios_list(page)
    actual = sl.get_scenario_count()
    with allure.step(f"Beklenen: >={count}, Bulunan: {actual}"):
        assert actual >= count, (
            f"Senaryo sayısı yetersiz. Beklenen: >={count}, Bulunan: {actual}"
        )


@then("toplu işlem butonları görünür olmalıdır")
@allure.step("Toplu işlem butonları kontrolü")
def assert_bulk_actions_visible(page):
    assert page.locator("[data-testid='bulk-actions']").is_visible(), (
        "Toplu işlem butonları görünür değil"
    )


@then("doğrulama hatası görünür olmalıdır")
@allure.step("Doğrulama hatası kontrolü")
def assert_validation_error_visible(page):
    assert page.locator("[data-testid='validation-error']").is_visible(), (
        "Doğrulama hatası mesajı görünür değil"
    )


@then("üretilen senaryolar görünür olmalıdır")
@allure.step("Üretilen BDD senaryoları kontrolü")
def assert_generated_scenarios_visible(page):
    assert page.locator("[data-testid='generated-scenarios']").is_visible(), (
        "Üretilen BDD senaryoları görünür değil"
    )


@then("senaryo detay bilgileri görünür olmalıdır")
@allure.step("Senaryo detay kontrolü")
def assert_scenario_detail_visible(page):
    assert page.locator("[data-testid='scenario-detail']").is_visible(), (
        "Senaryo detay paneli görünür değil"
    )
    assert page.locator("[data-testid='scenario-steps']").is_visible(), (
        "Senaryo adımları görünür değil"
    )


@then("versiyon listesi görünür olmalıdır")
@allure.step("Versiyon listesi kontrolü")
def assert_version_list_visible(page):
    assert page.locator("[data-testid='version-list']").is_visible(), (
        "Versiyon listesi görünür değil"
    )


@then("gereksinim seçici görünür olmalıdır")
@allure.step("Gereksinim seçici kontrolü")
def assert_requirement_selector_visible(page):
    assert page.locator("[data-testid='requirement-selector']").is_visible(), (
        "Gereksinim seçici görünür değil"
    )
