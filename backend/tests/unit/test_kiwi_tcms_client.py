"""Contract tests for the Kiwi JSON-RPC client using httpx.MockTransport.

No network: a mock transport asserts the request shape (endpoint, method,
params) and returns canned JSON-RPC responses, covering auth, filter wrappers,
RPC-level errors and HTTP 4xx handling.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.domains.kiwi_tcms.client import KiwiClient, KiwiError

BASE = "https://kiwi.example.com"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_transport(handler):
    return httpx.MockTransport(handler)


def test_login_and_list_products_request_shape():
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{BASE}/json-rpc/"
        body = json.loads(request.content)
        seen.append(body)
        if body["method"] == "Auth.login":
            assert body["params"] == ["api-user", "tok"]
            return httpx.Response(200, json={"result": "session-key", "id": body["id"]})
        if body["method"] == "Product.filter":
            assert body["params"] == [{}]
            return httpx.Response(
                200, json={"result": [{"id": 1, "name": "Web"}, {"id": 2, "name": "API"}], "id": body["id"]}
            )
        if body["method"] == "Auth.logout":
            return httpx.Response(200, json={"result": None, "id": body["id"]})
        raise AssertionError(f"unexpected method {body['method']}")

    async def scenario():
        async with KiwiClient(BASE, "api-user", "tok", transport=_make_transport(handler)) as kiwi:
            products = await kiwi.list_products()
            assert [p["name"] for p in products] == ["Web", "API"]
            assert await kiwi.ping() == 2

    _run(scenario())
    methods = [b["method"] for b in seen]
    assert methods[0] == "Auth.login"  # login happens on __aenter__
    assert "Product.filter" in methods


def test_list_cases_uses_category_product_query():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "TestCase.filter":
            captured["params"] = body["params"]
            return httpx.Response(200, json={"result": [{"id": 10}], "id": body["id"]})
        return httpx.Response(200, json={"result": [], "id": body["id"]})

    async def scenario():
        async with KiwiClient(BASE, "u", "p", transport=_make_transport(handler)) as kiwi:
            await kiwi.list_cases(5)

    _run(scenario())
    assert captured["params"] == [{"category__product": 5}]


def test_rpc_error_is_raised():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "Auth.login":
            return httpx.Response(200, json={"result": "ok", "id": body["id"]})
        return httpx.Response(200, json={"error": {"message": "permission denied"}, "id": body["id"]})

    async def scenario():
        async with KiwiClient(BASE, "u", "p", transport=_make_transport(handler)) as kiwi:
            await kiwi.list_products()

    with pytest.raises(KiwiError, match="permission denied"):
        _run(scenario())


def test_http_4xx_raises_without_retry():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "Auth.login":
            calls["n"] += 1
            return httpx.Response(401, json={"detail": "unauthorized"})
        return httpx.Response(200, json={"result": [], "id": body["id"]})

    async def scenario():
        async with KiwiClient(BASE, "u", "bad", transport=_make_transport(handler)):
            pass

    with pytest.raises(KiwiError, match="401"):
        _run(scenario())
    assert calls["n"] == 1  # 4xx must not be retried
