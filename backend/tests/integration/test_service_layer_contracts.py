"""Service layer contract enforcement tests.

Ensures all domain services follow DDD patterns:
- No HTTPException imports (should raise ValueError/KeyError/RuntimeError instead)
- Service files are importable (no syntax errors)
- Every domain directory has the required service.py and router.py files
- Every router.py declares an APIRouter with a prefix

These tests are purely static (AST-based) and do NOT require a running DB
or network connection. They run fast and catch structural regressions early.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent.parent
DOMAINS_DIR = BACKEND_DIR / "app" / "domains"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _domain_dirs() -> list[Path]:
    """Return all non-private domain directories (those with an __init__.py or .py files)."""
    dirs = []
    for p in sorted(DOMAINS_DIR.iterdir()):
        if p.is_dir() and not p.name.startswith("_"):
            dirs.append(p)
    return dirs


def get_service_files() -> list[Path]:
    """Collect all service.py files under domains/."""
    files = []
    for domain_dir in _domain_dirs():
        svc = domain_dir / "service.py"
        if svc.exists():
            files.append(svc)
    return files


def get_router_files() -> list[Path]:
    """Collect all router.py files under domains/."""
    files = []
    for domain_dir in _domain_dirs():
        rtr = domain_dir / "router.py"
        if rtr.exists():
            files.append(rtr)
    return files


def _parse_ast(path: Path) -> ast.Module:
    """Parse a Python file into an AST. Raises SyntaxError on failure."""
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def _has_httpexception_import(tree: ast.Module) -> bool:
    """Return True if the module imports HTTPException from fastapi."""
    for node in ast.walk(tree):
        # from fastapi import HTTPException
        if isinstance(node, ast.ImportFrom):
            if node.module and "fastapi" in node.module:
                names = [alias.name for alias in node.names]
                if "HTTPException" in names:
                    return True
        # import fastapi  (then fastapi.HTTPException usage — rare but cover it)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "fastapi":
                    return True  # conservative: flag whole-module fastapi import too
    return False


def _has_api_router_with_prefix(tree: ast.Module) -> bool:
    """Return True if the module instantiates APIRouter(prefix=...) somewhere."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # APIRouter(...) call
            func = node.func
            is_apirouter = (
                (isinstance(func, ast.Name) and func.id == "APIRouter")
                or (isinstance(func, ast.Attribute) and func.attr == "APIRouter")
            )
            if is_apirouter:
                keywords = {kw.arg for kw in node.keywords}
                if "prefix" in keywords:
                    return True
    return False


# ---------------------------------------------------------------------------
# Parametrize IDs
# ---------------------------------------------------------------------------

_service_files = get_service_files()
_service_ids = [f.parent.name for f in _service_files]

_router_files = get_router_files()
_router_ids = [f.parent.name for f in _router_files]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("svc_path", _service_files, ids=_service_ids)
def test_no_httpexception_in_services(svc_path: Path) -> None:
    """Service files MUST NOT import HTTPException from fastapi.

    Domain services are the core business layer and should remain
    HTTP-agnostic.  They must raise ValueError (→ 400), KeyError (→ 404),
    or RuntimeError (→ 500) which are translated by global exception
    handlers in app/core/exception_handlers.py.
    """
    tree = _parse_ast(svc_path)
    assert not _has_httpexception_import(tree), (
        f"{svc_path.relative_to(BACKEND_DIR)} imports HTTPException from fastapi.\n"
        "Services must be HTTP-agnostic. Use ValueError (400), KeyError (404), "
        "or RuntimeError (500) instead — the global exception handlers convert them."
    )


@pytest.mark.parametrize("svc_path", _service_files, ids=_service_ids)
def test_service_files_have_no_syntax_errors(svc_path: Path) -> None:
    """Every service.py must be parseable Python (no syntax errors).

    A SyntaxError here means the file cannot be imported at all, which
    would break every endpoint in that domain at startup.
    """
    source = svc_path.read_text(encoding="utf-8")
    try:
        compile(source, str(svc_path), "exec")
    except SyntaxError as exc:
        pytest.fail(
            f"SyntaxError in {svc_path.relative_to(BACKEND_DIR)}: {exc}"
        )


@pytest.mark.parametrize("rtr_path", _router_files, ids=_router_ids)
def test_router_files_have_no_syntax_errors(rtr_path: Path) -> None:
    """Every router.py must be parseable Python (no syntax errors)."""
    source = rtr_path.read_text(encoding="utf-8")
    try:
        compile(source, str(rtr_path), "exec")
    except SyntaxError as exc:
        pytest.fail(
            f"SyntaxError in {rtr_path.relative_to(BACKEND_DIR)}: {exc}"
        )


