from __future__ import annotations

import contextlib
import os
from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_client_cookies(client: TestClient):
    """Keep auth cookies from leaking between tests."""
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.fixture(scope="session")
def db_ready(client: TestClient) -> bool:
    """DB hazır mı? — engine durumunu görmezden gelir.

    `/ready` 503 dönse bile (engine erişilemez — test ortamında beklenen
    durum), `checks.database.status == "ok"` ise true döner. Bu fixture
    testi yalnızca DB varlığına göre atlar; engine bağımlılığı değildir.
    """
    r = client.get("/ready")
    # 200 veya 503 her ikisi de body döndürür — engine sorunu test'i kırmamalı
    if r.status_code not in (200, 503):
        pytest.skip(f"/ready beklenmeyen HTTP {r.status_code}")
    body = r.json()
    db_status = (body.get("checks") or {}).get("database") or {}
    return db_status.get("status") == "ok"


@pytest.fixture(scope="session")
def admin_token(client: TestClient, db_ready: bool) -> str:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def operator_token(client: TestClient, db_ready: bool) -> str:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@test.com", "password": "test123"},
    )
    if r.status_code != 200:
        pytest.skip("Operator kullanıcı seed edilmemiş")
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def operator_headers(operator_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture(scope="session")
def viewer_token(client: TestClient, db_ready: bool) -> str:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@test.com", "password": "test123"},
    )
    if r.status_code != 200:
        pytest.skip("Viewer kullanıcı seed edilmemiş")
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def viewer_headers(viewer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture()
def feature_flags_svc():
    """feature_flags service singleton'ını döner.

    Test_ai_governance.py gibi dosyalardaki `try/except ImportError: skip`
    kalıplarını ortadan kaldırmak için conftest'te merkezi fixture olarak
    tanımlandı. Module her zaman mevcut — import hatası olursa testi
    açıkça fail et, sessizce atla.
    """
    from app.domains.feature_flags.service import feature_flags
    from app.domains.feature_flags.schemas import FlagUpdate
    return feature_flags, FlagUpdate


@pytest.fixture()
def mock_db_session() -> MagicMock:
    """MagicMock SQLAlchemy session with standard query chain.

    Supports: session.query(Model).filter(...).first() / .all() / .count()
    Also supports: session.add(), session.commit(), session.rollback(), session.close()
    """
    session = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = None
    filter_mock.all.return_value = []
    filter_mock.count.return_value = 0
    filter_mock.one_or_none.return_value = None
    filter_mock.filter.return_value = filter_mock  # chaining support
    filter_mock.order_by.return_value = filter_mock
    filter_mock.limit.return_value = filter_mock
    filter_mock.offset.return_value = filter_mock
    query_mock.filter.return_value = filter_mock
    query_mock.filter_by.return_value = filter_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = None
    query_mock.get.return_value = None
    session.query.return_value = query_mock
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    session.flush.return_value = None
    session.refresh.return_value = None
    return session


@pytest.fixture()
def mock_http_client() -> MagicMock:
    """MagicMock httpx.AsyncClient with mocked get/post/put/delete responses.

    Default responses return status_code=200 with empty JSON body {}.
    Override per-test: mock_http_client.get.return_value = MagicMock(status_code=404, json=lambda: {...})
    """
    client = MagicMock()

    def _make_response(status_code: int = 200, data: dict | None = None) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.json = MagicMock(return_value=data or {})
        resp.text = ""
        resp.content = b""
        resp.raise_for_status = MagicMock(return_value=None)
        return resp

    default_resp = _make_response()
    client.get = AsyncMock(return_value=default_resp)
    client.post = AsyncMock(return_value=default_resp)
    client.put = AsyncMock(return_value=default_resp)
    client.patch = AsyncMock(return_value=default_resp)
    client.delete = AsyncMock(return_value=default_resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture()
def override_settings():
    """Returns a context manager that temporarily overrides app.config.settings attributes.

    Usage:
        def test_something(override_settings):
            with override_settings(DEBUG=True, MAX_RETRIES=0):
                ...  # settings patched for this block only
    """
    @contextmanager
    def _override(**kwargs: object) -> Generator[None, None, None]:
        try:
            from app.config import settings
        except ImportError:
            try:
                from app.core.config import settings
            except ImportError:
                pytest.skip("app.config.settings or app.core.config.settings not found")
                return

        original = {k: getattr(settings, k, None) for k in kwargs}
        try:
            for k, v in kwargs.items():
                setattr(settings, k, v)
            yield
        finally:
            for k, v in original.items():
                if v is None:
                    with contextlib.suppress(AttributeError):
                        delattr(settings, k)
                else:
                    setattr(settings, k, v)

    return _override


@pytest.fixture()
def test_management_session() -> MagicMock:
    """MagicMock SQLAlchemy session pre-configured for test_management model queries.

    Provides ready-made return values for the three most common lookups used
    by test_management domain tests, so individual test files do not need to
    repeat the setup boilerplate.

    Usage:
        def test_something(test_management_session):
            svc = MyService(db=test_management_session)
            result = svc.get_project("proj-001")
            test_management_session.get.assert_called()

    Override per-test by reassigning the mock attributes, e.g.:
        test_management_session.get.return_value = None  # simulate not-found
    """
    session = MagicMock()

    # ── standard query chain ─────────────────────────────────────────────────
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = None
    filter_mock.all.return_value = []
    filter_mock.count.return_value = 0
    filter_mock.one_or_none.return_value = None
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = filter_mock
    filter_mock.limit.return_value = filter_mock
    filter_mock.offset.return_value = filter_mock
    query_mock.filter.return_value = filter_mock
    query_mock.filter_by.return_value = filter_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = None
    query_mock.get.return_value = None
    session.query.return_value = query_mock

    # ── scalar / scalars (SQLAlchemy 2.x style) ──────────────────────────────
    session.scalar.return_value = None
    session.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    session.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

    # ── mutation helpers ──────────────────────────────────────────────────────
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    session.flush.return_value = None
    session.refresh.return_value = None

    # ── test_management-specific pre-configured mock objects ─────────────────
    fake_project = MagicMock()
    fake_project.id = "proj-test-001"
    fake_project.name = "Default Test Project"
    fake_project.key = "DTP"
    fake_project.status = "active"
    fake_project.tenant_id = "00000000-0000-0000-0000-000000000001"
    fake_project.suites = []
    fake_project.cases = []
    fake_project.plans = []

    fake_test_case = MagicMock()
    fake_test_case.id = "tc-test-001"
    fake_test_case.project_id = "proj-test-001"
    fake_test_case.title = "Default Test Case"
    fake_test_case.status = "active"
    fake_test_case.priority = "medium"
    fake_test_case.steps = []

    fake_test_run = MagicMock()
    fake_test_run.id = "run-test-001"
    fake_test_run.project_id = "proj-test-001"
    fake_test_run.status = "pending"
    fake_test_run.results = []

    # Convenience helpers — callers can use these directly or override them.
    session.get_project_by_id = MagicMock(return_value=fake_project)
    session.get_test_case = MagicMock(return_value=fake_test_case)
    session.get_test_run = MagicMock(return_value=fake_test_run)

    # session.get() returns the fake_project by default (most common lookup).
    session.get.return_value = fake_project

    return session


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "smoke: Hızlı sağlık kontrolü testleri")
    config.addinivalue_line("markers", "service: API servis katmanı testleri")
    config.addinivalue_line("markers", "regression: Regresyon testleri")
    config.addinivalue_line("markers", "integration: Entegrasyon testleri")
    config.addinivalue_line("markers", "slow: Yavaş testler")
    config.addinivalue_line("markers", "security: Güvenlik testleri")
    config.addinivalue_line("markers", "rbac: Yetkilendirme matris testleri")
    config.addinivalue_line("markers", "contract: API kontrat testleri")
    config.addinivalue_line("markers", "bdd: BDD senaryo testleri")
    config.addinivalue_line("markers", "P0: En yüksek öncelik")
    config.addinivalue_line("markers", "P1: Yüksek öncelik")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-tag tests based on file path conventions."""
    for item in items:
        filepath = str(item.fspath)
        if "test_smoke" in filepath:
            item.add_marker(pytest.mark.smoke)
            item.add_marker(pytest.mark.P1)
        elif "test_schema" in filepath:
            item.add_marker(pytest.mark.regression)
            item.add_marker(pytest.mark.service)
        elif "integration" in filepath:
            item.add_marker(pytest.mark.integration)
        elif "/api/" in filepath:
            item.add_marker(pytest.mark.service)
        elif "/rbac/" in filepath:
            item.add_marker(pytest.mark.rbac)
        elif "/security/" in filepath:
            item.add_marker(pytest.mark.security)
        elif "/contract/" in filepath:
            item.add_marker(pytest.mark.contract)
        elif "/bdd/" in filepath:
            item.add_marker(pytest.mark.bdd)
