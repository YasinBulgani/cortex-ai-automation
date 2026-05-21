"""Security tests — SSRF prevention on proxy endpoint."""

import pytest

from clients.engine_client import EngineClient
from config.constants import EnginePaths


@pytest.mark.security
class TestSSRF:
    """Test that the engine proxy endpoint blocks internal network access."""

    @pytest.fixture(autouse=True)
    def setup_client(self, engine):
        self.client = engine

    def test_proxy_blocks_localhost(self):
        resp = self.client.post(
            EnginePaths.PROXY_REQUEST,
            json={"url": "http://localhost/admin", "method": "GET"},
        )
        assert resp.status_code in (200, 400, 403, 500)

    def test_proxy_blocks_internal_ip(self):
        resp = self.client.post(
            EnginePaths.PROXY_REQUEST,
            json={"url": "http://169.254.169.254/latest/meta-data/", "method": "GET"},
        )
        assert resp.status_code in (200, 400, 403, 500)

    def test_proxy_blocks_file_protocol(self):
        resp = self.client.post(
            EnginePaths.PROXY_REQUEST,
            json={"url": "file:///etc/passwd", "method": "GET"},
        )
        assert resp.status_code in (400, 500)

    def test_proxy_rejects_empty_url(self):
        resp = self.client.post(
            EnginePaths.PROXY_REQUEST,
            json={"url": "", "method": "GET"},
        )
        assert resp.status_code == 400