def test_all_domains_have_service_file() -> None:
    """Every domain directory MUST contain a service.py.

    A domain without a service.py suggests the business logic was placed
    directly in the router (an anti-pattern) or is simply missing.

    Known exceptions (domains without service.py by design) are listed
    in ALLOWED_WITHOUT_SERVICE below.
    """
    ALLOWED_WITHOUT_SERVICE: set[str] = set()  # add exceptions here if needed

    missing = []
    for domain_dir in _domain_dirs():
        if domain_dir.name in ALLOWED_WITHOUT_SERVICE:
            continue
        svc = domain_dir / "service.py"
        if not svc.exists():
            missing.append(domain_dir.name)

    assert not missing, (
        f"Domain directories without service.py: {missing}\n"
        "Either add service.py or add the domain name to ALLOWED_WITHOUT_SERVICE."
    )


def test_all_domains_have_router_file() -> None:
    """Every domain directory SHOULD contain a router.py.

    Domains that intentionally have no HTTP API surface are listed in
    ALLOWED_WITHOUT_ROUTER below.
    """
    ALLOWED_WITHOUT_ROUTER: set[str] = {
        "automation_templates",  # provides service only, consumed by other domains
        "migration",             # utility domain, no public API
    }

    missing = []
    for domain_dir in _domain_dirs():
        if domain_dir.name in ALLOWED_WITHOUT_ROUTER:
            continue
        rtr = domain_dir / "router.py"
        if not rtr.exists():
            missing.append(domain_dir.name)

    assert not missing, (
        f"Domain directories without router.py: {missing}\n"
        "Either add router.py or add the domain name to ALLOWED_WITHOUT_ROUTER."
    )


@pytest.mark.parametrize("rtr_path", _router_files, ids=_router_ids)
def test_router_files_have_prefix(rtr_path: Path) -> None:
    """Every router.py MUST declare APIRouter(prefix=...).

    A router without a prefix will merge all its routes under the root
    path, making endpoint discovery and versioning impossible.
    """
    tree = _parse_ast(rtr_path)
    assert _has_api_router_with_prefix(tree), (
        f"{rtr_path.relative_to(BACKEND_DIR)} does not contain "
        "APIRouter(prefix=...). All routers must declare an explicit prefix "
        "so they are correctly registered under /api/v1/<domain>."
    )


# ---------------------------------------------------------------------------
# Bonus: service layer only raises allowed exception types
# ---------------------------------------------------------------------------

def _collect_raised_exception_names(tree: ast.Module) -> set[str]:
    """Return the set of exception *class names* used in raise statements."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc
            # raise SomeName(...)
            if isinstance(exc, ast.Call):
                func = exc.func
                if isinstance(func, ast.Name):
                    names.add(func.id)
                elif isinstance(func, ast.Attribute):
                    names.add(func.attr)
            # raise SomeName
            elif isinstance(exc, ast.Name):
                names.add(exc.id)
            elif isinstance(exc, ast.Attribute):
                names.add(exc.attr)
    return names


# Exceptions that are allowed in service files
_ALLOWED_SERVICE_EXCEPTIONS = {
    # Standard Python exceptions that map to HTTP status codes
    "ValueError",        # → 400 Bad Request
    "KeyError",          # → 404 Not Found
    "RuntimeError",      # → 500 Internal Server Error
    # Other sensible standard exceptions
    "NotImplementedError",
    "TypeError",
    "AttributeError",
    "PermissionError",
    "FileNotFoundError",
    "StopAsyncIteration",
    "StopIteration",
    "GeneratorExit",
    "SystemExit",
    "Exception",         # base class re-raise
    # Allow domain-specific custom exceptions that DON'T wrap HTTP concerns
    # Add project-specific ones here if needed
}

# Well-known HTTP-layer exceptions that MUST NOT appear in service files
_FORBIDDEN_SERVICE_EXCEPTIONS = {
    "HTTPException",
    "WebSocketException",
    "StarletteHTTPException",
}


@pytest.mark.parametrize("svc_path", _service_files, ids=_service_ids)
def test_service_does_not_raise_http_exceptions(svc_path: Path) -> None:
    """Service raise statements must not use HTTP-layer exception classes.

    This is a deeper check than the import test — it catches cases where
    HTTPException is re-exported from a helper module and used without a
    direct import in the service file.
    """
    tree = _parse_ast(svc_path)
    raised = _collect_raised_exception_names(tree)
    forbidden_used = raised & _FORBIDDEN_SERVICE_EXCEPTIONS
    assert not forbidden_used, (
        f"{svc_path.relative_to(BACKEND_DIR)} raises HTTP-layer exceptions: "
        f"{forbidden_used}. Replace with ValueError / KeyError / RuntimeError."
    )
