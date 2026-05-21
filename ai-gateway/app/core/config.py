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
    # "development" | "staging" | "production" — ENV veya APP_ENV env var'ından okunur.
    ENV: str = "development"
    # Boş bırakılırsa startup'ta HATA verilir — production'da mutlaka .env'den set et.
    INTERNAL_KEY: str = ""
    # Virgülle ayrılmış izin verilen origin'ler. Boşsa sadece localhost'a izin verilir.
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    @property
    def is_production_like(self) -> bool:
        """True ise production/staging — güvenlik kontrolleri sıkı uygulanır."""
        return self.ENV.strip().lower() in {"production", "prod", "staging"}

    # ── AI Sağlayıcı Seçimi ─────────────────────────────────────────────────
    # "vllm"   → vLLM zincirin başına alınır (self-hosted, open-source ilk)
    # "ollama" → Ollama zincirin başına alınır (primary)
    # "auto"   → local-only modda vllm → ollama; cloud açıkken fallback genişler
    AI_PROVIDER: str = "ollama"
    # Enterprise varsayılanı: müşteri verisi cloud sağlayıcılara gitmez.
    AI_LOCAL_ONLY: bool = True

    # ── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/1"
    CACHE_TTL_SECONDS: int = 300          # 5 dakika cache
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_CONCURRENT_REQUESTS: int = 16

    # ── Fallback Zinciri ────────────────────────────────────────────────────
    MAX_RETRIES: int = 2
    RETRY_DELAY_SECONDS: float = 0.5
    REQUEST_TIMEOUT_SECONDS: int = 45

    # ── Groq (llama3-70b — ÜCRETSIZ) ────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_RPM_LIMIT: int = 30
    GROQ_TPM_LIMIT: int = 14400
    GROQ_ENABLED: bool = False

    # ── Gemini (1.5 Flash — ÜCRETSIZ) ───────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_RPM_LIMIT: int = 15
    GEMINI_TPD_LIMIT: int = 1_500_000
    GEMINI_ENABLED: bool = False

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
    OLLAMA_EMBED_MODEL: str = "bge-m3"             # DSL semantic search / RAG embeddings

    # ── vLLM (Self-hosted, açık kaynak — PagedAttention + continuous batch) ─
    # OpenAI-uyumlu API sunucusu. Varsayılan: kapalı (opt-in).
    # Açıldığında PROVIDER_ORDER başına alınır — en hızlı ve en güçlü katman.
    VLLM_ENABLED: bool = False
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    VLLM_API_KEY: str = ""  # vLLM --api-key ile başlatıldıysa doldurulur
    VLLM_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"  # Apache-2.0, çok dilli
    VLLM_TIMEOUT_SECONDS: int = 120

    # ── Token Limitleri ──────────────────────────────────────────────────────
    MAX_INPUT_TOKENS: int = 3000
    MAX_OUTPUT_TOKENS: int = 2000
    CHUNK_SIZE_TOKENS: int = 2000

    @property
    def PROVIDER_ORDER(self) -> list[str]:
        """
        Etkin sağlayıcılardan oluşan fallback sırasını döndürür.

        AI_PROVIDER=vllm   → vLLM zincirin başında (self-hosted, open-source).
        AI_PROVIDER=ollama → Ollama zincirin başında.
        AI_LOCAL_ONLY=true ise cloud sağlayıcılar zincire alınmaz.
        Aksi halde: vllm → groq → gemini → ollama sırası uygulanır.

        Devre dışı bırakılan sağlayıcılar (*_ENABLED=False) listeden çıkarılır.
        vllm varsayılan olarak kapalıdır; opt-in için VLLM_ENABLED=true verin.
        """
        mode = self.AI_PROVIDER.lower()
        if self.AI_LOCAL_ONLY:
            if mode == "vllm":
                candidate = ["vllm", "ollama"]
            elif mode == "ollama":
                candidate = ["ollama", "vllm"]
            else:
                candidate = ["vllm", "ollama"]
        elif mode == "vllm":
            candidate = ["vllm", "groq", "gemini", "ollama"]
        elif mode == "ollama":
            candidate = ["ollama", "vllm", "groq", "gemini"]
        else:
            candidate = ["vllm", "groq", "gemini", "ollama"]

        enabled_map = {
            "vllm": self.VLLM_ENABLED,
            "groq": self.GROQ_ENABLED,
            "gemini": self.GEMINI_ENABLED,
            "ollama": self.OLLAMA_ENABLED,
        }
        return [name for name in candidate if enabled_map.get(name, False)]

    def model_for_task(self, task_type: str) -> str:
        """Task type'a göre doğru Ollama modelini döndür."""
        analyst_tasks = {
            "analyze_document", "generate_test_cases", "suggest_regression", "debug_test",
            # Backend'den gelen ek analiz görevleri
            "test_analysis", "quality_judge", "scenario_generation",
            "accessibility_analysis", "visual_verify", "test_generation",
        }
        coder_tasks = {
            "generate_gherkin", "generate_java_steps", "generate_playwright",
            # Backend'den gelen ek kod görevleri
            "code_generation", "dsl_alias_gen", "dsl_extract",
            "generate_mobile_steps", "mobile_scenario", "test_data_generation",
        }
        nexus_tasks = {"nexus_code_analyze"}
        # LLM Agent görev sınıfları:
        #   llm_agent_plan → hipotez üretimi + sıra planı + bulgu sınıflandırma
        #     JSON güvenilirliği kritik → analyst model (qwen2.5:14b)
        #   llm_agent_think → düşünce + gözlem → kısa metin, hız öncelikli
        #     fast model yeterli (llama3.1:8b / mistral)
        agent_plan_tasks = {"llm_agent_plan", "llm_agent_classify"}
        agent_think_tasks = {"llm_agent_think", "llm_agent_observe", "llm_agent_summary"}
        if task_type in agent_plan_tasks:
            return self.OLLAMA_MODEL_ANALYST
        if task_type in agent_think_tasks:
            return self.OLLAMA_MODEL_FAST
        if task_type in analyst_tasks:
            return self.OLLAMA_MODEL_ANALYST
        if task_type in coder_tasks:
            return self.OLLAMA_MODEL_CODER
        if task_type in nexus_tasks:
            return self.OLLAMA_MODEL_CODER  # qwen2.5-coder — hem kod hem analiz
        return self.OLLAMA_MODEL_FAST

    def temperature_for_task(self, task_type: str) -> float:
        """Task type'a göre optimum temperature döndür.

        Düşük = deterministik (analiz, kod), yüksek = yaratıcı (chat, senaryo).
        """
        temps = {
            "analyze_document":      0.2,
            "generate_test_cases":   0.4,
            "nexus_code_analyze":    0.2,
            "suggest_regression":    0.2,
            "debug_test":            0.2,
            "generate_gherkin":      0.3,
            "generate_java_steps":   0.2,
            "generate_playwright":   0.2,
            "chat":                  0.7,
            # Backend ek task type'ları
            "quality_judge":         0.1,  # Deterministik değerlendirme
            "accessibility_analysis":0.2,
            "code_generation":       0.2,
            "dsl_alias_gen":         0.2,
            "dsl_extract":           0.2,
            "generate_mobile_steps": 0.3,
            "mobile_scenario":       0.4,
            "test_analysis":         0.2,
            "test_generation":       0.4,
            "test_data_generation":  0.3,
            "scenario_generation":   0.5,
            "visual_verify":         0.1,
            "general_stream":        0.7,
        }
        return temps.get(task_type, 0.5)

    def max_tokens_for_task(self, task_type: str) -> int:
        """Task type'a göre optimum max_tokens döndür.

        Geniş analiz görevleri daha fazla çıktı token'ı gerektirir.
        Değerler model context window'larına göre ayarlanmıştır:
          qwen2.5:14b  → 8192 context
          qwen2.5-coder:7b → 8192 context
          llama3.1:8b  → 4096 context
        """
        limits = {
            "analyze_document":      5000,  # Detaylı JSON analiz raporu
            "generate_test_cases":   5000,  # Zengin test case listesi
            "nexus_code_analyze":    6000,  # Tam QA analizi — en uzun çıktı
            "suggest_regression":    4000,  # Regresyon seti JSON
            "debug_test":            3000,  # Kök neden + öneri
            "generate_gherkin":      4000,  # Gherkin feature dosyası
            "generate_java_steps":   4000,  # Java step definitions
            "generate_playwright":   4000,  # Playwright kod bloğu
            "chat":                  2000,  # Genel sohbet — hızlı yanıt
            # Backend ek task type'ları
            "quality_judge":         2000,
            "accessibility_analysis":3000,
            "code_generation":       4000,
            "dsl_alias_gen":         2000,
            "dsl_extract":           3000,
            "generate_mobile_steps": 4000,
            "mobile_scenario":       4000,
            "test_analysis":         3000,
            "test_generation":       5000,
            "test_data_generation":  3000,
            "scenario_generation":   4000,
            "visual_verify":         2000,
            "general_stream":        2000,
        }
        return limits.get(task_type, self.MAX_OUTPUT_TOKENS)


settings = Settings()
