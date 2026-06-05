"""Async JSON-RPC client for Kiwi TCMS.

Kiwi exposes a single JSON-RPC endpoint at ``{base_url}/json-rpc/``. Auth is
session-based: call ``Auth.login`` once, the response sets a ``sessionid``
cookie, and subsequent calls reuse it. Most data methods are ``<Model>.filter``
wrappers around Django QuerySets and accept a single query dict.

Mirrors the retry/error conventions of
``app/domains/agents/engine_client.py`` but keeps one cookie-bearing
``httpx.AsyncClient`` alive for the duration of a sync via ``async with``.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0
_MAX_RETRIES = 2


class KiwiError(RuntimeError):
    """Raised when Kiwi returns a JSON-RPC error or the call fails after retries."""


class KiwiClient:
    """Cookie-session JSON-RPC client. Use as an async context manager.

    Example::

        async with KiwiClient(base_url, username, secret) as kiwi:
            products = await kiwi.list_products()
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        secret: str,
        *,
        verify_ssl: bool = True,
        timeout: float = _TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._endpoint = base_url.rstrip("/") + "/json-rpc/"
        self._username = username
        self._secret = secret
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._transport = transport  # test seam: inject httpx.MockTransport
        self._client: Optional[httpx.AsyncClient] = None
        self._rpc_id = 0

    # ── lifecycle ──────────────────────────────────────────────────────
    async def __aenter__(self) -> KiwiClient:
        self._client = httpx.AsyncClient(
            timeout=self._timeout, verify=self._verify_ssl, transport=self._transport
        )
        await self.login()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            try:
                await self._call("Auth.logout", [])
            except Exception:  # logout is best-effort
                pass
            await self._client.aclose()
            self._client = None

    # ── auth ───────────────────────────────────────────────────────────
    async def login(self) -> None:
        """Authenticate; the resulting ``sessionid`` cookie is stored on the client."""
        await self._call("Auth.login", [self._username, self._secret])

    async def ping(self) -> int:
        """Lightweight reachability check used by 'test connection'. Returns product count."""
        return len(await self.list_products())

    # ── data methods (all <Model>.filter wrappers) ─────────────────────
    async def list_products(self, query: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        return await self._filter("Product", query or {})

    async def list_categories(self, product_id: int) -> list[dict[str, Any]]:
        return await self._filter("Category", {"product": product_id})

    async def list_cases(self, product_id: int) -> list[dict[str, Any]]:
        # Cases are tied to a product through their category.
        return await self._filter("TestCase", {"category__product": product_id})

    async def list_plans(self, product_id: int) -> list[dict[str, Any]]:
        return await self._filter("TestPlan", {"product": product_id})

    async def list_runs(self, product_id: int) -> list[dict[str, Any]]:
        return await self._filter("TestRun", {"plan__product": product_id})

    async def list_executions(self, run_id: int) -> list[dict[str, Any]]:
        return await self._filter("TestExecution", {"run": run_id})

    async def list_bugs(self, product_id: int) -> list[dict[str, Any]]:
        # Kiwi Bug model — linked to executions via execution_id or product
        return await self._filter("Bug", {"runs__plan__product": product_id})

    # ── low level ──────────────────────────────────────────────────────
    async def _filter(self, model: str, query: dict[str, Any]) -> list[dict[str, Any]]:
        result = await self._call(f"{model}.filter", [query])
        if result is None:
            return []
        if not isinstance(result, list):
            raise KiwiError(f"{model}.filter beklenmeyen yanıt tipi: {type(result).__name__}")
        return result

    async def _call(self, method: str, params: list[Any]) -> Any:
        if self._client is None:
            raise KiwiError("KiwiClient kullanılmadan önce 'async with' ile açılmalı")

        self._rpc_id += 1
        body = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._rpc_id}
        last_exc: Optional[Exception] = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await self._client.post(self._endpoint, json=body)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and data.get("error"):
                    err = data["error"]
                    msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                    raise KiwiError(f"Kiwi RPC hatası ({method}): {msg}")
                return data.get("result") if isinstance(data, dict) else data
            except httpx.HTTPStatusError as exc:
                # 4xx (auth/permission) — kalıcı, retry etme
                if 400 <= exc.response.status_code < 500:
                    raise KiwiError(
                        f"Kiwi HTTP {exc.response.status_code} ({method}): kimlik/izin veya URL hatalı"
                    ) from exc
                last_exc = exc
                logger.warning("Kiwi 5xx deneme %d/%d (%s)", attempt, _MAX_RETRIES, method)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                logger.warning("Kiwi bağlantı/timeout deneme %d/%d (%s)", attempt, _MAX_RETRIES, method)

        raise KiwiError(f"Kiwi'ye ulaşılamadı ({method}): {last_exc}")
