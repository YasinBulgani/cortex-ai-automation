"""
Mobile routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/mobile_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/mobile.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile", tags=["engine", "mobile"])

# ── SSE run kuyrukları ────────────────────────────────────────────────────────
# master run_id → queue.Queue  (tüm cihazların birleşik çıktısı)
_run_queues: dict[str, queue.Queue] = {}
_run_lock = threading.Lock()


# ─── Config dependency (placeholder — gerçek settings'den import) ─────────

class _Settings:
    """Geçici settings stub. Gerçek config.py'den alınacak."""
    BROWSERSTACK_USERNAME: str = os.environ.get("BROWSERSTACK_USERNAME", "")
    BROWSERSTACK_ACCESS_KEY: str = os.environ.get("BROWSERSTACK_ACCESS_KEY", "")
    BROWSERSTACK_BUILD: str = os.environ.get("BROWSERSTACK_BUILD", "")
    BROWSERSTACK_PROJECT: str = os.environ.get("BROWSERSTACK_PROJECT", "")
    SAUCE_USERNAME: str = os.environ.get("SAUCE_USERNAME", "")
    SAUCE_ACCESS_KEY: str = os.environ.get("SAUCE_ACCESS_KEY", "")
    SAUCE_REGION: str = os.environ.get("SAUCE_REGION", "us-west-1")
    BASE_DIR: Path = Path(__file__).resolve().parents[5]
    TESTS_DIR: Path = BASE_DIR / "tests"
    MOBILE_ARTIFACTS_DIR: Path = BASE_DIR / "mobile_artifacts"


_settings = _Settings()


def get_settings() -> _Settings:
    return _settings


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RunSingleBody(BaseModel):
    device_slug: str = Field("", description="Cihaz slug veya device_name")
    device_name: str = Field("")
    browser: str = Field("chromium")
    base_url: str = Field("")
    tags: str = Field("")
    scenario_ids: list[str] = Field(default_factory=list)
    app_upload_id: str | None = None


class RunParallelBody(BaseModel):
    device_slugs: list[str] = Field(default_factory=list)
    device_names: list[str] = Field(default_factory=list)
    browser: str = Field("chromium")
    base_url: str = Field("")
    tags: str = Field("")
    scenario_ids: list[str] = Field(default_factory=list)
    app_upload_id: str | None = None


class RunLiveBody(BaseModel):
    serials: list[str] = Field(default_factory=list)
    tags: str = Field("")
    uploaded_app_id: str | None = None
    project_id: str | None = None


class LaunchEmulatorBody(BaseModel):
    avd_name: str = Field("")
    simulator_udid: str = Field("")


# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _active_farm(s: _Settings) -> str:
    """Aktif cihaz farm'ını döndürür: 'browserstack' | 'sauce' | 'local'."""
    if s.BROWSERSTACK_USERNAME and s.BROWSERSTACK_ACCESS_KEY:
        return "browserstack"
    if s.SAUCE_USERNAME and s.SAUCE_ACCESS_KEY:
        return "sauce"
    return "local"


def _build_pytest_cmd(
    browser: str,
    base_url: str,
    tags: str,
    scenario_ids: list[str],
    s: _Settings,
) -> list[str]:
    """Tek cihaz için pytest komut listesi oluşturur."""
    cmd = [
        sys.executable, "-m", "pytest",
        "--tb=short", "-v", "--color=no",
        "--import-mode=importlib",
        f"--browser={browser}",
        str(s.TESTS_DIR),
    ]
    if tags and tags not in ("not ai", ""):
        cmd += ["-m", tags]
    return cmd


