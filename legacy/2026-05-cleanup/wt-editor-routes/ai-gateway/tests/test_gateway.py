"""
Nexus QA AI Gateway — Temel Testler
Çalıştırmak: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.core.config import settings


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "Nexus QA" in data["service"]


@pytest.mark.asyncio
async def test_ping(client):
    response = await client.get("/ping")
    assert response.status_code == 200
    assert response.json()["pong"] is True


@pytest.mark.asyncio
async def test_providers_endpoint(client):
    response = await client.get("/ai/providers")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert len(data["providers"]) == 5
    names = [p["name"] for p in data["providers"]]
    assert "vllm" in names
    assert "groq" in names
    assert "gemini" in names
    assert "ollama" in names
    assert "g4f" in names
    # Açık kaynak bayrağı her sağlayıcıda olmalı
    for p in data["providers"]:
        assert "open_source" in p, f"open_source alanı yok: {p['name']}"
    # Sadece self-hosted / local sağlayıcılar open_source=True
    oss = {p["name"] for p in data["providers"] if p["open_source"]}
    assert oss == {"vllm", "ollama"}


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/ai/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "providers" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")


@pytest.mark.asyncio
async def test_complete_missing_messages(client):
    """Mesaj yoksa 422 döndürmeli."""
    response = await client.post("/ai/complete", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_complete_invalid_internal_key(client):
    """Yanlış internal key 403 döndürmeli."""
    response = await client.post(
        "/ai/complete",
        json={
            "messages": [{"role": "user", "content": "test"}],
        },
        headers={"X-Internal-Key": "yanlis-key"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_complete_requires_internal_key(client):
    """Header yoksa 401 döndürmeli."""
    response = await client.post(
        "/ai/complete",
        json={
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_complete_timeout_returns_504(client, monkeypatch):
    """Tüm sağlayıcılar timeout olursa 504 dönmeli."""

    async def _route_timeout(_: object):
        raise TimeoutError("gateway timeout")

    monkeypatch.setattr("app.routes.ai_routes.ai_router.route", _route_timeout)
    response = await client.post(
        "/ai/complete",
        json={
            "messages": [{"role": "user", "content": "test"}],
        },
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
    )
    assert response.status_code == 504


@pytest.mark.asyncio
async def test_providers_endpoint_reflects_live_health(client, monkeypatch):
    """providers endpoint endpoint statusları canlı sağlık kontrolüne göre döndürmeli."""

    async def _health_check():
        return {
            "groq": True,
            "gemini": False,
            "ollama": False,
            "g4f": True,
        }

    monkeypatch.setattr("app.routes.ai_routes.ai_router.health_check", _health_check)
    response = await client.get("/ai/providers")
    assert response.status_code == 200
    data = response.json()
    status_by_name = {item["name"]: item["status"] for item in data["providers"]}
    assert status_by_name["groq"] == "available"
    assert status_by_name["gemini"] == "unavailable"
    assert status_by_name["ollama"] == "unavailable"
    assert status_by_name["g4f"] == "available"
