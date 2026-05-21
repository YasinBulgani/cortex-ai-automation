"""
steps/bgts_synthetic_steps.py — Sentetik Veri Üretimi BDD adım tanımları.

synthetic_data.feature dosyasındaki tüm adımlar için step implementation.
common_steps'teki genel adımları re-export eder, ek olarak httpx tabanlı
API çağrıları ve sentetik veri işlemleri için adımlar sağlar.
"""
from __future__ import annotations

import sys
from pathlib import Path

import allure
import httpx
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
from test_data.fixtures import get_api_payload, load_test_data

API_BASE = "http://localhost:8000"


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def _api_url(path: str) -> str:
    return f"{API_BASE}{path}"


def _get_payload(name: str) -> dict:
    return get_api_payload(name)


# ── EK GIVEN ADIMLARI ───────────────────────────────────────────────────────

@given("sentetik veri API servisi çalışıyor")
@allure.step("API sağlık kontrolü: sentetik veri servisi")
def synthetic_api_health_check():
    with allure.step("GET /health endpoint kontrolü"):
        try:
            resp = httpx.get(_api_url("/health"), timeout=10)
            assert resp.status_code == 200, f"API sağlık kontrolü başarısız: {resp.status_code}"
        except httpx.ConnectError:
            allure.attach(
                "API servisi erişilemez — localhost:8000",
                name="API Hata",
                attachment_type=allure.attachment_type.TEXT,
            )


@given(parsers.parse('kullanıcı "{dataset_id}" veri setini seçmiştir'))
@allure.step("Veri seti seç: {dataset_id}")
def select_dataset(dataset_id: str, ai_results):
    ai_results["selected_dataset"] = dataset_id


# ── EK WHEN ADIMLARI ────────────────────────────────────────────────────────

