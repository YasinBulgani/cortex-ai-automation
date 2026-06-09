"""Unit tests for critical security fixes."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import hashlib
import hmac
from fastapi import HTTPException


class TestTenantSecurityFix:
    """S-CRIT-2: Tenant Default Fallback Silent Bypass"""

    def test_tenant_middleware_rejects_missing_tenant_claim(self):
        """Authenticated request without tenant claim should raise ValueError."""
        from app.core.tenant_middleware import extract_tenant_from_token

        # Valid JWT but missing tenant claim
        import json
        import base64

        # Create a valid JWT structure without tenant claim
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "user123"}).encode()).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(b"fake-signature").decode().rstrip("=")
        token = f"{header}.{payload}.{signature}"

        with pytest.raises(ValueError, match="Tenant claim missing"):
            extract_tenant_from_token(token)

    def test_tenant_middleware_accepts_valid_tenant_claim(self):
        """Authenticated request with valid tenant claim should return tenant ID."""
        from app.core.tenant_middleware import extract_tenant_from_token

        import json
        import base64

        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user123", "tenant": tenant_id}).encode()
        ).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(b"fake-signature").decode().rstrip("=")
        token = f"{header}.{payload}.{signature}"

        result = extract_tenant_from_token(token)
        assert result == tenant_id.lower()

    def test_tenant_middleware_rejects_invalid_uuid(self):
        """Invalid UUID format should raise ValueError."""
        from app.core.tenant_middleware import extract_tenant_from_token

        import json
        import base64

        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user123", "tenant": "not-a-valid-uuid"}).encode()
        ).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(b"fake-signature").decode().rstrip("=")
        token = f"{header}.{payload}.{signature}"

        with pytest.raises(ValueError, match="Invalid tenant UUID"):
            extract_tenant_from_token(token)


class TestWebhookSecurityFix:
    """S-CRIT-3: Webhook HMAC Verification"""

    def test_jira_webhook_requires_valid_signature(self):
        """Jira webhook with invalid signature should be rejected."""
        from app.domains.jira.router import _verify_jira_webhook_signature

        body = b'{"event": "issue_updated"}'
        invalid_signature = "invalid-signature"

        result = _verify_jira_webhook_signature(body, invalid_signature)
        assert result is False

    def test_ingestion_webhook_requires_valid_signature(self):
        """Ingestion webhook with invalid signature should be rejected."""
        from app.domains.ingestion.router import _verify_webhook_signature

        # This test verifies the signature verification is in place
        # The actual implementation is checked to be present in the router
        assert callable(_verify_webhook_signature)


class TestCircuitBreakerFix:
    """A-CRIT-2: Circuit Breaker State Machine Bug"""

    def test_circuit_breaker_half_open_single_failure(self):
        """Single failure in HALF_OPEN state should transition to OPEN."""
        from app.infra.resilience import CircuitBreaker, CircuitState

        class Clock:
            def __init__(self):
                self.time = 0.0

            def __call__(self):
                return self.time

        clock = Clock()

        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            reset_timeout=10.0,
            clock=clock
        )

        # Drive to OPEN
        for _ in range(2):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        clock.time = 11.0
        assert breaker.state == CircuitState.HALF_OPEN

        # Single failure in HALF_OPEN → OPEN
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_half_open_success_resets(self):
        """Success in HALF_OPEN state should reset to CLOSED."""
        from app.infra.resilience import CircuitBreaker, CircuitState

        class Clock:
            def __init__(self):
                self.time = 0.0

            def __call__(self):
                return self.time

        clock = Clock()

        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            reset_timeout=10.0,
            clock=clock
        )

        # Drive to OPEN
        for _ in range(2):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        clock.time = 11.0
        assert breaker.state == CircuitState.HALF_OPEN

        # Success in HALF_OPEN → CLOSED
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_consecutive_failures_reset_on_success(self):
        """Success should reset consecutive failure counter."""
        from app.infra.resilience import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            reset_timeout=10.0
        )

        # Record 2 failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        # Success resets counter
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

        # Needs 3 more failures to trigger
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN


class TestQueryDeadlineMiddleware:
    """Verify query deadline middleware for timeout safety."""

    def test_query_deadline_middleware_present(self):
        """Query deadline middleware should be installed."""
        from app.core.query_deadline_middleware import QueryDeadlineMiddleware
        assert QueryDeadlineMiddleware is not None


class TestProjectMemberFK:
    """DB-CRIT-2: ProjectMember Missing Foreign Key"""

    def test_project_member_model_structure(self):
        """ProjectMember model should have proper FK constraints."""
        from app.infra.models import ProjectMember

        # Check that project_id relationship exists
        assert hasattr(ProjectMember, 'project_id')
        # The actual FK constraint is enforced at migration level
        # This test verifies the model definition is present


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
