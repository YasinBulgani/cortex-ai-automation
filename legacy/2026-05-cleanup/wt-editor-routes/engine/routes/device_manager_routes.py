"""
Visium Device Manager — AI Destekli Cihaz Yönetim API'si
=========================================================
Android (ADB) + iOS (xcrun simctl) cihazların merkezi yönetimi:
  - Detaylı cihaz keşfi (Android emülatör/fiziksel + iOS simülatör)
  - Canlı ekran yansıtma (periyodik screenshot SSE)
  - Uygulama yönetimi (listele, kur, kaldır, temizle, başlat, durdur)
  - Dosya yöneticisi (listele, push, pull, sil)
  - Canlı logcat/log stream (SSE)
  - Performans izleme (CPU, RAM, batarya SSE)
  - AI destekli sağlık analizi, sorun giderme, log analizi
  - AVD/Simulator başlatma

Blueprint: device_mgr_bp  →  /api/device-manager/...
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

from flask import Blueprint, request, jsonify, Response, send_file

from config.settings import settings

logger = logging.getLogger(__name__)

device_mgr_bp = Blueprint("device_manager", __name__)

_device_cache: dict = {"devices": [], "ts": 0}
_CACHE_TTL = 5

_executor = ThreadPoolExecutor(max_workers=8)


# ═══════════════════════════════════════════════════════════════════════════════
# ADB / xcrun Yardımcılar
# ═══════════════════════════════════════════════════════════════════════════════

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


SHELL_BLOCKLIST = [
    "rm -rf /", "reboot", "format", "mkfs", "dd if=",
    "su ", "su\n", "chmod 777 /", "flash", "fastboot",
    "wipe", "factory_reset",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Cihaz Keşfi
# ═══════════════════════════════════════════════════════════════════════════════

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
                app_count = len([l for l in ps.splitlines() if l.strip()])
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
        return _device_cache["devices"]

    android_future = _executor.submit(_discover_android_devices)
    ios_future = _executor.submit(_discover_ios_simulators)
    devices = android_future.result(timeout=15) + ios_future.result(timeout=15)
    _device_cache["devices"] = devices
    _device_cache["ts"] = now
    return devices


# ═══════════════════════════════════════════════════════════════════════════════
# Cihaz Listesi
# ═══════════════════════════════════════════════════════════════════════════════

@device_mgr_bp.route("/api/device-manager/devices", methods=["GET"])
def list_managed_devices():
    devices = _discover_all_devices()
    android = [d for d in devices if d.get("platform") == "android"]
    ios = [d for d in devices if d.get("platform") == "ios"]
    online = [d for d in devices if d.get("online")]
    emulators = [d for d in devices if d.get("device_type") == "emulator"]
    simulators = [d for d in devices if d.get("device_type") == "simulator"]
    physicals = [d for d in devices if d.get("device_type") == "physical"]

    return jsonify({
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
    })


@device_mgr_bp.route("/api/device-manager/device/<serial>/details", methods=["GET"])
def device_details(serial: str):
    devices = _discover_all_devices()
    device = next((d for d in devices if d["serial"] == serial), None)
    if not device:
        return jsonify({"error": f"Cihaz bulunamadı: {serial}"}), 404
    return jsonify(device)


# ═══════════════════════════════════════════════════════════════════════════════
# Canlı Ekran Yansıtma (Periyodik Screenshot SSE)
# ═══════════════════════════════════════════════════════════════════════════════

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


@device_mgr_bp.route("/api/device-manager/device/<serial>/live-screen", methods=["GET"])
def live_screen(serial: str):
    interval = int(request.args.get("interval", "1500"))
    interval = max(500, min(interval, 10000))
    platform = request.args.get("platform", "android")

    def generate():
        while True:
            b64 = _take_screenshot_b64(serial, platform)
            if b64:
                yield f"data: {json.dumps({'type': 'frame', 'data': b64, 'ts': datetime.utcnow().isoformat()})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'text': 'Screenshot alınamadı'})}\n\n"
            time.sleep(interval / 1000.0)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


# ═══════════════════════════════════════════════════════════════════════════════
# Temel Aksiyonlar (reboot, screenshot, install, shell)
# ═══════════════════════════════════════════════════════════════════════════════

@device_mgr_bp.route("/api/device-manager/actions/reboot", methods=["POST"])
def action_reboot():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    platform = data.get("platform", "android")
    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400
    try:
        if platform == "ios":
            subprocess.run(["xcrun", "simctl", "shutdown", serial], capture_output=True, timeout=10)
            time.sleep(1)
            subprocess.run(["xcrun", "simctl", "boot", serial], capture_output=True, timeout=10)
        else:
            _adb_cmd(serial, "reboot", timeout=15)
        return jsonify({"success": True, "serial": serial, "action": "reboot"})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/actions/screenshot", methods=["POST"])
def action_screenshot():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    platform = data.get("platform", "android")
    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400
    b64 = _take_screenshot_b64(serial, platform)
    if b64:
        return jsonify({"success": True, "serial": serial, "screenshot_b64": b64})
    return jsonify({"success": False, "error": "Screenshot alınamadı"}), 500


@device_mgr_bp.route("/api/device-manager/actions/install", methods=["POST"])
def action_install():
    serial = request.form.get("serial", "").strip()
    platform = request.form.get("platform", "android")
    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400
    if "file" not in request.files:
        return jsonify({"error": "Dosya gerekli"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Dosya adı boş"}), 400

    tmp_dir = Path(settings.BASE_DIR) / "tmp_install"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f.filename
    f.save(str(tmp_path))

    try:
        if platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "install", serial, str(tmp_path)],
                capture_output=True, text=True, timeout=120,
            )
            return jsonify({"success": result.returncode == 0, "serial": serial,
                            "filename": f.filename, "output": result.stdout.strip() or result.stderr.strip()})
        else:
            result = subprocess.run(
                ["adb", "-s", serial, "install", "-r", str(tmp_path)],
                capture_output=True, text=True, timeout=120,
            )
            return jsonify({"success": "Success" in result.stdout, "serial": serial,
                            "filename": f.filename, "output": result.stdout.strip()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        tmp_path.unlink(missing_ok=True)


@device_mgr_bp.route("/api/device-manager/actions/shell", methods=["POST"])
def action_shell():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    command = data.get("command", "").strip()
    platform = data.get("platform", "android")
    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400
    if not command:
        return jsonify({"error": "command zorunludur"}), 400
    if any(b in command for b in SHELL_BLOCKLIST):
        return jsonify({"error": "Bu komut güvenlik nedeniyle engellendi"}), 403

    try:
        if platform == "ios":
            result = subprocess.run(
                ["xcrun", "simctl", "spawn", serial] + command.split(),
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout.strip() or result.stderr.strip()
        else:
            output = _adb_shell(serial, command, timeout=15)
        return jsonify({"success": True, "serial": serial, "command": command, "output": output})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Uygulama Yönetimi
# ═══════════════════════════════════════════════════════════════════════════════

@device_mgr_bp.route("/api/device-manager/device/<serial>/apps", methods=["GET"])
def list_apps(serial: str):
    platform = request.args.get("platform", "android")
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
        return jsonify({"apps": apps, "count": len(apps), "serial": serial})
    except Exception as exc:
        return jsonify({"apps": [], "count": 0, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/actions/uninstall", methods=["POST"])
def action_uninstall():
    data = request.json or {}
    serial, package = data.get("serial", "").strip(), data.get("package", "").strip()
    platform = data.get("platform", "android")
    if not serial or not package:
        return jsonify({"error": "serial ve package zorunludur"}), 400
    try:
        if platform == "ios":
            result = subprocess.run(["xcrun", "simctl", "uninstall", serial, package],
                                    capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(["adb", "-s", serial, "uninstall", package],
                                    capture_output=True, text=True, timeout=30)
        return jsonify({"success": result.returncode == 0, "serial": serial, "package": package,
                        "output": result.stdout.strip()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/actions/clear-data", methods=["POST"])
def action_clear_data():
    data = request.json or {}
    serial, package = data.get("serial", "").strip(), data.get("package", "").strip()
    if not serial or not package:
        return jsonify({"error": "serial ve package zorunludur"}), 400
    try:
        output = _adb_shell(serial, f"pm clear {package}", timeout=15)
        return jsonify({"success": "Success" in output, "serial": serial, "package": package, "output": output})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/actions/force-stop", methods=["POST"])
def action_force_stop():
    data = request.json or {}
    serial, package = data.get("serial", "").strip(), data.get("package", "").strip()
    if not serial or not package:
        return jsonify({"error": "serial ve package zorunludur"}), 400
    try:
        _adb_shell(serial, f"am force-stop {package}", timeout=10)
        return jsonify({"success": True, "serial": serial, "package": package})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/actions/launch-app", methods=["POST"])
def action_launch_app():
    data = request.json or {}
    serial, package = data.get("serial", "").strip(), data.get("package", "").strip()
    platform = data.get("platform", "android")
    if not serial or not package:
        return jsonify({"error": "serial ve package zorunludur"}), 400
    try:
        if platform == "ios":
            result = subprocess.run(["xcrun", "simctl", "launch", serial, package],
                                    capture_output=True, text=True, timeout=15)
            output = result.stdout.strip()
        else:
            output = _adb_shell(serial, f"monkey -p {package} -c android.intent.category.LAUNCHER 1", timeout=10)
        return jsonify({"success": True, "serial": serial, "package": package, "output": output})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Dosya Yöneticisi
# ═══════════════════════════════════════════════════════════════════════════════

@device_mgr_bp.route("/api/device-manager/device/<serial>/files", methods=["GET"])
def list_files(serial: str):
    path = request.args.get("path", "/sdcard")
    platform = request.args.get("platform", "android")
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
        return jsonify({"files": files, "current_path": path, "serial": serial})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 403
    except Exception as exc:
        return jsonify({"files": [], "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/files/pull", methods=["POST"])
def file_pull():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    remote_path = data.get("path", "").strip()
    if not serial or not remote_path:
        return jsonify({"error": "serial ve path zorunludur"}), 400
    try:
        remote_path = _sanitize_path(remote_path)
        local_dir = Path(settings.BASE_DIR) / "tmp_file_transfer"
        local_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(remote_path).name
        local_path = local_dir / f"{serial}_{filename}"
        subprocess.run(["adb", "-s", serial, "pull", remote_path, str(local_path)],
                        capture_output=True, timeout=30)
        if local_path.exists():
            b64 = base64.b64encode(local_path.read_bytes()).decode("utf-8")
            size = local_path.stat().st_size
            local_path.unlink(missing_ok=True)
            return jsonify({"success": True, "filename": filename, "size": size, "data_b64": b64})
        return jsonify({"success": False, "error": "Dosya indirilemedi"}), 500
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 403
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/files/push", methods=["POST"])
def file_push():
    serial = request.form.get("serial", "").strip()
    remote_dir = request.form.get("remote_dir", "/sdcard").strip()
    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400
    if "file" not in request.files:
        return jsonify({"error": "Dosya gerekli"}), 400
    try:
        remote_dir = _sanitize_path(remote_dir)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 403

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Dosya adı boş"}), 400

    tmp_dir = Path(settings.BASE_DIR) / "tmp_file_transfer"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f.filename
    f.save(str(tmp_path))

    try:
        remote_path = f"{remote_dir}/{f.filename}".replace("//", "/")
        result = subprocess.run(["adb", "-s", serial, "push", str(tmp_path), remote_path],
                                capture_output=True, text=True, timeout=60)
        return jsonify({"success": result.returncode == 0, "serial": serial,
                        "remote_path": remote_path, "output": result.stdout.strip()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        tmp_path.unlink(missing_ok=True)


@device_mgr_bp.route("/api/device-manager/files/delete", methods=["DELETE"])
def file_delete():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    remote_path = data.get("path", "").strip()
    if not serial or not remote_path:
        return jsonify({"error": "serial ve path zorunludur"}), 400
    try:
        remote_path = _sanitize_path(remote_path)
        if remote_path in ("/", "/sdcard", "/data", "/system"):
            return jsonify({"error": "Kök dizin silinemez"}), 403
        _adb_shell(serial, f"rm -rf {remote_path}", timeout=10)
        return jsonify({"success": True, "serial": serial, "path": remote_path})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 403
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Canlı Logcat / Log Stream (SSE)
# ═══════════════════════════════════════════════════════════════════════════════

@device_mgr_bp.route("/api/device-manager/device/<serial>/logcat-stream", methods=["GET"])
def logcat_stream(serial: str):
    level = request.args.get("level", "V")
    tag = request.args.get("tag", "")
    platform = request.args.get("platform", "android")

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

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


@device_mgr_bp.route("/api/device-manager/device/<serial>/logcat", methods=["GET"])
def device_logcat(serial: str):
    lines_param = request.args.get("lines", "100")
    filter_tag = request.args.get("tag", "")

    def generate():
        cmd = ["adb", "-s", serial, "logcat", "-t", lines_param]
        if filter_tag:
            cmd += [f"{filter_tag}:V", "*:S"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            for line in result.stdout.splitlines():
                yield f"data: {json.dumps({'line': line}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ═══════════════════════════════════════════════════════════════════════════════
# Performans İzleme (SSE)
# ═══════════════════════════════════════════════════════════════════════════════

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


@device_mgr_bp.route("/api/device-manager/device/<serial>/perf-stream", methods=["GET"])
def perf_stream(serial: str):
    interval = int(request.args.get("interval", "2000"))
    interval = max(1000, min(interval, 30000))

    def generate():
        while True:
            metrics = _collect_perf_metrics(serial)
            yield f"data: {json.dumps(metrics, ensure_ascii=False)}\n\n"
            time.sleep(interval / 1000.0)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


# ═══════════════════════════════════════════════════════════════════════════════
# AI Destekli Özellikler
# ═══════════════════════════════════════════════════════════════════════════════

def _call_ai(system: str, prompt: str, temperature: float = 0.3) -> str:
    from core.ai_engine import AIEngine
    ai = AIEngine()
    return ai._call_llm([
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ], temperature=temperature)


@device_mgr_bp.route("/api/device-manager/ai/analyze", methods=["POST"])
def ai_analyze_device():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400

    devices = _discover_all_devices()
    device = next((d for d in devices if d["serial"] == serial), None)
    if not device:
        return jsonify({"error": "Cihaz bulunamadı"}), 404

    logcat_snippet = ""
    if device.get("platform") == "android":
        try:
            result = subprocess.run(
                ["adb", "-s", serial, "logcat", "-t", "50", "*:W"],
                capture_output=True, text=True, timeout=10,
            )
            logcat_snippet = result.stdout.strip()[-2000:]
        except Exception:
            logcat_snippet = "(logcat okunamadı)"

    device_info = json.dumps(device, indent=2, ensure_ascii=False, default=str)
    prompt = f"""Sen kıdemli bir mobil platform mühendisisin.
