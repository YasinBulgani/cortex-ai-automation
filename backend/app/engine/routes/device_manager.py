"""
Device Manager routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/device_manager_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/device_manager.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device-manager", tags=["engine", "device-manager"])

# ─── Config dependency (placeholder — gerçek settings'den import) ─────────

class _Settings:
    """Geçici settings stub. Gerçek config.py'den alınacak."""
    BASE_DIR: Path = Path(__file__).resolve().parents[5]


_settings = _Settings()


def get_settings() -> _Settings:
    return _settings


# ─── Demo cihazlar ───────────────────────────────────────────────────────────

_DEMO_DEVICES = [
    {
        "serial": "emulator-5554", "device_type": "emulator", "platform": "android",
        "name": "Pixel 7 Pro (API 34)", "brand": "Google", "model": "Pixel 7 Pro",
        "android_version": "14", "api_level": "34", "abi": "x86_64",
        "screen_size": "1440x3120", "locale": "tr-TR",
        "battery": {"level": 100, "status": "charging", "temperature": 27.0},
        "memory": {"total_mb": 3072, "available_mb": 1800},
        "storage": {"total_gb": 8.0, "free_gb": 5.5},
        "health_score": 95, "installed_apps_count": 12,
        "uptime": "demo", "online": True, "state": "device", "demo": True,
    },
    {
        "serial": "emulator-5556", "device_type": "emulator", "platform": "android",
        "name": "Samsung Galaxy S23 (API 33)", "brand": "Samsung", "model": "Galaxy S23",
        "android_version": "13", "api_level": "33", "abi": "x86_64",
        "screen_size": "1080x2340", "locale": "en-US",
        "battery": {"level": 78, "status": "discharging", "temperature": 31.5},
        "memory": {"total_mb": 2048, "available_mb": 900},
        "storage": {"total_gb": 8.0, "free_gb": 3.2},
        "health_score": 81, "installed_apps_count": 8,
        "uptime": "demo", "online": True, "state": "device", "demo": True,
    },
    {
        "serial": "emulator-5558", "device_type": "emulator", "platform": "android",
        "name": "Pixel 6 (API 31)", "brand": "Google", "model": "Pixel 6",
        "android_version": "12", "api_level": "31", "abi": "x86_64",
        "screen_size": "1080x2400", "locale": "tr-TR",
        "battery": {"level": 45, "status": "discharging", "temperature": 33.0},
        "memory": {"total_mb": 2048, "available_mb": 600},
        "storage": {"total_gb": 8.0, "free_gb": 1.8},
        "health_score": 62, "installed_apps_count": 5,
        "uptime": "demo", "online": False, "state": "offline", "demo": True,
    },
    {
        "serial": "emulator-5560", "device_type": "emulator", "platform": "android",
        "name": "Xiaomi 13 (API 34)", "brand": "Xiaomi", "model": "Xiaomi 13",
        "android_version": "14", "api_level": "34", "abi": "x86_64",
        "screen_size": "1080x2400", "locale": "tr-TR",
        "battery": {"level": 92, "status": "charging", "temperature": 28.5},
        "memory": {"total_mb": 4096, "available_mb": 2200},
        "storage": {"total_gb": 8.0, "free_gb": 4.1},
        "health_score": 88, "installed_apps_count": 9,
        "uptime": "demo", "online": True, "state": "device", "demo": True,
    },
]

_device_cache: dict = {"devices": [], "ts": 0.0}
_CACHE_TTL = 5

_executor = ThreadPoolExecutor(max_workers=8)

SHELL_BLOCKLIST = [
    "rm -rf /", "reboot", "format", "mkfs", "dd if=",
    "su ", "su\n", "chmod 777 /", "flash", "fastboot",
    "wipe", "factory_reset",
]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ActionSerialBody(BaseModel):
    serial: str = Field(..., min_length=1)
    platform: str = Field("android")


class ActionPackageBody(BaseModel):
    serial: str = Field(..., min_length=1)
    package: str = Field(..., min_length=1)
    platform: str = Field("android")


class ActionShellBody(BaseModel):
    serial: str = Field(..., min_length=1)
    command: str = Field(..., min_length=1)
    platform: str = Field("android")


class FilePullBody(BaseModel):
    serial: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


class FileDeleteBody(BaseModel):
    serial: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


class AiAnalyzeBody(BaseModel):
    serial: str = Field(..., min_length=1)


class AiTroubleshootBody(BaseModel):
    serial: str = Field("")
    question: str = Field(..., min_length=1)


class AiRecommendBody(BaseModel):
    test_type: str = Field("genel")


class AiAnalyzeLogsBody(BaseModel):
    serial: str = Field(..., min_length=1)
    log_type: str = Field("logcat")
    lines: int = Field(200, ge=1, le=500)


