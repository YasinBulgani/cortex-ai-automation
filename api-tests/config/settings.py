import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.test"))


class Settings:
    FASTAPI_BASE_URL: str = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
    ENGINE_BASE_URL: str = os.getenv("ENGINE_BASE_URL", "http://localhost:5001")
    TEST_USER_EMAIL: str = os.getenv("TEST_USER_EMAIL", "test@bgts.com")
    TEST_USER_PASSWORD: str = os.getenv("TEST_USER_PASSWORD", "test123")
    ADMIN_USER_EMAIL: str = os.getenv("ADMIN_USER_EMAIL", "admin@bgts.com")
    ADMIN_USER_PASSWORD: str = os.getenv("ADMIN_USER_PASSWORD", "admin123")
    REQUEST_TIMEOUT: float = 30.0


settings = Settings()
