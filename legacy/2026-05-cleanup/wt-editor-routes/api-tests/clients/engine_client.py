"""Flask engine client with session-based auth."""

import httpx

from clients.base_client import BaseClient
from config.constants import EnginePaths
from config.settings import settings


class EngineClient(BaseClient):
    def __init__(self):
        super().__init__(settings.ENGINE_BASE_URL)

    def login(self, email: str, password: str) -> dict:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.post(
                self._url(EnginePaths.AUTH_LOGIN),
                json={"email": email, "password": password},
            )
            if resp.status_code == 200:
                self.set_session_cookies(dict(resp.cookies))
            return {"status_code": resp.status_code, "data": resp.json()}

    def login_default_user(self) -> dict:
        return self.login(settings.TEST_USER_EMAIL, settings.TEST_USER_PASSWORD)

    def register(self, email: str, password: str) -> dict:
        resp = self.post(EnginePaths.AUTH_REGISTER, json={"email": email, "password": password})
        return {"status_code": resp.status_code, "data": resp.json()}

    def logout(self) -> dict:
        resp = self.post(EnginePaths.AUTH_LOGOUT)
        return {"status_code": resp.status_code, "data": resp.json()}

    def get_settings(self) -> dict:
        resp = self.get(EnginePaths.SETTINGS)
        return {"status_code": resp.status_code, "data": resp.json()}

    def get_features(self) -> dict:
        resp = self.get(EnginePaths.FEATURES)
        return {"status_code": resp.status_code, "data": resp.json()}

    def get_health(self) -> dict:
        resp = self.get(EnginePaths.HEALTH)
        return {"status_code": resp.status_code, "data": resp.json()}
