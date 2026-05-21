"""AI/LLM service — unified interface for OpenAI and Anthropic + RAG hafiza."""

from __future__ import annotations

import json
import inspect
import logging
import time
from functools import wraps
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# ── Cached LLM Clients (Singleton) ──────────────────────────────────────
# Her cagri icin yeni client olusturmak TCP + TLS overhead yaratir.
# Thread-safe: OpenAI/Anthropic client'lari dahili olarak thread-safe.
import threading

_client_lock = threading.Lock()
_openai_client = None
_anthropic_client = None
_ollama_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        with _client_lock:
            if _openai_client is None:
                from openai import OpenAI
                _openai_client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        with _client_lock:
            if _anthropic_client is None:
                from anthropic import Anthropic
                _anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_ollama_client():
    global _ollama_client
    if _ollama_client is None:
        with _client_lock:
            if _ollama_client is None:
                from openai import OpenAI
                _ollama_client = OpenAI(
                    api_key="ollama",
                    base_url=settings.ollama_base_url,
                )
    return _ollama_client


# ── Async LLM Clients (Singleton) ──────────────────────────────────────
import asyncio

_async_lock = asyncio.Lock()
_async_openai_client = None
_async_anthropic_client = None
_async_ollama_client = None


async def _get_async_openai_client():
    global _async_openai_client
    if _async_openai_client is None:
        async with _async_lock:
            if _async_openai_client is None:
                from openai import AsyncOpenAI
                _async_openai_client = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
    return _async_openai_client


async def _get_async_anthropic_client():
    global _async_anthropic_client
    if _async_anthropic_client is None:
        async with _async_lock:
            if _async_anthropic_client is None:
                from anthropic import AsyncAnthropic
                _async_anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _async_anthropic_client


async def _get_async_ollama_client():
    global _async_ollama_client
    if _async_ollama_client is None:
        async with _async_lock:
            if _async_ollama_client is None:
                from openai import AsyncOpenAI
                _async_ollama_client = AsyncOpenAI(
                    api_key="ollama",
                    base_url=settings.ollama_base_url,
                )
    return _async_ollama_client


async def shutdown_async_clients() -> None:
    """Close cached async LLM clients during app shutdown."""
    global _async_openai_client, _async_anthropic_client, _async_ollama_client

    async with _async_lock:
        clients = [
            ("openai", _async_openai_client),
            ("anthropic", _async_anthropic_client),
            ("ollama", _async_ollama_client),
        ]

        for client_name, client in clients:
            if client is None:
                continue

            try:
                close_method = getattr(client, "close", None) or getattr(client, "aclose", None)
                if close_method is not None:
                    result = close_method()
                    if inspect.isawaitable(result):
                        await result
                logger.info("Async %s client kapatildi.", client_name)
            except Exception:
                logger.debug("Async %s client kapatilamadi.", client_name, exc_info=True)

        _async_openai_client = None
        _async_anthropic_client = None
        _async_ollama_client = None


def _allow_provider_fallback() -> bool:
    return bool(getattr(settings, "allow_provider_fallback", False))


