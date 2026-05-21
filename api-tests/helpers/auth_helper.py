"""Authentication helpers for test setup."""

from clients.fastapi_client import FastAPIClient
from clients.engine_client import EngineClient
from config.settings import settings


def get_authenticated_fastapi_client() -> FastAPIClient:
    client = FastAPIClient()
    client.login_default_user()
    return client


def get_authenticated_engine_client() -> EngineClient:
    client = EngineClient()
    client.login_default_user()
    return client


def get_unauthenticated_fastapi_client() -> FastAPIClient:
    return FastAPIClient()


def get_unauthenticated_engine_client() -> EngineClient:
    return EngineClient()
