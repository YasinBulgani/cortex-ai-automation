"""Async AI Gateway Client — agents/v2 için."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

AI_GATEWAY_BASE = os.environ.get("AI_GATEWAY_BASE_URL", "http://127.0.0.1:8080")
INTERNAL_KEY = os.environ.get(
    "GATEWAY_INTERNAL_KEY", "nexusqa-gateway-internal-key-change-me"
)
DEFAULT_TIMEOUT = 120.0
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5

_JSON_TASK_TYPES = frozenset({
    "analyze_document", "generate_test_cases", "suggest_regression", "debug_test",
})

_SCHEMA_VERSION_BY_TASK: dict[str, str] = {
    "analyze_document": "v1",
    "generate_test_cases": "v1",
    "suggest_regression": "v1",
    "debug_test": "v1",
}

# Maliyet hesabı TEK kaynaktan: infra/registry/model_registry.yaml
# (2026-Q2, Dalga 0 konsolidasyonu — ADR-0010 referansı).
# Eski _COST_TABLE kaldırıldı; drift riski bitti.
from app.domains.ai.model_registry import compute_cost_usd as _registry_compute_cost


def calculate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Geriye dönük API — model_registry'ye delege eder."""
    if not model:
        return 0.0
    return _registry_compute_cost(
        model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


class AIGatewayError(RuntimeError):
    pass


class AIGatewayTimeout(AIGatewayError):
    pass


class AIGatewayUnavailable(AIGatewayError):
    pass


@dataclass
class GatewayUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, other: "GatewayUsage") -> "GatewayUsage":
        return GatewayUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


@dataclass
class GatewayResponse:
    content: str
    provider_used: str
    model_used: str
    latency_ms: int
    cached: bool = False
    correlation_id: str | None = None
    usage: GatewayUsage = field(default_factory=GatewayUsage)
    raw: dict[str, Any] = field(default_factory=dict)

    def parsed_json(self) -> dict | list | None:
        return parse_json_safe(self.content)


def parse_json_safe(raw: str) -> dict | list | None:
    text = raw.strip() if raw else ""
    if not text:
        return None
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        s, e = text.find(start_char), text.rfind(end_char)
        if s != -1 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except json.JSONDecodeError:
                pass
    return None


