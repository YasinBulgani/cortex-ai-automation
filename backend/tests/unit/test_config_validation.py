"""Config sır doğrulama testleri.

Varsayılan `change-me` / `bgts-internal-key-change-me` /
`nexusqa-gateway-internal-key-change-me` değerlerinin production ortamında
startup'ta ValueError fırlattığını doğrular. Development modunda yalnızca
uyarı verilir, startup başarılı olur.
"""

from __future__ import annotations

import importlib

import pytest


_PROD_DATABASE_URL = (
    "postgresql+psycopg2://prod_user:s3cr3t@db.prod.internal:5432/neurex_prod"
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Her test için env'i izole et."""
    for var in (
        "ENV",
        "APP_ENV",
        "DEBUG",
        "DATABASE_URL",
        "JWT_SECRET",
        "ENGINE_INTERNAL_KEY",
        "GATEWAY_INTERNAL_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def _load_settings():
    """Ayarları cache'lemeden yeni bir Settings örneği yarat.

    Test izolasyonu için `.env` dosyasını yok say — yalnızca monkeypatch'in
    set ettiği ortam değişkenleri kullanılır.
    """
    from app import config as config_module

    importlib.reload(config_module)
    return config_module.Settings(_env_file=None)


def test_default_secrets_raise_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", _PROD_DATABASE_URL)

    with pytest.raises(ValueError) as exc_info:
        _load_settings()

    assert "JWT_SECRET" in str(exc_info.value)


def test_custom_jwt_but_default_engine_key_fails_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", _PROD_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", "x" * 64)

    with pytest.raises(ValueError) as exc_info:
        _load_settings()

    assert "ENGINE_INTERNAL_KEY" in str(exc_info.value)


def test_all_custom_secrets_pass_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", _PROD_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", "x" * 64)
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "engine-key-" + "y" * 30)
    monkeypatch.setenv("GATEWAY_INTERNAL_KEY", "gateway-key-" + "z" * 30)
    monkeypatch.setenv("DATABASE_URL", "postgresql://prod_user:securepwd@db:5432/nexusqa")

    settings = _load_settings()
    assert settings.jwt_secret == "x" * 64
    assert settings.engine_internal_key.startswith("engine-key-")


def test_default_secrets_warn_but_pass_in_debug(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DEBUG", "true")

    settings = _load_settings()
    assert settings.jwt_secret.startswith("change-me")
    # En az bir güvenlik uyarısı log'lanmış olmalı
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert any("JWT_SECRET" in r.getMessage() for r in warnings)