class LaunchAvdBody(BaseModel):
    avd_name: str = Field("")
    simulator_udid: str = Field("")


# ─── ADB / xcrun Yardımcılar ─────────────────────────────────────────────────

def _adb_cmd(serial: str, *args: str, timeout: int = 10) -> str:
    cmd = ["adb", "-s", serial] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


def _adb_shell(serial: str, shell_cmd: str, timeout: int = 10) -> str:
    return _adb_cmd(serial, "shell", shell_cmd, timeout=timeout)


def _get_prop(serial: str, prop: str) -> str:
    try:
        return _adb_shell(serial, f"getprop {prop}", timeout=5)
    except Exception:
        return ""


def _is_tool_available(tool: str) -> bool:
    try:
        subprocess.run([tool, "--version"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _is_adb_available() -> bool:
    return _is_tool_available("adb")


def _is_xcrun_available() -> bool:
    try:
        subprocess.run(["xcrun", "simctl", "list"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _sanitize_path(path: str) -> str:
    normalized = os.path.normpath(path)
    if ".." in normalized.split(os.sep):
        raise ValueError("Path traversal tespit edildi")
    return normalized


# ─── Cihaz Keşfi ─────────────────────────────────────────────────────────────

def _compute_health_score(battery: dict, memory: dict, storage: dict) -> int:
    score = 100
    bat_level = battery.get("level", 100)
    if bat_level < 20:
        score -= 30
    elif bat_level < 50:
        score -= 10
    bat_temp = battery.get("temperature", 25)
    if bat_temp > 45:
        score -= 25
    elif bat_temp > 40:
        score -= 10
    mem_total = memory.get("total_kb", 1)
    mem_avail = memory.get("available_kb", 1)
    if mem_total > 0 and (1 - mem_avail / mem_total) > 0.9:
        score -= 25
    elif mem_total > 0 and (1 - mem_avail / mem_total) > 0.75:
        score -= 10
    stor_total = storage.get("total_kb", 1)
    stor_avail = storage.get("available_kb", 1)
    if stor_total > 0 and (1 - stor_avail / stor_total) > 0.95:
        score -= 20
    elif stor_total > 0 and (1 - stor_avail / stor_total) > 0.85:
        score -= 10
    return max(0, min(100, score))


def _discover_android_devices() -> list[dict]:
    devices = []
    if not _is_adb_available():
        return devices
    try:
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=8)
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            is_emulator = serial.startswith("emulator-")
            device_type = "emulator" if is_emulator else "physical"

            if state != "device":
                devices.append({"serial": serial, "state": state, "device_type": device_type,
                                "name": serial, "platform": "android", "online": False})
                continue

            model = _get_prop(serial, "ro.product.model") or serial
            brand = _get_prop(serial, "ro.product.brand")
            android_ver = _get_prop(serial, "ro.build.version.release") or "?"
            api_level = _get_prop(serial, "ro.build.version.sdk") or "?"
            abi = _get_prop(serial, "ro.product.cpu.abi")
            build_id = _get_prop(serial, "ro.build.display.id")
            device_name = _get_prop(serial, "ro.product.device")
            locale = _get_prop(serial, "persist.sys.locale") or _get_prop(serial, "ro.product.locale")
            density = _get_prop(serial, "ro.sf.lcd_density")

            screen_size = ""
            try:
                wm = _adb_shell(serial, "wm size", timeout=3)
                if "Physical size:" in wm:
                    screen_size = wm.split("Physical size:")[-1].strip()
            except Exception:
                pass

            battery: dict = {}
            try:
                bat_out = _adb_shell(serial, "dumpsys battery", timeout=5)
                for bl in bat_out.splitlines():
                    bl = bl.strip()
                    if bl.startswith("level:"):
                        battery["level"] = int(bl.split(":")[1].strip())
                    elif bl.startswith("status:"):
                        sc = int(bl.split(":")[1].strip())
                        battery["status"] = {1: "unknown", 2: "charging", 3: "discharging",
                                             4: "not_charging", 5: "full"}.get(sc, "unknown")
                    elif bl.startswith("temperature:"):
                        battery["temperature"] = int(bl.split(":")[1].strip()) / 10
            except Exception:
                pass

            memory: dict = {}
            try:
                mem_out = _adb_shell(serial, "cat /proc/meminfo", timeout=3)
                for ml in mem_out.splitlines():
                    if ml.startswith("MemTotal:"):
                        memory["total_kb"] = int(re.search(r"(\d+)", ml).group(1))
                    elif ml.startswith("MemAvailable:"):
                        memory["available_kb"] = int(re.search(r"(\d+)", ml).group(1))
            except Exception:
                pass

            storage: dict = {}
            try:
                df_out = _adb_shell(serial, "df /data", timeout=5)
                dl = df_out.strip().splitlines()
                if len(dl) >= 2:
                    dp = dl[1].split()
                    if len(dp) >= 4:
                        storage = {"total_kb": int(dp[1]), "used_kb": int(dp[2]), "available_kb": int(dp[3])}
            except Exception:
                pass

            app_count = 0
            try:
                ps = _adb_shell(serial, "pm list packages -3", timeout=5)
                app_count = len([ll for ll in ps.splitlines() if ll.strip()])
            except Exception:
                pass

            uptime = ""
            try:
                up_raw = _adb_shell(serial, "cat /proc/uptime", timeout=3)
                if up_raw:
                    secs = float(up_raw.split()[0])
                    uptime = f"{int(secs // 3600)}s {int((secs % 3600) // 60)}dk"
            except Exception:
                pass

            devices.append({
                "serial": serial, "state": state, "online": True,
                "platform": "android", "device_type": device_type,
                "name": model, "brand": (brand or "").capitalize(),
                "device_code": device_name, "android_version": android_ver,
                "api_level": api_level, "sdk_int": api_level,
                "abi": abi, "build_id": build_id, "locale": locale,
                "density": density, "screen_size": screen_size,
                "battery": battery, "memory": memory, "storage": storage,
                "installed_apps_count": app_count, "uptime": uptime,
                "health_score": _compute_health_score(battery, memory, storage),
                "discovered_at": datetime.utcnow().isoformat(),
            })
    except FileNotFoundError:
        logger.debug("adb bulunamadı")
    except Exception as exc:
        logger.debug("Android keşif hatası: %s", exc)
    return devices


def _discover_ios_simulators() -> list[dict]:
    devices = []
    if not _is_xcrun_available():
        return devices
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        for runtime, sims in data.get("devices", {}).items():
            ios_version = "?"
            if "iOS-" in runtime:
                ios_version = runtime.split("iOS-")[-1].replace("-", ".")
            elif "tvOS-" in runtime:
                ios_version = "tvOS " + runtime.split("tvOS-")[-1].replace("-", ".")
            elif "watchOS-" in runtime:
                ios_version = "watchOS " + runtime.split("watchOS-")[-1].replace("-", ".")
            for sim in sims:
                is_booted = sim.get("state") == "Booted"
                devices.append({
                    "serial": sim.get("udid", ""),
                    "state": "device" if is_booted else "shutdown",
                    "online": is_booted,
                    "platform": "ios",
                    "device_type": "simulator",
                    "name": sim.get("name", "iOS Simulator"),
                    "brand": "Apple",
                    "device_code": sim.get("deviceTypeIdentifier", ""),
                    "android_version": "",
                    "api_level": "",
                    "sdk_int": "",
                    "abi": "arm64" if "arm64" in (sim.get("deviceTypeIdentifier") or "") else "x86_64",
                    "build_id": runtime.split(".")[-1] if runtime else "",
                    "locale": "",
                    "density": "",
                    "screen_size": "",
                    "battery": {"level": 100, "status": "full", "temperature": 25},
                    "memory": {},
                    "storage": {},
                    "installed_apps_count": 0,
                    "uptime": "",
                    "ios_version": ios_version,
                    "health_score": 95 if is_booted else 50,
                    "discovered_at": datetime.utcnow().isoformat(),
                })
    except FileNotFoundError:
        logger.debug("xcrun bulunamadı")
    except Exception as exc:
        logger.debug("iOS keşif hatası: %s", exc)
    return devices


def _discover_all_devices(use_cache: bool = True) -> list[dict]:
    now = time.time()
    if use_cache and _device_cache["devices"] and (now - _device_cache["ts"]) < _CACHE_TTL:
        return _device_cache["devices"]  # type: ignore[return-value]

    android_future = _executor.submit(_discover_android_devices)
    ios_future = _executor.submit(_discover_ios_simulators)
    devices = android_future.result(timeout=15) + ios_future.result(timeout=15)
    _device_cache["devices"] = devices
    _device_cache["ts"] = now
    return devices


# ─── Routes — Cihaz Listesi ───────────────────────────────────────────────────

@router.get("/devices")
def list_managed_devices():
    """Tüm bağlı/keşfedilen cihazları döndürür. Gerçek cihaz yoksa demo cihazlar döner."""
    devices = _discover_all_devices()
    if not devices:
        devices = list(_DEMO_DEVICES)

    android = [d for d in devices if d.get("platform") == "android"]
    ios = [d for d in devices if d.get("platform") == "ios"]
    online = [d for d in devices if d.get("online")]
    emulators = [d for d in devices if d.get("device_type") == "emulator"]
    simulators = [d for d in devices if d.get("device_type") == "simulator"]
    physicals = [d for d in devices if d.get("device_type") == "physical"]

    return {
        "devices": devices,
        "summary": {
            "total": len(devices), "online": len(online),
            "android": len(android), "ios": len(ios),
            "emulators": len(emulators), "simulators": len(simulators),
            "physical": len(physicals),
            "adb_available": _is_adb_available(),
            "xcrun_available": _is_xcrun_available(),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/device/{serial}/details")
def device_details(serial: str):
    """Belirtilen serial'a ait cihaz detaylarını döndürür."""
    devices = _discover_all_devices()
    device = next((d for d in devices if d["serial"] == serial), None)
    if not device:
        raise HTTPException(status_code=404, detail=f"Cihaz bulunamadı: {serial}")
    return device


# ─── Routes — Canlı Ekran Yansıtma ───────────────────────────────────────────

def _take_screenshot_b64(serial: str, platform: str) -> str | None:
    try:
        if platform == "android":
            raw = subprocess.run(
                ["adb", "-s", serial, "exec-out", "screencap", "-p"],
                capture_output=True, timeout=8,
            )
            if raw.stdout:
                return base64.b64encode(raw.stdout).decode("utf-8")
        elif platform == "ios":
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["xcrun", "simctl", "io", serial, "screenshot", tmp_path],
                capture_output=True, timeout=8,
            )
            p = Path(tmp_path)
            if p.exists() and p.stat().st_size > 0:
                b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
                p.unlink(missing_ok=True)
                return b64
            p.unlink(missing_ok=True)
    except Exception as exc:
        logger.debug("Screenshot hatası [%s]: %s", serial, exc)
    return None


@router.get("/device/{serial}/live-screen")
def live_screen(
    serial: str,
    interval: int = Query(1500, ge=500, le=10000),
    platform: str = Query("android"),
):
    """SSE: Cihaz ekranını periyodik screenshot ile yansıtır."""
    def generate():
        while True:
            b64 = _take_screenshot_b64(serial, platform)
            if b64:
                yield f"data: {json.dumps({'type': 'frame', 'data': b64, 'ts': datetime.utcnow().isoformat()})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'text': 'Screenshot alınamadı'})}\n\n"
            time.sleep(interval / 1000.0)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ─── Routes — Temel Aksiyonlar ────────────────────────────────────────────────

@router.post("/actions/reboot")
def action_reboot(body: ActionSerialBody):
    """Cihazı yeniden başlatır (Android: adb reboot, iOS: simctl shutdown+boot)."""
    try:
        if body.platform == "ios":
            subprocess.run(["xcrun", "simctl", "shutdown", body.serial], capture_output=True, timeout=10)
            time.sleep(1)
            subprocess.run(["xcrun", "simctl", "boot", body.serial], capture_output=True, timeout=10)
        else:
            _adb_cmd(body.serial, "reboot", timeout=15)
        return {"success": True, "serial": body.serial, "action": "reboot"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/actions/screenshot")
def action_screenshot(body: ActionSerialBody):
    """Cihaz ekranının anlık görüntüsünü (base64) döndürür."""
    b64 = _take_screenshot_b64(body.serial, body.platform)
    if b64:
        return {"success": True, "serial": body.serial, "screenshot_b64": b64}
    raise HTTPException(status_code=500, detail="Screenshot alınamadı")


@router.post("/actions/install")
async def action_install(
    serial: str = Query(...),
    platform: str = Query("android"),
    file: UploadFile = File(...),
    s: _Settings = Depends(get_settings),
):
    """APK/IPA dosyasını cihaza kurar."""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş")

    tmp_dir = Path(s.BASE_DIR) / "tmp_install"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / filename
    tmp_path.write_bytes(await file.read())

    try:
        if platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "install", serial, str(tmp_path)],
                capture_output=True, text=True, timeout=120,
            )
            return {"success": result.returncode == 0, "serial": serial,
                    "filename": filename, "output": result.stdout.strip() or result.stderr.strip()}
        else:
            result = subprocess.run(
                ["adb", "-s", serial, "install", "-r", str(tmp_path)],
                capture_output=True, text=True, timeout=120,
            )
            return {"success": "Success" in result.stdout, "serial": serial,
                    "filename": filename, "output": result.stdout.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/actions/shell")
def action_shell(body: ActionShellBody):
    """Cihazda shell komutu çalıştırır (güvenlik listesi kontrolü ile)."""
    if any(b in body.command for b in SHELL_BLOCKLIST):
        raise HTTPException(status_code=403, detail="Bu komut güvenlik nedeniyle engellendi")
    try:
        if body.platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "spawn", body.serial] + body.command.split(),
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout.strip() or result.stderr.strip()
        else:
            output = _adb_shell(body.serial, body.command, timeout=15)
        return {"success": True, "serial": body.serial, "command": body.command, "output": output}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Routes — Uygulama Yönetimi ───────────────────────────────────────────────

@router.get("/device/{serial}/apps")
def list_apps(serial: str, platform: str = Query("android")):
    """Cihazda yüklü uygulamaları listeler."""
    try:
        apps = []
        if platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "listapps", serial],
                capture_output=True, text=True, timeout=15,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if "CFBundleIdentifier" in line:
                    bid = line.split("=")[-1].strip().strip('";')
                    apps.append({"package": bid, "name": bid.split(".")[-1]})
        else:
            result = _adb_shell(serial, "pm list packages -3", timeout=10)
            for line in result.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    pkg = line.replace("package:", "")
                    apps.append({"package": pkg, "name": pkg.split(".")[-1]})
        return {"apps": apps, "count": len(apps), "serial": serial}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/actions/uninstall")
def action_uninstall(body: ActionPackageBody):
    """Uygulamayı cihazdan kaldırır."""
    try:
        if body.platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "uninstall", body.serial, body.package],
                capture_output=True, text=True, timeout=30,
            )
        else:
            result = subprocess.run(
                ["adb", "-s", body.serial, "uninstall", body.package],
                capture_output=True, text=True, timeout=30,
            )
        return {"success": result.returncode == 0, "serial": body.serial,
                "package": body.package, "output": result.stdout.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/actions/clear-data")
def action_clear_data(body: ActionPackageBody):
    """Uygulama verilerini siler (Android only)."""
    try:
        output = _adb_shell(body.serial, f"pm clear {body.package}", timeout=15)
        return {"success": "Success" in output, "serial": body.serial,
                "package": body.package, "output": output}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/actions/force-stop")
def action_force_stop(body: ActionPackageBody):
    """Uygulamayı zorla durdurur (Android only)."""
    try:
        _adb_shell(body.serial, f"am force-stop {body.package}", timeout=10)
        return {"success": True, "serial": body.serial, "package": body.package}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/actions/launch-app")
def action_launch_app(body: ActionPackageBody):
    """Uygulamayı başlatır."""
    try:
        if body.platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "launch", body.serial, body.package],
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout.strip()
        else:
            output = _adb_shell(
                body.serial,
                f"monkey -p {body.package} -c android.intent.category.LAUNCHER 1",
                timeout=10,
            )
        return {"success": True, "serial": body.serial, "package": body.package, "output": output}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Routes — Dosya Yöneticisi ───────────────────────────────────────────────

