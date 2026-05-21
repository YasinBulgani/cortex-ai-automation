"""Pure unit tests için parent conftest override'ı.

tests/conftest.py, autouse ``clear_client_cookies`` fixture'ı ile her
testte ``app.main`` import'unu tetikler. Bu, a11y/dsl/yaml gibi saf
birim testleri için gereksiz — ve test branch'inde main.py kırık olduğu
durumlarda bu birim testlerini de patlatır.

Bu conftest, unit klasörü için ``clear_client_cookies``'i no-op'a indirger.
API/integration testleri farklı klasörlerde, onlar parent conftest'in
gerçek sürümünü kullanır.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def clear_client_cookies():
    """Unit testler TestClient/app.main gerektirmez — no-op override."""
    yield


@pytest.fixture(autouse=True)
def _unit_gateway_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit testler gerçek gateway key gerektirmez — stub değer."""
    monkeypatch.setenv("GATEWAY_INTERNAL_KEY", "unit-test-gateway-key")
