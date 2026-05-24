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


@pytest.fixture()
def feature_flags_svc():
    """FeatureFlags service'ini döner — unit testlere açık erişim (P1 #41).

    test_ai_governance.py, test_ai_enhancements.py vb. inline
    ``try/except ImportError: skip`` yerine bu fixture'ı kullanabilir.
    Import başarısız olursa testi açıkça fail et, sessizce atla.
    """
    from app.domains.feature_flags.service import feature_flags
    from app.domains.feature_flags.schemas import FlagUpdate
    return feature_flags, FlagUpdate


@pytest.fixture()
def feature_flags():
    """FeatureFlags service singleton — tests that call fixture.set_flag(...).

    Alias of feature_flags_svc that returns only the service (not the tuple),
    matching the call pattern used in test_ai_governance.py, test_ai_enhancements.py,
    test_ai_observability.py, test_ai_safety.py, test_smart_model_router.py.
    """
    from app.domains.feature_flags.service import feature_flags as svc
    return svc
