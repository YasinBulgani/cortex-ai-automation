"""Mobile domain testleri için fixture'lar.

Ana app'in ağır importundan kaçınmak için minimal FastAPI app + mobile router.
"""
from __future__ import annotations

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ortam değişkenlerini test için ayarla — JWT_SECRET ve engine key gerektiren
# validator'ları devre dışı bırak (DEBUG=true → production=False).
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-minimum-sixty-four-chars-mobile-tests-only")
os.environ.setdefault("ENGINE_INTERNAL_KEY", "test-engine-internal-key-32chars")
os.environ.setdefault("GATEWAY_INTERNAL_KEY", "test-gateway-internal-key-32char")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mobile.db")


# Root conftest'teki clear_client_cookies (autouse=True) mobile testlerde
# app.main'i yüklemez; burada no-op olarak override edilir.
@pytest.fixture(autouse=True)
def clear_client_cookies():
    yield


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
    import app.domains.mobile.artifact_store as _a

    _b._broker = None  # type: ignore[attr-defined]
    _o._store = None  # type: ignore[attr-defined]
    _a._store = None  # type: ignore[attr-defined]
    yield
