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

from app.config import settings

logger = logging.getLogger(__name__)

# Not: Env override'ları korunur; yoksa Settings üzerinden okunur.
# Bu sayede .env ve üretim override'ları tutarlı çalışır.
TIMEOUT = 90.0
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.5   # saniye — 1.5s, 3s, 6s

# Persistent HTTP client — TCP bağlantısını request'ler arasında yeniden kullanır.
# httpx.Client thread-safe; module-level singleton güvenlidir.
_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=httpx.Timeout(TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_client


def _gateway_base() -> str:
    return (os.environ.get("AI_GATEWAY_BASE_URL") or settings.ai_gateway_base_url).rstrip("/")


def _internal_key() -> str:
    return os.environ.get("GATEWAY_INTERNAL_KEY") or settings.gateway_internal_key


# Geriye dönük uyumluluk — eski kodlar bu modül-seviye değişkenleri okuyabiliyor
AI_GATEWAY_BASE = _gateway_base()
INTERNAL_KEY = _internal_key()


def _gateway_headers() -> dict:
    key = os.environ.get("GATEWAY_INTERNAL_KEY") or ""
    if not key:
        raise RuntimeError(
            "GATEWAY_INTERNAL_KEY ortam degiskeni ayarlanmamis. "
            "Guvenli bir key tanimlayin: export GATEWAY_INTERNAL_KEY=$(openssl rand -hex 32)"
        )
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Key": key,
    }
    # Correlation ID — aktif request'ten al (varsa)
    try:
        from app.domains.ai.correlation import get_correlation_id, HEADER_NAME
        cid = get_correlation_id()
        if cid:
            headers[HEADER_NAME] = cid
    except Exception:
        pass
    return headers


# JSON çıktısı gereken task type'lar
_JSON_TASK_TYPES = frozenset({
    "analyze_document",
    "generate_test_cases",
    "suggest_regression",
    "debug_test",
})

_SCHEMA_VERSION_BY_TASK: dict[str, str] = {
    "analyze_document": "v1",
    "generate_test_cases": "v1",
    "suggest_regression": "v1",
    "debug_test": "v1",
}


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


def _redact_pii(text: str) -> tuple[str, int]:
    """PII regex'lerini LLM'e gitmeden once uygula. (redacted_text, sayac) doner.

    KnowledgeStore.mask_sensitive RAG ingest'te kullaniliyor. Ayni regex'leri
    prompt yolunda da uyguluyoruz — TCKN/IBAN/kart OpenAI'a hic cikmasin.

    Flag ``ai.pii.redact`` default True. Kapanirsa bypass.
    """
    try:
        from app.domains.feature_flags.service import feature_flags
        if not feature_flags.is_enabled("ai.pii.redact", default=True):
            return text, 0
    except Exception:
        pass

    try:
        from app.domains.ai.knowledge_store import mask_sensitive, _MASK_PATTERNS
        if not text:
            return text, 0
        original = text
        masked = mask_sensitive(text)
        if masked == original:
            return masked, 0
        # Kac match oldugunu kaba tahmin: her pattern için substitution sayisi
        count = 0
        for pattern, _replacement in _MASK_PATTERNS:
            count += len(pattern.findall(original))
        return masked, count
    except Exception:
        return text, 0


def _resolve_from_registry(
    task_type: str,
    *,
    tenant_id: str | None = None,
) -> tuple[str | None, dict | None]:
    """Prompt registry'den sistem prompt'u cek (varsa).

    Convention: registry'de prompt_id = task_type.
    - ``ai.prompts.registry`` flag'i kapaliysa (None, None) doner.
    - Prompt yoksa (None, None) doner — caller kendi default'unu kullanmali.
    - Bulursa (system_prompt, meta) doner; meta = {"version": N, "prompt_id": ...}.
    """
    try:
        from app.domains.feature_flags.service import feature_flags
        from app.config import settings

        if not feature_flags.is_enabled(
            "ai.prompts.registry",
            tenant_id=tenant_id,
            default=settings.ai_prompt_registry_enabled,
        ):
            return None, None
    except Exception:
        try:
            from app.config import settings
            if not settings.ai_prompt_registry_enabled:
                return None, None
        except Exception:
            return None, None

    try:
        from app.domains.prompts.service import resolve as prompt_resolve
        resolved = prompt_resolve(task_type, tenant_id=tenant_id, env="prod")
        if resolved is None:
            return None, None
        meta = {
            "prompt_id": task_type,
            "version": resolved.version,
            "decision_reason": resolved.decision_reason,
        }
        return resolved.system_prompt, meta
    except Exception as exc:
        logger.debug("registry resolve hatasi: %s", exc)
        return None, None


