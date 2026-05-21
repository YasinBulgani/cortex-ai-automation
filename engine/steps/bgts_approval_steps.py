"""
steps/bgts_approval_steps.py — Onay İş Akışı BDD adım tanımları.

approvals.feature dosyasındaki tüm adımlar için POM tabanlı step implementation.
ApprovalsPage POM'u kullanır.
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
from pages.approvals_page import ApprovalsPage
from locators.locator_manager import LocatorManager


def _approvals_page(page, project_id: str = "test-project") -> ApprovalsPage:
    return ApprovalsPage(page, project_id=project_id, locator_manager=LocatorManager())


# ── GIVEN ────────────────────────────────────────────────────────────────────

@given("kullanıcı onay kuyruğunu görüntülüyor")
@allure.step("Onay kuyruğuna git")
def user_viewing_approval_queue(page):
    ap = _approvals_page(page)
    ap.goto()
    ap.assert_page_loaded()


@given(parsers.parse('kullanıcı "{project_id}" projesinin onay kuyruğunda'))
@allure.step("Onay kuyruğuna git: {project_id}")
def user_on_project_approval_queue(page, project_id: str):
    ap = _approvals_page(page, project_id=project_id)
    ap.goto()


# ── WHEN — Navigasyon ────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{approval_id}" onay öğesini açar'))
@allure.step("Onay öğesini aç: {approval_id}")
def open_approval_item(page, approval_id: str):
    ap = _approvals_page(page)
    ap.view_split(approval_id)


@when("kullanıcı ilk onay öğesini açar")
@allure.step("İlk onay öğesini aç")
def open_first_approval_item(page):
    page.locator("[data-testid='approval-item']").first.click()


# ── WHEN — Karar ─────────────────────────────────────────────────────────────

@when(parsers.parse('kullanıcı "{approval_id}" onayını onaylar'))
@allure.step("Onay ver: {approval_id}")
def approve_item(page, approval_id: str):
    ap = _approvals_page(page)
    ap.approve(approval_id)


@when(parsers.parse('kullanıcı "{approval_id}" onayını reddeder'))
@allure.step("Reddet: {approval_id}")
def reject_item(page, approval_id: str):
    ap = _approvals_page(page)
    ap.reject(approval_id)


@when(parsers.parse('kullanıcı "{approval_id}" onayını "{reason}" sebebiyle reddeder'))
@allure.step("Sebepli red: {approval_id} — {reason}")
def reject_item_with_reason(page, approval_id: str, reason: str):
    ap = _approvals_page(page)
    ap.reject(approval_id, reason=reason)


@when("kullanıcı onay taslağını onaylar")
@allure.step("Görüntülenen taslağı onayla")
def approve_current_draft(page):
    page.get_by_text("Onayla", exact=False).first.click()


@when("kullanıcı onay taslağını reddeder")
@allure.step("Görüntülenen taslağı reddet")
def reject_current_draft(page):
    page.get_by_text("Reddet", exact=False).first.click()


@when(parsers.parse('kullanıcı taslağı "{content}" olarak düzenleyip onaylar'))
@allure.step("Düzenle ve onayla: {content}")
def edit_and_approve_draft(page, content: str):
    page.get_by_text("Düzenle", exact=False).first.click()
    page.locator("[data-testid='draft-editor']").fill(content)
    page.get_by_text("Kaydet ve Onayla", exact=False).first.click()


# ── THEN ─────────────────────────────────────────────────────────────────────

@then("onay listesi görünür olmalıdır")
@allure.step("Onay listesi görünürlük kontrolü")
def assert_approval_list_visible(page):
    assert page.locator("[data-testid='approval-list']").is_visible(), (
        "Onay listesi görünür değil"
    )
    allure.attach(
        page.screenshot(),
        name="Onay Listesi",
        attachment_type=allure.attachment_type.PNG,
    )


@then("bekleyen onay sayısı görünür olmalıdır")
@allure.step("Bekleyen onay sayacı kontrolü")
def assert_pending_count_visible(page):
    assert page.locator("[data-testid='pending-count']").is_visible(), (
        "Bekleyen onay sayısı görünür değil"
    )


@then("split view paneli görünür olmalıdır")
@allure.step("Split view kontrolü")
def assert_split_view_visible(page):
    assert page.locator("[data-testid='split-view']").is_visible(), (
        "Split view paneli görünür değil"
    )


@then("kaynak panel görünür olmalıdır")
@allure.step("Kaynak panel kontrolü")
def assert_source_panel_visible(page):
    assert page.locator("[data-testid='source-panel']").is_visible(), (
        "Kaynak doküman paneli görünür değil"
    )


@then("taslak panel görünür olmalıdır")
@allure.step("Taslak panel kontrolü")
def assert_draft_panel_visible(page):
    assert page.locator("[data-testid='draft-panel']").is_visible(), (
        "AI taslak paneli görünür değil"
    )


@then("başarı mesajı veya onay listesi görünür olmalıdır")
@allure.step("İşlem sonucu kontrolü")
def assert_success_or_list_visible(page):
    success = page.locator("[data-testid='success-message']")
    approval_list = page.locator("[data-testid='approval-list']")
    assert success.is_visible() or approval_list.is_visible(), (
        "Ne başarı mesajı ne de onay listesi görünür değil"
    )
    allure.attach(
        page.screenshot(),
        name="İşlem Sonucu",
        attachment_type=allure.attachment_type.PNG,
    )


@then(parsers.parse('bekleyen onay sayısı en az {count:d} olmalıdır'))
@allure.step("Bekleyen onay sayısı kontrolü: en az {count}")
def assert_pending_approval_count(page, count: int):
    ap = _approvals_page(page)
    actual = ap.get_approval_count()
    with allure.step(f"Beklenen: >={count}, Bulunan: {actual}"):
        assert actual >= count, (
            f"Bekleyen onay sayısı yetersiz. Beklenen: >={count}, Bulunan: {actual}"
        )
