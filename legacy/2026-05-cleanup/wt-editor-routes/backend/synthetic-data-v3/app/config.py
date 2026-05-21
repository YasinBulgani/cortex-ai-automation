"""
Uygulama ayarları — .env dosyasından yüklenir.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/synthetic_data.db"
    APP_TITLE: str = "TestwrightAI Synthetic Data Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    UPLOAD_DIR: str = "uploads"
    EXPORT_DIR: str = "exports"

    class Config:
        env_file = ".env_v2"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
