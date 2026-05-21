"""Device Broker — cihaz lifecycle yönetimi.

MVP: in-memory registry. F1'de AVD/Simulator gerçek lifecycle (avdmanager / simctl
subprocess çağrıları) ve kira (lease) protokolü eklenecek.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from .schemas import Device, DeviceCreate, DeviceStatus, PhysicalEnrollRequest

_logger = logging.getLogger(__name__)


# ── Seed device farm — 10 sanal cihaz ─────────────────────────
_INITIAL_FARM: list[dict] = [
    # 6 Android AVD (karışık OS sürümü)
    {"name": "Pixel 8",            "platform": "android", "os_version": "14", "profile": "pixel_8",       "kind": "emulator",  "appium_port": 4723},
    {"name": "Pixel 8 Pro",        "platform": "android", "os_version": "14", "profile": "pixel_8_pro",   "kind": "emulator",  "appium_port": 4724},
    {"name": "Galaxy S23 (OneUI)", "platform": "android", "os_version": "13", "profile": "galaxy_s23",    "kind": "emulator",  "appium_port": 4725},
    {"name": "Pixel 6",            "platform": "android", "os_version": "12", "profile": "pixel_6",       "kind": "emulator",  "appium_port": 4726},
    {"name": "Pixel 5 (legacy)",   "platform": "android", "os_version": "11", "profile": "pixel_5",       "kind": "emulator",  "appium_port": 4727},
    {"name": "Nexus 5X (legacy)",  "platform": "android", "os_version": "9",  "profile": "nexus_5x",      "kind": "emulator",  "appium_port": 4728},
    # 4 iOS Simulator
    {"name": "iPhone 15 Pro",      "platform": "ios",     "os_version": "17", "profile": "iphone_15_pro", "kind": "simulator", "appium_port": 4730},
    {"name": "iPhone 15",          "platform": "ios",     "os_version": "17", "profile": "iphone_15",     "kind": "simulator", "appium_port": 4731},
    {"name": "iPhone 14",          "platform": "ios",     "os_version": "16", "profile": "iphone_14",     "kind": "simulator", "appium_port": 4732},
    {"name": "iPhone SE (3rd)",    "platform": "ios",     "os_version": "15", "profile": "iphone_se_3",   "kind": "simulator", "appium_port": 4733},
]


class DeviceBroker:
    """Thread-safe in-memory device broker.

    Gerçek dünyada:
      - Redis backed (multi-worker safe)
      - AVD/simctl subprocess sargısı
      - Lease semafor (her cihaz tek session)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: dict[str, Device] = {}
        self._lease_semaphores: dict[str, asyncio.Semaphore] = {}
        self._seed()

    def _seed(self) -> None:
        for spec in _INITIAL_FARM:
            dev_id = f"{spec['platform'][:3]}-{spec['profile']}"
            self._devices[dev_id] = Device(
                id=dev_id,
                name=spec["name"],
                platform=spec["platform"],  # type: ignore[arg-type]
                os_version=spec["os_version"],
                profile=spec["profile"],
                kind=spec["kind"],  # type: ignore[arg-type]
                appium_url=f"http://127.0.0.1:{spec['appium_port']}",
                status="offline" if spec["profile"] == "nexus_5x" else "idle",
                battery=100,
                cpu_pct=5,
                ram_pct=30,
                last_seen=datetime.now(timezone.utc),
            )

    # ── CRUD ──────────────────────────────────────────────────
    def list(self) -> list[Device]:
        with self._lock:
            return list(self._devices.values())

    def get(self, device_id: str) -> Optional[Device]:
        with self._lock:
            return self._devices.get(device_id)

    def upsert(self, device: Device) -> Device:
        with self._lock:
            self._devices[device.id] = device
            return device

    def enroll_physical(self, req: PhysicalEnrollRequest) -> Device:
        """Fiziksel cihaz kaydı — ADB/WDA handshake MVP'de stub."""
        dev_id = f"phy-{uuid.uuid4().hex[:8]}"
        device = Device(
            id=dev_id,
            name=req.name,
            platform=req.platform,
            os_version=req.os_version,
            profile=req.profile or req.name.lower().replace(" ", "_"),
            kind="physical",
            appium_url=req.appium_url,
            status="idle",
            battery=100,
            cpu_pct=5,
            ram_pct=30,
            last_seen=datetime.now(timezone.utc),
        )
        with self._lock:
            self._devices[dev_id] = device
        _logger.info("Fiziksel cihaz enrolled: %s (%s)", dev_id, req.name)
        # TODO: ADB handshake (android) / idb describe-target (ios) arka planda
        return device

    def update_status(self, device_id: str, status: DeviceStatus, **fields) -> Optional[Device]:
        with self._lock:
            dev = self._devices.get(device_id)
            if not dev:
                return None
            updated = dev.model_copy(update={"status": status, **fields, "last_seen": datetime.now(timezone.utc)})
            self._devices[device_id] = updated
            return updated

    def reboot(self, device_id: str) -> Optional[Device]:
        """Cihazı yeniden başlat — MVP'de sadece state değiştirir."""
        self.update_status(device_id, "booting", cpu_pct=5, ram_pct=22, battery=100)
        # Gerçek dünyada: subprocess.run(["adb", "-s", serial, "reboot"])
        # Simülasyon: 2 sn sonra idle
        def _back_to_idle():
            import time
            time.sleep(2.0)
            self.update_status(device_id, "idle")

        threading.Thread(target=_back_to_idle, daemon=True).start()
        return self.get(device_id)

    # ── Lease / pool selection ────────────────────────────────
    def pick_available(self, platform: str = "both", count: int = 1) -> list[Device]:
        with self._lock:
            pool = [
                d for d in self._devices.values()
                if d.status == "idle"
                and (platform == "both" or d.platform == platform)
            ]
            return pool[:count]

    def stats(self) -> dict:
        with self._lock:
            devs = list(self._devices.values())
            return {
                "total": len(devs),
                "online": sum(1 for d in devs if d.status != "offline"),
                "running": sum(1 for d in devs if d.status == "running"),
                "idle": sum(1 for d in devs if d.status == "idle"),
                "offline": sum(1 for d in devs if d.status == "offline"),
                "by_platform": {
                    "android": sum(1 for d in devs if d.platform == "android"),
                    "ios": sum(1 for d in devs if d.platform == "ios"),
                },
            }


# Singleton
_broker: Optional[DeviceBroker] = None
_broker_lock = threading.Lock()


def get_broker() -> DeviceBroker:
    global _broker
    if _broker is None:
        with _broker_lock:
            if _broker is None:
                _broker = DeviceBroker()
    return _broker
