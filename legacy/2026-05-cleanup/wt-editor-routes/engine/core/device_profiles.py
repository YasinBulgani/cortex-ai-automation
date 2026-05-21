"""
core/device_profiles — Mobil cihaz profil kataloğu

Bu modül Playwright mobil emülasyonu ve gerçek cihaz farm
entegrasyonları (BrowserStack, Sauce Labs) için kullanılan
cihaz profillerini tanımlar.

Katalog kök değişkenleri:
    DEVICE_CATALOG       — Desteklenen tüm cihazların listesi
    DEVICE_MAP           — {slug: DeviceProfile}
    DEVICE_MAP_BY_NAME   — {name: DeviceProfile}

Not: Bu dosya önceden mevcut olup silinmişti; cache'deki .pyc
ve mobile_routes.py/conftest.py kullanım yerlerinden rekonstrükte
edildi (2026-04-19).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DeviceProfile:
    """Tek bir mobil cihaz profili."""

    slug: str
    name: str
    playwright_key: str = ""  # Playwright devices[<key>] ile eşleşir
    width: int = 390
    height: int = 844
    device_scale_factor: float = 3.0
    is_mobile: bool = True
    has_touch: bool = True
    user_agent: str = ""
    platform: str = "ios"  # "ios" | "android"
    farm_device_name: str = ""
    farm_os_version: str = ""

    def to_playwright_context_options(self) -> Dict[str, Any]:
        """Playwright BrowserContext oluşturma parametrelerini döndürür."""
        opts: Dict[str, Any] = {
            "viewport": {"width": self.width, "height": self.height},
            "device_scale_factor": self.device_scale_factor,
            "is_mobile": self.is_mobile,
            "has_touch": self.has_touch,
        }
        if self.user_agent:
            opts["user_agent"] = self.user_agent
        return opts

    def to_dict(self) -> Dict[str, Any]:
        """Katalog API'si için JSON serileştirilebilir temsil."""
        return asdict(self)


# ── iOS cihazları ────────────────────────────────────────────────────────────
_iphone_ua_17 = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)
_iphone_ua_16 = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1"
)
_ipad_ua_17 = (
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

# ── Android cihazları ────────────────────────────────────────────────────────
_pixel_7_ua = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
    "Mobile Safari/537.36"
)
_pixel_5_ua = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
    "Mobile Safari/537.36"
)
_s23_ua = (
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
    "Mobile Safari/537.36"
)
_tab_s8_ua = (
    "Mozilla/5.0 (Linux; Android 13; SM-X700) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
    "Safari/537.36"
)


DEVICE_CATALOG: List[DeviceProfile] = [
    DeviceProfile(
        slug="iphone_14_pro",
        name="iPhone 14 Pro",
        playwright_key="iPhone 14 Pro",
        width=393,
        height=852,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        user_agent=_iphone_ua_17,
        platform="ios",
        farm_device_name="iPhone 14 Pro",
        farm_os_version="16",
    ),
    DeviceProfile(
        slug="iphone_15",
        name="iPhone 15",
        playwright_key="iPhone 15",
        width=393,
        height=852,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        user_agent=_iphone_ua_17,
        platform="ios",
        farm_device_name="iPhone 15",
        farm_os_version="17",
    ),
    DeviceProfile(
        slug="iphone_12",
        name="iPhone 12",
        playwright_key="iPhone 12",
        width=390,
        height=844,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        user_agent=_iphone_ua_16,
        platform="ios",
        farm_device_name="iPhone 12",
        farm_os_version="16",
    ),
    DeviceProfile(
        slug="ipad_pro_11",
        name="iPad Pro 11",
        playwright_key="iPad Pro 11",
        width=834,
        height=1194,
        device_scale_factor=2.0,
        is_mobile=True,
        has_touch=True,
        user_agent=_ipad_ua_17,
        platform="ios",
        farm_device_name="iPad Pro 11 2022",
        farm_os_version="17",
    ),
    DeviceProfile(
        slug="pixel_7",
        name="Pixel 7",
        playwright_key="Pixel 7",
        width=412,
        height=915,
        device_scale_factor=2.625,
        is_mobile=True,
        has_touch=True,
        user_agent=_pixel_7_ua,
        platform="android",
        farm_device_name="Google Pixel 7",
        farm_os_version="13.0",
    ),
    DeviceProfile(
        slug="pixel_5",
        name="Pixel 5",
        playwright_key="Pixel 5",
        width=393,
        height=851,
        device_scale_factor=2.75,
        is_mobile=True,
        has_touch=True,
        user_agent=_pixel_5_ua,
        platform="android",
        farm_device_name="Google Pixel 5",
        farm_os_version="12.0",
    ),
    DeviceProfile(
        slug="samsung_galaxy_s23",
        name="Samsung Galaxy S23",
        playwright_key="Galaxy S23",
        width=360,
        height=780,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        user_agent=_s23_ua,
        platform="android",
        farm_device_name="Samsung Galaxy S23",
        farm_os_version="13.0",
    ),
    DeviceProfile(
        slug="samsung_galaxy_tab_s8",
        name="Samsung Galaxy Tab S8",
        playwright_key="",
        width=800,
        height=1280,
        device_scale_factor=2.0,
        is_mobile=True,
        has_touch=True,
        user_agent=_tab_s8_ua,
        platform="android",
        farm_device_name="Samsung Galaxy Tab S8",
        farm_os_version="13.0",
    ),
]

DEVICE_MAP: Dict[str, DeviceProfile] = {d.slug: d for d in DEVICE_CATALOG}
DEVICE_MAP_BY_NAME: Dict[str, DeviceProfile] = {d.name: d for d in DEVICE_CATALOG}


__all__ = [
    "DeviceProfile",
    "DEVICE_CATALOG",
    "DEVICE_MAP",
    "DEVICE_MAP_BY_NAME",
]
