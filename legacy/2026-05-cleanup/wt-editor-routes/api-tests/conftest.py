"""Shared pytest fixtures for API tests."""

import pytest

from clients.fastapi_client import FastAPIClient
from clients.engine_client import EngineClient
from helpers.auth_helper import (
    get_authenticated_fastapi_client,
    get_authenticated_engine_client,
    get_unauthenticated_fastapi_client,
    get_unauthenticated_engine_client,
)
from helpers.data_factory import random_project_name


@pytest.fixture(scope="session")
def api() -> FastAPIClient:
    """Authenticated FastAPI client (session-scoped, single login)."""
    return get_authenticated_fastapi_client()


@pytest.fixture(scope="session")
def engine() -> EngineClient:
    """Authenticated Engine client (session-scoped, single login)."""
    return get_authenticated_engine_client()


@pytest.fixture
def api_noauth() -> FastAPIClient:
    """Unauthenticated FastAPI client for negative tests."""
    return get_unauthenticated_fastapi_client()


@pytest.fixture
def engine_noauth() -> EngineClient:
    """Unauthenticated Engine client for negative tests."""
    return get_unauthenticated_engine_client()


@pytest.fixture(scope="session")
def test_project(api: FastAPIClient) -> dict:
    """Create a shared test project for the session."""
    result = api.create_project(random_project_name(), "Otomasyon test projesi")
    assert result["status_code"] == 201, f"Project creation failed: {result}"
    return result["data"]


@pytest.fixture(scope="session")
def project_id(test_project: dict) -> str:
    return test_project["id"]
