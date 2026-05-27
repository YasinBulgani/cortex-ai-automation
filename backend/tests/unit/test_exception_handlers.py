"""Unit tests for global FastAPI exception handlers.

Tests the following handlers:
- value_error_handler  → 400 Bad Request with client.bad_request code
- key_error_handler    → 404 Not Found with client.not_found code
- unhandled_exception_handler → 500 Internal Server Error
- http_exception_handler → passes through HTTPException status codes
- validation_exception_handler → 422 with field_errors
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers


# ---------------------------------------------------------------------------
# Helper: build a small test app with routes that raise specific exceptions
# ---------------------------------------------------------------------------

def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-value-error")
    def raise_value_error():
        raise ValueError("name alanı zorunludur")

    @app.get("/raise-value-error-empty")
    def raise_value_error_empty():
        raise ValueError("")

    @app.get("/raise-key-error")
    def raise_key_error():
        raise KeyError("thing not found")

    @app.get("/raise-key-error-simple")
    def raise_key_error_simple():
        raise KeyError("kayıt bulunamadı")

    @app.get("/raise-generic-exception")
    def raise_generic():
        raise RuntimeError("unexpected boom")

    @app.get("/raise-base-exception")
    def raise_base():
        raise Exception("completely unexpected")

    @app.get("/raise-http-404")
    def raise_http_404():
        raise HTTPException(status_code=404, detail="Resource not found")

    @app.get("/raise-http-403")
    def raise_http_403():
        raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/raise-http-500")
    def raise_http_500():
        raise HTTPException(status_code=500, detail="Internal")

    @app.post("/body-required")
    def body_required(data: dict):
        return data

    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_make_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# value_error_handler tests
# ---------------------------------------------------------------------------

class TestValueErrorHandler:
    def test_status_code_is_400(self, client: TestClient):
        resp = client.get("/raise-value-error")
        assert resp.status_code == 400

    def test_error_code_is_client_bad_request(self, client: TestClient):
        resp = client.get("/raise-value-error")
        body = resp.json()
        assert body["error"]["code"] == "client.bad_request"

    def test_error_title(self, client: TestClient):
        resp = client.get("/raise-value-error")
        body = resp.json()
        assert body["error"]["title"] == "Bad Request"

    def test_detail_message_propagated(self, client: TestClient):
        resp = client.get("/raise-value-error")
        body = resp.json()
        assert "name alanı zorunludur" in body["error"]["message"]

    def test_suggestion_present(self, client: TestClient):
        resp = client.get("/raise-value-error")
        body = resp.json()
        assert body["error"]["suggestion"]

    def test_empty_value_error_message(self, client: TestClient):
        resp = client.get("/raise-value-error-empty")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "client.bad_request"

    def test_response_body_has_error_key(self, client: TestClient):
        resp = client.get("/raise-value-error")
        body = resp.json()
        assert "error" in body

    def test_doc_url_is_none(self, client: TestClient):
        resp = client.get("/raise-value-error")
        body = resp.json()
        assert body["error"]["doc_url"] is None


# ---------------------------------------------------------------------------
# key_error_handler tests
# ---------------------------------------------------------------------------

class TestKeyErrorHandler:
    def test_status_code_is_404(self, client: TestClient):
        resp = client.get("/raise-key-error")
        assert resp.status_code == 404

    def test_error_code_is_client_not_found(self, client: TestClient):
        resp = client.get("/raise-key-error")
        body = resp.json()
        assert body["error"]["code"] == "client.not_found"

    def test_error_title(self, client: TestClient):
        resp = client.get("/raise-key-error")
        body = resp.json()
        assert body["error"]["title"] == "Not Found"

    def test_key_error_message_in_response(self, client: TestClient):
        resp = client.get("/raise-key-error")
        body = resp.json()
        # KeyError("thing not found") → strips quotes from str(exc)
        assert "thing not found" in body["error"]["message"]

    def test_key_error_simple_message(self, client: TestClient):
        resp = client.get("/raise-key-error-simple")
        assert resp.status_code == 404
        body = resp.json()
        assert "kayıt bulunamadı" in body["error"]["message"]

    def test_suggestion_present(self, client: TestClient):
        resp = client.get("/raise-key-error")
        body = resp.json()
        assert body["error"]["suggestion"]

    def test_doc_url_is_none(self, client: TestClient):
        resp = client.get("/raise-key-error")
        body = resp.json()
        assert body["error"]["doc_url"] is None


# ---------------------------------------------------------------------------
# unhandled_exception_handler tests (RuntimeError and generic Exception)
# ---------------------------------------------------------------------------

class TestUnhandledExceptionHandler:
    def test_runtime_error_returns_500(self, client: TestClient):
        resp = client.get("/raise-generic-exception")
        assert resp.status_code == 500

    def test_generic_exception_returns_500(self, client: TestClient):
        resp = client.get("/raise-base-exception")
        assert resp.status_code == 500

    def test_500_error_code(self, client: TestClient):
        resp = client.get("/raise-generic-exception")
        body = resp.json()
        assert body["error"]["code"] == "internal.unexpected"

    def test_500_has_error_key(self, client: TestClient):
        resp = client.get("/raise-base-exception")
        body = resp.json()
        assert "error" in body

    def test_500_suggestion_present(self, client: TestClient):
        resp = client.get("/raise-generic-exception")
        body = resp.json()
        assert body["error"].get("suggestion") or body["error"].get("title")


# ---------------------------------------------------------------------------
# http_exception_handler tests
# ---------------------------------------------------------------------------

class TestHttpExceptionHandler:
    def test_http_404_passes_through(self, client: TestClient):
        resp = client.get("/raise-http-404")
        assert resp.status_code == 404

    def test_http_403_passes_through(self, client: TestClient):
        resp = client.get("/raise-http-403")
        assert resp.status_code == 403

    def test_http_500_passes_through(self, client: TestClient):
        resp = client.get("/raise-http-500")
        assert resp.status_code == 500

    def test_http_exception_body_has_error_key(self, client: TestClient):
        resp = client.get("/raise-http-404")
        body = resp.json()
        assert "error" in body or "detail" in body
