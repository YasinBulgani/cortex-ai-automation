"""
helpers/api_client.py — TestwrightAI Platform REST API istemcisi.

pytest-bdd adimlarinda kullanilmak uzere tasarlanmis,
oturum yonetimi ve CRUD kisayollari iceren hafif HTTP sarmalayici.
"""
from __future__ import annotations

import httpx
from typing import Any


class APIClient:
    """TestwrightAI FastAPI backend ile iletisim kuran HTTP istemcisi."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=timeout)
        self._token: str | None = None

    # -- Oturum -----------------------------------------------------------------

    def login(self, email: str, password: str) -> httpx.Response:
        resp = self._client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token")
        return resp

    def set_token(self, token: str):
        self._token = token

    def clear_token(self):
        self._token = None

    @property
    def auth_headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    # -- Genel HTTP metodlari ---------------------------------------------------

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._client.get(path, headers=self.auth_headers, **kwargs)

    def post(self, path: str, json: Any = None, **kwargs) -> httpx.Response:
        return self._client.post(path, json=json, headers=self.auth_headers, **kwargs)

    def put(self, path: str, json: Any = None, **kwargs) -> httpx.Response:
        return self._client.put(path, json=json, headers=self.auth_headers, **kwargs)

    def patch(self, path: str, json: Any = None, **kwargs) -> httpx.Response:
        return self._client.patch(path, json=json, headers=self.auth_headers, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self._client.delete(path, headers=self.auth_headers, **kwargs)

    # -- TSPM kisayollari -------------------------------------------------------

    def tspm(self, path: str) -> str:
        """TSPM prefix'i ekler: /api/v1/tspm/..."""
        return f"/api/v1/tspm/{path.lstrip('/')}"

    def project_path(self, project_id: str, sub: str = "") -> str:
        base = f"/api/v1/tspm/projects/{project_id}"
        return f"{base}/{sub.lstrip('/')}" if sub else base

    # -- Temizlik ---------------------------------------------------------------

    def close(self):
        self._client.close()
