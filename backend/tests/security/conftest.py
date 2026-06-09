"""Fixtures and configuration for security tests."""

from __future__ import annotations

import os

import pytest


def pytest_configure(config):
    """Register security test markers."""
    config.addinivalue_line("markers", "security: Security test (OWASP)")
    config.addinivalue_line("markers", "owasp_a01: OWASP A01 - Broken Access Control")
    config.addinivalue_line("markers", "owasp_a03: OWASP A03 - Injection")
    config.addinivalue_line("markers", "owasp_a06: OWASP A06 - Vulnerable Components")
    config.addinivalue_line("markers", "owasp_a07: OWASP A07 - Cross-Site Scripting")


@pytest.fixture(scope="session")
def security_config():
    """Security test configuration."""
    return {
        "max_login_attempts": 5,
        "lockout_duration_seconds": 300,
        "rate_limit_per_minute": 60,
        "sql_injection_payloads": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users--",
            "'; SELECT pg_sleep(5); --",
        ],
        "xss_payloads": [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
        ],
    }


@pytest.fixture
def log_security_test(request):
    """Log security test execution."""
    test_name = request.node.name
    marker = request.node.get_closest_marker("owasp_a03") or request.node.get_closest_marker("security")
    category = marker.name if marker else "security"

    yield

    print(f"[{category}] {test_name}")