Aşağıdaki cihaz bilgilerini ve son log çıktısını analiz et.
Türkçe ve teknik bir rapor oluştur.

CİHAZ BİLGİLERİ:
{device_info}

SON LOG (Warning+):
{logcat_snippet or "(log mevcut değil)"}

Lütfen şu başlıklar altında analiz yap:
1. **Genel Durum Özeti**
2. **Performans Değerlendirmesi**
3. **Tespit Edilen Sorunlar**
4. **Öneriler**
5. **Test Uygunluğu**
6. **Risk Skoru** (0-10)

Yanıtı Markdown formatında ver.
"""
    try:
        analysis = _call_ai("Sen kıdemli bir mobil platform ve QA mühendisisin.", prompt)
        return jsonify({"serial": serial, "device_name": device.get("name", serial),
                        "health_score": device.get("health_score", 0), "analysis": analysis,
                        "analyzed_at": datetime.utcnow().isoformat()})
    except Exception as exc:
        logger.error("AI analiz hatası: %s", exc)
        return jsonify({"serial": serial, "device_name": device.get("name", serial),
                        "health_score": device.get("health_score", 0),
                        "analysis": _fallback_analysis(device),
                        "analyzed_at": datetime.utcnow().isoformat(), "ai_fallback": True})


def _fallback_analysis(device: dict) -> str:
    lines = ["## Cihaz Durum Raporu (Kural Tabanlı)\n"]
    hs = device.get("health_score", 0)
    bat = device.get("battery", {})
    lines.append(f"**Cihaz:** {device.get('name', '?')} ({device.get('brand', '')})")
    lines.append(f"**Platform:** {device.get('platform', '?').upper()}")
    lines.append(f"**Sağlık Puanı:** {hs}/100\n")
    if bat.get("level", 100) < 20:
        lines.append("- Batarya seviyesi kritik.")
    if bat.get("temperature", 25) > 40:
        lines.append("- Cihaz aşırı ısınıyor.")
    status = "uygundur" if hs >= 80 else "kullanılabilir ama optimizasyon gerekir" if hs >= 50 else "uygun değil"
    lines.append(f"\n**Sonuç:** Cihaz test koşumu için {status}.")
    return "\n".join(lines)


@device_mgr_bp.route("/api/device-manager/ai/troubleshoot", methods=["POST"])
def ai_troubleshoot():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question zorunludur"}), 400

    device_context = ""
    if serial:
        devices = _discover_all_devices()
        device = next((d for d in devices if d["serial"] == serial), None)
        if device:
            device_context = f"\nCihaz Bilgileri:\n{json.dumps(device, indent=2, ensure_ascii=False, default=str)}"

    prompt = f"""Sen mobil cihaz yönetimi konusunda uzman bir mühendissin (Android + iOS).
