"""Integration tests for AI streaming endpoints (/api/v1/ai/stream/)."""

import pytest
from fastapi.testclient import TestClient


class _FakeStreamingService:
    async def stream_scenario_generation(self, **kwargs):
        yield {"type": "chunk", "content": "scenario"}

    async def stream_test_analysis(self, **kwargs):
        yield {"type": "chunk", "content": "analysis"}

    async def stream_test_data_generation(self, **kwargs):
        yield {"type": "chunk", "content": "test-data"}

    async def stream_general(self, **kwargs):
        yield {"type": "chunk", "content": "general"}


@pytest.fixture
def fake_streaming_service(monkeypatch):
    monkeypatch.setattr(
        "app.domains.ai.streaming_service.get_streaming_service",
        lambda: _FakeStreamingService(),
    )


class TestAIStreaming:
    """AI SSE streaming endpoint tests.

    The LLM backend may not be available, so streaming endpoints may return
    an error inside the SSE stream or a 500.  We primarily verify that the
    endpoints accept proper payloads and return the correct content-type.
    """

    PREFIX = "/api/v1/ai/stream"

    # ── Auth guard ──────────────────────────────────────────────────────

    def test_stream_scenarios_requires_auth(
        self, client: TestClient
    ) -> None:
        """POST /stream/scenarios without auth must return 401."""
        r = client.post(
            f"{self.PREFIX}/scenarios",
            json={"description": "test"},
        )
        assert r.status_code == 401

    # ── Content-type checks ─────────────────────────────────────────────

    def test_stream_scenarios_content_type(
        self, client: TestClient, auth_headers: dict, fake_streaming_service
    ) -> None:
        """POST /stream/scenarios returns text/event-stream."""
        r = client.post(
            f"{self.PREFIX}/scenarios",
            json={
                "description": "Login senaryolari",
                "context": "Internet bankaciligi",
                "count": 2,
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct
        assert "data:" in r.text

    def test_stream_analysis_content_type(
        self, client: TestClient, auth_headers: dict, fake_streaming_service
    ) -> None:
        """POST /stream/analysis returns text/event-stream."""
        r = client.post(
            f"{self.PREFIX}/analysis",
            json={
                "execution_data": "Test1: PASS, Test2: FAIL",
                "question": "Neden basarisiz?",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct
        assert "data:" in r.text

    def test_stream_test_data_content_type(
        self, client: TestClient, auth_headers: dict, fake_streaming_service
    ) -> None:
        """POST /stream/test-data returns text/event-stream."""
        r = client.post(
            f"{self.PREFIX}/test-data",
            json={
                "description": "Banka hesap bilgileri",
                "row_count": 3,
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct
        assert "data:" in r.text

    def test_stream_general_content_type(
        self, client: TestClient, auth_headers: dict, fake_streaming_service
    ) -> None:
        """POST /stream/general returns text/event-stream."""
        r = client.post(
            f"{self.PREFIX}/general",
            json={
                "system_prompt": "Sen bir QA muhendisisin.",
                "user_message": "Merhaba",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct
        assert "data:" in r.text

    # ── Body acceptance ─────────────────────────────────────────────────

    def test_stream_scenarios_accepts_body(
        self, client: TestClient, auth_headers: dict, fake_streaming_service
    ) -> None:
        """POST /stream/scenarios accepts a proper ScenarioStreamRequest body."""
        r = client.post(
            f"{self.PREFIX}/scenarios",
            json={
                "description": "EFT transfer senaryolari",
                "context": "BDDK regülasyonlari",
                "count": 5,
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    # ── Existing endpoint ───────────────────────────────────────────────

    def test_existing_endpoint_providers(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /ai/providers still works (non-streaming sanity check)."""
        r = client.get(
            "/api/v1/ai/providers",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "active" in body
        assert "providers" in body
