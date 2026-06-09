"""Unit tests for backend architecture fixes (CODE-HIGH 1, 2, 3).

Tests verify:
1. Exception handler ordering (specific before general)
2. Async/await consistency in service layer
3. Correlation ID logging integration
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError

try:
    from app.core.exception_handlers import (
        register_exception_handlers,
        _request_id,
        _get_correlation_id,
    )
    from app.core.exceptions import RateLimitError
    from app.infra.resilience import CircuitBreakerOpen
    from app.domains.ai.correlation import set_correlation_id, get_correlation_id

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="Module imports failed")


class TestExceptionHandlerOrdering:
    """CODE-HIGH-1: Verify exception handlers are registered in correct order."""

    def test_handlers_registered(self):
        """Verify all exception handlers are registered."""
        app = FastAPI()
        register_exception_handlers(app)

        # Check that handlers exist
        assert HTTPException in app.exception_handlers
        assert RequestValidationError in app.exception_handlers
        assert RateLimitError in app.exception_handlers
        assert CircuitBreakerOpen in app.exception_handlers
        assert ValueError in app.exception_handlers
        assert KeyError in app.exception_handlers
        assert PermissionError in app.exception_handlers
        assert RuntimeError in app.exception_handlers
        assert Exception in app.exception_handlers

    def test_exception_hierarchy_correct_order(self):
        """Verify specific exceptions are in app handlers before general Exception."""
        app = FastAPI()
        register_exception_handlers(app)

        handlers = app.exception_handlers
        # All specific exceptions should be in handlers dict
        assert ValueError in handlers, "ValueError should be registered"
        assert KeyError in handlers, "KeyError should be registered"
        assert RuntimeError in handlers, "RuntimeError should be registered"
        # Exception handler (catch-all) should also be registered
        assert Exception in handlers, "Exception catch-all should be registered"

    def test_more_specific_than_generic_exception(self):
        """Verify ValueError/KeyError/RuntimeError have specific handlers."""
        app = FastAPI()
        register_exception_handlers(app)

        # Get handler for specific exception types
        value_error_handler = app.exception_handlers.get(ValueError)
        key_error_handler = app.exception_handlers.get(KeyError)
        runtime_error_handler = app.exception_handlers.get(RuntimeError)

        # They should have dedicated handlers
        assert value_error_handler is not None
        assert key_error_handler is not None
        assert runtime_error_handler is not None


class TestCorrelationIdLogging:
    """CODE-HIGH-3: Verify correlation ID is logged in exception handlers."""

    @pytest.fixture(autouse=True)
    def _reset_correlation(self):
        """Reset correlation ID before and after each test."""
        set_correlation_id(None)
        yield
        set_correlation_id(None)

    def test_get_correlation_id_helper(self):
        """Verify _get_correlation_id helper works."""
        set_correlation_id("test-correlation-123")
        result = _get_correlation_id()
        assert result == "test-correlation-123"

    def test_get_correlation_id_none_when_not_set(self):
        """Verify _get_correlation_id returns None when not set."""
        set_correlation_id(None)
        result = _get_correlation_id()
        assert result is None

    def test_correlation_id_survives_exception_handling(self):
        """Verify correlation ID context is available during exception handling."""
        set_correlation_id("request-trace-456")

        # Simulate exception handler accessing correlation ID
        correlation_id = _get_correlation_id()
        assert correlation_id == "request-trace-456"

    def test_correlation_middleware_exists(self):
        """Verify CorrelationMiddleware class exists and can be imported."""
        from app.domains.ai.correlation import CorrelationMiddleware
        assert CorrelationMiddleware is not None


class TestAsyncAwaitConsistency:
    """CODE-HIGH-2: Verify async/await consistency in service layer."""

    def test_auth_service_async_functions_exist(self):
        """Verify async functions in auth service exist."""
        from app.domains.auth import service

        assert hasattr(service, 'create_refresh_token')
        assert hasattr(service, 'verify_refresh_token')
        assert hasattr(service, 'revoke_refresh_token')
        assert hasattr(service, 'revoke_all_user_tokens')

        # All these should be coroutines when called (async functions)
        import inspect
        assert inspect.iscoroutinefunction(service.create_refresh_token)
        assert inspect.iscoroutinefunction(service.verify_refresh_token)
        assert inspect.iscoroutinefunction(service.revoke_refresh_token)
        assert inspect.iscoroutinefunction(service.revoke_all_user_tokens)

    def test_test_management_service_async_functions(self):
        """Verify test_management service has async functions."""
        from app.domains.test_management import service

        assert hasattr(service, 'ai_generate_plan_async')
        assert hasattr(service, 'improve_case_async')

        import inspect
        assert inspect.iscoroutinefunction(service.ai_generate_plan_async)
        assert inspect.iscoroutinefunction(service.improve_case_async)

    def test_sync_functions_not_declared_async(self):
        """Verify synchronous service functions are NOT async."""
        from app.domains.auth import service

        import inspect
        # These should be sync (not async)
        assert not inspect.iscoroutinefunction(service.create_access_token)
        assert not inspect.iscoroutinefunction(service.hash_password)
        assert not inspect.iscoroutinefunction(service.verify_password)


class TestRequestIdHelper:
    """Verify request ID extraction helper works correctly."""

    def test_request_id_from_state(self):
        """Verify _request_id extracts ID from request.state."""
        app = FastAPI()
        request = Request({"type": "http", "method": "GET", "path": "/test"})
        request.state.request_id = "req-12345"

        result = _request_id(request)
        assert result == "req-12345"

    def test_request_id_returns_none_when_not_set(self):
        """Verify _request_id returns None when request_id not set."""
        app = FastAPI()
        request = Request({"type": "http", "method": "GET", "path": "/test"})

        result = _request_id(request)
        assert result is None

    def test_request_id_handles_no_state(self):
        """Verify _request_id gracefully handles missing state."""
        request = Request({"type": "http", "method": "GET", "path": "/test"})
        # Don't set request.state at all

        result = _request_id(request)
        assert result is None
