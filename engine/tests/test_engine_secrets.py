"""Engine sır varsayılanlarının prod'da reddedildiğini doğrular.

`engine/app.py` production/staging modunda ENGINE_SECRET_KEY ve
ENGINE_INTERNAL_KEY varsayılan string'lerine izin vermemelidir.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("APP_ENV", "ENV", "ENGINE_SECRET_KEY", "ENGINE_INTERNAL_KEY"):
        monkeypatch.delenv(var, raising=False)

    # `.env` import chain'inin monkeypatch'i override etmesini engelle —
    # config.settings içindeki load_dotenv, test izolasyonunu bozar.
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)

    # Modül cache temizliği — ilgili tüm engine modülleri yeniden yüklensin
    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("config.") or mod == "config":
            sys.modules.pop(mod, None)


def _reload_engine_app():
    # engine/app.py modül ismi `app` — re-import tetikle
    if "app" in sys.modules:
        del sys.modules["app"]
    return importlib.import_module("app")


def test_defaults_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError) as exc_info:
        _reload_engine_app()
    assert "ENGINE_SECRET_KEY" in str(exc_info.value)
    assert "ENGINE_INTERNAL_KEY" in str(exc_info.value)


def test_custom_values_pass_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "y" * 32)
    # Import başarılı olmalı
    mod = _reload_engine_app()
    assert mod.INTERNAL_KEY == "y" * 32


def test_defaults_warn_but_pass_in_development(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    caplog.set_level("WARNING")
    mod = _reload_engine_app()
    assert mod.INTERNAL_KEY == "bgts-internal-key-change-me"
    # Bir uyarı bekleniyor
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert any("GÜVENLİK" in r.getMessage() for r in warnings)
