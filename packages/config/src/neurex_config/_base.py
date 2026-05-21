"""Base settings shared across all Neurex QA Python services."""

from __future__ import annotations

import logging
import os
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_JWT_DEFAULT = "change-me-in-production-use-long-random-secret"
_INSECURE_DB_MARKERS = ("localhost", "127.0.0.1", "sqlite", "change-me", "placeholder", "example.com")


class BaseServiceSettings(BaseSettings):
    """Shared base for all Neurex QA service settings.

    Service-specific settings classes extend this and add their own fields.
    Common fields (app_env, debug, database_url, redis_url, jwt_secret, otel) are here.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Identity ──────────────────────────────────────────────────────
    service_name: str = "neurex-service"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    testing: bool = False
    ci: bool = False

    # ── Database ──────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://twai_user:twai_pass@127.0.0.1:5432/syndata_db"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────
    jwt_secret: str = _INSECURE_JWT_DEFAULT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── OTel ─────────────────────────────────────────────────────────
    otel_endpoint: str = ""
    otel_disabled: bool = False

    # ── CORS ──────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def is_production_like(self) -> bool:
        return self.app_env in ("production", "staging")

    @property
    def is_test_like(self) -> bool:
        return self.app_env == "test" or self.testing or self.ci

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "BaseServiceSettings":
        if not self.is_production_like:
            return self
        errors: list[str] = []
        if self.jwt_secret == _INSECURE_JWT_DEFAULT:
            errors.append("JWT_SECRET is default — must be changed in production")
        for marker in _INSECURE_DB_MARKERS:
            if marker in self.database_url:
                errors.append(f"DATABASE_URL contains '{marker}' — not safe for production")
                break
        if errors:
            raise ValueError(f"Insecure settings in {self.app_env}: " + "; ".join(errors))
        return self

    @field_validator("app_env", mode="before")
    @classmethod
    def _coerce_app_env(cls, v: str) -> str:
        mapping = {"prod": "production", "dev": "development", "ci": "test"}
        return mapping.get(str(v).lower(), str(v).lower())
