"""
Visium Farm — Mobil Test Otomasyon API'si
==========================================
Playwright mobil emülasyon tabanlı test koşumu:
  - Cihaz katalogu + farm durumu
  - Tekli / paralel cihaz koşumu (SSE stream)
  - APK / IPA yükleme
  - BrowserStack / Sauce Labs gerçek cihaz farm entegrasyonu

Blueprint: mobile_bp  →  /api/mobile/...
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import subprocess
import threading
import queue
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, Response

from config.settings import settings
from core.device_profiles import DEVICE_CATALOG, DEVICE_MAP

logger = logging.getLogger(__name__)

mobile_bp = Blueprint("mobile", __name__)

# ── SSE run kuyrukları ────────────────────────────────────────────────────────
# master run_id → queue.Queue  (tüm cihazların birleşik çıktısı)
# child  run_id → queue.Queue  (tek cihazın çıktısı — ileride kullanılabilir)
_run_queues: dict[str, queue.Queue] = {}
_run_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════════════════
# Yardımcı: pytest subprocess başlat
# ═══════════════════════════════════════════════════════════════════════════════

def _active_farm() -> str:
    """Aktif cihaz farm'ını döndürür: 'browserstack' | 'sauce' | 'local'."""
    if settings.BROWSERSTACK_USERNAME and settings.BROWSERSTACK_ACCESS_KEY:
        return "browserstack"
    if settings.SAUCE_USERNAME and settings.SAUCE_ACCESS_KEY:
        return "sauce"
    return "local"


def _build_pytest_cmd(
    browser: str,
    base_url: str,
    tags: str,
    scenario_ids: list[str],
) -> list[str]:
    """Tek cihaz için pytest komut listesi oluşturur."""
    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=short", "-v", "--color=no",
        "--import-mode=importlib",
        f"--browser={browser}",
        str(settings.TESTS_DIR),
    ]
    if tags and tags not in ("not ai", ""):
        cmd += ["-m", tags]
    return cmd


def _farm_env_overrides() -> dict:
    """
    Aktif farm için subprocess'e geçirilmesi gereken env değişkenlerini döndürür.
    BrowserStack / Sauce kimlik bilgileri subprocess'e miras bırakılır,
    böylece BrowserEngine.start() doğru farm'ı otomatik seçebilir.
    """
    farm = _active_farm()
    extra: dict = {}
    if farm == "browserstack":
        extra["BROWSERSTACK_USERNAME"] = settings.BROWSERSTACK_USERNAME
        extra["BROWSERSTACK_ACCESS_KEY"] = settings.BROWSERSTACK_ACCESS_KEY
        extra["BROWSERSTACK_BUILD"] = settings.BROWSERSTACK_BUILD
        extra["BROWSERSTACK_PROJECT"] = settings.BROWSERSTACK_PROJECT
    elif farm == "sauce":
        extra["SAUCE_USERNAME"] = settings.SAUCE_USERNAME
        extra["SAUCE_ACCESS_KEY"] = settings.SAUCE_ACCESS_KEY
        extra["SAUCE_REGION"] = settings.SAUCE_REGION
    return extra