class AsyncAIGatewayClient:
    def __init__(
        self,
        base_url: str = AI_GATEWAY_BASE,
        internal_key: str = INTERNAL_KEY,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.internal_key = internal_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Key": self.internal_key,
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @asynccontextmanager
    async def lifespan(self):
        try:
            yield self
        finally:
            await self.close()

    async def complete(
        self,
        *,
        task_type: str = "chat",
        user_message: str,
        system_message: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        json_mode: bool | None = None,
        model_override: str | None = None,
        project_id: str | None = None,
        correlation_id: str | None = None,
        tenant_id: str | None = None,
    ) -> GatewayResponse:
        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        effective_json = json_mode if json_mode is not None else (task_type in _JSON_TASK_TYPES)

        payload: dict[str, Any] = {
            "task_type": task_type,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "json_mode": effective_json,
        }
        schema_version = _SCHEMA_VERSION_BY_TASK.get(task_type)
        if effective_json and schema_version:
            payload["schema_version"] = schema_version
        if project_id:
            payload["project_id"] = project_id
        if model_override:
            payload["model_override"] = model_override
        if correlation_id:
            payload["correlation_id"] = correlation_id
        _budget_preflight(payload, tenant_id=tenant_id)

        return await self._request("/ai/complete", payload)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        task_type: str = "chat",
        temperature: float = 0.3,
        max_tokens: int = 4000,
        model_override: str | None = None,
        correlation_id: str | None = None,
        tenant_id: str | None = None,
    ) -> GatewayResponse:
        payload: dict[str, Any] = {
            "task_type": task_type,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "json_mode": task_type in _JSON_TASK_TYPES,
        }
        schema_version = _SCHEMA_VERSION_BY_TASK.get(task_type)
        if task_type in _JSON_TASK_TYPES and schema_version:
            payload["schema_version"] = schema_version
        if model_override:
            payload["model_override"] = model_override
        if correlation_id:
            payload["correlation_id"] = correlation_id
        _budget_preflight(payload, tenant_id=tenant_id)
        return await self._request("/ai/complete", payload)

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        if not texts:
            return {"vectors": [], "model": model or "-", "dim": 0, "latency_ms": 0}
        payload: dict[str, Any] = {"texts": texts}
        if model:
            payload["model"] = model
        if correlation_id:
            payload["correlation_id"] = correlation_id

        client = await self._get_client()
        resp = await client.post("/ai/embed", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get("/ping", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def providers(self) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get("/ai/providers")
        resp.raise_for_status()
        return resp.json()

    async def _request(self, path: str, payload: dict[str, Any]) -> GatewayResponse:
        client = await self._get_client()
        last_exc: Exception | None = None
        start = time.monotonic()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post(path, json=payload)
                resp.raise_for_status()
                data = resp.json()

                input_tokens = _estimate_input_tokens(payload.get("messages", []))
                output_tokens = data.get("tokens_used", 0) or _estimate_tokens(data.get("content", ""))
                model = data.get("model_used", "")
                cost = calculate_cost_usd(model, input_tokens, output_tokens)

                usage = GatewayUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost_usd=cost,
                )

                logger.info(
                    "Gateway OK — task=%s provider=%s model=%s latency=%sms "
                    "tokens=%d cost=$%.4f (deneme %d)",
                    payload.get("task_type"),
                    data.get("provider_used"),
                    model,
                    data.get("latency_ms", 0),
                    usage.total_tokens,
                    usage.cost_usd,
                    attempt,
                )

                _enforce_structured_output(payload, data.get("content", ""), model)

                return GatewayResponse(
                    content=data.get("content", ""),
                    provider_used=data.get("provider_used", "unknown"),
                    model_used=model,
                    latency_ms=data.get("latency_ms", int((time.monotonic() - start) * 1000)),
                    cached=data.get("cached", False),
                    correlation_id=data.get("correlation_id"),
                    usage=usage,
                    raw=data,
                )

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (429, 503) and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    logger.warning("Gateway %s — %.1fs bekleniyor (deneme %d)",
                                   status, wait, attempt)
                    await asyncio.sleep(wait)
                    last_exc = exc
                    continue
                body = exc.response.text[:200] if exc.response else ""
                raise AIGatewayError(f"Gateway HTTP {status}: {body}") from exc

            except httpx.TimeoutException as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
                    last_exc = exc
                    continue
                raise AIGatewayTimeout(f"Gateway timeout: {exc}") from exc

            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
                    last_exc = exc
                    continue
                raise AIGatewayUnavailable(f"Gateway erişilemedi: {exc}") from exc

        raise AIGatewayError(f"Gateway {MAX_RETRIES} denemede cevap vermedi") from last_exc


_tiktoken_enc = None


def _get_tiktoken():
    global _tiktoken_enc
    if _tiktoken_enc is not None:
        return _tiktoken_enc
    try:
        import tiktoken
        _tiktoken_enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        _tiktoken_enc = False
    return _tiktoken_enc if _tiktoken_enc else None


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    enc = _get_tiktoken()
    if enc:
        try:
            return len(enc.encode(text))
        except Exception:
            pass
    return int(len(text.split()) * 1.35) + len(text) // 100


def _estimate_input_tokens(messages: list[dict[str, Any]]) -> int:
    total = 0
    for m in messages:
        content = m.get("content", "")
        total += _estimate_tokens(content) + 4
    return total


def _budget_preflight(payload: dict[str, Any], *, tenant_id: str | None) -> None:
    """Run a best-effort budget check before hitting the gateway."""
    try:
        from app.config import settings

        if not settings.ai_budget_preflight_required and not tenant_id:
            return
        tenant = tenant_id or "default"
        estimated_input = _estimate_input_tokens(payload.get("messages", []))
        estimated_output = int(payload.get("max_tokens") or 0)
        model = str(payload.get("model_override") or "")
        estimated_cost = (
            calculate_cost_usd(model, estimated_input, estimated_output)
            if model
            else 0.0
        )
        from app.domains.ai.budget import check_budget

        status = check_budget(tenant, additional_cost_usd=estimated_cost)
        payload["budget_preflight"] = {
            "tenant_id": tenant,
            "estimated_cost_usd": estimated_cost,
            "reason": status.reason,
            "pct_used": status.pct_used(),
        }
        if not status.allowed:
            raise AIGatewayError(
                f"Budget preflight blocked tenant={tenant} reason={status.reason} "
                f"projected_cost=${estimated_cost:.6f}"
            )
    except AIGatewayError:
        raise
    except Exception as exc:
        logger.debug("Budget preflight skipped: %s", exc)


def _enforce_structured_output(payload: dict[str, Any], content: str, model: str) -> None:
    try:
        from app.config import settings
        from app.domains.ai.structured_output import (
            StructuredOutputValidationError,
            should_validate_task,
            structured_enabled,
            validate_response,
        )

        if not settings.ai_structured_output_fail_closed:
            return
        task_type = str(payload.get("task_type") or "chat")
        if not structured_enabled() or not should_validate_task(task_type):
            return
        valid, err_msg, _ = validate_response(task_type, content)
        if valid:
            return
        try:
            from app.domains.ai.metrics import record_schema_violation

            record_schema_violation(task_type=task_type, model=model or "unknown")
        except Exception:
            pass
        raise StructuredOutputValidationError(
            f"Structured output validation failed for task={task_type}: {err_msg}"
        )
    except StructuredOutputValidationError:
        raise
    except Exception as exc:
        logger.debug("structured output enforcement skipped: %s", exc)


_singleton: AsyncAIGatewayClient | None = None


def get_gateway_client() -> AsyncAIGatewayClient:
    global _singleton
    if _singleton is None:
        _singleton = AsyncAIGatewayClient()
    return _singleton


async def close_gateway_client() -> None:
    global _singleton
    if _singleton:
        await _singleton.close()
        _singleton = None


async def ai_complete(
    user_message: str,
    *,
    task_type: str = "chat",
    system_message: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
    json_mode: bool | None = None,
    model_override: str | None = None,
    project_id: str | None = None,
    correlation_id: str | None = None,
    tenant_id: str | None = None,
) -> GatewayResponse:
    client = get_gateway_client()
    return await client.complete(
        task_type=task_type,
        user_message=user_message,
        system_message=system_message,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
        model_override=model_override,
        project_id=project_id,
        correlation_id=correlation_id,
        tenant_id=tenant_id,
    )


async def ai_embed(
    texts: list[str],
    *,
    model: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    client = get_gateway_client()
    return await client.embed(texts, model=model, correlation_id=correlation_id)
