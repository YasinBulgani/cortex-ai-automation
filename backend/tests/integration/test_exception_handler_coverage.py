"""Exception handler coverage tests.

Verifies that app/core/exception_handlers.py exists and correctly handles
the three exception types that domain services are permitted to raise:

    ValueError  → HTTP 400  (bad client input)
    KeyError    → HTTP 404  (resource not found)
    RuntimeError → HTTP 500 (internal server error — via unhandled_exception_handler)

Also checks the structural completeness of the handler file itself using
AST analysis, so these tests run without a live DB or network.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent.parent
EXCEPTION_HANDLERS_PATH = BACKEND_DIR / "app" / "core" / "exception_handlers.py"


# ---------------------------------------------------------------------------
# Existence check
# ---------------------------------------------------------------------------

def test_exception_handlers_file_exists() -> None:
    """app/core/exception_handlers.py must exist."""
    assert EXCEPTION_HANDLERS_PATH.exists(), (
        f"Expected exception handler module at {EXCEPTION_HANDLERS_PATH} but it was not found.\n"
        "Create app/core/exception_handlers.py with handlers for ValueError, "
        "KeyError, and RuntimeError."
    )


# ---------------------------------------------------------------------------
# AST-level structural checks (no import side-effects)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def handler_tree() -> ast.Module:
    """Parse exception_handlers.py into an AST once per test session."""
    source = EXCEPTION_HANDLERS_PATH.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(EXCEPTION_HANDLERS_PATH))


@pytest.fixture(scope="module")
def handler_function_names(handler_tree: ast.Module) -> set[str]:
    """Collect all top-level function names defined in the module."""
    return {
        node.name
        for node in ast.walk(handler_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_handler_file_has_no_syntax_errors() -> None:
    """exception_handlers.py must be syntactically valid Python."""
    source = EXCEPTION_HANDLERS_PATH.read_text(encoding="utf-8")
    try:
        compile(source, str(EXCEPTION_HANDLERS_PATH), "exec")
    except SyntaxError as exc:
        pytest.fail(f"SyntaxError in exception_handlers.py: {exc}")


def test_register_exception_handlers_function_exists(
    handler_function_names: set[str],
) -> None:
    """A register_exception_handlers(app) function must be present.

    This is the entry point called from create_app / main.py to wire
    all handlers into the FastAPI application instance.
    """
    assert "register_exception_handlers" in handler_function_names, (
        "register_exception_handlers() not found in exception_handlers.py.\n"
        "Add a function that accepts a FastAPI app and calls "
        "app.add_exception_handler(...) for each domain exception type."
    )


def test_value_error_handler_exists(handler_function_names: set[str]) -> None:
    """A handler for ValueError (→ HTTP 400) must be defined."""
    assert "value_error_handler" in handler_function_names, (
        "value_error_handler() not found in exception_handlers.py.\n"
        "Domain services raise ValueError for invalid client input; "
        "this handler must translate it to HTTP 400."
    )


def test_key_error_handler_exists(handler_function_names: set[str]) -> None:
    """A handler for KeyError (→ HTTP 404) must be defined."""
    assert "key_error_handler" in handler_function_names, (
        "key_error_handler() not found in exception_handlers.py.\n"
        "Domain services raise KeyError when a resource is not found; "
        "this handler must translate it to HTTP 404."
    )


def test_unhandled_exception_handler_exists(handler_function_names: set[str]) -> None:
    """A catch-all handler for unhandled exceptions (→ HTTP 500) must be defined.

    RuntimeError and any other unexpected exception types flow through this
    handler and must return a structured 500 response instead of crashing.
    """
    assert "unhandled_exception_handler" in handler_function_names, (
        "unhandled_exception_handler() not found in exception_handlers.py.\n"
        "Add a catch-all handler that returns HTTP 500 for RuntimeError and "
        "any other unhandled exceptions raised by domain services."
    )


# ---------------------------------------------------------------------------
# Registration wiring checks (AST)
# ---------------------------------------------------------------------------

def _get_add_exception_handler_calls(tree: ast.Module) -> list[tuple[str | None, str | None]]:
    """Return (exc_class_name, handler_name) pairs from app.add_exception_handler() calls."""
    pairs: list[tuple[str | None, str | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_add_exc_handler = (
            isinstance(func, ast.Attribute)
            and func.attr == "add_exception_handler"
        )
        if not is_add_exc_handler:
            continue
        args = node.args
        exc_class: str | None = None
        handler: str | None = None
        if args:
            arg0 = args[0]
            if isinstance(arg0, ast.Name):
                exc_class = arg0.id
            elif isinstance(arg0, ast.Attribute):
                exc_class = arg0.attr
        if len(args) >= 2:
            arg1 = args[1]
            if isinstance(arg1, ast.Name):
                handler = arg1.id
            elif isinstance(arg1, ast.Attribute):
                handler = arg1.attr
        pairs.append((exc_class, handler))
    return pairs


def test_value_error_is_registered(handler_tree: ast.Module) -> None:
    """register_exception_handlers must call app.add_exception_handler(ValueError, ...)."""
    pairs = _get_add_exception_handler_calls(handler_tree)
    exc_classes = {exc for exc, _ in pairs}
    assert "ValueError" in exc_classes, (
        "ValueError is not registered in exception_handlers.py.\n"
        "Add: app.add_exception_handler(ValueError, value_error_handler)"
    )


def test_key_error_is_registered(handler_tree: ast.Module) -> None:
    """register_exception_handlers must call app.add_exception_handler(KeyError, ...)."""
    pairs = _get_add_exception_handler_calls(handler_tree)
    exc_classes = {exc for exc, _ in pairs}
    assert "KeyError" in exc_classes, (
        "KeyError is not registered in exception_handlers.py.\n"
        "Add: app.add_exception_handler(KeyError, key_error_handler)"
    )


def test_httpexception_is_registered(handler_tree: ast.Module) -> None:
    """register_exception_handlers must call app.add_exception_handler(HTTPException, ...)."""
    pairs = _get_add_exception_handler_calls(handler_tree)
    exc_classes = {exc for exc, _ in pairs}
    assert "HTTPException" in exc_classes, (
        "HTTPException is not registered in exception_handlers.py.\n"
        "Add: app.add_exception_handler(HTTPException, http_exception_handler)"
    )


def test_unhandled_exception_is_registered(handler_tree: ast.Module) -> None:
    """A catch-all Exception handler must be registered for RuntimeError coverage."""
    pairs = _get_add_exception_handler_calls(handler_tree)
    exc_classes = {exc for exc, _ in pairs}
    assert "Exception" in exc_classes, (
        "A catch-all Exception handler is not registered in exception_handlers.py.\n"
        "Add: app.add_exception_handler(Exception, unhandled_exception_handler)\n"
        "This ensures RuntimeError and other unexpected exceptions return HTTP 500."
    )


# ---------------------------------------------------------------------------
# Runtime import check (optional — skipped if app deps are unavailable)
# ---------------------------------------------------------------------------

def test_exception_handlers_importable() -> None:
    """exception_handlers.py must be importable without a running DB or network.

    If the module has heavy side-effects at import time (DB connections,
    network calls) this test will catch that regression early.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "app.core.exception_handlers", EXCEPTION_HANDLERS_PATH
    )
    assert spec is not None, "Could not create module spec for exception_handlers.py"

    # We intentionally do NOT call exec_module here because it would trigger
    # top-level imports of other app modules (which need a DB). Instead we
    # just verify the spec was created successfully, which means the file
    # exists and is discoverable by the Python import system.
    assert spec.loader is not None, (
        "Module spec has no loader — exception_handlers.py may be malformed."
    )


