"""router_registry üzerinden tüm domain router'larının gerçekten
FastAPI uygulamasına bağlandığını doğrulayan entegrasyon testleri.

Amaç: n8n, cicd gibi router'ların `main.py`'de unutulması durumunda CI'da
erken yakalamak. "Router tanımlı ama uygulamaya kayıtlı değil" regresyonunu
engeller.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path_prefix",
    [
        "/api/v1/n8n",
        "/api/v1/cicd",
        "/api/v1/tspm",
        "/api/v1/auth",
        "/api/v1/dsl",
    ],
)
def test_critical_router_prefix_present(path_prefix: str) -> None:
    """Kritik router prefix'leri OpenAPI içinde bulunmalı — 404 regresyonu önler."""
    from app.main import app

    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = list(spec.get("paths", {}).keys())
    assert any(p.startswith(path_prefix) for p in paths), (
        f"{path_prefix} prefix'i hiçbir endpoint'e sahip değil. "
        f"Bu genellikle app/core/router_registry.py içindeki _PREFIXED_ROUTERS "
        f"listesinden atlandığı anlamına gelir."
    )


def test_all_registered_routers_have_at_least_one_route() -> None:
    """Registry'deki her router en az bir endpoint tanımlamış olmalı."""
    from app.core.router_registry import _PREFIXED_ROUTERS, _UNPREFIXED_ROUTERS

    empty: list[str] = []
    for router in (*_PREFIXED_ROUTERS, *_UNPREFIXED_ROUTERS):
        if not router.routes:
            empty.append(router.prefix or "<no-prefix>")
    assert not empty, f"Boş router'lar: {empty}"
