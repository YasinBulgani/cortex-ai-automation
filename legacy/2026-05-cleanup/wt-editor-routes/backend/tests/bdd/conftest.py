"""BDD test shared fixtures — used by all step definition modules."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def ctx() -> dict:
    """Mutable context dict shared across Given/When/Then steps."""
    return {}


@pytest.fixture()
def api(client: TestClient) -> TestClient:
    return client


@pytest.fixture()
def admin_auth(auth_headers: dict[str, str]) -> dict[str, str]:
    return auth_headers


def unique(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"
