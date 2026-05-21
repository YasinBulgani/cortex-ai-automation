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

from app.config import settings


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
