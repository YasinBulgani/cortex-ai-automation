"""
Nexus QA — AI Gateway Konfigürasyonu
Tüm AI sağlayıcı ayarları ve fallback zinciri burada tanımlanır.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Servis ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Nexus QA AI Gateway"
    APP_VERSION: str = "1.0.0"
    PORT: int = 8080
    DEBUG: bool = False
    INTERNAL_KEY: str = "nexusqa-gateway-internal-key-change-me"

    # ── AI Sağlayıcı Seçimi ─────────────────────────────────────────────────
    # "vllm"   → vLLM zincirin başına alınır (self-hosted, open-source ilk)
    # "ollama" → Ollama zincirin başına alınır (primary)
    # "auto"   → (vllm →) groq → gemini → ollama (→ g4f opsiyonel) sırasıyla
    AI_PROVIDER: str = "auto"

    # ── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/1"
    CACHE_TTL_SECONDS: int = 300          # 5 dakika cache
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Fallback Zinciri ────────────────────────────────────────────────────
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 1.0
    REQUEST_TIMEOUT_SECONDS: int = 60

    # ── Groq (llama3-70b — ÜCRETSIZ) ────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_RPM_LIMIT: int = 30
    GROQ_TPM_LIMIT: int = 14400
    GROQ_ENABLED: bool = True

    # ── Gemini (1.5 Flash — ÜCRETSIZ) ───────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_RPM_LIMIT: int = 15
    GEMINI_TPD_LIMIT: int = 1_500_000
    GEMINI_ENABLED: bool = True

    # ── Ollama (Local — SINIRSIZ) ────────────────────────────────────────────
    # OLLAMA_BASE_URL: OpenAI-compat endpoint (örn. http://host.docker.internal:11434/v1)
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434/v1"
    OLLAMA_API_KEY: str = "ollama"         # Ollama OpenAI-compat API için gerekli (değer önemsiz)
    OLLAMA_ENABLED: bool = True

    # Genel fallback model
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_FALLBACK_MODEL: str = "mistral"

    # Göreve özel modeller — .env'den okunur
    OLLAMA_MODEL_ANALYST: str = "qwen2.5:14b"    # Analiz, test case üretimi, debug
    OLLAMA_MODEL_FAST: str = "llama3.1:8b"        # Sohbet, hızlı yanıtlar
    OLLAMA_MODEL_CODER: str = "qwen2.5-coder:7b"  # Gherkin, Java, Playwright kod üretimi

    # ── g4f (Fallback — API key gerekmez, GÜVENİLMEZ) ───────────────────────
    # Resmi olmayan bir istemci — prod için kapalıdır. Sadece G4F_ENABLED=true
    # ile opt-in edildiğinde fallback zincirine dahil edilir.
    G4F_MODEL: str = "gpt-3.5-turbo"
    G4F_ENABLED: bool = False

    # ── vLLM (Self-hosted, açık kaynak — PagedAttention + continuous batch) ─
    # OpenAI-uyumlu API sunucusu. Varsayılan: kapalı (opt-in).
    # Açıldığında PROVIDER_ORDER başına alınır — en hızlı ve en güçlü katman.
    VLLM_ENABLED: bool = False
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    VLLM_API_KEY: str = ""  # vLLM --api-key ile başlatıldıysa doldurulur
    VLLM_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"  # Apache-2.0, çok dilli
    VLLM_TIMEOUT_SECONDS: int = 120

    # ── Token Limitleri ──────────────────────────────────────────────────────
    MAX_INPUT_TOKENS: int = 4000
    MAX_OUTPUT_TOKENS: int = 4000
    CHUNK_SIZE_TOKENS: int = 3000

    @property
    def PROVIDER_ORDER(self) -> list[str]:
        """
        Etkin sağlayıcılardan oluşan fallback sırasını döndürür.

        AI_PROVIDER=vllm   → vLLM zincirin başında (self-hosted, open-source).
        AI_PROVIDER=ollama → Ollama zincirin başında.
        Aksi halde ve VLLM_ENABLED ise: vllm → groq → gemini → ollama → (g4f ops.)
        Aksi halde VLLM kapalıysa:       groq → gemini → ollama → (g4f opsiyonel)

        Devre dışı bırakılan sağlayıcılar (*_ENABLED=False) listeden çıkarılır.
        g4f ve vllm varsayılan olarak kapalıdır; opt-in için *_ENABLED=true verin.
        """
        mode = self.AI_PROVIDER.lower()
        if mode == "vllm":
            candidate = ["vllm", "groq", "gemini", "ollama", "g4f"]
        elif mode == "ollama":
            candidate = ["ollama", "vllm", "groq", "gemini", "g4f"]
        else:
            candidate = ["vllm", "groq", "gemini", "ollama", "g4f"]

        enabled_map = {
            "vllm": self.VLLM_ENABLED,
            "groq": self.GROQ_ENABLED,
            "gemini": self.GEMINI_ENABLED,
            "ollama": self.OLLAMA_ENABLED,
            "g4f": self.G4F_ENABLED,
        }
        return [name for name in candidate if enabled_map.get(name, False)]

    def model_for_task(self, task_type: str) -> str:
        """Task type'a göre doğru Ollama modelini döndür."""
        analyst_tasks = {"analyze_document", "generate_test_cases", "suggest_regression", "debug_test"}
        coder_tasks = {"generate_gherkin", "generate_java_steps", "generate_playwright"}
        if task_type in analyst_tasks:
            return self.OLLAMA_MODEL_ANALYST
        if task_type in coder_tasks:
            return self.OLLAMA_MODEL_CODER
        return self.OLLAMA_MODEL_FAST


settings = Settings()