def _single_device_worker(
    q_ref: queue.Queue,
    device_slug: str,
    browser: str,
    base_url: str,
    tags: str,
    scenario_ids: list[str],
    app_upload_id: str | None,
) -> None:
    """Tek cihazda test koşar; çıktıları q_ref'e device_name tag'i ile yazar."""
    env = os.environ.copy()
    env["MOBILE_DEVICE_NAME"] = device_slug
    env.update(_farm_env_overrides())   # BrowserStack / Sauce bilgilerini aktar
    if base_url:
        env["BASE_URL"] = base_url
    if app_upload_id:
        env["MOBILE_APP_UPLOAD_ID"] = app_upload_id

    device = DEVICE_MAP.get(device_slug)
    device_display = device.name if device else device_slug
    farm = _active_farm()

    def _put(msg: dict):
        msg["device_name"] = device_display
        q_ref.put(msg)

    farm_note = f" [farm: {farm}]" if farm != "local" else ""
    _put({"type": "output", "text": f"[{device_display}]{farm_note} Test koşumu başlatılıyor..."})

    cmd = _build_pytest_cmd(browser, base_url, tags, scenario_ids)
    passed = failed = 0

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        try:
            for line in proc.stdout:
                line_str = line.rstrip()
                if line_str.startswith("__SCREENSHOT__:"):
                    _put({"type": "image", "data": line_str.split(":", 1)[1]})
                else:
                    _put({"type": "output", "text": line_str})
                    p_match = re.search(r"(\d+) passed", line_str)
                    f_match = re.search(r"(\d+) failed", line_str)
                    if p_match:
                        passed = int(p_match.group(1))
                    if f_match:
                        failed = int(f_match.group(1))
                    # Bireysel test sonuçları
                    if re.match(r"PASSED ", line_str):
                        _put({"type": "test_result", "status": "passed", "text": line_str})
                    elif re.match(r"FAILED ", line_str):
                        _put({"type": "test_result", "status": "failed", "text": line_str})
        finally:
            proc.stdout.close()  # resource sızıntısını önle

        proc.wait()
        _put({
            "type": "done",
            "returncode": proc.returncode,
            "passed": passed,
            "failed": failed,
        })
    except Exception as exc:
        _put({"type": "error", "text": str(exc)})
        _put({"type": "done", "returncode": 1, "passed": passed, "failed": failed})


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: GET /api/mobile/devices
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/devices", methods=["GET"])
def list_devices():
    """Desteklenen cihaz kataloğunu döndürür."""
    return jsonify([d.to_dict() for d in DEVICE_CATALOG])


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: GET /api/mobile/farm-status
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/farm-status", methods=["GET"])
def farm_status():
    """
    Aktif cihaz farm konfigürasyonunu döndürür.
    BrowserStack ya da Sauce Labs kimlik bilgileri ayarlanmışsa ilgili farm aktif sayılır.
    """
    farm = _active_farm()

    bs_configured = bool(settings.BROWSERSTACK_USERNAME and settings.BROWSERSTACK_ACCESS_KEY)
    sauce_configured = bool(settings.SAUCE_USERNAME and settings.SAUCE_ACCESS_KEY)

    # Hassas değerleri gizle — yalnızca ilk 4 karakter göster
    def _mask(val: str) -> str:
        return val[:4] + "****" if len(val) > 4 else "****"

    payload = {
        "active_farm": farm,
        "local_emulation": farm == "local",
        "device_count": len(DEVICE_CATALOG),
        "browserstack": {
            "configured": bs_configured,
            "username": _mask(settings.BROWSERSTACK_USERNAME) if bs_configured else None,
            "build": settings.BROWSERSTACK_BUILD if bs_configured else None,
            "project": settings.BROWSERSTACK_PROJECT if bs_configured else None,
            "ws_endpoint": "wss://cdp.browserstack.com/playwright",
        },
        "sauce": {
            "configured": sauce_configured,
            "username": _mask(settings.SAUCE_USERNAME) if sauce_configured else None,
            "region": settings.SAUCE_REGION if sauce_configured else None,
            "ws_endpoint": (
                f"wss://ondemand.{settings.SAUCE_REGION}.saucelabs.com/playwright"
                if sauce_configured else None
            ),
        },
        "note": {
            "browserstack": "Testler BrowserStack Automate üzerinde gerçek tarayıcıyla çalışacak.",
            "sauce": "Testler Sauce Labs Playwright entegrasyonu üzerinde çalışacak.",
            "local": "Playwright yerel emülasyon kullanılıyor (gerçek cihaz yok).",
        }.get(farm, ""),
    }
    return jsonify(payload)


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: GET /api/mobile/emulators
# Android Studio AVD + iOS Simulator bağlı cihazları döndürür
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_adb_devices() -> list[dict]:
    """
    'adb devices -l' çıktısını ayrıştırır.
    Emülatörler emulator-XXXX satırlarından, gerçek cihazlar USB/tcpip'ten tanınır.
    """
    devices = []
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:          # İlk satır "List of devices attached" başlığı
            line = line.strip()
            if not line or "offline" in line or "unauthorized" in line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state  = parts[1]           # "device" | "offline" | "unauthorized"
            if state != "device":
                continue

            # Cihaz adını ADB'den sorgula
            name_res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "ro.product.model"],
                capture_output=True, text=True, timeout=3,
            )
            model = name_res.stdout.strip() or serial

            # Versiyon
            ver_res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "ro.build.version.release"],
                capture_output=True, text=True, timeout=3,
            )
            android_ver = ver_res.stdout.strip() or "?"

            # API Level
            api_res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "ro.build.version.sdk"],
                capture_output=True, text=True, timeout=3,
            )
            api_level = api_res.stdout.strip() or "?"

            is_emulator = serial.startswith("emulator-")
            device_type = "emulator" if is_emulator else "physical"

            devices.append({
                "serial":       serial,
                "name":         model,
                "platform":     "android",
                "os":           f"Android {android_ver} (API {api_level})",
                "device_type":  device_type,
                "state":        state,
                "icon":         "🤖",
                "source":       "adb",
            })
    except FileNotFoundError:
        logger.debug("adb bulunamadı — Android emülatör tespiti atlanıyor")
    except subprocess.TimeoutExpired:
        logger.debug("adb komutu zaman aşımına uğradı")
    except Exception as exc:
        logger.debug("ADB hatası: %s", exc)
    return devices


