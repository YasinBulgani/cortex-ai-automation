"""Integration tests for newly registered domain routers (2026-05-24 fix).

Previously these 8 domains had router.py files but were NOT connected to
the FastAPI app in router_registry.py. All their endpoints returned 404.

These tests verify the routers are now properly registered and return auth
errors (401/403) rather than 404 — confirming the router fix works.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "method"),
    [
        # events domain — GET /api/v1/events/history
        ("/api/v1/events", "GET"),
        # marketplace domain — GET /api/v1/marketplace/items
        ("/api/v1/marketplace/items", "GET"),
        # visual domain — POST /api/v1/visual/compare (requires upload, 422 ok)
        ("/api/v1/visual/compare", "POST"),
        # pilot domain — GET /api/v1/pilot/sessions
        ("/api/v1/pilot/sessions", "GET"),
        # defects domain — GET /api/v1/defects
        ("/api/v1/defects", "GET"),
        # ingestion domain — GET /api/v1/ingestion/projects/test
        ("/api/v1/ingestion/projects/test", "GET"),
        # knowledge_base domain — GET /api/v1/kb/articles
        ("/api/v1/kb/articles", "GET"),
        # compliance domain — GET /api/v1/compliance/controls
        ("/api/v1/compliance/controls", "GET"),
    ],
)
def test_newly_registered_domain_not_404(path: str, method: str, client: TestClient) -> None:
    """Newly registered domain router responds with any status != 404.

    404 = router not registered (regression check).
    401/403/422/200 = router IS registered (expected for auth-required endpoints).
    """
    if method == "GET":
        r = client.get(path)
    elif method == "POST":
        r = client.post(path)
    else:
        r = client.request(method, path)

    assert r.status_code != 404, (
        f"{method} {path} döndürdü 404 — router_registry.py'deki kayıt kontrol et. "
        f"Bu domain router'ı 2026-05-24'te eklendi, kayıp mı?"
    )