def _farm_env_overrides(s: _Settings) -> dict:
    """Aktif farm için subprocess env değişkenlerini döndürür."""
    farm = _active_farm(s)
    extra: dict = {}
    if farm == "browserstack":
        extra["BROWSERSTACK_USERNAME"] = s.BROWSERSTACK_USERNAME
        extra["BROWSERSTACK_ACCESS_KEY"] = s.BROWSERSTACK_ACCESS_KEY
        extra["BROWSERSTACK_BUILD"] = s.BROWSERSTACK_BUILD
        extra["BROWSERSTACK_PROJECT"] = s.BROWSERSTACK_PROJECT
    elif farm == "sauce":
        extra["SAUCE_USERNAME"] = s.SAUCE_USERNAME
        extra["SAUCE_ACCESS_KEY"] = s.SAUCE_ACCESS_KEY
        extra["SAUCE_REGION"] = s.SAUCE_REGION
    return extra


def _is_tool_available(tool: str) -> bool:
    """PATH'te araç var mı kontrol eder."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, timeout=2)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _detect_adb_devices() -> list[dict]:
    """'adb devices -l' çıktısını ayrıştırır."""
    devices = []
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:
            line = line.strip()
            if not line or "offline" in line or "unauthorized" in line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state = parts[1]
            if state != "device":
                continue
            name_res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "ro.product.model"],
                capture_output=True, text=True, timeout=3,
            )
            model = name_res.stdout.strip() or serial
            ver_res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "ro.build.version.release"],
                capture_output=True, text=True, timeout=3,
            )
            android_ver = ver_res.stdout.strip() or "?"
            api_res = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "ro.build.version.sdk"],
                capture_output=True, text=True, timeout=3,
            )
            api_level = api_res.stdout.strip() or "?"
            is_emulator = serial.startswith("emulator-")
            devices.append({
                "serial": serial,
                "name": model,
                "platform": "android",
                "os": f"Android {android_ver} (API {api_level})",
                "device_type": "emulator" if is_emulator else "physical",
                "state": state,
                "icon": "robot",
                "source": "adb",
            })
    except FileNotFoundError:
        logger.debug("adb bulunamadı — Android emülatör tespiti atlanıyor")
    except subprocess.TimeoutExpired:
        logger.debug("adb komutu zaman aşımına uğradı")
    except Exception as exc:
        logger.debug("ADB hatası: %s", exc)
    return devices


def _detect_ios_simulators() -> list[dict]:
    """'xcrun simctl list devices --json' çıktısını ayrıştırır (macOS)."""
    devices = []
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True, text=True, timeout=8,
        )
        data = json.loads(result.stdout)
        for runtime, sims in data.get("devices", {}).items():
            ios_version = "?"
            if "iOS-" in runtime:
                ios_version = runtime.split("iOS-")[-1].replace("-", ".")
            for sim in sims:
                if sim.get("state") != "Booted":
                    continue
                devices.append({
                    "serial": sim.get("udid", ""),
                    "name": sim.get("name", "iOS Simulator"),
                    "platform": "ios",
                    "os": f"iOS {ios_version}",
                    "device_type": "simulator",
                    "state": "device",
                    "icon": "apple",
                    "source": "xcrun",
                })
    except FileNotFoundError:
        logger.debug("xcrun bulunamadı — iOS simülatör tespiti atlanıyor (macOS gerekli)")
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        logger.debug("xcrun hatası: %s", exc)
    except Exception as exc:
        logger.debug("iOS simülatör tespiti hatası: %s", exc)
    return devices


def _single_device_worker(
    q_ref: queue.Queue,
    device_slug: str,
    browser: str,
    base_url: str,
    tags: str,
    scenario_ids: list[str],
    app_upload_id: str | None,
    s: _Settings,
) -> None:
    """Tek cihazda test koşar; çıktıları q_ref'e device_name tag'i ile yazar."""
    env = os.environ.copy()
    env["MOBILE_DEVICE_NAME"] = device_slug
    env.update(_farm_env_overrides(s))
    if base_url:
        env["BASE_URL"] = base_url
    if app_upload_id:
        env["MOBILE_APP_UPLOAD_ID"] = app_upload_id

    farm = _active_farm(s)
    device_display = device_slug

    def _put(msg: dict):
        msg["device_name"] = device_display
        q_ref.put(msg)

    farm_note = f" [farm: {farm}]" if farm != "local" else ""
    _put({"type": "output", "text": f"[{device_display}]{farm_note} Test koşumu başlatılıyor..."})

    cmd = _build_pytest_cmd(browser, base_url, tags, scenario_ids, s)
    passed = failed = 0

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(s.BASE_DIR),
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
            proc.stdout.close()

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


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/devices")
def list_devices(s: Annotated[_Settings, Depends(get_settings)]):
    """Desteklenen cihaz kataloğunu döndürür."""
    android = _detect_adb_devices()
    ios = _detect_ios_simulators()
    return android + ios


@router.get("/farm-status")
def farm_status(s: Annotated[_Settings, Depends(get_settings)]):
    """Aktif cihaz farm konfigürasyonunu döndürür."""
    farm = _active_farm(s)
    bs_configured = bool(s.BROWSERSTACK_USERNAME and s.BROWSERSTACK_ACCESS_KEY)
    sauce_configured = bool(s.SAUCE_USERNAME and s.SAUCE_ACCESS_KEY)

    def _mask(val: str) -> str:
        return val[:4] + "****" if len(val) > 4 else "****"

    return {
        "active_farm": farm,
        "local_emulation": farm == "local",
        "browserstack": {
            "configured": bs_configured,
            "username": _mask(s.BROWSERSTACK_USERNAME) if bs_configured else None,
            "build": s.BROWSERSTACK_BUILD if bs_configured else None,
            "project": s.BROWSERSTACK_PROJECT if bs_configured else None,
            "ws_endpoint": "wss://cdp.browserstack.com/playwright",
        },
        "sauce": {
            "configured": sauce_configured,
            "username": _mask(s.SAUCE_USERNAME) if sauce_configured else None,
            "region": s.SAUCE_REGION if sauce_configured else None,
            "ws_endpoint": (
                f"wss://ondemand.{s.SAUCE_REGION}.saucelabs.com/playwright"
                if sauce_configured else None
            ),
        },
        "note": {
            "browserstack": "Testler BrowserStack Automate üzerinde gerçek tarayıcıyla çalışacak.",
            "sauce": "Testler Sauce Labs Playwright entegrasyonu üzerinde çalışacak.",
            "local": "Playwright yerel emülasyon kullanılıyor (gerçek cihaz yok).",
        }.get(farm, ""),
    }


@router.get("/emulators")
def list_emulators(s: Annotated[_Settings, Depends(get_settings)]):
    """Yerel makinede çalışan Android emülatörleri (ADB) ve iOS simülatörleri döndürür."""
    android_devices = _detect_adb_devices()
    ios_devices = _detect_ios_simulators()
    all_devices = android_devices + ios_devices
    return {
        "total": len(all_devices),
        "android": len(android_devices),
        "ios": len(ios_devices),
        "devices": all_devices,
        "adb_available": _is_tool_available("adb"),
        "xcrun_available": _is_tool_available("xcrun"),
    }


@router.post("/emulators/launch")
def launch_emulator(body: LaunchEmulatorBody):
    """Belirtilen AVD'yi (Android) ya da Simulator'ü (iOS) başlatır."""
    avd_name = body.avd_name.strip()
    sim_udid = body.simulator_udid.strip()

    if avd_name:
        try:
            subprocess.Popen(
                ["emulator", "-avd", avd_name, "-no-snapshot-load"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"launched": True, "avd_name": avd_name, "note": "Emülatör arka planda başlatılıyor..."}
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Android emulator komutu bulunamadı. Android Studio SDK'yı PATH'e ekleyin.")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    elif sim_udid:
        try:
            subprocess.run(["xcrun", "simctl", "boot", sim_udid], check=False, timeout=10)
            subprocess.Popen(["open", "-a", "Simulator"])
            return {"launched": True, "simulator_udid": sim_udid, "note": "iOS Simulator açılıyor..."}
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="xcrun bulunamadı. Xcode Command Line Tools gerekli.")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    else:
        raise HTTPException(status_code=400, detail="avd_name veya simulator_udid zorunludur")


@router.get("/avds")
def list_avds():
    """'emulator -list-avds' çıktısını döndürür."""
    try:
        result = subprocess.run(
            ["emulator", "-list-avds"],
            capture_output=True, text=True, timeout=8,
        )
        avds = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return {"avds": avds, "count": len(avds), "emulator_available": True}
    except FileNotFoundError:
        return {
            "avds": [], "count": 0, "emulator_available": False,
            "note": "Android emulator bulunamadı. Android Studio SDK PATH ayarını kontrol edin.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_single(
    body: RunSingleBody,
    s: Annotated[_Settings, Depends(get_settings)],
):
    """Tek bir cihazda test koşturur. SSE için run_id döndürür."""
    device_slug = (body.device_slug or body.device_name).strip()
    if not device_slug:
        raise HTTPException(status_code=400, detail="device_slug zorunludur")

    browser = body.browser.lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"

    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_" + device_slug
    q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[run_id] = q

    threading.Thread(
        target=_single_device_worker,
        args=(q, device_slug, browser, body.base_url, body.tags, body.scenario_ids, body.app_upload_id, s),
        daemon=True,
    ).start()

    return {"run_id": run_id, "device_slug": device_slug}


@router.post("/run-parallel", status_code=status.HTTP_201_CREATED)
def run_parallel(
    body: RunParallelBody,
    s: Annotated[_Settings, Depends(get_settings)],
):
    """Birden fazla cihazda eş zamanlı test koşturur."""
    device_slugs = body.device_slugs or body.device_names
    if not device_slugs:
        raise HTTPException(status_code=400, detail="device_slugs listesi zorunludur")

    browser = body.browser.lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"

    master_run_id = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_parallel"
    master_q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[master_run_id] = master_q

    total_devices = len(device_slugs)
    done_count = [0]
    done_lock = threading.Lock()

    def _device_thread_realtime(slug: str):
        env = os.environ.copy()
        env["MOBILE_DEVICE_NAME"] = slug
        env.update(_farm_env_overrides(s))
        if body.base_url:
            env["BASE_URL"] = body.base_url
        if body.app_upload_id:
            env["MOBILE_APP_UPLOAD_ID"] = body.app_upload_id

        farm = _active_farm(s)

        def _put(msg: dict):
            msg["device_name"] = slug
            master_q.put(msg)

        farm_note = f" [farm: {farm}]" if farm != "local" else ""
        _put({"type": "output", "text": f"[{slug}]{farm_note} Test koşumu başlatılıyor..."})

        cmd = _build_pytest_cmd(browser, body.base_url, body.tags, body.scenario_ids, s)
        passed = failed = 0

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(s.BASE_DIR),
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
                proc.stdout.close()

            proc.wait()
            _put({"type": "done", "returncode": proc.returncode, "passed": passed, "failed": failed})
        except Exception as exc:
            _put({"type": "error", "text": str(exc)})
            _put({"type": "done", "returncode": 1, "passed": passed, "failed": failed})

        with done_lock:
            done_count[0] += 1
            if done_count[0] >= total_devices:
                master_q.put({"type": "all_done", "device_name": "__master__"})

    for slug in device_slugs:
        threading.Thread(target=_device_thread_realtime, args=(slug,), daemon=True).start()

    device_run_ids = {s_slug: f"{master_run_id}_{s_slug}" for s_slug in device_slugs}
    return {
        "run_id": master_run_id,
        "device_slugs": device_slugs,
        "device_run_ids": device_run_ids,
        "stream_url": f"/api/mobile/run/{master_run_id}/stream",
    }


@router.get("/run/{run_id}/stream")
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
                    if msg.get("type") == "done" and not any(x in run_id for x in ("_parallel", "_live")):
                        yield f"data: {json.dumps({'type': 'all_done', 'run_id': run_id}, ensure_ascii=False)}\n\n"
                        break
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            with _run_lock:
                _run_queues.pop(run_id, None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/run/{run_id}/stop")
def stop_mobile_run(run_id: str):
    """Aktif SSE stream'i iptal eder."""
    with _run_lock:
        q = _run_queues.pop(run_id, None)
    if q:
        q.put({"type": "all_done", "device_name": "__stopped__", "stopped": True})
        return {"stopped": True, "run_id": run_id}
    raise HTTPException(status_code=404, detail="run bulunamadı")