@router.get("/device/{serial}/files")
def list_files(
    serial: str,
    path: str = Query("/sdcard"),
    platform: str = Query("android"),
):
    """Cihaz dosya sistemini listeler."""
    try:
        path = _sanitize_path(path)
        files = []
        if platform == "android":
            output = _adb_shell(serial, f"ls -la {path}", timeout=10)
            for line in output.splitlines():
                parts = line.split()
                if len(parts) < 7 or line.startswith("total"):
                    continue
                perms = parts[0]
                is_dir = perms.startswith("d")
                name = " ".join(parts[6:]) if len(parts) > 6 else parts[-1]
                if name in (".", ".."):
                    continue
                size = 0
                try:
                    size = int(parts[4])
                except (ValueError, IndexError):
                    pass
                files.append({"name": name, "is_dir": is_dir, "size": size, "permissions": perms,
                              "path": f"{path}/{name}".replace("//", "/")})
        return {"files": files, "current_path": path, "serial": serial}
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/files/pull")
def file_pull(body: FilePullBody, s: Annotated[_Settings, Depends(get_settings)]):
    """Cihazdan dosya indirir (base64 olarak döndürür)."""
    try:
        remote_path = _sanitize_path(body.path)
        local_dir = Path(s.BASE_DIR) / "tmp_file_transfer"
        local_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(remote_path).name
        local_path = local_dir / f"{body.serial}_{filename}"
        subprocess.run(
            ["adb", "-s", body.serial, "pull", remote_path, str(local_path)],
            capture_output=True, timeout=30,
        )
        if local_path.exists():
            b64 = base64.b64encode(local_path.read_bytes()).decode("utf-8")
            size = local_path.stat().st_size
            local_path.unlink(missing_ok=True)
            return {"success": True, "filename": filename, "size": size, "data_b64": b64}
        raise HTTPException(status_code=500, detail="Dosya indirilemedi")
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/files/push")
async def file_push(
    serial: str = Query(...),
    remote_dir: str = Query("/sdcard"),
    file: UploadFile = File(...),
    s: _Settings = Depends(get_settings),
):
    """Cihaza dosya yükler."""
    try:
        remote_dir = _sanitize_path(remote_dir)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))

    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş")

    tmp_dir = Path(s.BASE_DIR) / "tmp_file_transfer"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / filename
    tmp_path.write_bytes(await file.read())

    try:
        remote_path = f"{remote_dir}/{filename}".replace("//", "/")
        result = subprocess.run(
            ["adb", "-s", serial, "push", str(tmp_path), remote_path],
            capture_output=True, text=True, timeout=60,
        )
        return {"success": result.returncode == 0, "serial": serial,
                "remote_path": remote_path, "output": result.stdout.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/files/delete")
def file_delete(body: FileDeleteBody):
    """Cihazdan dosya/dizin siler."""
    try:
        remote_path = _sanitize_path(body.path)
        if remote_path in ("/", "/sdcard", "/data", "/system"):
            raise HTTPException(status_code=403, detail="Kök dizin silinemez")
        _adb_shell(body.serial, f"rm -rf {remote_path}", timeout=10)
        return {"success": True, "serial": body.serial, "path": remote_path}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Routes — Canlı Log Stream (SSE) ─────────────────────────────────────────

@router.get("/device/{serial}/logcat-stream")
def logcat_stream(
    serial: str,
    level: str = Query("V"),
    tag: str = Query(""),
    platform: str = Query("android"),
):
    """SSE: Canlı logcat/log stream."""
    def generate():
        try:
            if platform == "ios":
                cmd = ["xcrun", "simctl", "spawn", serial, "log", "stream",
                       "--level", level.lower() if level else "debug"]
            else:
                cmd = ["adb", "-s", serial, "logcat", f"*:{level}"]
                if tag:
                    cmd = ["adb", "-s", serial, "logcat", f"{tag}:{level}", "*:S"]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)
            try:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        yield f"data: {json.dumps({'type': 'log', 'line': line}, ensure_ascii=False)}\n\n"
            finally:
                proc.kill()
                proc.wait()
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/device/{serial}/logcat")
def device_logcat(
    serial: str,
    lines: str = Query("100"),
    tag: str = Query(""),
):
    """SSE: Son N logcat satırını döndürür (tek seferlik)."""
    def generate():
        cmd = ["adb", "-s", serial, "logcat", "-t", lines]
        if tag:
            cmd += [f"{tag}:V", "*:S"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            for line in result.stdout.splitlines():
                yield f"data: {json.dumps({'line': line}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Routes — Performans İzleme (SSE) ────────────────────────────────────────

def _collect_perf_metrics(serial: str) -> dict:
    metrics: dict = {"ts": datetime.utcnow().isoformat()}
    try:
        mem_out = _adb_shell(serial, "cat /proc/meminfo", timeout=3)
        for ml in mem_out.splitlines():
            if ml.startswith("MemTotal:"):
                metrics["mem_total_kb"] = int(re.search(r"(\d+)", ml).group(1))
            elif ml.startswith("MemAvailable:"):
                metrics["mem_available_kb"] = int(re.search(r"(\d+)", ml).group(1))
    except Exception:
        pass
    try:
        cpu_out = _adb_shell(serial, "dumpsys cpuinfo | head -1", timeout=5)
        m = re.search(r"([\d.]+)%\s+TOTAL", cpu_out)
        if m:
            metrics["cpu_percent"] = float(m.group(1))
    except Exception:
        pass
    try:
        bat_out = _adb_shell(serial, "dumpsys battery", timeout=5)
        for bl in bat_out.splitlines():
            bl = bl.strip()
            if bl.startswith("level:"):
                metrics["battery_level"] = int(bl.split(":")[1].strip())
            elif bl.startswith("temperature:"):
                metrics["battery_temp"] = int(bl.split(":")[1].strip()) / 10
    except Exception:
        pass
    return metrics


@router.get("/device/{serial}/perf-stream")
def perf_stream(
    serial: str,
    interval: int = Query(2000, ge=1000, le=30000),
):
    """SSE: CPU, RAM, batarya metriklerini periyodik olarak akıtır."""
    def generate():
        while True:
            metrics = _collect_perf_metrics(serial)
            yield f"data: {json.dumps(metrics, ensure_ascii=False)}\n\n"
            time.sleep(interval / 1000.0)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ─── Routes — AI Destekli Özellikler ─────────────────────────────────────────

def _call_ai(system: str, prompt: str, temperature: float = 0.3) -> str:
    """AI engine'i çağırır. Gerçek implementasyon app.domains.ai'dan import edilecek."""
    raise NotImplementedError("AI engine entegrasyonu henüz tamamlanmadı")


def _fallback_analysis(device: dict) -> str:
    lines = ["## Cihaz Durum Raporu (Kural Tabanlı)\n"]
    hs = device.get("health_score", 0)
    bat = device.get("battery", {})
    lines.append(f"**Cihaz:** {device.get('name', '?')} ({device.get('brand', '')})")
    lines.append(f"**Platform:** {device.get('platform', '?').upper()}")
    lines.append(f"**Saglik Puani:** {hs}/100\n")
    if bat.get("level", 100) < 20:
        lines.append("- Batarya seviyesi kritik.")
    if bat.get("temperature", 25) > 40:
        lines.append("- Cihaz asiri isiyor.")
    status_str = ("uygundur" if hs >= 80
                  else "kullanilabilir ama optimizasyon gerekir" if hs >= 50
                  else "uygun degil")
    lines.append(f"\n**Sonuc:** Cihaz test kosumu icin {status_str}.")
    return "\n".join(lines)


@router.post("/ai/analyze")
def ai_analyze_device(body: AiAnalyzeBody):
    """Cihaz sağlık analizini AI ile yapar; AI yoksa kural tabanlı fallback."""
    devices = _discover_all_devices()
    device = next((d for d in devices if d["serial"] == body.serial), None)
    if not device:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    logcat_snippet = ""
    if device.get("platform") == "android":
        try:
            result = subprocess.run(
                ["adb", "-s", body.serial, "logcat", "-t", "50", "*:W"],
                capture_output=True, text=True, timeout=10,
            )
            logcat_snippet = result.stdout.strip()[-2000:]
        except Exception:
            logcat_snippet = "(logcat okunamadi)"

    device_info = json.dumps(device, indent=2, ensure_ascii=False, default=str)
    prompt = (
        f"Sen kıdemli bir mobil platform mühendisisin.\n"
        f"Aşağıdaki cihaz bilgilerini ve son log çıktısını analiz et.\n\n"
        f"CİHAZ BİLGİLERİ:\n{device_info}\n\n"
        f"SON LOG (Warning+):\n{logcat_snippet or '(log mevcut değil)'}\n\n"
        f"1. Genel Durum Özeti\n2. Performans Değerlendirmesi\n"
        f"3. Tespit Edilen Sorunlar\n4. Öneriler\n5. Test Uygunluğu\n6. Risk Skoru (0-10)\n"
        f"Markdown formatında yanıtla."
    )
    try:
        analysis = _call_ai("Sen kıdemli bir mobil platform ve QA mühendisisin.", prompt)
        return {"serial": body.serial, "device_name": device.get("name", body.serial),
                "health_score": device.get("health_score", 0), "analysis": analysis,
                "analyzed_at": datetime.utcnow().isoformat()}
    except Exception as exc:
        logger.error("AI analiz hatası: %s", exc)
        return {"serial": body.serial, "device_name": device.get("name", body.serial),
                "health_score": device.get("health_score", 0),
                "analysis": _fallback_analysis(device),
                "analyzed_at": datetime.utcnow().isoformat(), "ai_fallback": True}


@router.post("/ai/troubleshoot")
def ai_troubleshoot(body: AiTroubleshootBody):
    """Mobil cihaz sorun giderme asistanı (AI destekli)."""
    device_context = ""
    if body.serial:
        devices = _discover_all_devices()
        device = next((d for d in devices if d["serial"] == body.serial), None)
        if device:
            device_context = f"\nCihaz Bilgileri:\n{json.dumps(device, indent=2, ensure_ascii=False, default=str)}"

    prompt = (
        f"Sen mobil cihaz yönetimi konusunda uzman bir mühendissin (Android + iOS).\n"
        f"Kısa, net ve uygulanabilir cevaplar ver. Gerekiyorsa ADB/xcrun komutları öner.\n"
        f"{device_context}\n\nKullanıcı Sorusu: {body.question}\n\n"
        f"Türkçe ve Markdown formatında yanıtla."
    )
    try:
        answer = _call_ai("Sen mobil cihaz yönetimi ve QA uzmanısın. Türkçe yanıt ver.", prompt, 0.4)
        return {"answer": answer, "serial": body.serial or None}
    except Exception as exc:
        return {"answer": f"AI kullanılamıyor: {exc}", "serial": body.serial or None, "ai_fallback": True}


@router.post("/ai/recommend-config")
def ai_recommend_config(body: AiRecommendBody):
    """Mevcut cihaz havuzuna göre optimum test yapılandırması önerir."""
    devices = _discover_all_devices()
    online = [d for d in devices if d.get("online")]
    summary = json.dumps(
        [{"name": d["name"], "platform": d.get("platform"),
          "version": d.get("android_version") or d.get("ios_version"),
          "health": d.get("health_score")} for d in online],
        indent=2, ensure_ascii=False, default=str,
    )
    prompt = (
        f'Sen bir mobil QA strateji uzmanısın.\n'
        f'Mevcut cihaz havuzuna göre "{body.test_type}" testi için optimum yapılandırmayı öner.\n\n'
        f"Mevcut Cihazlar:\n{summary}\n\nTürkçe ve Markdown formatında yanıtla."
    )
    try:
        rec = _call_ai("Sen mobil QA strateji uzmanısın.", prompt, 0.4)
        return {"test_type": body.test_type, "device_count": len(online), "recommendation": rec}
    except Exception as exc:
        return {"test_type": body.test_type, "device_count": len(online),
                "recommendation": f"AI önerisi oluşturulamadı: {exc}", "ai_fallback": True}


@router.post("/ai/analyze-logs")
def ai_analyze_logs(body: AiAnalyzeLogsBody):
    """Cihaz loglarını AI ile analiz eder."""
    log_content = ""
    try:
        if body.log_type == "crash":
            log_content = _adb_shell(body.serial, f"logcat -b crash -t {body.lines}", timeout=15)
        elif body.log_type == "anr":
            log_content = _adb_shell(
                body.serial,
                f"cat /data/anr/traces.txt 2>/dev/null | tail -{body.lines}",
                timeout=15,
            )
        else:
            log_content = _adb_shell(body.serial, f"logcat -t {body.lines} *:W", timeout=15)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Log okunamadı: {exc}")

    if not log_content.strip():
        return {"analysis": "Log içeriği boş — analiz edilecek veri yok.", "serial": body.serial}

    prompt = (
        f"Sen kıdemli bir mobil uygulama geliştirici ve QA mühendisisin.\n"
        f"Aşağıdaki {body.log_type} loglarını analiz et.\n\n"
        f"LOG İÇERİĞİ:\n{log_content[-3000:]}\n\n"
        f"1. Tespit Edilen Hatalar\n2. Kök Neden Analizi\n3. Bellek Sızıntısı Tespiti\n"
        f"4. Çözüm Önerileri\n5. Kritiklik Seviyesi\n\nTürkçe ve Markdown formatında yanıtla."
    )
    try:
        analysis = _call_ai("Sen mobil log analiz uzmanısın.", prompt)
        return {"serial": body.serial, "log_type": body.log_type, "analysis": analysis,
                "lines_analyzed": body.lines, "analyzed_at": datetime.utcnow().isoformat()}
    except Exception as exc:
        return {"serial": body.serial, "log_type": body.log_type,
                "analysis": f"AI analizi yapılamadı: {exc}", "ai_fallback": True}


# ─── Routes — AVD / Simulator Yönetimi ───────────────────────────────────────

@router.get("/avds")
def list_manager_avds():
    """Android Studio'da tanımlı AVD listesi."""
    try:
        result = subprocess.run(["emulator", "-list-avds"], capture_output=True, text=True, timeout=8)
        avds = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return {"avds": avds, "count": len(avds), "emulator_available": True}
    except FileNotFoundError:
        return {"avds": [], "count": 0, "emulator_available": False}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/simulators")
def list_manager_simulators():
    """Tüm iOS simülatörleri (booted + shutdown) döndürür."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        sims = []
        for runtime, devices in data.get("devices", {}).items():
            ios_ver = runtime.split("iOS-")[-1].replace("-", ".") if "iOS-" in runtime else runtime
            for d in devices:
                sims.append({"udid": d.get("udid"), "name": d.get("name"),
                             "state": d.get("state"), "runtime": ios_ver})
        return {"simulators": sims, "count": len(sims), "xcrun_available": True}
    except FileNotFoundError:
        return {"simulators": [], "count": 0, "xcrun_available": False}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/avds/launch")
def launch_manager_avd(body: LaunchAvdBody):
    """AVD (Android) veya iOS Simulator başlatır."""
    avd_name = body.avd_name.strip()
    sim_udid = body.simulator_udid.strip()

    if avd_name:
        try:
            subprocess.Popen(
                ["emulator", "-avd", avd_name, "-no-snapshot-load"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return {"launched": True, "avd_name": avd_name}
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="emulator komutu bulunamadı")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    elif sim_udid:
        try:
            subprocess.run(["xcrun", "simctl", "boot", sim_udid], check=False, timeout=10)
            subprocess.Popen(["open", "-a", "Simulator"])
            return {"launched": True, "simulator_udid": sim_udid}
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="xcrun bulunamadı")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    else:
        raise HTTPException(status_code=400, detail="avd_name veya simulator_udid zorunludur")
