"""
Uygulama ayarları — .env dosyasından yüklenir.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/synthetic_data_v2.db"
    APP_TITLE: str = "TestwrightAI Synthetic Data Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    UPLOAD_DIR: str = "/tmp/uploads"
    EXPORT_DIR: str = "/tmp/exports"

    class Config:
        env_file = "env_v2.env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