@router.post("/upload-app", status_code=status.HTTP_201_CREATED)
async def upload_app(
    file: UploadFile = File(...),
    s: _Settings = Depends(get_settings),
):
    """APK veya IPA dosyasını sunucuya yükler; upload_id döndürür."""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş")

    ext = Path(filename).suffix.lower()
    if ext not in (".apk", ".ipa", ".aab", ".xapk"):
        raise HTTPException(status_code=400, detail=f"Desteklenmeyen dosya türü: {ext}")

    platform_hint = "android" if ext in (".apk", ".aab", ".xapk") else "ios"

    upload_id = str(uuid.uuid4())
    upload_dir = s.MOBILE_ARTIFACTS_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / filename
    content = await file.read()
    dest_path.write_bytes(content)
    size = dest_path.stat().st_size

    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "size": size,
        "platform_hint": platform_hint,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    (upload_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info("Uygulama yüklendi: %s (%d bytes) -> %s", filename, size, upload_id)
    return meta


@router.get("/upload-app/{upload_id}")
def get_upload_status(upload_id: str, s: Annotated[_Settings, Depends(get_settings)]):
    """Belirtilen upload_id'nin durumunu döndürür."""
    meta_path = s.MOBILE_ARTIFACTS_DIR / upload_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Upload bulunamadı")
    return json.loads(meta_path.read_text(encoding="utf-8"))


@router.post("/run-live", status_code=status.HTTP_201_CREATED)
def run_live(
    body: RunLiveBody,
    s: Annotated[_Settings, Depends(get_settings)],
):
    """Gerçek (ADB/Appium bağlı) cihazlarda test koşturur."""
    if not body.serials:
        raise HTTPException(status_code=400, detail="serials listesi zorunludur")

    master_run_id = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_live"
    master_q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[master_run_id] = master_q

    total = len(body.serials)
    done_count = [0]
    done_lock = threading.Lock()

    def _live_device_worker(serial: str):
        def _put(msg: dict):
            msg["device_name"] = serial
            master_q.put(msg)

        env = os.environ.copy()
        env["MOBILE_DEVICE_SERIAL"] = serial
        if body.tags:
            env["MOBILE_TAGS"] = body.tags
        if body.uploaded_app_id:
            env["MOBILE_APP_UPLOAD_ID"] = body.uploaded_app_id
        if body.project_id:
            env["MOBILE_PROJECT_ID"] = body.project_id

        _put({"type": "output", "text": f"[{serial}] Canlı cihaz koşumu başlatılıyor..."})

        cmd = [
            sys.executable, "-m", "pytest",
            "--tb=short", "-v", "--color=no",
            "--import-mode=importlib",
            str(s.TESTS_DIR),
        ]
        if body.tags and body.tags not in ("not ai", ""):
            cmd += ["-m", body.tags]

        passed = failed = 0
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(s.BASE_DIR),
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
                proc.stdout.close()
            proc.wait()
            _put({"type": "done", "returncode": proc.returncode, "passed": passed, "failed": failed})
        except Exception as exc:
            _put({"type": "error", "text": str(exc)})
            _put({"type": "done", "returncode": 1, "passed": passed, "failed": failed})

        with done_lock:
            done_count[0] += 1
            if done_count[0] >= total:
                master_q.put({"type": "all_done", "device_name": "__master__"})

    for serial in body.serials:
        threading.Thread(target=_live_device_worker, args=(serial,), daemon=True).start()

    return {
        "run_id": master_run_id,
        "serials": body.serials,
        "stream_url": f"/api/mobile/run/{master_run_id}/stream",
    }
