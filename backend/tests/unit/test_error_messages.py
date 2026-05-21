"""error_messages + exception_handlers için birim testler.

UX-F2-203 — zenginleştirilmiş hata cevabı şeması.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.error_messages import (
    AppError,
    ERROR_CATALOG,
    enrich_legacy_detail,
    get_error_entry,
)
from app.core.exception_handlers import register_exception_handlers


# ── Katalog bütünlüğü ─────────────────────────────────────────────────────


def test_catalog_not_empty() -> None:
    assert len(ERROR_CATALOG) >= 20, "Katalog en az 20 kayıt içermeli"


def test_every_entry_has_required_fields() -> None:
    for code, entry in ERROR_CATALOG.items():
        assert entry.get("title"), f"{code}: title eksik"
        assert entry.get("message"), f"{code}: message eksik"
        assert entry.get("suggestion"), f"{code}: suggestion eksik"
        assert entry.get("http_status"), f"{code}: http_status eksik"


def test_every_code_dotted_lowercase() -> None:
    """Kod format kuralı: kategori.alt_kod (küçük harf, alt çizgi ile)."""
    for code in ERROR_CATALOG:
        assert "." in code, f"'{code}' kategori.kod formatında olmalı"
        assert code.islower() or "_" in code, f"'{code}' küçük harf olmalı"


def test_internal_unexpected_exists() -> None:
    """Fallback kaydı mutlaka var olmalı — get_error_entry'nin dayanağı."""
    assert "internal.unexpected" in ERROR_CATALOG


# ── get_error_entry ────────────────────────────────────────────────────────


def test_get_error_entry_known_code() -> None:
    entry = get_error_entry("auth.invalid_credentials")
    assert "Geçersiz" in entry["title"]


def test_get_error_entry_unknown_code_returns_fallback() -> None:
    entry = get_error_entry("nonexistent.code")
    assert entry is ERROR_CATALOG["internal.unexpected"]


# ── AppError ───────────────────────────────────────────────────────────────


def test_apperror_basic() -> None:
    err = AppError("auth.invalid_credentials")
    assert err.status_code == 401
    assert err.detail["code"] == "auth.invalid_credentials"
    assert "Geçersiz" in err.detail["title"]
    assert err.detail["suggestion"]


def test_apperror_with_context_fills_placeholders() -> None:
    err = AppError(
        "ai.gateway_unreachable",
        detail="Connection refused",
    )
    assert "Connection refused" in err.detail["message"]


def test_apperror_missing_context_keeps_placeholder() -> None:
    """Eksik ctx key mesajı patlatmamalı — {var} olarak kalır."""
    err = AppError("ai.model_not_found")   # model= eksik
    assert err.detail["code"] == "ai.model_not_found"
    assert "{model}" in err.detail["message"]   # format_map SafeDict


def test_apperror_http_status_override() -> None:
    err = AppError("auth.invalid_credentials", http_status=418)
    assert err.status_code == 418


def test_apperror_unknown_code_falls_back_to_500() -> None:
    err = AppError("bogus.code")
    assert err.status_code == 500
    assert err.detail["code"] == "bogus.code"   # code kendi değeri
    assert err.detail["title"]   # fallback'ten dolduruldu


# ── enrich_legacy_detail ───────────────────────────────────────────────────


def test_enrich_legacy_string() -> None:
    out = enrich_legacy_detail("Kullanıcı bulunamadı", 404)
    assert out["code"] == "legacy.http_404"
    assert out["title"] == "Kullanıcı bulunamadı"
    assert out["message"] == "Kullanıcı bulunamadı"


def test_enrich_legacy_passes_through_apperror_dict() -> None:
    """Zaten AppError formatındaki detail yeniden sarılmamalı."""
    existing = {
        "code": "auth.invalid_credentials",
        "title": "t",
        "message": "m",
        "suggestion": "s",
        "doc_url": None,
    }
    out = enrich_legacy_detail(existing, 401)
    assert out is existing


def test_enrich_legacy_truncates_long_titles() -> None:
    long = "x" * 200
    out = enrich_legacy_detail(long, 400)
    assert len(out["title"]) <= 80


# ── End-to-end: FastAPI + handlers ─────────────────────────────────────────


@pytest.fixture
def test_app() -> TestClient:
    """Minimal FastAPI app — sadece handler'lar + 3 test endpoint."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/apperror")
    def ep_apperror():
        raise AppError("auth.invalid_credentials")

    @app.get("/legacy")
    def ep_legacy():
        raise HTTPException(404, "Özel kayıt yok")

    @app.get("/boom")
    def ep_boom():
        raise RuntimeError("something exploded")

    @app.post("/validate")
    def ep_validate(payload: dict):   # intentionally strict — 422 için
        if "name" not in payload:
            raise AppError("validation.invalid_input", detail="name zorunlu")
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


def test_e2e_apperror_response_shape(test_app: TestClient) -> None:
    r = test_app.get("/apperror")
    assert r.status_code == 401
    body = r.json()
    assert set(body.keys()) >= {"error", "request_id"}
    err = body["error"]
    assert err["code"] == "auth.invalid_credentials"
    assert err["title"]
    assert err["message"]
    assert err["suggestion"]


def test_e2e_legacy_httpexception_wrapped(test_app: TestClient) -> None:
    r = test_app.get("/legacy")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "legacy.http_404"
    assert body["error"]["message"] == "Özel kayıt yok"


def test_e2e_unhandled_exception_returns_500(test_app: TestClient) -> None:
    r = test_app.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal.unexpected"
    assert body["error"]["suggestion"]


def test_e2e_apperror_with_context(test_app: TestClient) -> None:
    r = test_app.post("/validate", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation.invalid_input"
    assert "name zorunlu" in body["error"]["message"]
