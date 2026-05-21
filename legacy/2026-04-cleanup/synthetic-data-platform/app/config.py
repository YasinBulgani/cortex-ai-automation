"""
Uygulama yapılandırma ayarları.

Pydantic Settings kullanılarak ortam değişkenlerinden veya .env dosyasından yüklenir.
Tüm konfigürasyon değerleri merkezi olarak bu modülde tanımlanır.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Uygulama ayarları — .env dosyasından veya ortam değişkenlerinden okunur.

    Öncelik sırası:
    1. Ortam değişkenleri (en yüksek)
    2. .env dosyası
    3. Varsayılan değerler (en düşük)
    """

    # ── Uygulama Genel Ayarları ──────────────────────────────────────
    APP_NAME: str = "SyntheticBankData"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── Veritabanı Ayarları ──────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "synth_user"
    DB_PASSWORD: str = "synth_pass"
    DB_NAME: str = "synth_bank"

    # Doğrudan DATABASE_URL tanımlamak isterseniz bu alanı kullanın.
    # Boş bırakılırsa yukarıdaki parçalardan otomatik oluşturulur.
    DATABASE_URL: Optional[str] = None

    @property
    def database_url(self) -> str:
        """
        SQLAlchemy bağlantı dizesini döndürür.

        Eğer DATABASE_URL doğrudan tanımlıysa onu kullanır,
        aksi halde parça parça değerlerden oluşturur.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def async_database_url(self) -> str:
        """Asenkron SQLAlchemy bağlantı dizesi (asyncpg driver)."""
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            ).replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://"
            )
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── Dosya Yükleme Ayarları ───────────────────────────────────────
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: list[str] = [".csv", ".sql", ".ddl", ".xlsx", ".json"]

    # ── Faker / Veri Üretim Ayarları ─────────────────────────────────
    FAKER_LOCALE: str = "tr_TR"
    DEFAULT_BATCH_SIZE: int = 1_000
    MAX_BATCH_SIZE: int = 100_000

    # ── LLM / AI Entegrasyon Ayarları ─────────────────────────────────
    LLM_PROVIDER: str = "fallback"       # openai, anthropic, ollama, fallback
    LLM_API_KEY: str = ""                # API anahtarı (OpenAI veya Anthropic)
    LLM_MODEL: str = ""                  # Model adı (ör. gpt-4o-mini, claude-sonnet-4-20250514)
    LLM_ENDPOINT: str = ""               # Ollama endpoint (ör. http://localhost:11434)
    LLM_TEMPERATURE: float = 0.1         # Üretim sıcaklığı (0.0-1.0)
    LLM_MAX_TOKENS: int = 2000           # Maksimum token sayısı

    # ── Loglama Ayarları ─────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )

    # ── Pydantic Settings Konfigürasyonu ─────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=True,
        extra="ignore",
    )


# Uygulama genelinde kullanılacak tekil (singleton) ayar nesnesi
settings = Settings()
