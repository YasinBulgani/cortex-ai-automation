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

import contextlib
import os
from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

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
def mock_db_session() -> MagicMock:
    """MagicMock SQLAlchemy session with standard query chain."""
    session = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = None
    filter_mock.all.return_value = []
    filter_mock.count.return_value = 0
    filter_mock.one_or_none.return_value = None
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = filter_mock
    filter_mock.limit.return_value = filter_mock
    filter_mock.offset.return_value = filter_mock
    query_mock.filter.return_value = filter_mock
    query_mock.filter_by.return_value = filter_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = None
    query_mock.get.return_value = None
    session.query.return_value = query_mock
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    session.flush.return_value = None
    session.refresh.return_value = None
    return session


@pytest.fixture()
def mock_http_client() -> MagicMock:
    """MagicMock httpx.AsyncClient with mocked get/post/put/delete responses."""
    client = MagicMock()

    def _make_response(status_code: int = 200, data: dict | None = None) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.json = MagicMock(return_value=data or {})
        resp.text = ""
        resp.content = b""
        resp.raise_for_status = MagicMock(return_value=None)
        return resp

    default_resp = _make_response()
    client.get = AsyncMock(return_value=default_resp)
    client.post = AsyncMock(return_value=default_resp)
    client.put = AsyncMock(return_value=default_resp)
    client.patch = AsyncMock(return_value=default_resp)
    client.delete = AsyncMock(return_value=default_resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture()
def override_settings():
    """Returns a context manager that temporarily overrides app.config.settings attributes."""
    @contextmanager
    def _override(**kwargs: object) -> Generator[None, None, None]:
        try:
            from app.config import settings
        except ImportError:
            try:
                from app.core.config import settings
            except ImportError:
                pytest.skip("app.config.settings or app.core.config.settings not found")
                return

        original = {k: getattr(settings, k, None) for k in kwargs}
        try:
            for k, v in kwargs.items():
                setattr(settings, k, v)
            yield
        finally:
            for k, v in original.items():
                if v is None:
                    with contextlib.suppress(AttributeError):
                        delattr(settings, k)
                else:
                    setattr(settings, k, v)

    return _override


@pytest.fixture()
def rbac_audit_store():
    """In-memory audit store for RBAC SoD enforcement tests.

    Tries to import AuditStore from app.domains.rbac.policy.  If it is a
    Protocol / abstract base (duck-typed) a simple dict-backed stub is
    returned so pure-unit SoD tests never require the real implementation.
    """
    import inspect

    class _DictAuditStore:
        """Minimal dict-backed AuditStore stub — satisfies duck-typing."""

        def __init__(self) -> None:
            self._records: list[dict] = []

        # --- write -----------------------------------------------------------
        def record(self, *, actor: str, action: str, target: str, **meta: object) -> None:
            self._records.append({"actor": actor, "action": action, "target": target, **meta})

        def append(self, entry: dict) -> None:
            self._records.append(entry)

        # --- read ------------------------------------------------------------
        def all(self) -> list[dict]:
            return list(self._records)

        def filter(self, **criteria: object) -> list[dict]:
            results = self._records
            for key, value in criteria.items():
                results = [r for r in results if r.get(key) == value]
            return results

        # --- housekeeping ----------------------------------------------------
        def clear(self) -> None:
            self._records.clear()

        def __len__(self) -> int:
            return len(self._records)

    try:
        from app.domains.rbac.policy import AuditStore  # type: ignore[attr-defined]

        # If it's a Protocol or ABC without a concrete __init__ that works
        # bare, try to instantiate it; fall back to the stub on any error.
        if inspect.isabstract(AuditStore):
            return _DictAuditStore()
        try:
            return AuditStore()
        except Exception:
            return _DictAuditStore()
    except (ImportError, AttributeError):
        # Module or class not yet present — return the stub so tests can still run.
        return _DictAuditStore()


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