def _detect_ios_simulators() -> list[dict]:
    """
    'xcrun simctl list devices --json' çıktısını ayrıştırır (macOS).
    Yalnızca Booted (çalışan) simülatörleri döndürür.
    """
    devices = []
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True, text=True, timeout=8,
        )
        data = json.loads(result.stdout)
        for runtime, sims in data.get("devices", {}).items():
            # runtime: "com.apple.CoreSimulator.SimRuntime.iOS-17-0"
            ios_version = "?"
            if "iOS-" in runtime:
                ios_version = runtime.split("iOS-")[-1].replace("-", ".")
            for sim in sims:
                if sim.get("state") != "Booted":
                    continue
                devices.append({
                    "serial":       sim.get("udid", ""),
                    "name":         sim.get("name", "iOS Simulator"),
                    "platform":     "ios",
                    "os":           f"iOS {ios_version}",
                    "device_type":  "simulator",
                    "state":        "device",
                    "icon":         "🍎",
                    "source":       "xcrun",
                })
    except FileNotFoundError:
        logger.debug("xcrun bulunamadı — iOS simülatör tespiti atlanıyor (macOS gerekli)")
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        logger.debug("xcrun hatası: %s", exc)
    except Exception as exc:
        logger.debug("iOS simülatör tespiti hatası: %s", exc)
    return devices


@mobile_bp.route("/api/mobile/emulators", methods=["GET"])
def list_emulators():
    """
    Yerel makinede çalışan Android emülatörleri (ADB) ve
    iOS simülatörleri (xcrun simctl) döndürür.

    Her cihaz için:
      serial, name, platform, os, device_type (emulator|simulator|physical),
      state ("device"), icon, source ("adb"|"xcrun")
    """
    android_devices = _detect_adb_devices()
    ios_devices = _detect_ios_simulators()
    all_devices = android_devices + ios_devices

    return jsonify({
        "total": len(all_devices),
        "android": len(android_devices),
        "ios": len(ios_devices),
        "devices": all_devices,
        "adb_available": _is_tool_available("adb"),
        "xcrun_available": _is_tool_available("xcrun"),
    })


