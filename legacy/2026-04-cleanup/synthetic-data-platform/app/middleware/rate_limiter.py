"""
API Rate Limiting Middleware.

IP bazlı sliding window rate limiting ile API çağrılarını sınırlar.
Endpoint bazlı farklı limitler, whitelist desteği ve standart
rate limit header'ları sağlar.

Özellikler:
  - IP bazlı sliding window algoritması
  - Endpoint bazlı farklı limitler (upload, generate, diğer)
  - X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset header'ları
  - Whitelist IP desteği
  - 429 Too Many Requests response
  - Thread-safe in-memory storage
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


# ═══════════════════════════════════════════════════════════════════════
# Veri Yapıları
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class RateLimitRule:
    """
    Bir endpoint grubu için rate limit kuralı.

    Attributes:
        max_requests: Zaman penceresi içindeki maksimum istek sayısı.
        window_seconds: Sliding window süresi (saniye).
        description: Kuralın Türkçe açıklaması.
    """
    max_requests: int
    window_seconds: int = 60
    description: str = ""


@dataclass
class ClientWindow:
    """
    Bir istemcinin sliding window durumu.

    Attributes:
        timestamps: İstek zaman damgaları listesi.
        lock: Thread-safe erişim için kilit.
    """
    timestamps: list[float] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


# ═══════════════════════════════════════════════════════════════════════
# Varsayılan Rate Limit Kuralları
# ═══════════════════════════════════════════════════════════════════════

# Endpoint pattern → RateLimitRule eşleştirmesi
DEFAULT_RULES: dict[str, RateLimitRule] = {
    # Dosya yükleme — yoğun kaynak tüketimi
    "upload": RateLimitRule(
        max_requests=10,
        window_seconds=60,
        description="Dosya yükleme: 10 istek/dakika",
    ),
    # Sentetik veri üretimi — en ağır işlem
    "generate": RateLimitRule(
        max_requests=5,
        window_seconds=60,
        description="Veri üretimi: 5 istek/dakika",
    ),
    # Analiz işlemleri
    "analyze": RateLimitRule(
        max_requests=15,
        window_seconds=60,
        description="Analiz işlemleri: 15 istek/dakika",
    ),
    # Genel API çağrıları
    "default": RateLimitRule(
        max_requests=60,
        window_seconds=60,
        description="Genel API: 60 istek/dakika",
    ),
}

# Endpoint yolu → kural grubu eşleştirmesi
ENDPOINT_RULE_MAP: dict[str, str] = {
    "/api/v1/upload": "upload",
    "/api/v1/generate": "generate",
    "/api/v1/generate-scenario": "generate",
    "/api/v1/generate-natural": "generate",
    "/api/v1/analyze": "analyze",
    "/api/v1/classify": "analyze",
    "/api/v1/detect-pii": "analyze",
    "/api/v1/infer-rules": "analyze",
    "/api/v1/infer-relationships": "analyze",
}


# ═══════════════════════════════════════════════════════════════════════
# Rate Limit Storage — In-Memory Sliding Window
# ═══════════════════════════════════════════════════════════════════════


class RateLimitStorage:
    """
    Thread-safe in-memory rate limit depolama.

    Her IP + endpoint grubu çifti için sliding window zaman damgalarını
    saklar. Belirli aralıklarla eski kayıtları temizler.
    """

    def __init__(self, cleanup_interval: int = 300):
        """
        Args:
            cleanup_interval: Eski kayıtları temizleme aralığı (saniye).
        """
        self._windows: dict[str, ClientWindow] = defaultdict(ClientWindow)
        self._global_lock = threading.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def _make_key(self, client_ip: str, rule_group: str) -> str:
        """IP + kural grubu için benzersiz anahtar oluştur."""
        return f"{client_ip}:{rule_group}"

    def _cleanup_expired(self, now: float, max_window: int = 300) -> None:
        """Süresi dolmuş zaman damgalarını temizle."""
        if now - self._last_cleanup < self._cleanup_interval:
            return

        with self._global_lock:
            expired_keys = []
            for key, window in self._windows.items():
                with window.lock:
                    window.timestamps = [
                        ts for ts in window.timestamps
                        if now - ts < max_window
                    ]
                    if not window.timestamps:
                        expired_keys.append(key)

            for key in expired_keys:
                del self._windows[key]

            self._last_cleanup = now

    def check_and_record(
        self, client_ip: str, rule_group: str, rule: RateLimitRule
    ) -> tuple[bool, int, int, float]:
        """
        İstek kontrolü yap ve kaydet.

        Args:
            client_ip: İstemci IP adresi.
            rule_group: Kural grubu adı.
            rule: Uygulanacak rate limit kuralı.

        Returns:
            Tuple: (izin_verildi, limit, kalan, reset_zamanı)
        """
        now = time.time()
        self._cleanup_expired(now)

        key = self._make_key(client_ip, rule_group)
        window = self._windows[key]

        with window.lock:
            # Sliding window: süresi dolmuş kayıtları temizle
            cutoff = now - rule.window_seconds
            window.timestamps = [
                ts for ts in window.timestamps if ts > cutoff
            ]

            current_count = len(window.timestamps)
            remaining = max(0, rule.max_requests - current_count)

            # En eski kaydın sona erme zamanı
            if window.timestamps:
                reset_time = window.timestamps[0] + rule.window_seconds
            else:
                reset_time = now + rule.window_seconds

            # Limit aşıldı mı?
            if current_count >= rule.max_requests:
                return False, rule.max_requests, 0, reset_time

            # İsteği kaydet
            window.timestamps.append(now)
            remaining = max(0, rule.max_requests - current_count - 1)

            return True, rule.max_requests, remaining, reset_time

    def get_client_stats(self, client_ip: str) -> dict[str, int]:
        """Bir istemcinin tüm kural grupları için istek sayılarını döndür."""
        now = time.time()
        stats = {}

        for key, window in self._windows.items():
            if key.startswith(f"{client_ip}:"):
                group = key.split(":", 1)[1]
                with window.lock:
                    active = sum(
                        1 for ts in window.timestamps
                        if now - ts < 300  # Son 5 dakika
                    )
                    stats[group] = active

        return stats

    def reset_client(self, client_ip: str) -> int:
        """Bir istemcinin tüm rate limit kayıtlarını sıfırla."""
        cleared = 0
        keys_to_remove = [
            key for key in self._windows
            if key.startswith(f"{client_ip}:")
        ]

        with self._global_lock:
            for key in keys_to_remove:
                del self._windows[key]
                cleared += 1

        return cleared


# ═══════════════════════════════════════════════════════════════════════
# Rate Limit Middleware
# ═══════════════════════════════════════════════════════════════════════


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Rate Limiting Middleware.

    IP bazlı sliding window algoritması ile API çağrılarını sınırlar.
    Her yanıta rate limit header'ları ekler.

    Kullanım:
        app.add_middleware(
            RateLimitMiddleware,
            rules=custom_rules,           # Opsiyonel
            whitelist_ips=["127.0.0.1"],  # Opsiyonel
        )
    """

    def __init__(
        self,
        app: ASGIApp,
        rules: Optional[dict[str, RateLimitRule]] = None,
        endpoint_map: Optional[dict[str, str]] = None,
        whitelist_ips: Optional[list[str]] = None,
        enabled: bool = True,
    ):
        """
        Args:
            app: ASGI uygulama örneği.
            rules: Kural grubu → RateLimitRule eşleştirmesi.
            endpoint_map: Endpoint yolu → kural grubu eşleştirmesi.
            whitelist_ips: Rate limit'ten muaf IP adresleri.
            enabled: Middleware aktif/pasif durumu.
        """
        super().__init__(app)
        self.rules = rules or DEFAULT_RULES
        self.endpoint_map = endpoint_map or ENDPOINT_RULE_MAP
        self.whitelist_ips = set(whitelist_ips or ["127.0.0.1", "::1"])
        self.enabled = enabled
        self.storage = RateLimitStorage()

    def _get_client_ip(self, request: Request) -> str:
        """
        İstemci IP adresini al.

        X-Forwarded-For, X-Real-IP header'larını kontrol eder.
        Proxy arkasında gerçek IP'yi tespit eder.
        """
        # Proxy/load balancer header'ları
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # İlk IP gerçek istemci IP'sidir
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Doğrudan bağlantı
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rule_group(self, path: str) -> str:
        """
        Endpoint yolundan kural grubunu belirle.

        Path prefix eşleştirmesi yapar. Bulamazsa 'default' döner.
        """
        for endpoint_prefix, group in self.endpoint_map.items():
            if path.startswith(endpoint_prefix):
                return group
        return "default"

    def _build_rate_limit_response(
        self,
        limit: int,
        remaining: int,
        reset_time: float,
        client_ip: str,
    ) -> JSONResponse:
        """429 Too Many Requests yanıtı oluştur."""
        retry_after = max(1, int(reset_time - time.time()))

        return JSONResponse(
            status_code=429,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "error_code": "RATE_LIMIT",
                "message": "Çok fazla istek gönderdiniz. Lütfen biraz bekleyin.",
                "detail": {
                    "limit": limit,
                    "remaining": 0,
                    "reset_after_seconds": retry_after,
                    "client_ip": client_ip,
                },
                "timestamp": time.time(),
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time)),
                "Retry-After": str(retry_after),
            },
        )

    def _add_rate_limit_headers(
        self,
        response: Response,
        limit: int,
        remaining: int,
        reset_time: float,
    ) -> Response:
        """Yanıta rate limit header'larını ekle."""
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        return response

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Her HTTP isteğini rate limit kontrolünden geçir.

        1. Middleware aktif mi kontrol et
        2. Whitelist IP kontrolü
        3. Kural grubunu belirle
        4. Sliding window kontrolü
        5. Header'ları ekle veya 429 döndür
        """
        # Middleware devre dışı
        if not self.enabled:
            return await call_next(request)

        # Sağlık kontrolü ve docs rate limit'ten muaf
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json", "/"):
            return await call_next(request)

        # İstemci IP'sini al
        client_ip = self._get_client_ip(request)

        # Whitelist kontrolü
        if client_ip in self.whitelist_ips:
            response = await call_next(request)
            response.headers["X-RateLimit-Whitelisted"] = "true"
            return response

        # Kural grubunu belirle
        rule_group = self._get_rule_group(path)
        rule = self.rules.get(rule_group, self.rules["default"])

        # Rate limit kontrolü
        allowed, limit, remaining, reset_time = self.storage.check_and_record(
            client_ip, rule_group, rule
        )

        if not allowed:
            return self._build_rate_limit_response(
                limit, remaining, reset_time, client_ip
            )

        # İsteği işle
        response = await call_next(request)

        # Rate limit header'larını ekle
        self._add_rate_limit_headers(response, limit, remaining, reset_time)

        return response


# ═══════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar
# ═══════════════════════════════════════════════════════════════════════


def create_rate_limiter(
    rules: Optional[dict[str, RateLimitRule]] = None,
    whitelist_ips: Optional[list[str]] = None,
    enabled: bool = True,
) -> dict:
    """
    Rate limiter yapılandırması oluştur.

    Returns:
        Middleware'e geçirilecek kwargs dict.
    """
    return {
        "rules": rules or DEFAULT_RULES,
        "whitelist_ips": whitelist_ips or ["127.0.0.1", "::1"],
        "enabled": enabled,
    }


def get_rate_limit_info() -> dict:
    """Aktif rate limit kurallarını döndür."""
    return {
        group: {
            "max_requests": rule.max_requests,
            "window_seconds": rule.window_seconds,
            "description": rule.description,
        }
        for group, rule in DEFAULT_RULES.items()
    }