Kullanıcının sorusunu yanıtla. Kısa, net ve uygulanabilir cevaplar ver.
Gerekiyorsa ADB/xcrun komutları öner.
{device_context}

Kullanıcı Sorusu: {question}

Yanıtı Türkçe ve Markdown formatında ver.
"""
    try:
        answer = _call_ai("Sen mobil cihaz yönetimi ve QA uzmanısın. Türkçe yanıt ver.", prompt, 0.4)
        return jsonify({"answer": answer, "serial": serial or None})
    except Exception as exc:
        return jsonify({"answer": f"AI kullanılamıyor: {exc}", "serial": serial or None, "ai_fallback": True})


@device_mgr_bp.route("/api/device-manager/ai/recommend-config", methods=["POST"])
def ai_recommend_config():
    data = request.json or {}
    test_type = data.get("test_type", "genel")
    devices = _discover_all_devices()
    online = [d for d in devices if d.get("online")]
    summary = json.dumps(
        [{"name": d["name"], "platform": d.get("platform"), "version": d.get("android_version") or d.get("ios_version"),
          "health": d.get("health_score")} for d in online],
        indent=2, ensure_ascii=False, default=str,
    )
    prompt = f"""Sen bir mobil QA strateji uzmanısın.
Mevcut cihaz havuzuna göre "{test_type}" testi için optimum yapılandırmayı öner.

