"""
steps/bgts_project_steps.py — Proje Yönetimi BDD adım tanımları.

projects.feature dosyasındaki tüm adımlar için POM tabanlı step implementation.
common_steps'teki genel adımları re-export eder, ek olarak ProjectsPage ve
DashboardPage POM'ları ile yüksek seviyeli proje işlem adımları sağlar.
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
from pages.projects_page import ProjectsPage
from pages.dashboard_page import DashboardPage
from pages.common_nav import CommonNav
from locators.locator_manager import LocatorManager
from test_data.fixtures import get_test_projects


def _projects_page(page, base_url: str = "") -> ProjectsPage:
    return ProjectsPage(page, locator_manager=LocatorManager(), base_url=base_url)


def _dashboard_page(page, project_id: str = "test-project", base_url: str = "") -> DashboardPage:
    return DashboardPage(page, project_id=project_id, locator_manager=LocatorManager(), base_url=base_url)


# ── GIVEN ────────────────────────────────────────────────────────────────────

@given("kullanıcı proje listesini görüntülüyor")
@allure.step("Proje listesi sayfasına git")
def user_viewing_project_list(page):
    pp = _projects_page(page)
    pp.goto()
    pp.assert_page_loaded()


@given(parsers.parse('kullanıcı "{project_name}" projesinin dashboard\'ında'))
@allure.step("Proje dashboard'ına git: {project_name}")
def user_on_project_dashboard(page, project_name: str):
    pp = _projects_page(page)
    pp.goto()
    pp.open_project(project_name)


# ── WHEN ─────────────────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{name}" adlı yeni proje oluşturur'))
@allure.step("Yeni proje oluştur: {name}")
def create_new_project(page, name: str):
    pp = _projects_page(page)
    page.get_by_text("Yeni Proje", exact=False).first.click()
    pp.create_project(name, description=f"{name} açıklaması")


@when(parsers.parse('kullanıcı "{name}" adlı projeye tıklar'))
@allure.step("Projeye tıkla: {name}")
def click_project(page, name: str):
    pp = _projects_page(page)
    pp.open_project(name)


@when(parsers.parse('kullanıcı "{name}" projesini siler'))
@allure.step("Projeyi sil: {name}")
def delete_project(page, name: str):
    pp = _projects_page(page)
    pp.delete_project(name)


@when(parsers.parse('kullanıcı projeleri "{query}" ile arar'))
@allure.step("Proje ara: {query}")
def search_projects(page, query: str):
    pp = _projects_page(page)
    pp.search_projects(query)


@when(parsers.parse('kullanıcı sidebar\'dan "{section}" bölümüne gider'))
@allure.step("Sidebar navigasyon: {section}")
def navigate_via_sidebar(page, section: str):
    nav = CommonNav(page, locator_manager=LocatorManager())
    section_map = {
        "Projeler": nav.go_to_projects,
        "Senaryolar": nav.go_to_scenarios,
        "Onaylar": nav.go_to_approvals,
        "İçe Aktar": nav.go_to_import,
    }
    action = section_map.get(section)
    if action:
        action()
    else:
        page.get_by_text(section, exact=False).first.click()


# ── THEN ─────────────────────────────────────────────────────────────────────

@then("proje listesi görünür olmalıdır")
@allure.step("Proje listesi görünürlük kontrolü")
def assert_project_list_visible(page):
    pp = _projects_page(page)
    pp.assert_page_loaded()
    allure.attach(
        page.screenshot(),
        name="Proje Listesi",
        attachment_type=allure.attachment_type.PNG,
    )


@then(parsers.parse('"{name}" projesi listede görünür olmalıdır'))
@allure.step("Proje görünürlük kontrolü: {name}")
def assert_project_in_list(page, name: str):
    pp = _projects_page(page)
    pp.assert_project_visible(name)


@then("dashboard istatistikleri görünür olmalıdır")
@allure.step("Dashboard istatistikleri görünürlük kontrolü")
def assert_dashboard_stats_visible(page):
    dp = _dashboard_page(page)
    stats = dp.get_stat_cards()
    with allure.step(f"Bulunan istatistik kartı: {len(stats)}"):
        assert len(stats) > 0, "Dashboard'da istatistik kartı bulunamadı"


@then("hızlı aksiyon butonları görünür olmalıdır")
@allure.step("Hızlı aksiyon butonları kontrolü")
def assert_quick_actions_visible(page):
    dp = _dashboard_page(page)
    actions = dp.get_quick_actions()
    with allure.step(f"Bulunan buton sayısı: {len(actions)}"):
        assert len(actions) > 0, "Hızlı aksiyon butonları bulunamadı"


@then(parsers.parse('proje sayısı en az {count:d} olmalıdır'))
@allure.step("Proje sayısı kontrolü: en az {count}")
def assert_project_count(page, count: int):
    pp = _projects_page(page)
    actual = pp.get_project_count()
    with allure.step(f"Beklenen: >={count}, Bulunan: {actual}"):
        assert actual >= count, (
            f"Proje sayısı yetersiz. Beklenen: >={count}, Bulunan: {actual}"
        )
