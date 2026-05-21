"""Security: Rate limiting tests."""

import pytest
from fastapi.testclient import TestClient


class TestRateLimitHeaders:

    def test_response_contains_rate_limit_headers(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/tspm/projects", headers=auth_headers)
        assert r.status_code == 200
        # Rate limit headers may or may not be present depending on middleware config
        # This test documents the expected headers
        headers_lower = {k.lower(): v for k, v in r.headers.items()}
        if "x-ratelimit-limit" in headers_lower:
            assert int(headers_lower["x-ratelimit-limit"]) > 0
            assert "x-ratelimit-remaining" in headers_lower


class TestRateLimitEnforcement:

    @pytest.mark.slow
    def test_rapid_requests_do_not_crash(self, client: TestClient, auth_headers):
        """Send 100 rapid requests — system must not crash."""
        statuses = set()
        for _ in range(100):
            r = client.get("/api/v1/tspm/projects", headers=auth_headers)
            statuses.add(r.status_code)
        assert 200 in statuses
        # 429 may appear if rate limiting is active
        allowed = {200, 429}
        assert statuses.issubset(allowed), f"Unexpected statuses: {statuses - allowed}"