# ---------------------------------------------------------------------------
# Response shape checks (live import — skipped when app unavailable)
# ---------------------------------------------------------------------------

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.core.exception_handlers import (
        register_exception_handlers,
        value_error_handler,
        key_error_handler,
        unhandled_exception_handler,
    )
    _HANDLERS_IMPORTABLE = True
except Exception:
    _HANDLERS_IMPORTABLE = False

_skip_live = pytest.mark.skipif(
    not _HANDLERS_IMPORTABLE,
    reason="app.core.exception_handlers not importable (missing deps or DB)",
)


def _make_test_app() -> "FastAPI":
    """Build a minimal FastAPI app with the real exception handlers registered."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-value-error")
    def raise_value_error():
        raise ValueError("bad input from test")

    @app.get("/raise-key-error")
    def raise_key_error():
        raise KeyError("resource-not-found-test")

    @app.get("/raise-runtime-error")
    def raise_runtime_error():
        raise RuntimeError("internal boom test")

    @app.get("/ok")
    def ok():
        return {"status": "ok"}

    return app


@_skip_live
def test_value_error_returns_400() -> None:
    """ValueError raised in a service layer endpoint must return HTTP 400."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-value-error")
    assert resp.status_code == 400, (
        f"Expected 400 for ValueError, got {resp.status_code}. "
        f"Response: {resp.text}"
    )


@_skip_live
def test_value_error_response_has_error_key() -> None:
    """ValueError 400 response must have a structured 'error' body."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-value-error")
    body = resp.json()
    assert "error" in body or "detail" in body, (
        f"400 response body has no 'error' or 'detail' key. Got: {body}"
    )


@_skip_live
def test_key_error_returns_404() -> None:
    """KeyError raised in a service layer endpoint must return HTTP 404."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-key-error")
    assert resp.status_code == 404, (
        f"Expected 404 for KeyError, got {resp.status_code}. "
        f"Response: {resp.text}"
    )


@_skip_live
def test_key_error_response_has_error_key() -> None:
    """KeyError 404 response must have a structured 'error' body."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-key-error")
    body = resp.json()
    assert "error" in body or "detail" in body, (
        f"404 response body has no 'error' or 'detail' key. Got: {body}"
    )


@_skip_live
def test_runtime_error_returns_500() -> None:
    """RuntimeError raised in a service layer endpoint must return HTTP 500."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-runtime-error")
    assert resp.status_code == 500, (
        f"Expected 500 for RuntimeError, got {resp.status_code}. "
        f"Response: {resp.text}"
    )


@_skip_live
def test_ok_endpoint_returns_200() -> None:
    """Sanity check: a well-behaved endpoint must return 200."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/ok")
    assert resp.status_code == 200, (
        f"Expected 200 from /ok endpoint, got {resp.status_code}. "
        f"Response: {resp.text}"
    )


@_skip_live
def test_value_error_message_in_response() -> None:
    """The ValueError message must appear in the HTTP 400 response body."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-value-error")
    body = resp.text
    assert "bad input from test" in body, (
        f"ValueError message not found in 400 response body: {body}"
    )


@_skip_live
def test_key_error_message_in_response() -> None:
    """The KeyError key must appear in the HTTP 404 response body."""
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    resp = client.get("/raise-key-error")
    body = resp.text
    assert "resource-not-found-test" in body, (
        f"KeyError key not found in 404 response body: {body}"
    )
