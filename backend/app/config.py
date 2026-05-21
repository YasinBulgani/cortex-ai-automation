"""Uygulama ayarları (ortam değişkenleri)."""

import logging
import os
import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

_INSECURE_JWT_DEFAULT = "change-me-in-production-use-long-random-secret"
_INSECURE_ENGINE_KEY_DEFAULT = "bgts-internal-key-change-me"
_INSECURE_GATEWAY_KEY_DEFAULT = "nexusqa-gateway-internal-key-change-me"
_INSECURE_DATABASE_MARKERS = (
    "localhost",
    "127.0.0.1",
    "sqlite",
    "example.com",
    "change-me",
    "changeme",
    "placeholder",
)
_INSECURE_DATABASE_DEFAULT = "postgresql+psycopg2://twai_user:twai_pass@127.0.0.1:5432/syndata_db"


def _is_production_env() -> bool:
    """`ENV` veya `APP_ENV` değişkeni `production`/`staging` ise True döner."""
    env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").strip().lower()
    return env in {"production", "prod", "staging"}


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
    # "Beni hatırla" seçeneği açıkken kullanılan TTL; standart TTL'den daha uzun.
    access_token_expire_minutes_remember_me: int = 60 * 24 * 7  # 7 gün
    refresh_token_expire_days: int = 7    # 7 gun
    password_reset_token_expire_minutes: int = 15
    allow_self_registration: bool = False

    artifacts_dir: str = "./data/artifacts"
    ai_workflow_artifact_retention_days: int = 30
    rq_queue_name: str = "syndata_jobs"
    ai_rq_queue_name: str = "ai_workflows"
    agents_v2_queue_backend: str = "auto"  # auto | rq | background

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

    # ── Tiered model aliases (OpenAI + Anthropic ikilisi üzerine kurulu) ─
    # smart_model_router.py bu alanlari Tier enum'una cevirir:
    #   MINI    → ucuz/hizli       (gpt-4o-mini)
    #   MID     → dengeli           (gpt-4o)
    #   PREMIUM → karmasik muhakeme (claude-sonnet-4)
    #   LOCAL   → son care fallback (qwen2.5:32b — tüm bulut saglayicilar dustugunde)
    openai_mini_model: str = "gpt-4o-mini"
    openai_mid_model: str = "gpt-4o"
    anthropic_premium_model: str = "claude-sonnet-4-20250514"
    ollama_fallback_model: str = "qwen2.5:32b"

    # Routing stratejisi: cost_optimized | balanced | quality_first
    # - cost_optimized  → mumkun oldugunca MINI; kritik taskler için PREMIUM
    # - balanced (default) → plan-belirli karar matrisi
    # - quality_first   → tüm testler için PREMIUM (pahali; benchmark için)
    ai_routing_mode: str = "balanced"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    ai_provider: str = "ollama"  # "openai" | "anthropic" | "ollama"
    ai_max_context_messages: int = 20
    ai_prompt_registry_enabled: bool = True
    # Enterprise/self-hosted varsayılanı: müşteri verisi dış LLM endpoint'lerine gitmez.
    # OpenAI-uyumlu yerel endpoint kullanmak için OPENAI_BASE_URL localhost/private
    # ağa işaret edebilir; dış sağlayıcılar için AI_LOCAL_ONLY=false gerekir.
    ai_local_only: bool = True

    # ── DSL Semantic Search — Cross-Encoder Reranker ──────────────────
    # Dense retrieval (bge-m3) sonrası cross-encoder ile yeniden sıralama.
    # Türkçe parafraz eşleşmelerini güçlendirir ("formunu aç" ↔ "open_url").
    # Opsiyonel bağımlılık: sentence-transformers. Kurulu değilse reranker
    # sessiz pass-through yapar, arama yolu bozulmaz.
    ai_model_reranker_enabled: bool = False
    ai_model_reranker: str = "seroe/bge-reranker-v2-m3-turkish-triplet"
    ai_model_reranker_top_k_in: int = 20   # retrieval havuzu
    ai_model_reranker_top_k_out: int = 5   # rerank sonrası dönecek adet
    ai_model_reranker_device: str = "cpu"  # "cpu" | "cuda" | "mps"

    # ── Accessibility AI Analyzer ─────────────────────────────────────
    # axe-core/Pa11y/Lighthouse tipi WCAG violation verilerini AI Gateway'e
    # gönderip Türkçe remediation üretir. Opt-in: kapalıyken sessiz no-op.
    ai_accessibility_enabled: bool = False
    ai_accessibility_max_violations: int = 10   # tek çağrıda LLM'e giden max
    ai_accessibility_temperature: float = 0.2

    # ── Ollama (local LLM) ────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"          # Ollama key gerektirmez, placeholder
    # Ajan modelleri — M3 24GB için optimize
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
    # Engine'e yapilan internal istekler için paylasilan anahtar.
    # Production'da ENGINE_INTERNAL_KEY env degiskeni ile override edilmelidir.
    engine_internal_key: str = _INSECURE_ENGINE_KEY_DEFAULT

    # ── AI Gateway (opsiyonel) ────────────────────────────────────────
    ai_gateway_base_url: str = "http://127.0.0.1:8080"
    gateway_internal_key: str = _INSECURE_GATEWAY_KEY_DEFAULT
    ai_gateway_required: bool = False
    ai_budget_preflight_required: bool = False
    ai_structured_output_fail_closed: bool = False

    # ── Stripe (faturalama) ───────────────────────────────────────────
    # Empty values disable the integration; checkout/portal endpoints
    # return 503 until set. Webhook secret is the value Stripe gives you
    # in the dashboard webhook config; rotating it requires a redeploy.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_success_url: str = "http://localhost:3000/admin/billing?status=success"
    stripe_cancel_url: str = "http://localhost:3000/admin/billing?status=cancel"
    stripe_portal_return_url: str = "http://localhost:3000/admin/billing"

    # ── Nexus Repo modülü ─────────────────────────────────────────────
    # Varsayılan kapalı — etkinleştirmek için NEXUS_REPO_ENABLED=true
    nexus_repo_enabled: bool = False

    # ── Rate Limiting ─────────────────────────────────────────────────
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_default: str = "60/minute"

    # ── E-posta ────────────────────────────────────────────────────────
    # EMAIL_BACKEND: "console" | "memory" | "smtp"
    email_backend: str = "console"
    # Şifre sıfırlama linklerinde kullanılacak public URL (frontend)
    # Örn: https://app.example.com — reset_url = f"{url}/reset-password?token=..."
    app_public_url: str = "http://localhost:3000"
    email_from: str = "no-reply@testwright.ai"

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

    # ── Nexus AI Autopilot ────────────────────────────────────────────
    # Sıfır insan müdahalesi omurgası. Varsayılan kapalı başlar; manuel
    # endpoint'ler her zaman kullanılabilir. Ortam değişkeni ile açıldığında
    # arka planda projeleri izler ve güvenli aksiyonları tetikler.
    nexus_autopilot_enabled: bool = False
    nexus_autopilot_background_mode: str = "observe"
    nexus_autopilot_interval_seconds: int = 900
    nexus_autopilot_start_delay_seconds: int = 45
    nexus_autopilot_apply_safe_actions: bool = True
    nexus_autopilot_max_projects_per_tick: int = 20

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """JWT ve engine/gateway internal key guvenlik dogrulamasi.

        NEDEN auto-generate YOK:
        Her restart'ta yeni secret üretmek tüm oturum tokenlarını geçersiz kılar.
        Production'da ilgili env var'lar ile sabit değerler şart.

        Üretim/staging (ENV=production|staging) modunda ve TESTING/CI=false iken
        varsayılan sırlar tespit edilirse uygulama startup'ta ValueError ile durur.
        Test ve CI ortamlarında (TESTING=true veya CI=true) bu kontrol atlanır.
        """
        production = self.is_production_like

        def _fail(var_name: str, example: str) -> None:
            raise ValueError(
                f"\n\n╔══════════════════════════════════════════════════════════╗\n"
                f"║  KRITIK GUVENLIK HATASI: {var_name} ayarlanmamis!\n"
                f"╠══════════════════════════════════════════════════════════╣\n"
                f"║  Üretim/staging ortaminda '{var_name}' env degiskeni\n"
                f"║  ZORUNLUDUR ve yeni bir random deger olmalidir.\n"
                f"║  Ornek:\n"
                f"║    export {var_name}={example}\n"
                f"╚══════════════════════════════════════════════════════════╝\n"
            )

        # JWT secret ------------------------------------------------------
        if self.jwt_secret == _INSECURE_JWT_DEFAULT:
            if production:
                _fail("JWT_SECRET", "$(openssl rand -base64 64)")
            _logger.warning(
                "GUVENLIK UYARISI: Varsayılan JWT_SECRET kullaniliyor. "
                "Yalnizca gelistirme modunda kabul edilebilir."
            )
        elif production and len(self.jwt_secret) < 64:
            raise ValueError(
                "JWT_SECRET en az 64 karakter olmalidir (mevcut: %d karakter)."
                % len(self.jwt_secret)
            )
        elif len(self.jwt_secret) < 32:
            _logger.warning(
                "GUVENLIK UYARISI: JWT_SECRET cok kisa (%d karakter); "
                "en az 64 karakter onerilir.",
                len(self.jwt_secret),
            )

        # Engine internal key --------------------------------------------
        if self.engine_internal_key == _INSECURE_ENGINE_KEY_DEFAULT:
            if production:
                _fail("ENGINE_INTERNAL_KEY", "$(openssl rand -hex 32)")
            _logger.warning(
                "GUVENLIK UYARISI: Varsayılan ENGINE_INTERNAL_KEY kullaniliyor. "
                "Yalnizca gelistirme modunda kabul edilebilir."
            )

        # Gateway internal key --------------------------------------------
        if self.gateway_internal_key == _INSECURE_GATEWAY_KEY_DEFAULT:
            if production:
                _fail("GATEWAY_INTERNAL_KEY", "$(openssl rand -hex 32)")
            _logger.warning(
                "GUVENLIK UYARISI: Varsayılan GATEWAY_INTERNAL_KEY kullaniliyor. "
                "Yalnizca gelistirme modunda kabul edilebilir."
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
        """True if app_env/ENV/APP_ENV is production, prod, or staging."""
        env = self.app_env.strip().lower()
        if not env or env == "development":
            env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or env).strip().lower()
        return env in {"production", "prod", "staging"} and not self.testing and not self.ci

    @property
    def is_test_like(self) -> bool:
        """True if TESTING=true veya CI=true — arka plan işlemleri atlanır."""
        return self.testing or self.ci


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
