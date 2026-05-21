"""Mobile domain testleri için fixture'lar.

Ana app'in ağır importundan kaçınmak için minimal FastAPI app + mobile router.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def mobile_app() -> FastAPI:
    """Sadece mobile router ile minimal FastAPI app."""
    from app.domains.mobile.router import router as mobile_router

    app = FastAPI(title="mobile-test")
    app.include_router(mobile_router, prefix="/api/v1")
    return app


@pytest.fixture()
def mobile_client(mobile_app: FastAPI) -> TestClient:
    return TestClient(mobile_app)


@pytest.fixture(autouse=True)
def _reset_mobile_state():
    """Her testten önce broker + session store'u sıfırla."""
    import app.domains.mobile.device_broker as _b
    import app.domains.mobile.orchestrator as _o

    _b._broker = None  # type: ignore[attr-defined]
    _o._store = None  # type: ignore[attr-defined]
    yield
