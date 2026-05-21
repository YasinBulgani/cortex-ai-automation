"""
Nexus QA — AI Gateway Client (Backend tarafı)
Backend servisleri bu modül aracılığıyla AI Gateway'e erişir.

Kullanım:
    from app.domains.ai.gateway_client import gateway_complete, gateway_analyze_document
    result = gateway_complete(task_type="chat", user_message="test yaz")
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

AI_GATEWAY_BASE = os.environ.get("AI_GATEWAY_BASE_URL", "http://127.0.0.1:8080")
TIMEOUT = 90.0
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.5   # saniye — 1.5s, 3s, 6s


def _require_internal_key() -> str:
    key = os.environ.get("GATEWAY_INTERNAL_KEY", "").strip()
    if not key:
        raise RuntimeError("GATEWAY_INTERNAL_KEY ayarlanmamis. Varsayilan internal key kullanimi devre disi.")
    return key


def _gateway_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": _require_internal_key(),
    }


# JSON çıktısı gereken task type'lar
_JSON_TASK_TYPES = frozenset({
    "analyze_document",
    "generate_test_cases",
    "suggest_regression",
    "debug_test",
})


def _parse_json_safe(raw: str) -> dict | list | None:
    """
    LLM yanıtından JSON parse et.
    Markdown fence, fazladan metin, ve kırpılmış JSON'a karşı dayanıklı.
    """
    text = raw.strip()

    # 1. Markdown code fence temizle
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    # 2. Direkt parse dene
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. İlk { veya [ den son } veya ] e kadar al
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    return None


def gateway_complete(
    task_type: str,
    user_message: str,
    system_message: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4000,
    project_id: str | None = None,
    json_mode: bool | None = None,
    model_override: str | None = None,
) -> str:
    """
    AI Gateway'e senkron istek gönder, yanıt metnini döndür.
    Tüm fallback zinciri (Ollama→Groq→Gemini→g4f) otomatik yönetilir.
    Hata durumunda 3 kez exponential backoff ile yeniden dener.
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": user_message})

    effective_json_mode = json_mode if json_mode is not None else (task_type in _JSON_TASK_TYPES)

    payload: dict[str, Any] = {
        "task_type": task_type,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "json_mode": effective_json_mode,
    }
    if project_id:
        payload["project_id"] = project_id
    if model_override:
        payload["model_override"] = model_override

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                f"{AI_GATEWAY_BASE}/ai/complete",
                json=payload,
                headers=_gateway_headers(),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            provider = data.get("provider_used", "unknown")
            model = data.get("model_used", "unknown")
            logger.info(
                f"AI Gateway OK — task={task_type} provider={provider} model={model} "
                f"latency={data.get('latency_ms', 0)}ms (deneme {attempt})"
            )
            return data["content"]

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # 503 veya 429 → retry; diğerleri → hemen fırlat
            if status in (429, 503, 504) and attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning(f"AI Gateway {status}, {wait:.1f}s beklenip tekrar denenecek (deneme {attempt})")
                time.sleep(wait)
                last_exc = exc
                continue
            logger.error(f"AI Gateway HTTP hatası {status}: {exc.response.text[:200]}")
            raise RuntimeError(f"AI Gateway hatası: {status}") from exc

        except httpx.RequestError as exc:
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning(f"AI Gateway bağlantı hatası, {wait:.1f}s sonra tekrar ({attempt}/{_MAX_RETRIES}): {exc}")
                time.sleep(wait)
                last_exc = exc
                continue
            logger.error(f"AI Gateway bağlantı hatası: {exc}")
            raise RuntimeError(
                f"AI Gateway'e bağlanılamadı ({AI_GATEWAY_BASE}). "
                "docker-compose up ile başlatın."
            ) from exc

    raise RuntimeError(f"AI Gateway {_MAX_RETRIES} denemede de yanıt vermedi") from last_exc


def gateway_analyze_document(
    doc_text: str,
    extra_instructions: str = "",
    project_id: str | None = None,
) -> dict[str, Any]:
    """Analiz dokümanını AI Gateway'e gönder. JSON parse edilip dict döner."""
    user_content = doc_text
    if extra_instructions:
        user_content += f"\n\n---\nEk Talimatlar:\n{extra_instructions}"

    raw = gateway_complete(
        task_type="analyze_document",
        user_message=user_content,
        temperature=0.3,
        max_tokens=4000,
        project_id=project_id,
    )

    parsed = _parse_json_safe(raw)
    if parsed and isinstance(parsed, dict):
        return parsed
    logger.warning("AI analiz yanıtı JSON parse edilemedi, ham metin döndürülüyor")
    return {"raw": raw, "modules": [], "total_estimated_cases": 0}