def _resolve_effective_provider() -> str:
    provider = settings.ai_provider
    if provider == "anthropic":
        if settings.anthropic_api_key:
            return "anthropic"
        if _allow_provider_fallback() and settings.openai_api_key:
            logger.warning("AI provider fallback: anthropic secili ama ANTHROPIC_API_KEY yok; openai kullaniliyor")
            return "openai"
        raise RuntimeError(
            "AI provider 'anthropic' secili ama ANTHROPIC_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )

    if provider == "openai":
        if settings.openai_api_key:
            return "openai"
        if _allow_provider_fallback() and settings.anthropic_api_key:
            logger.warning("AI provider fallback: openai secili ama OPENAI_API_KEY yok; anthropic kullaniliyor")
            return "anthropic"
        raise RuntimeError(
            "AI provider 'openai' secili ama OPENAI_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )

    if provider == "ollama":
        return "ollama"

    raise RuntimeError(f"Desteklenmeyen AI provider: {provider}")


# ── LLM Retry Decorator ──────────────────────────────────────────────────────
MAX_LLM_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # saniye


def _with_retry(func):
    """LLM cagirilari icin exponential backoff retry decorator."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_error: Exception | None = None
        for attempt in range(1, MAX_LLM_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_LLM_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "LLM %s retry %d/%d (%.1fs): %s",
                        func.__name__, attempt, MAX_LLM_RETRIES, wait, str(e)[:120],
                    )
                    time.sleep(wait)
                else:
                    logger.error("LLM %s %d denemede basarisiz: %s", func.__name__, MAX_LLM_RETRIES, e)
        raise last_error  # type: ignore[misc]
    return wrapper


def _with_async_retry(func):
    """Async LLM cagrilari icin exponential backoff retry decorator."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_error: Exception | None = None
        for attempt in range(1, MAX_LLM_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_LLM_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Async LLM %s retry %d/%d (%.1fs): %s",
                        func.__name__, attempt, MAX_LLM_RETRIES, wait, str(e)[:120],
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Async LLM %s %d denemede basarisiz: %s", func.__name__, MAX_LLM_RETRIES, e)
        raise last_error  # type: ignore[misc]
    return wrapper


def _resolve_trace_model(provider: str, requested_model: str | None) -> str:
    if requested_model:
        return requested_model
    if provider == "ollama":
        return getattr(settings, "ollama_model_analyst", "qwen2.5:32b")
    if provider == "anthropic":
        return settings.anthropic_model
    return settings.openai_model


def _estimate_trace_tokens(system: str, user_content: str, response: str) -> tuple[int, int, int]:
    prompt_tokens = (len(system) + len(user_content)) // 3
    completion_tokens = len(response) // 3
    return prompt_tokens, completion_tokens, prompt_tokens + completion_tokens


def _get_rag_context(
    query: str,
    sources: list[str] | None = None,
    top_k: int = 5,
    project_id: str | None = None,
) -> str:
    """
    KnowledgeStore'dan sorguyla ilgili bağlamı çek.
    Hata olursa sessizce boş string döndürür — LLM çağrısını asla engelleme.
    """
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        if not project_id:
            return ""
        store = KnowledgeStore(project_id=project_id)
        try:
            chunks = store.retrieve(query, top_k=top_k, sources=sources)
        finally:
            store.close()
        if not chunks:
            return ""
        lines = []
        for c in chunks:
            source_label = c.source.replace("_", " ").title()
            lines.append(f"[{source_label} | benzerlik: {c.similarity:.2f}]\n{c.content}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.debug("RAG context alınamadı: %s", e)
        return ""


async def _get_rag_context_async(
    query: str,
    sources: list[str] | None = None,
    top_k: int = 5,
    project_id: str | None = None,
) -> str:
    """
    KnowledgeStore'dan async olarak bağlam çek.
    Event loop'u bloklamaz — asyncio.to_thread kullanır.
    Hata olursa sessizce boş string döndürür.
    """
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        if not project_id:
            return ""
        store = KnowledgeStore(project_id=project_id)
        try:
            chunks = await store.retrieve_async(query, top_k=top_k, sources=sources)
        finally:
            store.close()
        if not chunks:
            return ""
        lines = []
        for c in chunks:
            source_label = c.source.replace("_", " ").title()
            lines.append(f"[{source_label} | benzerlik: {c.similarity:.2f}]\n{c.content}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.debug("Async RAG context alınamadı: %s", e)
        return ""


SYSTEM_PROMPT_CHAT = """\
Sen TestwrightAI (Test Intelligence Platform) için bir AI asistansın. Türkçe yanıt ver.

## Görevin
Test mühendislerine PROJEYE ÖZGÜ yardım sağlamak:
- Test senaryoları oluşturma ve iyileştirme
- Test sonuçlarını analiz etme
- Kapsam boşluklarını tespit etme
- BDD/Gherkin formatında senaryo yazma
- Test stratejisi önerileri sunma
- Hata kalıplarını analiz etme

## Önemli Kurallar
- "Proje Hafızası" bölümünde sağlanan GERÇEK proje bağlamını MUTLAKA kullan
- Cevaplarında projede kullanılan gerçek modül, tablo, endpoint isimlerini referans al
- Generic tavsiyeler yerine projeye özgü, uygulanabilir öneriler ver
- Geçmiş hata kalıpları ve öğrenimler varsa onları referans al

Yanıtların kısa, net ve uygulanabilir olsun. Gerektiğinde kod blokları ve yapılandırılmış çıktılar kullan.
"""

SYSTEM_PROMPT_ANALYSIS = """\
Sen bir kıdemli QA analisti ve test mühendisisin. Türkçe yanıt ver.
Sana verilen test koşu sonuçlarını analiz et ve şu JSON formatında yanıt ver:
{
  "summary": "Genel durum özeti",
  "insights": [
    {
      "category": "failure_pattern|coverage_gap|flaky_test|optimization|risk",
      "severity": "info|warning|critical",
      "title": "Kısa başlık",
      "description": "Detaylı açıklama",
      "affected_scenarios": ["senaryo id veya başlıkları"],
      "suggestion": "İyileştirme önerisi"
    }
  ],
  "recommendations": ["Genel öneriler listesi"]
}
"""

SYSTEM_PROMPT_SCENARIO_GEN = """\
Sen bir kıdemli QA mühendisisin. Türkçe yanıt ver.
Kullanıcının açıklamasına göre test senaryoları üret. MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "scenarios": [
    {
      "title": "Senaryo başlığı",
      "description": "Açıklama",
      "steps": [
        {"keyword": "Olduğu gibi", "text": "adım açıklaması"},
        {"keyword": "Eğer", "text": "adım açıklaması"},
        {"keyword": "O zaman", "text": "adım açıklaması"}
      ],
      "tags": ["pozitif", "login"],
      "priority": "high|medium|low"
    }
  ]
}
Pozitif, negatif ve sınır değer senaryolarını dahil et.
"""

SYSTEM_PROMPT_TESTDATA = """\
Sen bir test veri mühendisisin. Türkçe yanıt ver.
Kullanıcının açıklamasına göre test verisi üret. MUTLAKA aşağıdaki JSON formatında yanıt ver:
{
  "columns": [
    {"name": "kolon_adı", "type": "string|number|boolean|date", "description": "açıklama"}
  ],
  "rows": [
    {"kolon_adı": "değer", ...}
  ]
}
Gerçekçi Türkçe veriler kullan. Sınır değerler ve edge case'leri dahil et.
"""


@_with_retry
def _call_openai(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY ayarlanmamis.")

    client = _get_openai_client()
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_content})

    kwargs: dict[str, Any] = {
        "model": model or settings.openai_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else 0.3,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


@_with_retry
def _call_anthropic(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY ayarlanmamis.")

    client = _get_anthropic_client()
    messages: list[dict[str, str]] = []

    if history:
        messages.extend(history)

    prompt = user_content
    if json_mode:
        prompt += "\n\nMUTLAKA gecerli JSON formatinda yanit ver, baska bir sey yazma."

    messages.append({"role": "user", "content": prompt})

    response = client.messages.create(
        model=model or settings.anthropic_model,
        max_tokens=max_tokens or 4096,
        system=system,
        messages=messages,
        temperature=temperature if temperature is not None else 0.3,
    )
    return response.content[0].text


@_with_retry
def _call_ollama(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    client = _get_ollama_client()
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_content})

    resolved_model = model or getattr(settings, "ollama_model_analyst", "qwen2.5:32b")
    num_predict = min(max_tokens or 1024, 4096)

    # Model bazlı context window — büyük modeller daha fazla context kullanabilir
    _OLLAMA_CTX = {
        "qwen2.5:32b": 16384,       # 32K destekler, 16K güvenli kullanım
        "qwen2.5:14b": 8192,        # 8K güvenli
        "mistral:latest": 4096,     # Chat icin kucuk context yeterli
        "mistral:7b": 4096,
        "qwen2.5-coder:7b": 8192,
        "llama3.1:8b": 4096,
    }
    num_ctx = _OLLAMA_CTX.get(resolved_model, 4096)

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else 0.3,
        "extra_body": {"num_ctx": num_ctx, "num_predict": num_predict},
    }
    if json_mode:
        kwargs["extra_body"]["format"] = "json"

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


# ── Async Provider Calls ────────────────────────────────────────────────────

@_with_async_retry
async def _async_call_openai(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY ayarlanmamis.")

    client = await _get_async_openai_client()
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_content})

    kwargs: dict[str, Any] = {
        "model": model or settings.openai_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else 0.3,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


@_with_async_retry
async def _async_call_anthropic(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY ayarlanmamis.")

    client = await _get_async_anthropic_client()
    messages: list[dict[str, str]] = []

    if history:
        messages.extend(history)

    prompt = user_content
    if json_mode:
        prompt += "\n\nMUTLAKA gecerli JSON formatinda yanit ver, baska bir sey yazma."

    messages.append({"role": "user", "content": prompt})

    response = await client.messages.create(
        model=model or settings.anthropic_model,
        max_tokens=max_tokens or 4096,
        system=system,
        messages=messages,
        temperature=temperature if temperature is not None else 0.3,
    )
    return response.content[0].text


@_with_async_retry
async def _async_call_ollama(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    client = await _get_async_ollama_client()
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_content})

    resolved_model = model or getattr(settings, "ollama_model_analyst", "qwen2.5:32b")
    num_predict = min(max_tokens or 1024, 4096)

    _OLLAMA_CTX = {
        "qwen2.5:32b": 16384,
        "qwen2.5:14b": 8192,
        "mistral:latest": 4096,     # Chat icin kucuk context yeterli
        "mistral:7b": 4096,
        "qwen2.5-coder:7b": 8192,
        "llama3.1:8b": 4096,
    }
    num_ctx = _OLLAMA_CTX.get(resolved_model, 4096)

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else 0.3,
        "extra_body": {"num_ctx": num_ctx, "num_predict": num_predict},
    }
    if json_mode:
        kwargs["extra_body"]["format"] = "json"

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def call_llm(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    _trace_agent: str = "chat_service",
    _trace_phase: str | None = None,
    _trace_run_id: str | None = None,
    _trace_project_id: str | None = None,
    _trace_user_id: str | None = None,
    _trace_task_type: str | None = None,
) -> str:
    """Unified LLM call — provider'a gore yonlendir, temperature/model parametrik. Trace kaydeder."""
    provider = _resolve_effective_provider()
    kw: dict[str, Any] = dict(
        json_mode=json_mode, history=history,
        temperature=temperature, model=model, max_tokens=max_tokens,
    )

    resolved_model = _resolve_trace_model(provider, model)

    t0 = time.time()
    success = True
    error_msg = ""
    result = ""

    try:
        if provider == "ollama":
            result = _call_ollama(system, user_content, **kw)
        elif provider == "anthropic":
            result = _call_anthropic(system, user_content, **kw)
        else:
            result = _call_openai(system, user_content, **kw)
        return result
    except Exception as exc:
        success = False
        error_msg = str(exc)[:2000]
        raise
    finally:
        # ── Trace kaydi (fire-and-forget) ──
        latency_ms = int((time.time() - t0) * 1000)

        _prompt_tokens = None
        _completion_tokens = None
        _total_tokens = None
        try:
            _prompt_tokens, _completion_tokens, _total_tokens = _estimate_trace_tokens(system, user_content, result)
        except Exception:
            pass

        try:
            from app.domains.ai.llm_trace import log_llm_call
            log_llm_call(
                agent_name=_trace_agent,
                model=resolved_model or "unknown",
                system_prompt=system,
                user_prompt=user_content,
                response=result,
                latency_ms=latency_ms,
                success=success,
                error_message=error_msg,
                temperature=temperature,
                max_tokens=max_tokens,
                run_id=_trace_run_id,
                phase=_trace_phase,
                prompt_tokens=_prompt_tokens,
                completion_tokens=_completion_tokens,
                total_tokens=_total_tokens,
                project_id=_trace_project_id,
                user_id=_trace_user_id,
                provider=provider,
                task_type=_trace_task_type or _trace_phase or _trace_agent,
                metadata={
                    "history_length": len(history or []),
                    "json_mode": json_mode,
                },
            )
        except Exception:
            pass  # Trace asla pipeline'i kirmaz


async def async_call_llm(
    system: str,
    user_content: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    _trace_agent: str = "chat_service",
    _trace_phase: str | None = None,
    _trace_run_id: str | None = None,
    _trace_project_id: str | None = None,
    _trace_user_id: str | None = None,
    _trace_task_type: str | None = None,
) -> str:
    """Async unified LLM call — non-blocking, FastAPI uyumlu. Trace kaydeder."""
    provider = _resolve_effective_provider()
    kw: dict[str, Any] = dict(
        json_mode=json_mode, history=history,
        temperature=temperature, model=model, max_tokens=max_tokens,
    )

    resolved_model = _resolve_trace_model(provider, model)

    t0 = time.time()
    success = True
    error_msg = ""
    result = ""

    try:
        if provider == "ollama":
            result = await _async_call_ollama(system, user_content, **kw)
        elif provider == "anthropic":
            result = await _async_call_anthropic(system, user_content, **kw)
        else:
            result = await _async_call_openai(system, user_content, **kw)
        return result
    except Exception as exc:
        success = False
        error_msg = str(exc)[:2000]
        raise
    finally:
        # ── Trace kaydi (fire-and-forget, async) ──
        latency_ms = int((time.time() - t0) * 1000)

        _prompt_tokens = None
        _completion_tokens = None
        _total_tokens = None
        try:
            _prompt_tokens, _completion_tokens, _total_tokens = _estimate_trace_tokens(system, user_content, result)
        except Exception:
            pass

        _trace_kwargs = dict(
            agent_name=_trace_agent,
            model=resolved_model or "unknown",
            system_prompt=system,
            user_prompt=user_content,
            response=result,
            latency_ms=latency_ms,
            success=success,
            error_message=error_msg,
            temperature=temperature,
            max_tokens=max_tokens,
            run_id=_trace_run_id,
            phase=_trace_phase,
            prompt_tokens=_prompt_tokens,
            completion_tokens=_completion_tokens,
            total_tokens=_total_tokens,
            project_id=_trace_project_id,
            user_id=_trace_user_id,
            provider=provider,
            task_type=_trace_task_type or _trace_phase or _trace_agent,
            metadata={
                "history_length": len(history or []),
                "json_mode": json_mode,
            },
        )
        try:
            loop = asyncio.get_running_loop()
            from app.domains.ai.llm_trace import log_llm_call
            loop.run_in_executor(None, lambda: log_llm_call(**_trace_kwargs))
        except Exception:
            pass  # Trace asla pipeline'i kirmaz


def _parse_json_response(raw: str) -> dict:
    """
    Gelismis JSON parser — LLM ciktilarindaki yaygin sorunlari handle eder.

    Strateji sirasi:
      1. Dogrudan parse
      2. Markdown kod blogu temizleme (```json ... ```)
      3. Ilk { ... } veya [ ... ] extraction (brace matching)
      4. Trailing comma temizleme
      5. Tek tirnak → cift tirnak donusumu
    """
    if not raw or not raw.strip():
        raise ValueError("Bos LLM yaniti — JSON parse edilemiyor.")

    raw = raw.strip()

    # 1. Dogrudan parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Markdown kod blogu temizleme (```json\n...\n``` veya ```\n...\n```)
    cleaned = raw
    if "```" in cleaned:
        import re as _re
        # ```json ... ``` veya ``` ... ```
        match = _re.search(r'```(?:json|JSON)?\s*\n(.*?)\n\s*```', cleaned, _re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # 3. Ilk { ... } veya [ ... ] extraction (brace matching)
    for open_ch, close_ch in [('{', '}'), ('[', ']')]:
        start = raw.find(open_ch)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape_next = False
        end = -1
        for i in range(start, len(raw)):
            ch = raw[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > start:
            extracted = raw[start:end]
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                # 4. Trailing comma temizleme
                import re as _re
                no_trailing = _re.sub(r',\s*([}\]])', r'\1', extracted)
                try:
                    return json.loads(no_trailing)
                except json.JSONDecodeError:
                    pass

    # 5. Tek tirnak → cift tirnak donusumu (son care)
    try:
        import re as _re
        # Sadece key/value etrafindaki tek tirnaklari degistir
        single_to_double = raw.replace("'", '"')
        return json.loads(single_to_double)
    except (json.JSONDecodeError, Exception):
        pass

    logger.error("JSON parse basarisiz (5 strateji denendi): %s", raw[:500])
    raise ValueError("AI yaniti gecerli JSON formatinda degil — tum parse stratejileri basarisiz.")


# ── Public API ────────────────────────────────────────────────────────

def chat_completion(
    user_message: str,
    history: list[dict] | None = None,
    context: str = "",
    project_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """
    RAG destekli sohbet tamamlama.
    Kullanıcı mesajıyla ilgili geçmiş execution, insight ve feature bağlamı
    otomatik olarak system prompt'a eklenir.
    """
    rag = _get_rag_context(
        user_message,
        sources=["execution", "error_pattern", "chat_history"],
        top_k=3,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_CHAT
    if rag:
        system += f"\n\n## Proje Hafızasından İlgili Bağlam\nAşağıdaki bilgiler projenin gerçek verilerinden otomatik çekilmiştir:\n{rag}"
    if context:
        system += f"\n\n## Ek Proje Bağlamı\n{context}"
    return call_llm(
        system,
        user_message,
        history=history,
        model=_resolve_chat_model(),
        _trace_project_id=project_id,
        _trace_user_id=user_id,
        _trace_task_type="chat",
        _trace_phase="chat",
    )


def _build_chat_system_prompt(
    user_message: str,
    context: str = "",
    project_id: str | None = None,
) -> str:
    """Build the RAG-augmented system prompt for chat (shared by sync and stream)."""
    rag = _get_rag_context(
        user_message,
        sources=["execution", "error_pattern", "chat_history"],
        top_k=3,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_CHAT
    if rag:
        system += f"\n\n## Proje Hafızasından İlgili Bağlam\nAşağıdaki bilgiler projenin gerçek verilerinden otomatik çekilmiştir:\n{rag}"
    if context:
        system += f"\n\n## Ek Proje Bağlamı\n{context}"
    return system


async def _build_chat_system_prompt_async(
    user_message: str,
    context: str = "",
    project_id: str | None = None,
) -> str:
    """Build the RAG-augmented system prompt for chat (async version)."""
    rag = await _get_rag_context_async(
        user_message,
        sources=["execution", "error_pattern", "chat_history"],
        top_k=3,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_CHAT
    if rag:
        system += f"\n\n## Proje Hafızasından İlgili Bağlam\nAşağıdaki bilgiler projenin gerçek verilerinden otomatik çekilmiştir:\n{rag}"
    if context:
        system += f"\n\n## Ek Proje Bağlamı\n{context}"
    return system


def chat_completion_stream(
    user_message: str,
    history: list[dict] | None = None,
    context: str = "",
    project_id: str | None = None,
):
    """
    RAG destekli streaming sohbet tamamlama.
    OpenAI-uyumlu SDK'nın stream=True modunu kullanarak
    her token chunk'ını yield eder.

    Yields:
        str: Her bir token/chunk metni.

    Raises:
        ValueError: API key ayarlanmamışsa.
        Exception: LLM çağrısı başarısız olursa.
    """
    system = _build_chat_system_prompt(user_message, context, project_id=project_id)
    provider = _resolve_effective_provider()

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    if provider == "anthropic":
        # Anthropic streaming
        yield from _stream_anthropic(system, messages, history)
    elif provider == "ollama":
        # Ollama uses OpenAI-compatible API — chat icin hizli model
        yield from _stream_openai_compatible(
            client=_get_ollama_client(),
            model=_resolve_chat_model() or settings.ollama_model_fast,
            messages=messages,
        )
    else:
        # OpenAI (default)
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY ayarlanmamis.")
        yield from _stream_openai_compatible(
            client=_get_openai_client(),
            model=settings.openai_model,
            messages=messages,
        )


def _stream_openai_compatible(
    client,
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """OpenAI-uyumlu API'den streaming token'ları yield eder."""
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3 if temperature is None else temperature,
            max_tokens=2048 if max_tokens is None else max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error("Streaming LLM hatası (%s): %s", model, e)
        raise


def _stream_anthropic(
    system: str,
    messages: list[dict[str, str]],
    history: list[dict] | None = None,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """Anthropic SDK streaming — text delta'ları yield eder."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY ayarlanmamis.")

    client = _get_anthropic_client()

    # Anthropic expects system as a separate param, not in messages
    # Filter out the system message from messages list
    api_messages = [m for m in messages if m.get("role") != "system"]

    try:
        with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=2048 if max_tokens is None else max_tokens,
            system=system,
            messages=api_messages,
            temperature=0.3 if temperature is None else temperature,
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error("Streaming Anthropic hatası: %s", e)
        raise


def analyze_test_results(
    execution_data: str,
    question: str = "",
    project_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    """
    RAG destekli test sonucu analizi.
    Geçmişteki benzer hata pattern'ları ve insight'lar bağlama eklenir.
    """
    query = question or execution_data[:300]
    rag = _get_rag_context(
        query,
        sources=["insight", "error_pattern", "execution"],
        top_k=4,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_ANALYSIS
    if rag:
        system += f"\n\n## Geçmiş Benzer Durumlar\n{rag}"
    user_content = f"Test Koşu Verileri:\n{execution_data}"
    if question:
        user_content += f"\n\nKullanıcı Sorusu: {question}"
    raw = call_llm(
        system,
        user_content,
        json_mode=True,
        _trace_project_id=project_id,
        _trace_user_id=user_id,
        _trace_task_type="test_analysis",
        _trace_phase="analysis",
    )
    return _parse_json_response(raw)


def generate_scenarios(
    description: str,
    context: str = "",
    count: int = 5,
    project_id: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """
    RAG destekli senaryo üretimi.
    Projedeki mevcut BDD feature dosyaları bağlama eklenerek
    projeye özgü stil ve terminoloji korunur.
    """
    rag = _get_rag_context(
        description,
        sources=["feature_file", "docs"],
        top_k=4,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_SCENARIO_GEN
    if rag:
        system += f"\n\n## Projedeki Mevcut Senaryo Örnekleri\n{rag}\n\nYukarıdaki örneklerin stil ve terminolojisini kullan."
    user_content = f"Açıklama: {description}\nİstenen senaryo sayısı: {count}"
    if context:
        user_content += f"\n\nEk Bağlam:\n{context}"
    raw = call_llm(
        system,
        user_content,
        json_mode=True,
        _trace_project_id=project_id,
        _trace_user_id=user_id,
        _trace_task_type="scenario_generation",
        _trace_phase="scenarios",
    )
    parsed = _parse_json_response(raw)
    return parsed.get("scenarios", [])


def generate_test_data(description: str, columns: list[dict] | None = None, row_count: int = 10) -> dict:
    user_content = f"Açıklama: {description}\nİstenen satır sayısı: {row_count}"
    if columns:
        user_content += f"\n\nMevcut kolon tanımları:\n{json.dumps(columns, ensure_ascii=False)}"
    raw = call_llm(
        SYSTEM_PROMPT_TESTDATA,
        user_content,
        json_mode=True,
        _trace_task_type="test_data_generation",
        _trace_phase="test_data",
    )
    return _parse_json_response(raw)


# ═══ Async Public API ═══════════════════════════════════════════════════


def _resolve_chat_model() -> str | None:
    """Chat icin hizli model sec (Ollama'da mistral, diger provider'larda None=default)."""
    provider = _resolve_effective_provider()
    if provider == "ollama":
        return getattr(settings, "ollama_model_chat", None) or settings.ollama_model_fast
    return None  # OpenAI/Anthropic default model zaten uygun


async def async_chat_completion(
    user_message: str,
    history: list[dict] | None = None,
    context: str = "",
    project_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Async RAG destekli sohbet tamamlama."""
    system = await _build_chat_system_prompt_async(user_message, context, project_id=project_id)
    return await async_call_llm(
        system,
        user_message,
        history=history,
        model=_resolve_chat_model(),
        _trace_project_id=project_id,
        _trace_user_id=user_id,
        _trace_task_type="chat",
        _trace_phase="chat",
    )


async def async_chat_completion_stream(
    user_message: str,
    history: list[dict] | None = None,
    context: str = "",
    project_id: str | None = None,
    user_id: str | None = None,
):
    """Async RAG destekli streaming sohbet — AsyncGenerator olarak token yield eder."""
    system = await _build_chat_system_prompt_async(user_message, context, project_id=project_id)
    async for token in async_stream_llm(
        system,
        user_message,
        history=history,
        model=_resolve_chat_model(),
        _trace_agent="chat_stream",
        _trace_phase="stream_chat",
        _trace_project_id=project_id,
        _trace_user_id=user_id,
    ):
        yield token


async def _async_stream_openai_compatible(
    client,
    model: str,
    messages: list[dict],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """Async OpenAI-uyumlu streaming."""
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3 if temperature is None else temperature,
        max_tokens=2048 if max_tokens is None else max_tokens,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def _async_stream_anthropic(
    system: str,
    messages: list[dict],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """Async Anthropic streaming."""
    client = await _get_async_anthropic_client()
    api_messages = [m for m in messages if m.get("role") != "system"]
    async with client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=2048 if max_tokens is None else max_tokens,
        system=system,
        messages=api_messages,
        temperature=0.3 if temperature is None else temperature,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def async_analyze_test_results(
    execution_data: str,
    question: str = "",
    project_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    """Async RAG destekli test sonucu analizi."""
    query = question or execution_data[:300]
    rag = await _get_rag_context_async(
        query,
        sources=["insight", "error_pattern"],
        top_k=3,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_ANALYSIS
    if rag:
        system += f"\n\n## Gecmis Benzer Durumlar\n{rag}"
    user_content = f"Test Kosu Verileri:\n{execution_data}"
    if question:
        user_content += f"\n\nKullanici Sorusu: {question}"
    raw = await async_call_llm(
        system,
        user_content,
        json_mode=True,
        _trace_project_id=project_id,
        _trace_user_id=user_id,
        _trace_task_type="test_analysis",
        _trace_phase="analysis",
    )
    return _parse_json_response(raw)


async def async_generate_scenarios(
    description: str,
    context: str = "",
    count: int = 5,
    project_id: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """Async RAG destekli senaryo uretimi."""
    rag = await _get_rag_context_async(
        description,
        sources=["feature_file", "docs"],
        top_k=3,
        project_id=project_id,
    )
    system = SYSTEM_PROMPT_SCENARIO_GEN
    if rag:
        system += f"\n\n## Projedeki Mevcut Senaryo Ornekleri\n{rag}\n\nYukaridaki orneklerin stil ve terminolojisini kullan."
    user_content = f"Aciklama: {description}\nIstenen senaryo sayisi: {count}"
    if context:
        user_content += f"\n\nEk Baglam:\n{context}"
    raw = await async_call_llm(
        system,
        user_content,
        json_mode=True,
        _trace_project_id=project_id,
        _trace_user_id=user_id,
        _trace_task_type="scenario_generation",
        _trace_phase="scenarios",
    )
    parsed = _parse_json_response(raw)
    return parsed.get("scenarios", [])


async def async_generate_test_data(description: str, columns: list[dict] | None = None, row_count: int = 10) -> dict:
    """Async test verisi uretimi."""
    user_content = f"Aciklama: {description}\nIstenen satir sayisi: {row_count}"
    if columns:
        user_content += f"\n\nMevcut kolon tanimlari:\n{json.dumps(columns, ensure_ascii=False)}"
    raw = await async_call_llm(
        SYSTEM_PROMPT_TESTDATA,
        user_content,
        json_mode=True,
        _trace_task_type="test_data_generation",
        _trace_phase="test_data",
    )
    return _parse_json_response(raw)


# ── Async Streaming for ALL LLM Operations ──────────────────────────────


async def async_stream_llm(
    system: str,
    user_content: str,
    *,
    history: list[dict] | None = None,
    temperature: float | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    _trace_agent: str = "streaming_service",
    _trace_phase: str | None = None,
    _trace_run_id: str | None = None,
    _trace_project_id: str | None = None,
    _trace_user_id: str | None = None,
    _trace_task_type: str | None = None,
):
    """
    Genel amacli async streaming LLM — chat disinda da kullanilabilir.
    Senaryo uretimi, test uretimi, analiz gibi islemleri de stream edebilir.
    """
    provider = _resolve_effective_provider()
    resolved_model = _resolve_trace_model(provider, model)
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    collected_tokens: list[str] = []
    success = True
    error_msg = ""
    t0 = time.time()

    try:
        if provider == "anthropic":
            async for token in _async_stream_anthropic(
                system,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                collected_tokens.append(token)
                yield token
        elif provider == "ollama":
            client = await _get_async_ollama_client()
            async for token in _async_stream_openai_compatible(
                client,
                resolved_model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                collected_tokens.append(token)
                yield token
        else:
            client = await _get_async_openai_client()
            async for token in _async_stream_openai_compatible(
                client,
                resolved_model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                collected_tokens.append(token)
                yield token
    except Exception as exc:
        success = False
        error_msg = str(exc)[:2000]
        raise
    finally:
        response = "".join(collected_tokens)
        latency_ms = int((time.time() - t0) * 1000)

        try:
            prompt_tokens, completion_tokens, total_tokens = _estimate_trace_tokens(system, user_content, response)
        except Exception:
            prompt_tokens = completion_tokens = total_tokens = None

        _trace_kwargs = dict(
            agent_name=_trace_agent,
            model=resolved_model,
            system_prompt=system,
            user_prompt=user_content,
            response=response,
            latency_ms=latency_ms,
            success=success,
            error_message=error_msg,
            run_id=_trace_run_id,
            phase=_trace_phase,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            project_id=_trace_project_id,
            user_id=_trace_user_id,
            provider=provider,
            task_type=_trace_task_type or _trace_phase or _trace_agent,
            is_streaming=True,
            metadata={
                "history_length": len(history or []),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        try:
            loop = asyncio.get_running_loop()
            from app.domains.ai.llm_trace import log_llm_call
            loop.run_in_executor(None, lambda: log_llm_call(**_trace_kwargs))
        except Exception:
            pass  # Trace asla pipeline'i kirmaz