def gateway_complete(
    task_type: str,
    user_message: str,
    system_message: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4000,
    project_id: str | None = None,
    json_mode: bool | None = None,
    model_override: str | None = None,
    *,
    use_cache: bool = True,
    tenant_id: str | None = None,
) -> str:
    """
    AI Gateway'e senkron istek gönder, yanıt metnini döndür.

    Ek katmanlar (2026-04 güncellemesi):
      1. Semantic cache lookup (``ai.cache.semantic`` flag, default True)
      2. PII redaction (``ai.pii.redact`` flag, default True)
      3. Prompt registry resolve (``ai.prompts.registry`` flag, default False)

    Tüm fallback zinciri (vLLM→Ollama→Groq→Gemini) otomatik yönetilir.
    Hata durumunda 3 kez exponential backoff ile yeniden dener.
    """
    # 1) PII redaction — LLM'e gitmeden once hassas veriyi maskele
    redacted_user, pii_count = _redact_pii(user_message)
    redacted_sys, _ = _redact_pii(system_message or "")

    # 2) Prompt registry'den sistem prompt'u cek (varsa)
    if not system_message:
        reg_sys, _reg_meta = _resolve_from_registry(task_type, tenant_id=tenant_id)
        if reg_sys:
            redacted_sys, _ = _redact_pii(reg_sys)

    # 3) Semantic cache lookup
    if use_cache:
        try:
            from app.domains.ai.semantic_cache import cache_get
            cached = cache_get(
                task_type=task_type,
                user_msg=redacted_user,
                system_msg=redacted_sys if redacted_sys else None,
                tenant_id=tenant_id,
            )
            if cached:
                logger.info(
                    "AI Gateway CACHE %s — task=%s sim=%.3f hits=%d",
                    cached.source, task_type, cached.similarity, cached.hits,
                )
                return cached.response
        except Exception as exc:
            logger.debug("cache_get hatasi (pass): %s", exc)

    # 4) Gateway cagri
    messages = []
    if redacted_sys:
        messages.append({"role": "system", "content": redacted_sys})
    messages.append({"role": "user", "content": redacted_user})

    effective_json_mode = json_mode if json_mode is not None else (task_type in _JSON_TASK_TYPES)

    payload: dict[str, Any] = {
        "task_type": task_type,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "json_mode": effective_json_mode,
    }
    schema_version = _SCHEMA_VERSION_BY_TASK.get(task_type)
    if effective_json_mode and schema_version:
        payload["schema_version"] = schema_version
    if project_id:
        payload["project_id"] = project_id
    if model_override:
        payload["model_override"] = model_override

    _budget_preflight(payload, tenant_id=tenant_id)

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        # Deadline check — asildiysa erken fail (Faz 1.D)
        try:
            from app.domains.ai.deadline import check_deadline, remaining_ms, DeadlineExceededError
            check_deadline(f"gateway_complete attempt={attempt}")
            rem = remaining_ms()
            effective_timeout = TIMEOUT
            if rem is not None:
                effective_timeout = min(TIMEOUT, max(1.0, rem / 1000.0))
        except DeadlineExceededError:
            raise
        except Exception:
            effective_timeout = TIMEOUT

        try:
            resp = _get_http_client().post(
                f"{AI_GATEWAY_BASE}/ai/complete",
                json=payload,
                headers=_gateway_headers(),
                timeout=effective_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            provider = data.get("provider_used", "unknown")
            model = data.get("model_used", "unknown")
            content = data["content"]
            logger.info(
                f"AI Gateway OK — task={task_type} provider={provider} model={model} "
                f"latency={data.get('latency_ms', 0)}ms pii_redacted={pii_count} (deneme {attempt})"
            )

            # Rate-limit header'larini kaydet (proaktif throttle için)
            try:
                from app.domains.ai.rate_limit_monitor import record_rate_limit_headers
                record_rate_limit_headers(model, dict(resp.headers))
            except Exception:
                pass

            # Structured output validation + auto-fix retry (Faz 1.A)
            try:
                from app.domains.ai.structured_output import (
                    structured_enabled,
                    validate_response,
                    build_retry_prompt,
                    should_validate_task,
                )
                if structured_enabled(tenant_id) and should_validate_task(task_type):
                    valid, err_msg, _ = validate_response(task_type, content)
                    if not valid and attempt == 1 and err_msg:
                        # Tek retry ile duzeltmeyi dene
                        logger.info("Structured output invalid, 1x auto-fix retry: %s", err_msg[:100])
                        retry_user = build_retry_prompt(redacted_user, content, err_msg)
                        payload["messages"] = [
                            {"role": "system", "content": redacted_sys} if redacted_sys else None,
                            {"role": "user", "content": retry_user},
                        ]
                        payload["messages"] = [m for m in payload["messages"] if m]
                        # retry attempt — direkt bir kez daha gateway'e
                        resp2 = _get_http_client().post(
                            f"{AI_GATEWAY_BASE}/ai/complete",
                            json=payload,
                            headers=_gateway_headers(),
                            timeout=TIMEOUT,
                        )
                        if resp2.status_code == 200:
                            data2 = resp2.json()
                            retry_content = data2.get("content", "")
                            valid2, _, _ = validate_response(task_type, retry_content)
                            if valid2:
                                content = retry_content
                                logger.info("Structured output auto-fix retry OK")
                                valid = True
                    if not valid and settings.ai_structured_output_fail_closed:
                        from app.domains.ai.structured_output import StructuredOutputValidationError

                        raise StructuredOutputValidationError(
                            f"Structured output validation failed: {err_msg}"
                        )
            except RuntimeError:
                raise
            except Exception as exc:
                logger.debug("structured_output check hatasi: %s", exc)

            # Output shield — PII leak, Luhn, SQL inject, jailbreak (Faz 1.B)
            try:
                from app.domains.ai.output_shield import inspect_output
                shield = inspect_output(
                    content,
                    task_type=task_type,
                    original_input=redacted_user,
                    tenant_id=tenant_id,
                )
                if shield.decision == "block":
                    logger.error(
                        "OutputShield BLOCK: task=%s score=%.2f — sanitized cevap doner",
                        task_type, shield.score,
                    )
                    content = shield.sanitized or content
                elif shield.decision == "warn":
                    logger.warning(
                        "OutputShield WARN: task=%s score=%.2f (ignored, response passes)",
                        task_type, shield.score,
                    )
            except Exception as exc:
                logger.debug("output_shield check hatasi: %s", exc)

            # 5) Cache'e yaz (fire-and-forget)
            if use_cache and content:
                try:
                    from app.domains.ai.semantic_cache import cache_set
                    cache_set(
                        task_type=task_type,
                        user_msg=redacted_user,
                        response=content,
                        system_msg=redacted_sys if redacted_sys else None,
                        tenant_id=tenant_id,
                    )
                except Exception as exc:
                    logger.debug("cache_set hatasi: %s", exc)

            return content

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (429, 503) and attempt < _MAX_RETRIES:
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


def _budget_preflight(payload: dict[str, Any], *, tenant_id: str | None) -> None:
    try:
        if not settings.ai_budget_preflight_required and not tenant_id:
            return
        tenant = tenant_id or "default"
        messages = payload.get("messages") or []
        estimated_input = sum(
            _rough_token_count(str(message.get("content", ""))) + 4
            for message in messages
            if isinstance(message, dict)
        )
        estimated_output = int(payload.get("max_tokens") or 0)
        model = str(payload.get("model_override") or "")
        estimated_cost = 0.0
        if model:
            from app.domains.ai.model_registry import compute_cost_usd

            estimated_cost = compute_cost_usd(
                model,
                input_tokens=estimated_input,
                output_tokens=estimated_output,
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
            raise RuntimeError(
                f"Budget preflight blocked tenant={tenant} reason={status.reason} "
                f"projected_cost=${estimated_cost:.6f}"
            )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.debug("budget preflight skipped: %s", exc)


def _rough_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / 4))


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
        max_tokens=2000,
        project_id=project_id,
    )

    parsed = _parse_json_safe(raw)
    if parsed and isinstance(parsed, dict):
        return parsed
    logger.warning("AI analiz yanıtı JSON parse edilemedi, ham metin döndürülüyor")
    return {"raw": raw, "modules": [], "total_estimated_cases": 0}


