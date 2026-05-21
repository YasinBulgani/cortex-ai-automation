"""Uygulama ayarları (ortam değişkenleri)."""

import logging
import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

_INSECURE_JWT_DEFAULT = "change-me-in-production-use-long-random-secret"
_INSECURE_DATABASE_DEFAULT = (
    "postgresql+psycopg2://bgts_user:bgts_pass@127.0.0.1:5432/syndata_db"
)
_INSECURE_ENGINE_KEY_DEFAULT = "bgts-internal-key-change-me"
_INSECURE_DATABASE_MARKERS = (
    "bgts_user",
    "bgts_pass",
    "changeme",
    "<db-user>",
    "<db-password>",
    "<db-name>",
    "change_me_db_",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Sentetik Veri Platformu"
    app_env: str = "development"
    debug: bool = False
    testing: bool = False
    ci: bool = False

    database_url: str = (
        "postgresql+psycopg2://twai_user:twai_pass@127.0.0.1:5432/syndata_db"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"

    # ── JWT Guvenlik ──────────────────────────────────────────────────
    jwt_secret: str = _INSECURE_JWT_DEFAULT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30  # 30 dakika (production guvenligi)
    refresh_token_expire_days: int = 7    # 7 gun
    password_reset_token_expire_minutes: int = 15
    allow_self_registration: bool = False

    artifacts_dir: str = "./data/artifacts"
    rq_queue_name: str = "syndata_jobs"

    cors_origins: str = (
        "http://127.0.0.1:3000,http://localhost:3000,"
        "http://127.0.0.1:3001,http://localhost:3001,"
        "http://127.0.0.1:3100,http://localhost:3100,"
        "http://127.0.0.1:3417,http://localhost:3417,"
        "http://127.0.0.1:5173,http://localhost:5173"
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    ai_provider: str = "openai"  # "openai" | "anthropic" | "ollama"
    allow_provider_fallback: bool = False
    ai_max_context_messages: int = 8

    # ── Ollama (local LLM) ────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"          # Ollama key gerektirmez, placeholder
    # Ajan modelleri — M3 24GB icin optimize
    # qwen2.5:32b → En iyi Turkce + JSON (analiz, senaryo, ogrenme)
    # mistral:latest → Hizli JSON karar (judge, regulation, otomasyon)
    # qwen2.5-coder:7b → Kod uretimi (Playwright, pytest, BDD)
    ollama_model_analyst: str = "qwen2.5:32b"        # Veri analisti + senaryo uretici + self-improving
    ollama_model_fast: str = "mistral:latest"         # Orkestrator + karar ajanlari (JSON native)
    ollama_model_coder: str = "qwen2.5-coder:7b"     # Playwright / pytest kod uretici
    ollama_model_chat: str = "mistral:latest"    # Chat icin hizli model (5-8x hizli)
    ollama_num_ctx_chat: int = 4096              # Chat icin kucuk context window

    n8n_base_url: str = "http://localhost:5678"
    n8n_api_key: str = ""

    # ── Engine / NexusQA ─────────────────────────────────────────────
    engine_base_url: str = "http://127.0.0.1:5001"
    # Engine'e yapilan internal istekler icin paylasilan anahtar.
    # Production'da ENGINE_INTERNAL_KEY env degiskeni ile override edilmelidir.
    engine_internal_key: str = "bgts-internal-key-change-me"

    # ── Rate Limiting ─────────────────────────────────────────────────
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_default: str = "60/minute"

    # ── AI Background Ops Agent ───────────────────────────────────────
    # ops_agent.py: periyodik servis saglik kontrolu + AI ozeti
    ai_background_enabled: bool = False
    ai_background_interval_seconds: int = 900         # 15 dakika
    ai_background_start_delay_seconds: int = 30
    ai_background_request_timeout_seconds: float = 5.0
    ai_background_targets: str = (
        "backend=http://localhost:8000/health,"
        "engine=http://localhost:5001/health"
    )
    ai_background_report_path: str = "./data/reports/ai_ops_latest.md"

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> "Settings":
        """JWT secret guvenlik dogrulamasi.

        NEDEN auto-generate YOK:
        Her restart'ta yeni secret üretmek tüm oturum tokenlarını geçersiz kılar.
        Production'da JWT_SECRET env var ile sabit bir değer şart.
        """
        if self.is_production_like:
            min_length = 64
        else:
            min_length = 32

        if self.jwt_secret == _INSECURE_JWT_DEFAULT:
            if self.is_production_like:
                raise ValueError(
                    "\n\n"
                    "╔══════════════════════════════════════════════════════════╗\n"
                    "║  KRITIK GUVENLIK HATASI: JWT_SECRET ayarlanmamis!       ║\n"
                    "╠══════════════════════════════════════════════════════════╣\n"
                    "║  Uretim ortaminda 'JWT_SECRET' ortam degiskeni           ║\n"
                    "║  ZORUNLUDUR ve en az 64 karakter olmalidir.              ║\n"
                    "║                                                          ║\n"
                    "║  Ornek (Linux/Mac):                                      ║\n"
                    "║    export JWT_SECRET=$(openssl rand -base64 64)          ║\n"
                    "║                                                          ║\n"
                    "║  .env dosyasina ekleyin:                                 ║\n"
                    "║    JWT_SECRET=<openssl rand -base64 64 ile ureteceginiz> ║\n"
                    "╚══════════════════════════════════════════════════════════╝\n"
                )
            else:
                _logger.warning(
                    "GUVENLIK UYARISI: Varsayilan JWT secret kullaniliyor. "
                    "Bu yalnizca development ortaminda kabul edilebilir. "
                    "Uretim icin JWT_SECRET env degiskenini ayarlayin."
                )
        elif len(self.jwt_secret) < min_length:
            if self.is_production_like:
                raise ValueError(
                    "KRITIK: APP_ENV=%s icin JWT_SECRET en az %d karakter olmali. "
                    "openssl rand -base64 64 ile yeni bir secret uretin."
                    % (self.app_env, min_length)
                )
            _logger.warning(
                "GUVENLIK UYARISI: JWT_SECRET cok kisa (%d karakter). "
                "En az 64 karakter kesinlikle oneriliyor.",
                len(self.jwt_secret),
            )
        return self

    @model_validator(mode="after")
    def _validate_database_url(self) -> "Settings":
        """Production/staging ortaminda placeholder DB credential'larini reddet."""
        normalized_url = self.database_url.strip().lower()
        has_insecure_marker = any(
            marker in normalized_url for marker in _INSECURE_DATABASE_MARKERS
        )

        if not has_insecure_marker:
            return self

        if self.is_production_like:
            raise ValueError(
                "KRITIK: APP_ENV=%s icin varsayilan/placeholder DB kimlik bilgileri "
                "kullanilamaz. DATABASE_URL ortam degiskenini guvenli degerlerle "
                "guncelleyin."
                % self.app_env
            )

        if normalized_url == _INSECURE_DATABASE_DEFAULT:
            _logger.warning(
                "GUVENLIK UYARISI: Varsayilan development DATABASE_URL kullaniliyor. "
                "Production/staging icin guvenli DB kullanicisi ve sifresi tanimlayin."
            )
        else:
            _logger.warning(
                "GUVENLIK UYARISI: DATABASE_URL icinde placeholder gorunuyor. "
                "Gercek veritabani kimlik bilgilerini girdiginizden emin olun."
            )
        return self

    @model_validator(mode="after")
    def _validate_engine_internal_key(self) -> "Settings":
        """Engine internal key'nin production'da guvenli olmasini zorunlu kilar."""
        key = self.engine_internal_key.strip()
        too_short = len(key) < 32
        is_default = key == _INSECURE_ENGINE_KEY_DEFAULT

        if self.is_production_like and (not key or is_default or too_short):
            raise ValueError(
                "KRITIK: APP_ENV=%s icin ENGINE_INTERNAL_KEY guvenli olmali "
                "(varsayilan degil ve en az 32 karakter)."
                % self.app_env
            )

        if not self.is_production_like and (is_default or too_short):
            _logger.warning(
                "GUVENLIK UYARISI: ENGINE_INTERNAL_KEY development fallback olarak zayif "
                "veya varsayilan degerde. Production ortaminda guclu bir anahtar kullanin."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production_like(self) -> bool:
        return self.app_env.strip().lower() in {"staging", "production", "prod"}

    @property
    def is_test_like(self) -> bool:
        return self.testing or self.ci or self.app_env.strip().lower() in {"test", "testing", "ci"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