Mevcut Cihazlar:
{summary}

Türkçe ve Markdown formatında yanıt ver.
"""
    try:
        rec = _call_ai("Sen mobil QA strateji uzmanısın.", prompt, 0.4)
        return jsonify({"test_type": test_type, "device_count": len(online), "recommendation": rec})
    except Exception as exc:
        return jsonify({"test_type": test_type, "device_count": len(online),
                        "recommendation": f"AI önerisi oluşturulamadı: {exc}", "ai_fallback": True})


@device_mgr_bp.route("/api/device-manager/ai/analyze-logs", methods=["POST"])
def ai_analyze_logs():
    data = request.json or {}
    serial = data.get("serial", "").strip()
    log_type = data.get("log_type", "logcat")
    lines_count = min(int(data.get("lines", 200)), 500)

    if not serial:
        return jsonify({"error": "serial zorunludur"}), 400

    log_content = ""
    try:
        if log_type == "crash":
            log_content = _adb_shell(serial, "logcat -b crash -t " + str(lines_count), timeout=15)
        elif log_type == "anr":
            log_content = _adb_shell(serial, "cat /data/anr/traces.txt 2>/dev/null | tail -" + str(lines_count), timeout=15)
        else:
            log_content = _adb_shell(serial, f"logcat -t {lines_count} *:W", timeout=15)
    except Exception as exc:
        return jsonify({"error": f"Log okunamadı: {exc}"}), 500

    if not log_content.strip():
        return jsonify({"analysis": "Log içeriği boş — analiz edilecek veri yok.", "serial": serial})

    prompt = f"""Sen kıdemli bir mobil uygulama geliştirici ve QA mühendisisin.
