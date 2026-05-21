import os
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
