"""Engine (MaviYaka / port 5001) istemcisi için merkezi yardımcılar.

Daha önce her domain router'ı kendi başına
`os.environ.get("ENGINE_BASE_URL", "http://127.0.0.1:5001")` sabitini tutuyordu.
Bu üretimde iki büyük soruna yol açıyordu:

1. `.env` veya container'da `ENGINE_BASE_URL` değiştirildiğinde bazı router'lar
   hâlâ localhost'a istek atıyordu.
2. `ENGINE_INTERNAL_KEY` için `bgts-internal-key-change-me` varsayılanı
   prod'da kolayca kalıyordu.

Bu modül tek bir kaynak sağlar. Tüm router'lar `engine_base_url()` ve
`engine_auth_headers()` çağırmalıdır.
"""

from __future__ import annotations

import os

import httpx

from app.config import settings
from app.infra.resilience import CircuitBreakerOpen, bounded_timeout, get_breaker

# Engine downstream'i için paylaşılan circuit breaker adı. Bu modülün
# engine_request()'i ve gelecekte migrate edilecek tüm call-site'lar aynı ismi
# kullanmalı ki hata sayımı global olsun.
_ENGINE_BREAKER_NAME = "engine"


def engine_base_url() -> str:
    """Engine taban URL'sini döndürür. Sondaki `/` karakteri kesilir."""
    # Mevcut kod bazı yerlerde doğrudan `os.environ` okuyordu; test
    # geriye dönüklüğü için env önceliği korunur, yoksa settings kullanılır.
    return (os.environ.get("ENGINE_BASE_URL") or settings.engine_base_url).rstrip("/")


def engine_internal_key() -> str:
    """Engine internal auth anahtarını döndürür."""
    return os.environ.get("ENGINE_INTERNAL_KEY") or settings.engine_internal_key


def engine_auth_headers() -> dict[str, str]:
    """Engine'e yapılan internal isteklerde kullanılacak `X-Internal-Key` başlıkları."""
    return {"X-Internal-Key": engine_internal_key()}


def engine_request(
    method: str,
    path: str,
    *,
    json: object | None = None,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
    **kwargs: object,
) -> httpx.Response:
    """Engine'e bounded-timeout + circuit-breaker korumalı senkron HTTP isteği.

    NEDEN (panel Faz 1): yavaş/çökük engine, dağıtık call-site'larda connection
    havuzunu tüketip tüm tenant'ları 503'e düşürebilir. Bu sarmalayıcı:
      - timeout'u [0, MAX_DOWNSTREAM_TIMEOUT] aralığına sıkıştırır (sınırsız bekleme yok),
      - art arda 5xx/bağlantı hatasında breaker'ı OPEN'a çeker → sonraki istekler
        downstream'e gitmeden CircuitBreakerOpen ile hızlıca reddedilir.

    DİKKAT: uzun-süren streaming yürütmeler (ör. tspm canlı test stream'i, 300s)
    için DEĞİLDİR — onlar meşru olarak uzundur. Yalnızca kısa engine RPC'leri için.

    CircuitBreakerOpen fırlatabilir (breaker OPEN iken). Çağıran yakalamalı.
    """
    breaker = get_breaker(_ENGINE_BREAKER_NAME)
    breaker.before_call()  # OPEN ise CircuitBreakerOpen → fast-fail

    url = f"{engine_base_url()}{path if path.startswith('/') else '/' + path}"
    merged_headers = {**engine_auth_headers(), **(headers or {})}
    try:
        resp = httpx.request(
            method,
            url,
            json=json,
            headers=merged_headers,
            timeout=bounded_timeout(timeout, domain='engine'),
            **kwargs,
        )
    except httpx.RequestError:
        breaker.record_failure()  # bağlantı/timeout = downstream sağlıksız
        raise

    if resp.status_code >= 500:
        breaker.record_failure()  # 5xx = engine sağlıksız
    else:
        breaker.record_success()  # 2xx-4xx = engine ayakta (4xx client hatası)
    return resp


async def engine_request_async(
    method: str,
    path: str,
    *,
    json: object | None = None,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
    **kwargs: object,
) -> httpx.Response:
    """Engine'e bounded-timeout + circuit-breaker korumalı async HTTP isteği.

    `engine_request`'in async varyantı. FastAPI async route'larında kullan.
    Aynı breaker'ı paylaşır (global hata sayımı) — sync ve async RPC'ler
    bir havuzda izlenir.

    Geçerli use-case: tspm/cicd/automation router'larında async dispatcher route'lar
    için engine RPC'ler (sabit timeout'lu, meşru uzun değil).
    """
    breaker = get_breaker(_ENGINE_BREAKER_NAME)
    try:
        breaker.before_call()
    except CircuitBreakerOpen:
        raise  # async handler'ı tetikle

    url = f"{engine_base_url()}{path if path.startswith('/') else '/' + path}"
    merged_headers = {**engine_auth_headers(), **(headers or {})}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method,
                url,
                json=json,
                headers=merged_headers,
                timeout=bounded_timeout(timeout, domain='engine'),
                **kwargs,
            )
    except httpx.RequestError:
        breaker.record_failure()
        raise

    if resp.status_code >= 500:
        breaker.record_failure()
    else:
        breaker.record_success()
    return resp