Aşağıdaki {log_type} loglarını analiz et.

LOG İÇERİĞİ:
{log_content[-3000:]}

Lütfen şunları belirle:
1. **Tespit Edilen Hatalar** — Her hata için kısa açıklama
2. **Kök Neden Analizi** — Hataların olası nedenleri
3. **Bellek Sızıntısı Tespiti** — Varsa bellek sorunları
4. **Çözüm Önerileri** — Her sorun için pratik çözüm
5. **Kritiklik Seviyesi** — Düşük/Orta/Yüksek/Kritik

Yanıtı Türkçe ve Markdown formatında ver.
"""
    try:
        analysis = _call_ai("Sen mobil log analiz uzmanısın.", prompt)
        return jsonify({"serial": serial, "log_type": log_type, "analysis": analysis,
                        "lines_analyzed": lines_count, "analyzed_at": datetime.utcnow().isoformat()})
    except Exception as exc:
        return jsonify({"serial": serial, "log_type": log_type,
                        "analysis": f"AI analizi yapılamadı: {exc}", "ai_fallback": True})


# ═══════════════════════════════════════════════════════════════════════════════
# AVD / Simulator Yönetimi
# ═══════════════════════════════════════════════════════════════════════════════

@device_mgr_bp.route("/api/device-manager/avds", methods=["GET"])
def list_manager_avds():
    try:
        result = subprocess.run(["emulator", "-list-avds"], capture_output=True, text=True, timeout=8)
        avds = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return jsonify({"avds": avds, "count": len(avds), "emulator_available": True})
    except FileNotFoundError:
        return jsonify({"avds": [], "count": 0, "emulator_available": False})
    except Exception as exc:
        return jsonify({"avds": [], "count": 0, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/simulators", methods=["GET"])
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
        return jsonify({"simulators": sims, "count": len(sims), "xcrun_available": True})
    except FileNotFoundError:
        return jsonify({"simulators": [], "count": 0, "xcrun_available": False})
    except Exception as exc:
        return jsonify({"simulators": [], "count": 0, "error": str(exc)}), 500


@device_mgr_bp.route("/api/device-manager/avds/launch", methods=["POST"])
def launch_manager_avd():
    data = request.json or {}
    avd_name = data.get("avd_name", "").strip()
    sim_udid = data.get("simulator_udid", "").strip()

    if avd_name:
        try:
            subprocess.Popen(["emulator", "-avd", avd_name, "-no-snapshot-load"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({"launched": True, "avd_name": avd_name})
        except FileNotFoundError:
            return jsonify({"launched": False, "error": "emulator komutu bulunamadı"}), 500
        except Exception as exc:
            return jsonify({"launched": False, "error": str(exc)}), 500
    elif sim_udid:
        try:
            subprocess.run(["xcrun", "simctl", "boot", sim_udid], check=False, timeout=10)
            subprocess.Popen(["open", "-a", "Simulator"])
            return jsonify({"launched": True, "simulator_udid": sim_udid})
        except FileNotFoundError:
            return jsonify({"launched": False, "error": "xcrun bulunamadı"}), 500
        except Exception as exc:
            return jsonify({"launched": False, "error": str(exc)}), 500
    else:
        return jsonify({"error": "avd_name veya simulator_udid zorunludur"}), 400