def gateway_analyze_document_multimodal(
    doc_text: str,
    images: list[str],
    extra_instructions: str = "",
    project_id: str | None = None,
) -> dict[str, Any]:
    """Multimodal analiz: metin + bir veya daha fazla görsel.

    images: data URL formatında base64 görseller, ör.
            ``data:image/png;base64,iVBORw0KGgo...`` veya http(s) URL'leri.

    Vision-capable model gerektirir (GPT-4o, Claude 3+, Gemini 1.5+).
    Gateway model_override='vision' ile uygun modeli seçer; yoksa fallback metne döner.

    JSON çıktı şeması analyze_document task'ıyla aynıdır.
    """
    user_text = doc_text
    if extra_instructions:
        user_text += f"\n\n---\nEk Talimatlar:\n{extra_instructions}"
    if not user_text.strip():
        user_text = "Aşağıdaki görselleri analiz et ve test alanlarını çıkar."

    # OpenAI-uyumlu multimodal content blokları
    content_parts: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for img in images[:8]:  # güvenlik için maks 8 görsel
        if not img:
            continue
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": img, "detail": "high"},
        })

    if len(content_parts) == 1:
        # Hiç görsel yok → düz text analizine düş
        return gateway_analyze_document(
            doc_text=doc_text,
            extra_instructions=extra_instructions,
            project_id=project_id,
        )

    # PII redaction (sadece text)
    redacted_text, pii_count = _redact_pii(user_text)
    content_parts[0]["text"] = redacted_text

    # Sistem prompt registry'den
    reg_sys, _ = _resolve_from_registry("analyze_document", tenant_id=None)
    messages: list[dict[str, Any]] = []
    if reg_sys:
        messages.append({"role": "system", "content": reg_sys})
    messages.append({"role": "user", "content": content_parts})

    payload: dict[str, Any] = {
        "task_type": "analyze_document",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2500,
        "json_mode": True,
        "model_override": "vision",  # gateway router buna göre vision-capable model seçer
    }
    if project_id:
        payload["project_id"] = project_id

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
            content = data.get("content") or ""
            logger.info(
                "AI Gateway OK (multimodal) — task=analyze_document images=%d pii_redacted=%d (deneme %d)",
                len(content_parts) - 1, pii_count, attempt,
            )
            parsed = _parse_json_safe(content)
            if parsed and isinstance(parsed, dict):
                return parsed
            return {"raw": content, "modules": [], "total_estimated_cases": 0}
        except Exception as exc:
            last_exc = exc
            logger.warning("Multimodal gateway hata (deneme %d): %s", attempt, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF * (2 ** (attempt - 1)))

    # Tüm denemeler başarısız → düz text fallback
    logger.error("Multimodal gateway tüm denemeler başarısız, text fallback'e geçiliyor: %s", last_exc)
    return gateway_analyze_document(
        doc_text=doc_text,
        extra_instructions=extra_instructions,
        project_id=project_id,
    )


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
        resp = _get_http_client().post(
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
        resp = httpx.get(
            f"{AI_GATEWAY_BASE}/ai/embed/model",
            headers=_gateway_headers(),
            timeout=3.0,
        )
        return resp.status_code == 200
    except Exception:
        return False
