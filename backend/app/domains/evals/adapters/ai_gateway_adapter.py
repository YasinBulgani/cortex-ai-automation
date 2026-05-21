"""AI Gateway eval adapter.

Deterministik CI modu:
    inputs._fixture varsa fixture aynen döner.

Canlı LLM modu:
    EVAL_RUN_LLM=1 set edilirse gateway'in /ai/complete endpoint'ine gerçek
    istek atar ve provider/attempt metadata'sını rapora taşır.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


class AiGatewayAdapter:
    name = "ai_gateway"

    def available(self) -> bool:
        if os.environ.get("EVAL_RUN_LLM") != "1":
            return True
        try:
            from app.domains.ai.gateway_client import gateway_is_available

            return gateway_is_available()
        except Exception as exc:
            logger.warning("AiGatewayAdapter unavailable: %s", exc)
            return False

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        fixture = inputs.get("_fixture")
        if isinstance(fixture, dict):
            return dict(fixture)

        if os.environ.get("EVAL_RUN_LLM") != "1":
            return {
                "content": "",
                "provider_used": "skipped",
                "model_used": "",
                "attempts": [],
                "latency_ms": 0,
                "error": "EVAL_RUN_LLM=1 gerekli",
            }

        from app.domains.ai.gateway_client import AI_GATEWAY_BASE, _gateway_headers

        messages: list[dict[str, str]] = []
        system_message = str(inputs.get("system_message") or "").strip()
        user_message = str(
            inputs.get("user_message") or inputs.get("prompt") or ""
        ).strip()
        if system_message:
            messages.append({"role": "system", "content": system_message})
        if user_message:
            messages.append({"role": "user", "content": user_message})
        if not messages:
            raise ValueError("inputs.user_message veya inputs.prompt zorunlu")

        payload: dict[str, Any] = {
            "task_type": str(inputs.get("task_type") or "chat"),
            "messages": messages,
            "temperature": float(inputs.get("temperature", 0.2)),
            "max_tokens": int(inputs.get("max_tokens", 512)),
            "json_mode": bool(inputs.get("json_mode", False)),
        }
        for optional in ("provider", "project_id", "correlation_id", "model_override"):
            value = inputs.get(optional)
            if value:
                payload[optional] = value

        timeout = float(inputs.get("timeout", 60.0))
        resp = httpx.post(
            f"{AI_GATEWAY_BASE}/ai/complete",
            json=payload,
            headers=_gateway_headers(),
            timeout=timeout,
        )
        data: dict[str, Any]
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}
        data["http_status"] = resp.status_code
        if resp.status_code >= 400:
            data.setdefault("error", resp.text[:500])
        return data


class AiGatewayLiveAdapter(AiGatewayAdapter):
    """Live-only adapter.

    Default eval suite yüklemelerinde canlı LLM gerektiren case'lerin PR gate'i
    kırmaması için ayrı adapter adı kullanılır. Bu adapter ancak
    EVAL_RUN_LLM=1 ve gateway erişilebilirken available=True döner.
    """

    name = "ai_gateway_live"

    def available(self) -> bool:
        if os.environ.get("EVAL_RUN_LLM") != "1":
            return False
        return super().available()
