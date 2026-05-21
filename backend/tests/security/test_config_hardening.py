"""Security regression tests for configuration hardening."""

import pytest
from pydantic import ValidationError

from app.config import Settings, _INSECURE_ENGINE_KEY_DEFAULT, _INSECURE_JWT_DEFAULT


_PROD_KWARGS = {"testing": False, "ci": False}


def test_development_allows_default_jwt_secret_for_local_bootstrap():
    settings = Settings(
        app_env="development",
        jwt_secret=_INSECURE_JWT_DEFAULT,
        database_url="postgresql+psycopg2://bgts_user:bgts_pass@127.0.0.1:5432/syndata_db",
        **_PROD_KWARGS,
    )

    assert settings.jwt_secret == _INSECURE_JWT_DEFAULT


def test_production_requires_minimum_64_char_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET en az 64 karakter"):
        Settings(
            app_env="production",
            jwt_secret="short-secret",
            database_url="postgresql+psycopg2://secure_user:secure_pass@db:5432/app_db",
            engine_internal_key="k" * 48,
            **_PROD_KWARGS,
        )


def test_staging_rejects_placeholder_database_credentials():
    with pytest.raises(ValidationError, match="DB kimlik bilgileri"):
        Settings(
            app_env="staging",
            jwt_secret="a" * 64,
            database_url=(
                "postgresql+psycopg2://CHANGEME_DB_USER:CHANGEME_DB_PASSWORD@"
                "db:5432/CHANGEME_DB_NAME"
            ),
            engine_internal_key="s" * 48,
            **_PROD_KWARGS,
        )


def test_production_accepts_non_placeholder_database_credentials():
    settings = Settings(
        app_env="production",
        jwt_secret="b" * 64,
        database_url="postgresql+psycopg2://secure_user:secure_pass@db:5432/app_db",
        engine_internal_key="c" * 48,
        **_PROD_KWARGS,
    )

    assert settings.is_production_like is True


def test_production_rejects_default_engine_internal_key():
    with pytest.raises(ValidationError, match="ENGINE_INTERNAL_KEY"):
        Settings(
            app_env="production",
            jwt_secret="x" * 64,
            database_url="postgresql+psycopg2://secure_user:secure_pass@db:5432/app_db",
            engine_internal_key=_INSECURE_ENGINE_KEY_DEFAULT,
            **_PROD_KWARGS,
        )