def gateway_generate_test_cases(
    module_info: str,
    project_id: str | None = None,
) -> list[dict]:
    """Modül bilgisinden test case listesi üret."""
    raw = gateway_complete(
        task_type="generate_test_cases",
        user_message=f"Aşağıdaki modül için kapsamlı test case'leri üret:\n\n{module_info}",
        temperature=0.5,
        max_tokens=4000,
        project_id=project_id,
    )
    parsed = _parse_json_safe(raw)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return parsed.get("test_cases", [])
    return []


def gateway_generate_gherkin(
    test_cases_json: str,
    feature_name: str,
    project_id: str | None = None,
) -> str:
    """Test case'lerden Gherkin feature içeriği üret."""
    return gateway_complete(
        task_type="generate_gherkin",
        user_message=f"Feature adı: {feature_name}\n\nTest case'ler:\n{test_cases_json}",
        temperature=0.4,
        max_tokens=4000,
        project_id=project_id,
    )


def gateway_suggest_regression(
    scenarios_summary: str,
    project_id: str | None = None,
) -> dict:
    """Senaryolar için regresyon seti öner."""
    raw = gateway_complete(
        task_type="suggest_regression",
        user_message=f"Aşağıdaki test senaryoları için optimal regresyon seti öner:\n\n{scenarios_summary}",
        temperature=0.3,
        max_tokens=3000,
        project_id=project_id,
    )
    parsed = _parse_json_safe(raw)
    if isinstance(parsed, dict):
        return parsed
    return {"regression_set": {}, "raw": raw}


def gateway_generate_java_steps(
    gherkin_content: str,
    project_id: str | None = None,
) -> str:
    """Gherkin senaryolarından Java NexusQA step definitions üret."""
    return gateway_complete(
        task_type="generate_java_steps",
        user_message=f"Aşağıdaki Gherkin senaryoları için Java step definition'ları üret:\n\n{gherkin_content}",
        temperature=0.3,
        max_tokens=4000,
        project_id=project_id,
    )


def gateway_debug_test(
    failed_tests_summary: str,
    project_id: str | None = None,
) -> str:
    """Başarısız testleri analiz et, kök neden ve düzeltme adımları üret."""
    return gateway_complete(
        task_type="debug_test",
        user_message=f"Aşağıdaki başarısız testleri analiz et:\n\n{failed_tests_summary}",
        temperature=0.3,
        max_tokens=3000,
        project_id=project_id,
    )


def gateway_is_available() -> bool:
    """AI Gateway'in erişilebilir olup olmadığını kontrol et."""
    try:
        resp = httpx.get(f"{AI_GATEWAY_BASE}/ping", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


# ── Embedding Proxy ─────────────────────────────────────────────────────────

def gateway_embed(
    texts: list[str],
    *,
    model: str | None = None,
    correlation_id: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Gateway'in /ai/embed endpoint'ini çağırıp vektör listesi döner.

    Dönüş:
        {"vectors": [[...]], "model": str, "dim": int, "latency_ms": int}

    Hatalar doğrudan RuntimeError olarak fırlatılır — çağıran katman
    (DSL semantic search) bu durumda lexical search'e düşer.
    """
    if not texts:
        return {"vectors": [], "model": model or "-", "dim": 0, "latency_ms": 0}

    payload: dict[str, Any] = {"texts": texts}
    if model:
        payload["model"] = model
    if correlation_id:
        payload["correlation_id"] = correlation_id

    try:
        resp = httpx.post(
            f"{AI_GATEWAY_BASE}/ai/embed",
            json=payload,
            headers=_gateway_headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.debug(
            "Gateway embed OK — count=%d dim=%s latency=%sms",
            len(texts),
            data.get("dim"),
            data.get("latency_ms"),
        )
        return data
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Gateway embed HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise RuntimeError(
            f"Gateway embed başarısız (HTTP {exc.response.status_code})"
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Gateway embed bağlantı hatası: %s", exc)
        raise RuntimeError(f"Gateway'e erişilemedi: {exc}") from exc


def gateway_embed_available() -> bool:
    """Gateway embed endpoint'i erişilebilir ve model ayarlı mı?"""
    try:
        resp = httpx.get(f"{AI_GATEWAY_BASE}/ai/embed/model", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False
