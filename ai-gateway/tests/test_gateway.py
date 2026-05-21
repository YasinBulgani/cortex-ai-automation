"""
Nexus QA AI Gateway — Temel Testler
Çalıştırmak: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.core.config import settings
from app.core.models import AIRequest, Message, ProviderAttempt, TaskType
from app.core.router import AIRouter
from app.core.schema_contracts import SchemaContractError
from app.providers.base import BaseProvider


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
    assert len(data["providers"]) == 4
    names = [p["name"] for p in data["providers"]]
    assert "vllm" in names
    assert "groq" in names
    assert "gemini" in names
    assert "ollama" in names
    assert "g4f" not in names
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
async def test_complete_invalid_internal_key(client, monkeypatch):
    """Yanlış internal key 403 döndürmeli (INTERNAL_KEY set olunca)."""
    monkeypatch.setattr(settings, "INTERNAL_KEY", "correct-test-key")
    response = await client.post(
        "/ai/complete",
        json={
            "messages": [{"role": "user", "content": "test"}],
        },
        headers={"X-Internal-Key": "yanlis-key"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_complete_requires_internal_key(client, monkeypatch):
    """Header yoksa 401 döndürmeli (INTERNAL_KEY set olunca)."""
    monkeypatch.setattr(settings, "INTERNAL_KEY", "correct-test-key")
    response = await client.post(
        "/ai/complete",
        json={
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert response.status_code == 401


def test_cache_key_is_scoped_by_tenant_task_and_schema():
    router = AIRouter()
    base = {
        "messages": [Message(role="user", content="aynı prompt")],
        "temperature": 0.1,
        "max_tokens": 100,
    }

    first = AIRequest(
        **base,
        task_type=TaskType.GENERATE_TEST_CASES,
        tenant_id="tenant-a",
        project_id="project-a",
        schema_version="v1",
    )
    different_tenant = first.model_copy(update={"tenant_id": "tenant-b"})
    different_task = first.model_copy(update={"task_type": TaskType.ANALYZE_DOCUMENT})
    different_schema = first.model_copy(update={"schema_version": "v2"})

    assert router._cache_key(first) != router._cache_key(different_tenant)
    assert router._cache_key(first) != router._cache_key(different_task)
    assert router._cache_key(first) != router._cache_key(different_schema)


@pytest.mark.asyncio
async def test_stream_requires_internal_key(client):
    """Stream endpoint'i header yoksa 401 döndürmeli."""
    response = await client.post(
        "/ai/stream",
        json={
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pipeline_requires_internal_key(client):
    """Pipeline endpoint'i header yoksa 401 döndürmeli."""
    response = await client.post(
        "/ai/pipeline",
        json={"document": "test dokumani"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_embed_model_requires_internal_key(client):
    """Embedding model bilgisi header yoksa 401 döndürmeli."""
    response = await client.get("/ai/embed/model")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_embed_model_info(client):
    """Embedding metadata endpoint'i backend anahtarıyla çalışmalı."""
    response = await client.get(
        "/ai/embed/model",
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == settings.OLLAMA_EMBED_MODEL
    assert data["provider"] == "ollama"
    assert data["base_url"]


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
async def test_complete_structured_task_requires_schema_version(client):
    response = await client.post(
        "/ai/complete",
        json={
            "task_type": "analyze_document",
            "messages": [{"role": "user", "content": "Login akisini analiz et"}],
        },
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
    )

    assert response.status_code == 502
    data = response.json()["detail"]
    assert data["error"] == "Structured output contract failed"
    assert data["error_type"] == "missing_contract"
    assert data["task_type"] == "analyze_document"


@pytest.mark.asyncio
async def test_complete_enforces_gateway_rate_limit(client, monkeypatch):
    from app.routes import ai_routes

    ai_routes._rate_buckets.clear()
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 1)

    async def _route_ok(request):
        from app.core.models import AIResponse, ProviderAttempt

        return AIResponse(
            content="ok",
            provider_used="ollama",
            model_used="llama3.1:8b",
            attempts=[ProviderAttempt(provider="ollama", success=True)],
            cached=False,
        )

    monkeypatch.setattr("app.routes.ai_routes.ai_router.route", _route_ok)
    payload = {
        "tenant_id": "tenant-rate",
        "project_id": "project-rate",
        "messages": [{"role": "user", "content": "test"}],
    }

    first = await client.post(
        "/ai/complete",
        json=payload,
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
    )
    second = await client.post(
        "/ai/complete",
        json=payload,
        headers={"X-Internal-Key": settings.INTERNAL_KEY},
    )

    assert first.status_code == 200
    assert second.status_code == 429


@pytest.mark.asyncio
async def test_complete_enforces_gateway_concurrency_limit(client, monkeypatch):
    from app.routes import ai_routes

    ai_routes._active_requests = 1
    monkeypatch.setattr(settings, "MAX_CONCURRENT_REQUESTS", 1)
    try:
        response = await client.post(
            "/ai/complete",
            json={
                "tenant_id": "tenant-capacity",
                "project_id": "project-capacity",
                "messages": [{"role": "user", "content": "test"}],
            },
            headers={"X-Internal-Key": settings.INTERNAL_KEY},
        )
    finally:
        ai_routes._active_requests = 0

    assert response.status_code == 503


class _FakeProvider(BaseProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, content: str):
        self._content = content

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: AIRequest) -> str:
        return self._content


@pytest.mark.asyncio
async def test_router_raises_schema_mismatch_for_invalid_analyze_document(monkeypatch):
    router = AIRouter()
    provider = _FakeProvider('{"summary":"eksik alanlar"}')

    async def _providers(_: object):
        return [provider]

    async def _cache(_: object):
        return None

    async def _set_cache(_: object, __: str):
        return None

    monkeypatch.setattr(router, "_get_ordered_providers", _providers)
    monkeypatch.setattr(router, "_check_cache", _cache)
    monkeypatch.setattr(router, "_set_cache", _set_cache)

    request = AIRequest(
        task_type=TaskType.ANALYZE_DOCUMENT,
        schema_version="v1",
        messages=[Message(role="user", content="analiz et")],
        temperature=0.0,
        max_tokens=200,
    )

    with pytest.raises(SchemaContractError) as exc:
        await router.route(request)

    assert exc.value.kind == "schema_mismatch"
    assert exc.value.task_type == "analyze_document"


@pytest.mark.asyncio
async def test_router_returns_validated_json_for_structured_task(monkeypatch):
    router = AIRouter()
    provider = _FakeProvider(
        """
        {
          "domain": "banking",
          "feature_area": "login",
          "title": "Login Analizi",
          "summary": "ok",
          "goals": ["giris"],
          "acceptance_criteria": [
            {"id":"AC-1","given":"kullanici login ekraninda","when":"gecerli bilgi girer","then":"dashboard acilir","priority":3}
          ],
          "risk_level": "medium"
        }
        """
    )

    async def _providers(_: object):
        return [provider]

    async def _cache(_: object):
        return None

    async def _set_cache(_: object, __: str):
        return None

    monkeypatch.setattr(router, "_get_ordered_providers", _providers)
    monkeypatch.setattr(router, "_check_cache", _cache)
    monkeypatch.setattr(router, "_set_cache", _set_cache)

    request = AIRequest(
        task_type=TaskType.ANALYZE_DOCUMENT,
        schema_version="v1",
        messages=[Message(role="user", content="analiz et")],
        temperature=0.0,
        max_tokens=200,
    )

    response = await router.route(request)

    assert response.provider_used == "fake"
    assert '"domain": "banking"' in response.content


@pytest.mark.asyncio
async def test_providers_endpoint_reflects_live_health(client, monkeypatch):
    """providers endpoint endpoint statusları canlı sağlık kontrolüne göre döndürmeli."""

    async def _health_check():
        return {
            "vllm": {"available": False, "in_chain": False, "latency_ms": 0, "model": None},
            "groq": {"available": True, "in_chain": True, "latency_ms": 10, "model": "llama3-70b-8192"},
            "gemini": {"available": False, "in_chain": False, "latency_ms": 0, "model": None},
            "ollama": {"available": False, "in_chain": True, "latency_ms": 0, "model": None},
        }

    monkeypatch.setattr("app.routes.ai_routes.ai_router.health_check", _health_check)
    response = await client.get("/ai/providers")
    assert response.status_code == 200
    data = response.json()
    names = [p["name"] for p in data["providers"]]
    assert "groq" in names
    assert "g4f" not in names
