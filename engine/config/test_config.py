"""
engine/config/test_config.py — E2E test konfigürasyonu.

Ortam değişkenlerinden yüklenen, makul varsayılanları olan test ayarları.
Tüm test dosyaları bu merkezi yapılandırmayı kullanır.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class TestConfig:
    """E2E test çalıştırması için tüm yapılandırma parametreleri."""

    # ── URL'ler ───────────────────────────────────────────────────────────────
    BASE_URL: str = field(
        default_factory=lambda: os.getenv("BASE_URL", "http://localhost:3000")
    )
    API_URL: str = field(
        default_factory=lambda: os.getenv("API_URL", "http://localhost:8000/api/v1")
    )
    ENGINE_URL: str = field(
        default_factory=lambda: os.getenv("ENGINE_URL", "http://localhost:5001")
    )

    # ── Tarayıcı ──────────────────────────────────────────────────────────────
    BROWSER: str = field(
        default_factory=lambda: os.getenv("BROWSER", "chromium")
    )
    HEADLESS: bool = field(
        default_factory=lambda: os.getenv("HEADLESS", "true").lower() == "true"
    )

    # ── Zaman Aşımı (ms) ─────────────────────────────────────────────────────
    DEFAULT_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_TIMEOUT", "30000"))
    )
    NAVIGATION_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("NAVIGATION_TIMEOUT", "60000"))
    )

    # ── Hata Ayıklama ────────────────────────────────────────────────────────
    SCREENSHOT_ON_FAILURE: bool = field(
        default_factory=lambda: os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
    )
    TRACE_ON_FAILURE: bool = field(
        default_factory=lambda: os.getenv("TRACE_ON_FAILURE", "true").lower() == "true"
    )

    # ── Yeniden Deneme ────────────────────────────────────────────────────────
    RETRY_COUNT: int = field(
        default_factory=lambda: int(os.getenv("RETRY_COUNT", "2"))
    )
    RETRY_DELAY: float = field(
        default_factory=lambda: float(os.getenv("RETRY_DELAY", "1.0"))
    )

    # ── Paralel Çalıştırma ───────────────────────────────────────────────────
    PARALLEL_WORKERS: int = field(
        default_factory=lambda: int(os.getenv("PARALLEL_WORKERS", "1"))
    )

    # ── Allure Rapor ─────────────────────────────────────────────────────────
    ALLURE_RESULTS_DIR: str = field(
        default_factory=lambda: os.getenv(
            "ALLURE_RESULTS_DIR", str(_ENGINE_DIR / "allure-results")
        )
    )

    # ── Dizinler ──────────────────────────────────────────────────────────────
    SCREENSHOTS_DIR: Path = field(
        default_factory=lambda: _ENGINE_DIR / "screenshots"
    )
    TRACES_DIR: Path = field(
        default_factory=lambda: _ENGINE_DIR / "traces"
    )

    # ── Viewport ──────────────────────────────────────────────────────────────
    VIEWPORT_WIDTH: int = field(
        default_factory=lambda: int(os.getenv("VIEWPORT_WIDTH", "1280"))
    )
    VIEWPORT_HEIGHT: int = field(
        default_factory=lambda: int(os.getenv("VIEWPORT_HEIGHT", "720"))
    )

    def __post_init__(self) -> None:
        self.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self.TRACES_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.ALLURE_RESULTS_DIR).mkdir(parents=True, exist_ok=True)


test_config = TestConfig()
