"""Security header and middleware tests for TestwrightAI Banking Platform.

Validates OWASP-recommended headers, CORS restrictions, and body-size limits.
"""

import pytest
from fastapi.testclient import TestClient


class TestSecurityHeaders:
    """Verify that every response carries the mandatory security headers."""

    def test_health_has_security_headers(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-XSS-Protection") == "1; mode=block"
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in r.headers.get("Permissions-Policy", "")

    def test_api_has_no_cache_header(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        cache_control = r.headers.get("Cache-Control", "")
        assert "no-store" in cache_control
        assert "no-cache" in cache_control

    def test_xss_protection_header(self, client: TestClient):
        r = client.get("/health")
        assert r.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_content_type_options_header(self, client: TestClient):
        r = client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    def test_frame_options_header(self, client: TestClient):
        r = client.get("/health")
        assert r.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy_header(self, client: TestClient):
        r = client.get("/health")
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_csp_header_on_api(self, client: TestClient):
        r = client.get("/health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp


class TestCORSRestrictions:
    """Verify that CORS is tightened for production safety."""

    def test_cors_methods_restricted(self, client: TestClient):
        """OPTIONS preflight must only expose allowed methods."""
        r = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        allowed = r.headers.get("access-control-allow-methods", "")
        # Wildcard must NOT be present
        assert allowed != "*"
        # TRACE / CONNECT must not be allowed
        assert "TRACE" not in allowed.upper()
        assert "CONNECT" not in allowed.upper()

    def test_cors_headers_restricted(self, client: TestClient):
        """Preflight must only expose explicitly allowed headers."""
        r = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        allowed_headers = r.headers.get("access-control-allow-headers", "")
        # Should not be wildcard
        assert allowed_headers != "*"


class TestRequestSizeLimit:
    """Verify body-size enforcement."""

    def test_oversized_body_rejected(self, client: TestClient):
        """A request with Content-Length > 10 MB must be rejected with 413."""
        # Build a payload slightly over 10 MB
        oversized = b"X" * (10 * 1024 * 1024 + 1)
        r = client.post(
            "/health",
            content=oversized,
            headers={"Content-Type": "application/octet-stream"},
        )
        # The middleware should return 413
        assert r.status_code == 413

    def test_normal_body_accepted(self, client: TestClient):
        """A small JSON body must pass through normally."""
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "pass"},
        )
        # 401 is expected (bad credentials), but NOT 413
        assert r.status_code != 413
