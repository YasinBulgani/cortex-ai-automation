"""Otomasyon Süiti API testleri.

Engine çağrıları `httpx.AsyncClient`'ın sonuçlarını monkeypatch ile
yerine koyarak (gerçek engine ayakta olmadan) doğrulanır.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def _auth(client: TestClient, db_ready: bool) -> dict:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    if resp.status_code != 200:
        pytest.skip(f"Login başarısız: {resp.status_code}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Stub Response / Client ──────────────────────────────────────────────────


class _StubResponse:
    def __init__(
        self,
        json_body: dict[str, Any] | None = None,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self._json = json_body or {}
        self.status_code = status_code
        self.text = text or ""
        self.content = (text or "").encode("utf-8")

    def json(self) -> dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("POST", "http://stub")
            response = httpx.Response(self.status_code, text=self.text)
            raise httpx.HTTPStatusError(
                f"stub {self.status_code}", request=request, response=response
            )


class _StubAsyncClient:
    """Service içindeki `httpx.AsyncClient(...)` context manager'ının yerine geçer."""

    def __init__(self, router: dict[tuple[str, str], _StubResponse]) -> None:
        self._router = router
        self.calls: list[tuple[str, str, Any]] = []

    async def __aenter__(self) -> "_StubAsyncClient":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        pass

    async def post(self, url: str, *, json: Any = None, headers: Any = None) -> _StubResponse:  # noqa: A002
        self.calls.append(("POST", url, json))
        return self._router.get(("POST", _strip_host(url))) or _StubResponse(
            json_body={"error": "no stub for " + url},
            status_code=500,
        )

    async def get(self, url: str, *, headers: Any = None) -> _StubResponse:
        self.calls.append(("GET", url, None))
        return self._router.get(("GET", _strip_host(url))) or _StubResponse(
            json_body={"error": "no stub for " + url},
            status_code=500,
        )


def _strip_host(url: str) -> str:
    # "http://host:port/path" → "/path"
    idx = url.find("/", len("http://"))
    return url[idx:] if idx != -1 else url


@pytest.fixture
def patch_httpx(monkeypatch: pytest.MonkeyPatch):
    """Test içinde engine'i taklit etmek için factory."""

    def _install(router: dict[tuple[str, str], _StubResponse]) -> _StubAsyncClient:
        stub = _StubAsyncClient(router)

        def _factory(*_a: Any, **_kw: Any) -> _StubAsyncClient:
            return stub

        from app.domains.automation_suite import service as suite_service

        monkeypatch.setattr(suite_service.httpx, "AsyncClient", _factory)
        return stub

    return _install


# ── Auth ────────────────────────────────────────────────────────────────────


def test_automation_suite_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/automation-suite/generate", json={}).status_code == 401
    assert client.post("/api/v1/automation-suite/run", json={}).status_code == 401
    assert client.get("/api/v1/automation-suite/runs/abc").status_code == 401


# ── Suggest (DSL'e dayanır, engine gerekmez) ────────────────────────────────


def test_catalog_suggest_returns_items(
    client: TestClient, db_ready: bool
) -> None:
    headers = _auth(client, db_ready)
    from app.domains.dsl.loader import catalog_cache

    catalog_cache.load()

    resp = client.post(
        "/api/v1/automation-suite/catalog/suggest",
        json={"description": "Kullanıcı butona tıklar"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


# ── Generate (engine stub'lı) ──────────────────────────────────────────────


def test_generate_success(
    client: TestClient, db_ready: bool, patch_httpx
) -> None:
    headers = _auth(client, db_ready)

    engine_body = {
        "ok": True,
        "test_title": "Login Testi",
        "steps_count": 2,
        "gherkin": (
            "Feature: Login Testi\n"
            "  Scenario: Kullanıcı giriş yapar\n"
            '    Given kullanıcı giriş sayfasındadır\n'
            '    When "Login" butonuna tıklar\n'
            "    Then anasayfa görünür\n"
        ),
        "playwright_code": "import pytest\n\ndef test_login(page):\n    pass\n",
        "feature_path": "engine/features/generated/login_testi.feature",
        "locators": {"login_button": "#login"},
        "model": "stub",
    }
    patch_httpx(
        {
            ("POST", "/api/pipeline/manual-to-automation"): _StubResponse(
                json_body=engine_body
            ),
        }
    )

    resp = client.post(
        "/api/v1/automation-suite/generate",
        json={
            "manual_test_id": 1,
            "target_url": "https://example.com",
            "framework": "playwright",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["test_title"] == "Login Testi"
    assert body["gherkin"].startswith("Feature:")
    assert body["feature_path"].endswith(".feature")
    # DSL zenginleştirme alanları var
    assert "dsl_matched_actions" in body
    assert "dsl_unknown_steps" in body


def test_generate_engine_unreachable(
    client: TestClient, db_ready: bool, patch_httpx
) -> None:
    headers = _auth(client, db_ready)

    # Boş router → her istek 500 döner → service RuntimeError fırlatır →
    # router 502 Bad Gateway çevirir
    patch_httpx({})

    resp = client.post(
        "/api/v1/automation-suite/generate",
        json={"manual_test_id": 999, "framework": "playwright"},
        headers=headers,
    )
    assert resp.status_code == 502


# ── Run status bulunamaz ───────────────────────────────────────────────────


def test_get_unknown_run_returns_404(client: TestClient, db_ready: bool) -> None:
    headers = _auth(client, db_ready)
    resp = client.get(
        "/api/v1/automation-suite/runs/notarealid",
        headers=headers,
    )
    assert resp.status_code == 404


# ── Run start validation ───────────────────────────────────────────────────


def test_run_requires_feature_path_or_suite_id(
    client: TestClient, db_ready: bool
) -> None:
    headers = _auth(client, db_ready)
    resp = client.post(
        "/api/v1/automation-suite/run",
        json={"framework": "playwright"},
        headers=headers,
    )
    # service.start_run içindeki ValueError → 400 Bad Request
    assert resp.status_code == 400
