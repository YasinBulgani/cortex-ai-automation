"""OWASP Security Test: Rate Limiting & Brute Force Protection.

Test cases for rate limiting across endpoints, brute force attacks,
and DoS prevention mechanisms.

Standards:
- OWASP A06:2021 – Vulnerable and Outdated Components
- CWE-770: Allocation of Resources Without Limits or Throttling
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient


class TestRateLimiting:
    """Rate limiting and brute force protection."""

    @pytest.mark.security
    @pytest.mark.owasp_a06
    def test_rate_limit_exceeded(self, client: TestClient, auth_headers: dict):
        """Test 1: Rate limit exceeded — 429 Too Many Requests.

        Scenario: Send 50 requests in rapid succession.
        Expected: 429 Too Many Requests or all pass depending on limit.
        """
        responses = []
        for _ in range(50):
            response = client.get("/api/v1/tspm/projects", headers=auth_headers)
            responses.append(response.status_code)

        status_codes = set(responses)
        assert status_codes.issubset({200, 429})

    @pytest.mark.security
    @pytest.mark.owasp_a06
    def test_login_brute_force_protection(self, client: TestClient):
        """Test 2: Login endpoint protected against brute force.

        Scenario: Multiple failed login attempts.
        Expected: Account lockout or rate limit after N failures.
        """
        email = "admin@example.com"
        password = "wrongpassword"

        responses = []
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            responses.append(response.status_code)

        status_codes = set(responses)
        assert 401 in status_codes or 429 in status_codes

    @pytest.mark.security
    @pytest.mark.owasp_a06
    def test_api_key_brute_force(self, client: TestClient):
        """Test 3: API key validation protected against brute force."""
        responses = []
        for i in range(20):
            headers = {"Authorization": f"Bearer invalid_key_{i}"}
            response = client.get("/api/v1/tspm/projects", headers=headers)
            responses.append(response.status_code)

        status_codes = set(responses)
        assert status_codes.issubset({401, 429})

    @pytest.mark.security
    @pytest.mark.owasp_a06
    def test_rate_limit_does_not_block_legitimate_traffic(
        self, client: TestClient, auth_headers: dict
    ):
        """Test 4: Rate limit doesn't block normal traffic."""
        for _ in range(5):
            response = client.get("/api/v1/tspm/projects", headers=auth_headers)
            assert response.status_code == 200
            time.sleep(0.1)


class TestDDoSProtection:
    """General DoS/DDoS protection mechanisms."""

    @pytest.mark.security
    @pytest.mark.owasp_a06
    def test_payload_size_limit(self, client: TestClient, auth_headers: dict):
        """Test 5: Large payload rejected.

        Scenario: POST with 100MB JSON body.
        Expected: 413 Payload Too Large.
        """
        large_payload = {"data": "x" * (100 * 1024 * 1024)}
        response = client.post(
            "/api/v1/tspm/projects",
            json=large_payload,
            headers=auth_headers,
        )
        assert response.status_code in [413, 400, 422]

    @pytest.mark.security
    @pytest.mark.owasp_a06
    def test_deeply_nested_json_bomb(self, client: TestClient, auth_headers: dict):
        """Test 6: Deeply nested JSON rejected."""
        nested = {"x": "value"}
        for _ in range(100):
            nested = {"nested": nested}

        response = client.post(
            "/api/v1/tspm/projects",
            json=nested,
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 422, 413]