@when("kullanıcı API üzerinden CSV dosyası yükler")
@allure.step("API: CSV dosyası yükle")
def api_upload_csv(ai_results):
    payload = _get_payload("upload_csv")
    with allure.step(f"POST {payload['endpoint']}"):
        try:
            resp = httpx.post(
                _api_url(payload["endpoint"]),
                json=payload.get("fields", {}),
                timeout=30,
            )
            ai_results["upload_response"] = {
                "status_code": resp.status_code,
                "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
            allure.attach(
                str(ai_results["upload_response"]),
                name="Upload Yanıt",
                attachment_type=allure.attachment_type.TEXT,
            )
        except httpx.ConnectError:
            ai_results["upload_response"] = {"status_code": 0, "body": "Bağlantı hatası"}


@when("kullanıcı API üzerinden veri analizi başlatır")
@allure.step("API: Veri analizi başlat")
def api_analyze_dataset(ai_results):
    payload = _get_payload("analyze_dataset")
    with allure.step(f"POST {payload['endpoint']}"):
        try:
            resp = httpx.post(
                _api_url(payload["endpoint"]),
                json=payload.get("body", {}),
                timeout=30,
            )
            ai_results["analysis_response"] = {
                "status_code": resp.status_code,
                "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
            allure.attach(
                str(ai_results["analysis_response"]),
                name="Analiz Yanıt",
                attachment_type=allure.attachment_type.TEXT,
            )
        except httpx.ConnectError:
            ai_results["analysis_response"] = {"status_code": 0, "body": "Bağlantı hatası"}


@when(parsers.parse('kullanıcı API üzerinden {count:d} adet sentetik kayıt üretir'))
@allure.step("API: {count} adet sentetik kayıt üret")
def api_generate_synthetic(count: int, ai_results):
    payload = _get_payload("generate_synthetic")
    body = payload.get("body", {}).copy()
    body["record_count"] = count
    with allure.step(f"POST {payload['endpoint']} — {count} kayıt"):
        try:
            resp = httpx.post(
                _api_url(payload["endpoint"]),
                json=body,
                timeout=60,
            )
            ai_results["generation_response"] = {
                "status_code": resp.status_code,
                "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
            allure.attach(
                str(ai_results["generation_response"]),
                name="Üretim Yanıt",
                attachment_type=allure.attachment_type.TEXT,
            )
        except httpx.ConnectError:
            ai_results["generation_response"] = {"status_code": 0, "body": "Bağlantı hatası"}


@when("kullanıcı API üzerinden PII taraması başlatır")
@allure.step("API: PII taraması başlat")
def api_pii_scan(ai_results):
    dataset_id = ai_results.get("selected_dataset", "ds-001")
    with allure.step(f"POST /api/v1/data/pii-scan — dataset: {dataset_id}"):
        try:
            resp = httpx.post(
                _api_url("/api/v1/data/pii-scan"),
                json={"dataset_id": dataset_id},
                timeout=30,
            )
            ai_results["pii_response"] = {
                "status_code": resp.status_code,
                "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
            allure.attach(
                str(ai_results["pii_response"]),
                name="PII Tarama Yanıt",
                attachment_type=allure.attachment_type.TEXT,
            )
        except httpx.ConnectError:
            ai_results["pii_response"] = {"status_code": 0, "body": "Bağlantı hatası"}


@when(parsers.parse('kullanıcı API üzerinden veri setini "{fmt}" formatında dışa aktarır'))
@allure.step("API: Veri setini {fmt} olarak dışa aktar")
def api_export_dataset(fmt: str, ai_results):
    dataset_id = ai_results.get("selected_dataset", "ds-001")
    with allure.step(f"POST /api/v1/data/export — format: {fmt}"):
        try:
            resp = httpx.post(
                _api_url("/api/v1/data/export"),
                json={"dataset_id": dataset_id, "format": fmt.lower()},
                timeout=30,
            )
            ai_results["export_response"] = {
                "status_code": resp.status_code,
                "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
            allure.attach(
                str(ai_results["export_response"]),
                name="Dışa Aktarma Yanıt",
                attachment_type=allure.attachment_type.TEXT,
            )
        except httpx.ConnectError:
            ai_results["export_response"] = {"status_code": 0, "body": "Bağlantı hatası"}


# ── EK THEN ADIMLARI ────────────────────────────────────────────────────────

@then("API yükleme başarılı olmalıdır")
@allure.step("API yükleme yanıtı doğrulama")
def assert_api_upload_success(ai_results):
    resp = ai_results.get("upload_response", {})
    with allure.step(f"Status code: {resp.get('status_code')}"):
        assert resp.get("status_code") in (200, 201), (
            f"Upload başarısız — status: {resp.get('status_code')}, body: {resp.get('body')}"
        )


@then("API analiz sonuçları dönmüş olmalıdır")
@allure.step("API analiz yanıtı doğrulama")
def assert_api_analysis_success(ai_results):
    resp = ai_results.get("analysis_response", {})
    with allure.step(f"Status code: {resp.get('status_code')}"):
        assert resp.get("status_code") == 200, (
            f"Analiz başarısız — status: {resp.get('status_code')}, body: {resp.get('body')}"
        )


@then("API sentetik veri üretimi başarılı olmalıdır")
@allure.step("API üretim yanıtı doğrulama")
def assert_api_generation_success(ai_results):
    resp = ai_results.get("generation_response", {})
    with allure.step(f"Status code: {resp.get('status_code')}"):
        assert resp.get("status_code") in (200, 201, 202), (
            f"Üretim başarısız — status: {resp.get('status_code')}, body: {resp.get('body')}"
        )


@then("PII tarama sonuçları dönmüş olmalıdır")
@allure.step("PII tarama yanıtı doğrulama")
def assert_pii_scan_success(ai_results):
    resp = ai_results.get("pii_response", {})
    with allure.step(f"Status code: {resp.get('status_code')}"):
        assert resp.get("status_code") == 200, (
            f"PII tarama başarısız — status: {resp.get('status_code')}, body: {resp.get('body')}"
        )


@then("API dışa aktarma başarılı olmalıdır")
@allure.step("API dışa aktarma yanıtı doğrulama")
def assert_api_export_success(ai_results):
    resp = ai_results.get("export_response", {})
    with allure.step(f"Status code: {resp.get('status_code')}"):
        assert resp.get("status_code") == 200, (
            f"Dışa aktarma başarısız — status: {resp.get('status_code')}, body: {resp.get('body')}"
        )
