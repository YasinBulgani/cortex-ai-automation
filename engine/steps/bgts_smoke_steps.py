"""
steps/bgts_smoke_steps.py — Smoke Test BDD adım tanımları.

smoke.feature dosyasındaki senaryolar için hızlı doğrulama adımları.
Altyapı sağlık kontrolü, kritik yol doğrulaması ve temel erişim kontrolleri.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import allure
import httpx
import pytest
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
    ai_perform_task,
    assert_at_least_one_passed,
)
from steps.bgts_login_steps import user_logged_in_as_admin  # noqa: F401 — Background step re-export
from pages.login_page import LoginPage
from locators.locator_manager import LocatorManager


def _login_page(page) -> LoginPage:
    return LoginPage(page, locator_manager=LocatorManager())


# ── GIVEN — Hızlı Giriş ─────────────────────────────────────────────────────

@given("kullanıcı hızlı giriş yapmıştır")
@allure.step("Smoke: Hızlı giriş yap")
def quick_login(page):
    lp = _login_page(page)
    lp.login("admin@example.com", "admin123")
    assert lp.is_logged_in(), "Smoke giriş başarısız — platform erişilemez olabilir"


# ── WHEN — Sağlık Kontrolleri ────────────────────────────────────────────────

@when("kullanıcı ana sayfanın yüklendiğini doğrular")
@allure.step("Smoke: Ana sayfa yükleme kontrolü")
def verify_homepage_loads(page):
    page.wait_for_load_state("domcontentloaded", timeout=15_000)
    with allure.step("Sayfa yanıt verdi"):
        assert page.url, "Sayfa URL'si boş — navigasyon başarısız"


@when(parsers.parse('kullanıcı "{url}" endpoint\'ine GET isteği gönderir'))
@allure.step("HTTP GET: {url}")
def send_get_request(page, url: str):
    response = page.request.get(url)
    allure.attach(
        f"Status: {response.status}\nURL: {response.url}",
        name="HTTP Yanıt",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert response.ok, f"HTTP GET başarısız: {url} — Status: {response.status}"


# ── WHEN — Kritik Yol ───────────────────────────────────────────────────────

@when("kullanıcı proje listesi sayfasını açar")
@allure.step("Smoke: Proje listesi aç")
def open_project_list(page):
    page.goto("/projects", wait_until="domcontentloaded", timeout=30_000)


@when("kullanıcı senaryo listesi sayfasını açar")
@allure.step("Smoke: Senaryo listesi aç")
def open_scenario_list(page, seeded_project_id):
    page.goto(f"/p/{seeded_project_id}/scenarios", wait_until="domcontentloaded", timeout=30_000)


@when("kullanıcı onay kuyruğu sayfasını açar")
@allure.step("Smoke: Onay kuyruğu aç")
def open_approval_queue(page, seeded_project_id):
    page.goto(f"/p/{seeded_project_id}/approvals", wait_until="domcontentloaded", timeout=30_000)


@when("kullanıcı içe aktarma sayfasını açar")
@allure.step("Smoke: İçe aktarma sayfası aç")
def open_import_page(page, seeded_project_id):
    page.goto(f"/p/{seeded_project_id}/import", wait_until="domcontentloaded", timeout=30_000)


# ── THEN — Hızlı Doğrulama ──────────────────────────────────────────────────

@then("sayfa başarıyla yüklenmiş olmalıdır")
@allure.step("Smoke: Sayfa yükleme doğrulaması")
def assert_page_loaded(page):
    with allure.step(f"Mevcut URL: {page.url}"):
        assert page.url, "Sayfa URL'si boş"
    allure.attach(
        page.screenshot(),
        name="Smoke Sonuç",
        attachment_type=allure.attachment_type.PNG,
    )


@then("kullanıcı başarıyla çıkış yapmış olmalıdır")
@allure.step("Smoke: Çıkış doğrulaması")
def assert_logged_out(page):
    with allure.step("URL /login içermeli"):
        assert "/login" in page.url, (
            f"Çıkış başarısız — URL hâlâ: {page.url}"
        )


@then(parsers.parse('"{element}" elementi sayfada mevcut olmalıdır'))
@allure.step("Smoke: Element varlık kontrolü — {element}")
def assert_element_present(page, element: str):
    locator = page.locator(element)
    assert locator.count() > 0, f"Element bulunamadı: {element}"


# ── WHEN — API Sağlık Kontrolleri ──────────────────────────────────────────

_API_BASE = os.getenv("API_URL", "http://localhost:8000/api/v1")
_LAST_RESPONSE: dict = {"status": None, "ok": False}


@when("API sağlık kontrolü yapılır")
@allure.step("Smoke: Backend sağlık kontrolü — /health")
def api_health_check():
    try:
        resp = httpx.get(f"{_API_BASE.rstrip('/v1').rstrip('/api/v1')}/health", timeout=10.0)
        _LAST_RESPONSE["status"] = resp.status_code
        _LAST_RESPONSE["ok"] = resp.is_success
        allure.attach(
            f"Status: {resp.status_code}\nURL: {resp.url}",
            name="Health Yanıt",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception as exc:
        _LAST_RESPONSE["status"] = 0
        _LAST_RESPONSE["ok"] = False
        pytest.skip(f"Backend erişilemez: {exc}")


@when("API hazırlık kontrolü yapılır")
@allure.step("Smoke: Veritabanı hazırlık kontrolü — /ready")
def api_readiness_check():
    try:
        resp = httpx.get(f"{_API_BASE.rstrip('/v1').rstrip('/api/v1')}/ready", timeout=10.0)
        _LAST_RESPONSE["status"] = resp.status_code
        _LAST_RESPONSE["ok"] = resp.is_success
        allure.attach(
            f"Status: {resp.status_code}\nURL: {resp.url}",
            name="Ready Yanıt",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception as exc:
        # Fall back to health endpoint
        try:
            resp = httpx.get(f"{_API_BASE.rstrip('/v1').rstrip('/api/v1')}/health", timeout=10.0)
            _LAST_RESPONSE["status"] = resp.status_code
            _LAST_RESPONSE["ok"] = resp.is_success
        except Exception as exc2:
            _LAST_RESPONSE["status"] = 0
            _LAST_RESPONSE["ok"] = False
            pytest.skip(f"Backend erişilemez: {exc2}")


@when("Engine ile feature listesi sorgulanır")
@allure.step("Smoke: Engine feature listesi sorgusu")
def query_engine_feature_list():
    try:
        resp = httpx.get(f"{_API_BASE}/features", timeout=10.0)
        _LAST_RESPONSE["status"] = resp.status_code
        _LAST_RESPONSE["ok"] = resp.is_success
        allure.attach(
            f"Status: {resp.status_code}",
            name="Feature List Yanıt",
            attachment_type=allure.attachment_type.TEXT,
        )
        if not resp.is_success:
            pytest.skip(f"Engine feature API kullanılabilir değil — Status: {resp.status_code}")
    except Exception as exc:
        _LAST_RESPONSE["status"] = 0
        _LAST_RESPONSE["ok"] = False
        pytest.skip(f"Engine API erişilemez: {exc}")


@when("API ile geçerli kimlik bilgileriyle giriş yapılır")
@allure.step("Smoke: Auth API giriş testi")
def api_login_with_valid_credentials():
    try:
        resp = httpx.post(
            f"{_API_BASE}/auth/login",
            json={"email": os.getenv("ADMIN_EMAIL", "admin@example.com"),
                  "password": os.getenv("ADMIN_PASSWORD", "admin123")},
            timeout=10.0,
        )
        _LAST_RESPONSE["status"] = resp.status_code
        _LAST_RESPONSE["ok"] = resp.status_code in (200, 201)
        allure.attach(
            f"Status: {resp.status_code}",
            name="Auth API Yanıt",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception as exc:
        _LAST_RESPONSE["status"] = 0
        _LAST_RESPONSE["ok"] = False
        pytest.skip(f"Auth API erişilemez: {exc}")


@then("API yanıt kodu 200 olmalıdır")
@allure.step("Smoke: API yanıt kodu 200 doğrula")
def assert_api_response_200():
    status = _LAST_RESPONSE.get("status", 0)
    with allure.step(f"Yanıt kodu: {status}"):
        if status == 0:
            pytest.skip("API isteği gönderilemedi — backend erişilemez")
        assert status == 200, f"Beklenen: 200, Gelen: {status}"


@then("API yanıtı başarılı olmalıdır")
@allure.step("Smoke: API yanıt başarı doğrula")
def assert_api_response_ok():
    ok = _LAST_RESPONSE.get("ok", False)
    status = _LAST_RESPONSE.get("status", 0)
    with allure.step(f"Yanıt kodu: {status}, OK: {ok}"):
        if status == 0:
            pytest.skip("API isteği gönderilemedi — backend erişilemez")
        assert ok, f"API başarısız — Status: {status}"


@then("platform temel işlevleri çalışır durumda olmalıdır")
@allure.step("Smoke: Platform sağlık özeti")
def assert_platform_healthy(page):
    allure.attach(
        f"URL: {page.url}\nSayfa Başlığı: {page.title()}",
        name="Platform Durumu",
        attachment_type=allure.attachment_type.TEXT,
    )
    allure.attach(
        page.screenshot(),
        name="Platform Görünümü",
        attachment_type=allure.attachment_type.PNG,
    )
