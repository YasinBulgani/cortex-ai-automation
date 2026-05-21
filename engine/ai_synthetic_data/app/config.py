from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TestwrightAI Synthetic Data Platform"
    app_version: str = "2.0.0"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://ai_user:ai_password@127.0.0.1:5432/synthetic_db"

    external_db_url: str = ""
    sample_size: int = 5000
    kde_bandwidth: str = "scott"
    max_gmm_components: int = 5
    default_row_count: int = 1000
    dp_epsilon: float = 3.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings():
    return Settings()
