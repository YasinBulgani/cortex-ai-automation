"""Base HTTP client with shared functionality."""

from typing import Any

import httpx

from config.settings import settings


class BaseClient:
    def __init__(self, base_url: str, timeout: float | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self._token: str | None = None
        self._session_cookies: dict[str, str] = {}

    def set_token(self, token: str) -> None:
        self._token = token

    def clear_token(self) -> None:
        self._token = None

    def set_session_cookies(self, cookies: dict[str, str]) -> None:
        self._session_cookies = cookies

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str, params: dict | None = None, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, cookies=self._session_cookies) as client:
            return client.get(
                self._url(path),
                params=params,
                headers=self._build_headers(kwargs.get("headers")),
            )

    def post(self, path: str, json: Any = None, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, cookies=self._session_cookies) as client:
            return client.post(
                self._url(path),
                json=json,
                headers=self._build_headers(kwargs.get("headers")),
                data=kwargs.get("data"),
                files=kwargs.get("files"),
            )

    def put(self, path: str, json: Any = None, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, cookies=self._session_cookies) as client:
            return client.put(
                self._url(path),
                json=json,
                headers=self._build_headers(kwargs.get("headers")),
            )

    def patch(self, path: str, json: Any = None, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, cookies=self._session_cookies) as client:
            return client.patch(
                self._url(path),
                json=json,
                headers=self._build_headers(kwargs.get("headers")),
            )

    def delete(self, path: str, json: Any = None, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, cookies=self._session_cookies) as client:
            return client.delete(
                self._url(path),
                headers=self._build_headers(kwargs.get("headers")),
            )