def _is_tool_available(tool: str) -> bool:
    """PATH'te adb veya xcrun var mı kontrol eder."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, timeout=2)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: POST /api/mobile/emulators/launch
# Android Studio AVD veya iOS Simulator başlatır
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/emulators/launch", methods=["POST"])
def launch_emulator():
    """
    Belirtilen AVD'yi başlatır (Android) ya da Simulator'ü açar (iOS).

    Body:
      { "avd_name": "Pixel_7_API_33" }         → Android AVD
      { "simulator_udid": "ABC-DEF-..." }        → iOS Simulator
    """
    data = request.json or {}
    avd_name = data.get("avd_name", "").strip()
    sim_udid = data.get("simulator_udid", "").strip()

    if avd_name:
        # Android emulator'ı arka planda başlat
        try:
            subprocess.Popen(
                ["emulator", "-avd", avd_name, "-no-snapshot-load"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return jsonify({"launched": True, "avd_name": avd_name, "note": "Emülatör arka planda başlatılıyor…"})
        except FileNotFoundError:
            return jsonify({"launched": False, "error": "Android emulator komutu bulunamadı. Android Studio SDK'yı PATH'e ekleyin."}), 500
        except Exception as exc:
            return jsonify({"launched": False, "error": str(exc)}), 500

    elif sim_udid:
        # iOS Simulator'ü başlat
        try:
            subprocess.run(["xcrun", "simctl", "boot", sim_udid], check=False, timeout=10)
            subprocess.Popen(["open", "-a", "Simulator"])
            return jsonify({"launched": True, "simulator_udid": sim_udid, "note": "iOS Simulator açılıyor…"})
        except FileNotFoundError:
            return jsonify({"launched": False, "error": "xcrun bulunamadı. Xcode Command Line Tools gerekli."}), 500
        except Exception as exc:
            return jsonify({"launched": False, "error": str(exc)}), 500
    else:
        return jsonify({"error": "avd_name veya simulator_udid zorunludur"}), 400


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: GET /api/mobile/avds
# Android Studio'da tanımlı AVD listesi
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/avds", methods=["GET"])
def list_avds():
    """
    'emulator -list-avds' çıktısını döndürür.
    Bağlı olmayan, yalnızca tanımlı AVD'leri listeler.
    """
    try:
        result = subprocess.run(
            ["emulator", "-list-avds"],
            capture_output=True, text=True, timeout=8,
        )
        avds = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return jsonify({
            "avds": avds,
            "count": len(avds),
            "emulator_available": True,
        })
    except FileNotFoundError:
        return jsonify({
            "avds": [],
            "count": 0,
            "emulator_available": False,
            "note": "Android emulator bulunamadı. Android Studio SDK PATH ayarını kontrol edin.",
        })
    except Exception as exc:
        return jsonify({"avds": [], "count": 0, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: POST /api/mobile/run  (tek cihaz)
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/run", methods=["POST"])
def run_single():
    """Tek bir cihazda test koşturur. SSE için run_id döndürür."""
    data = request.json or {}
    device_slug = (data.get("device_slug") or data.get("device_name", "")).strip()
    if not device_slug or device_slug not in DEVICE_MAP:
        return jsonify({"error": f"Geçersiz cihaz: {device_slug!r}"}), 400

    browser = str(data.get("browser", "chromium")).lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"
    base_url = str(data.get("base_url", "") or "")
    tags = str(data.get("tags", "") or "")
    scenario_ids: list[str] = data.get("scenario_ids") or []
    app_upload_id: str | None = data.get("app_upload_id") or None

    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_" + device_slug
    q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[run_id] = q

    threading.Thread(
        target=_single_device_worker,
        args=(q, device_slug, browser, base_url, tags, scenario_ids, app_upload_id),
        daemon=True,
    ).start()

    return jsonify({"run_id": run_id, "device_slug": device_slug})


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: POST /api/mobile/run-parallel  (çoklu cihaz)
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/run-parallel", methods=["POST"])
def run_parallel():
    """
    Birden fazla cihazda eş zamanlı test koşturur.
    Tek master SSE stream'i; her mesaj device_name tag'i taşır.
    """
    data = request.json or {}
    device_slugs: list[str] = data.get("device_slugs") or data.get("device_names") or []
    if not device_slugs:
        return jsonify({"error": "device_slugs listesi zorunludur"}), 400

    # Geçerli cihazları filtrele
    valid_slugs = [s for s in device_slugs if s in DEVICE_MAP]
    if not valid_slugs:
        return jsonify({"error": "Geçerli cihaz bulunamadı"}), 400

    browser = str(data.get("browser", "chromium")).lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"
    base_url = str(data.get("base_url", "") or "")
    tags = str(data.get("tags", "") or "")
    scenario_ids: list[str] = data.get("scenario_ids") or []
    app_upload_id: str | None = data.get("app_upload_id") or None

    master_run_id = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_parallel"
    master_q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[master_run_id] = master_q

    total_devices = len(valid_slugs)
    done_count = [0]
    done_lock = threading.Lock()

    def _device_thread(slug: str):
        device_q: queue.Queue = queue.Queue()
        _single_device_worker(device_q, slug, browser, base_url, tags, scenario_ids, app_upload_id)
        # _single_device_worker senkron çalışır — bitince kuyruğu master'a aktarıyoruz
        # Bunun yerine, gerçek zamanlı yönlendirme için ayrı thread pattern kullanıyoruz:

    def _device_thread_realtime(slug: str):
        env = os.environ.copy()
        env["MOBILE_DEVICE_NAME"] = slug
        env.update(_farm_env_overrides())   # BrowserStack / Sauce bilgilerini aktar
        if base_url:
            env["BASE_URL"] = base_url
        if app_upload_id:
            env["MOBILE_APP_UPLOAD_ID"] = app_upload_id

        device = DEVICE_MAP.get(slug)
        device_display = device.name if device else slug
        farm = _active_farm()

        def _put(msg: dict):
            msg["device_name"] = device_display
            master_q.put(msg)

        farm_note = f" [farm: {farm}]" if farm != "local" else ""
        _put({"type": "output", "text": f"[{device_display}]{farm_note} Test koşumu başlatılıyor..."})

        cmd = _build_pytest_cmd(browser, base_url, tags, scenario_ids)
        passed = failed = 0

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(settings.BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            try:
                for line in proc.stdout:
                    line_str = line.rstrip()
                    if line_str.startswith("__SCREENSHOT__:"):
                        _put({"type": "image", "data": line_str.split(":", 1)[1]})
                    else:
                        _put({"type": "output", "text": line_str})
                        p_match = re.search(r"(\d+) passed", line_str)
                        f_match = re.search(r"(\d+) failed", line_str)
                        if p_match:
                            passed = int(p_match.group(1))
                        if f_match:
                            failed = int(f_match.group(1))
                        if re.match(r"PASSED ", line_str):
                            _put({"type": "test_result", "status": "passed", "text": line_str})
                        elif re.match(r"FAILED ", line_str):
                            _put({"type": "test_result", "status": "failed", "text": line_str})
            finally:
                proc.stdout.close()  # resource sızıntısını önle

            proc.wait()
            _put({
                "type": "done",
                "returncode": proc.returncode,
                "passed": passed,
                "failed": failed,
            })
        except Exception as exc:
            _put({"type": "error", "text": str(exc)})
            _put({"type": "done", "returncode": 1, "passed": passed, "failed": failed})

        # Tüm cihazlar bitince master stream'i kapat
        with done_lock:
            done_count[0] += 1
            if done_count[0] >= total_devices:
                master_q.put({"type": "all_done", "device_name": "__master__"})

    for slug in valid_slugs:
        threading.Thread(target=_device_thread_realtime, args=(slug,), daemon=True).start()

    device_run_ids = {s: f"{master_run_id}_{s}" for s in valid_slugs}
    return jsonify({
        "run_id": master_run_id,
        "device_slugs": valid_slugs,
        "device_run_ids": device_run_ids,
        "stream_url": f"/api/mobile/run/{master_run_id}/stream",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: GET /api/mobile/run/<run_id>/stream  (SSE)
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/run/<run_id>/stream")
def stream_mobile_run(run_id: str):
    """SSE stream: run_id için canlı test çıktısı."""
    def generate():
        q = _run_queues.get(run_id)
        if not q:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Run ID bulunamadı veya oturum kapandı'})}\n\n"
            return

        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    if msg.get("type") == "all_done":
                        yield f"event: all_done\ndata: {json.dumps({'run_id': run_id})}\n\n"
                        break
                    # Tek cihaz koşumunda done ile bitir
                    if msg.get("type") == "done" and "_parallel" not in run_id:
                        break
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            with _run_lock:
                _run_queues.pop(run_id, None)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: POST /api/mobile/upload-app  (APK / IPA yükleme)
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/upload-app", methods=["POST"])
def upload_app():
    """APK veya IPA dosyasını sunucuya yükler; upload_id döndürür."""
    if "file" not in request.files:
        return jsonify({"error": "Dosya bulunamadı (field adı: 'file')"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Dosya adı boş"}), 400

    filename = f.filename
    ext = Path(filename).suffix.lower()
    if ext not in (".apk", ".ipa", ".aab", ".xapk"):
        return jsonify({"error": f"Desteklenmeyen dosya türü: {ext}"}), 400

    platform_hint = "android" if ext in (".apk", ".aab", ".xapk") else "ios"

    upload_id = str(uuid.uuid4())
    upload_dir = settings.MOBILE_ARTIFACTS_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / filename
    f.save(str(dest_path))
    size = dest_path.stat().st_size

    # Meta dosyası
    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "size": size,
        "platform_hint": platform_hint,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    (upload_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info("Uygulama yüklendi: %s (%d bytes) → %s", filename, size, upload_id)
    return jsonify(meta), 201


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint: GET /api/mobile/upload-app/<upload_id>
# ═══════════════════════════════════════════════════════════════════════════════

@mobile_bp.route("/api/mobile/upload-app/<upload_id>", methods=["GET"])
def get_upload_status(upload_id: str):
    """Belirtilen upload_id'nin durumunu döndürür."""
    meta_path = settings.MOBILE_ARTIFACTS_DIR / upload_id / "meta.json"
    if not meta_path.exists():
        return jsonify({"error": "Upload bulunamadı"}), 404
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return jsonify(meta)
