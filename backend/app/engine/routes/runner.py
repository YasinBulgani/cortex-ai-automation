"""
Runner routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/runner_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/runner.py — APIRouter, port 8000 (consolidated)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["engine", "runner"])

# ─── Global state ─────────────────────────────────────────────────────────────

_run_queues: dict[str, queue.Queue] = {}
_run_lock = threading.Lock()
_cancelled_runs: set[str] = set()

_DEFAULT_RUN_TIMEOUT_S = int(os.environ.get("RUN_TIMEOUT_S", str(30 * 60)))
_REAP_GRACE_S = 30

_VALID_RUN_MODES = {"simulation", "playwright"}
_DEFAULT_RUN_MODE = os.environ.get("TSPM_DEFAULT_RUN_MODE", "simulation").lower()
if _DEFAULT_RUN_MODE not in _VALID_RUN_MODES:
    _DEFAULT_RUN_MODE = "simulation"


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    markers: Optional[str] = "not ai"
    tags: Optional[str] = None
    feature: Optional[str] = None
    features_list: list[str] = Field(default_factory=list)
    browser: str = "chromium"


class NexusRunRequest(BaseModel):
    scenarios: list[dict] = Field(default_factory=list)
    browser: str = "chromium"
    mode: Optional[str] = None
    base_url: Optional[str] = ""


class MavenRunRequest(BaseModel):
    maven_path: str = ""


class CreateProjectRequest(BaseModel):
    name: str
    platform: str = "web"


class RunFeatureRequest(BaseModel):
    feature_path: str
    browser: str = "chromium"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_settings():
    """Engine settings — çevresel değişken yoksa geçici varsayılan döner."""
    try:
        from app.config import settings as app_settings  # type: ignore
        return app_settings
    except Exception:
        class _FallbackSettings:
            BASE_DIR = Path(__file__).parent.parent.parent.parent.parent
            ALLURE_RESULTS_DIR = BASE_DIR / "allure-results"
            ALLURE_REPORT_DIR = BASE_DIR / "allure-report"
            TESTS_DIR = BASE_DIR / "tests"
            FEATURES_DIR = BASE_DIR / "features"
        return _FallbackSettings()


def _record_test_run(run_id: str, marker: str, passed: int, failed: int, duration_ms: int) -> None:
    try:
        from app.domains.engine.db import record_test_run  # type: ignore
        record_test_run(run_id, marker, passed, failed, duration_ms)
    except Exception as e:
        logger.debug("record_test_run atlandı: %s", e)


def _spawn_timeout_watchdog(
    proc: subprocess.Popen,
    timeout_s: int,
    on_timeout,
) -> threading.Event:
    stop_event = threading.Event()

    def _watch() -> None:
        if stop_event.wait(timeout=timeout_s):
            return
        if proc.poll() is None:
            try:
                proc.kill()
            except Exception as e:
                logger.warning("watchdog kill hatası: %s", e)
            on_timeout()

    threading.Thread(target=_watch, daemon=True).start()
    return stop_event


def _step_import_lines(settings) -> list[str]:
    imports: list[str] = []
    steps_dir = settings.BASE_DIR / "steps"
    for step_file in sorted(steps_dir.glob("*.py")):
        if step_file.name.startswith("_") or step_file.name in {"__init__.py", "conftest.py"}:
            continue
        imports.append(f"from steps.{step_file.stem} import *  # noqa: F401,F403")
    return imports


def _build_glue_file_content(relative_feature_path: str, settings) -> str:
    lines = [
        "from pytest_bdd import scenarios",
        *_step_import_lines(settings),
        "",
        f'scenarios("{relative_feature_path}")',
        "",
    ]
    return "\n".join(lines)


def _nexus_status_for_scenario(scenario: dict) -> tuple[str, str]:
    steps = scenario.get("steps") or []
    if not steps:
        return "skipped", "Senaryoda çalıştırılabilir adım bulunamadı"
    fingerprint = json.dumps(
        {"id": scenario.get("id"), "title": scenario.get("title"), "steps": steps},
        ensure_ascii=False,
        sort_keys=True,
    )
    bucket = int(hashlib.md5(fingerprint.encode("utf-8")).hexdigest(), 16) % 10
    if bucket < 7:
        return "passed", ""
    if bucket < 9:
        return "failed", "TimeoutError: Element not found (engine deterministic simulation)"
    return "skipped", "Koşum planlayıcısı senaryoyu bu turda atladı"


def _maven_allowed_roots(settings) -> list[Path]:
    configured = os.environ.get("MAVEN_ALLOWED_ROOTS", "").strip()
    if configured:
        return [Path(item).resolve() for item in configured.split(os.pathsep) if item.strip()]
    default_root = Path(
        os.environ.get("MAVEN_PROJECT_PATH", str(settings.BASE_DIR / "NeurexTestOtomasyon"))
    ).resolve()
    return [default_root, (settings.BASE_DIR / "projects").resolve()]


def _is_within_root(candidate: Path, root: Path) -> bool:
    return candidate == root or root in candidate.parents


def _resolve_maven_project_path(raw_path: str, settings) -> Path | None:
    source = raw_path.strip() or os.environ.get(
        "MAVEN_PROJECT_PATH", str(settings.BASE_DIR / "NeurexTestOtomasyon")
    )
    candidate = Path(source)
    if not candidate.is_absolute():
        candidate = (settings.BASE_DIR / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not any(_is_within_root(candidate, root) for root in _maven_allowed_roots(settings)):
        return None
    return candidate


def _auto_heal_failures(q_ref: queue.Queue, run_id: str, failed_tests: list[dict]) -> None:
    if not failed_tests:
        return
    try:
        from core.self_healing.healer import SelfHealingEngine  # type: ignore
        healer = SelfHealingEngine()
        healed = []
        for ft in failed_tests[:10]:
            test_id = ft.get("test_id", "unknown")
            error_msg = ft.get("error_msg", "")
            if not error_msg:
                continue
            try:
                result = healer.diagnose_and_heal(test_id=test_id, error_message=error_msg)
                if result:
                    healed.append({
                        "test_id": test_id,
                        "category": result.category.value,
                        "fix": result.fix_applied[:300],
                        "confidence": result.confidence,
                        "auto_applied": result.auto_applied,
                    })
            except Exception as e:
                logger.debug("Self-heal failed for %s: %s", test_id, e)
        if healed:
            q_ref.put({
                "type": "self_heal",
                "run_id": run_id,
                "healed_count": len(healed),
                "results": healed,
            })
    except Exception as e:
        logger.debug("Auto-heal skipped: %s", e)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/run")
def run_tests(body: RunRequest):
    settings = _get_settings()
    markers = body.markers or body.tags or "not ai"
    feature = body.feature
    features_list = body.features_list
    browser = body.browser.lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"
    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

    q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[run_id] = q

    run_timeout = int(os.environ.get("PYTEST_RUN_TIMEOUT", "600"))

    def _worker(q_ref, r_id, m_str, f_single, f_list, _browser):
        cmd = [
            sys.executable, "-m", "pytest",
            "--alluredir", str(settings.ALLURE_RESULTS_DIR),
            "--tb=short", "-v", "--color=no",
            "--import-mode=importlib",
            f"--browser={_browser}",
        ]
        if f_list:
            for f in f_list:
                safe_name = f.replace("/", "_").replace("\\", "_")
                stem = Path(safe_name).stem
                test_file = settings.TESTS_DIR / f"test_{stem}.py"
                if test_file.exists():
                    cmd.append(str(test_file))
                else:
                    cmd.append(str(settings.TESTS_DIR))
                    break
        elif f_single:
            cmd.append(f_single)
        else:
            cmd.append(str(settings.TESTS_DIR))

        if m_str and m_str not in ("not ai", ""):
            cmd += ["-m", m_str]

        try:
            passed, failed = 0, 0
            start_time = datetime.now()
            failed_tests: list[dict] = []
            _current_test = None
            _current_error_lines: list[str] = []
            timed_out = {"flag": False}

            proc = subprocess.Popen(
                cmd, cwd=str(settings.BASE_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )

            def _on_timeout() -> None:
                timed_out["flag"] = True
                q_ref.put({
                    "type": "error",
                    "text": (
                        f"Koşum zaman aşımına uğradı "
                        f"({_DEFAULT_RUN_TIMEOUT_S // 60} dk); süreç sonlandırıldı."
                    ),
                })

            watchdog_stop = _spawn_timeout_watchdog(proc, _DEFAULT_RUN_TIMEOUT_S, _on_timeout)

            for line in proc.stdout:
                if r_id in _cancelled_runs:
                    proc.kill()
                    proc.wait()
                    q_ref.put({"type": "output", "text": "Koşum iptal edildi."})
                    q_ref.put({"type": "done", "returncode": -2, "cancelled": True})
                    with _run_lock:
                        _cancelled_runs.discard(r_id)
                    return

                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > run_timeout:
                    proc.kill()
                    proc.wait()
                    q_ref.put({"type": "error", "text": f"Test zaman aşımına uğradı (>{run_timeout}s)"})
                    q_ref.put({"type": "done", "returncode": -1})
                    return

                line_str = line.rstrip()
                if line_str.startswith("__SCREENSHOT__:"):
                    q_ref.put({"type": "image", "data": line_str.split(":", 1)[1]})
                else:
                    q_ref.put({"type": "output", "text": line_str})
                    p_match = re.search(r"(\d+) passed", line_str)
                    f_match = re.search(r"(\d+) failed", line_str)
                    if p_match:
                        passed = int(p_match.group(1))
                    if f_match:
                        failed = int(f_match.group(1))

                    fail_line = re.match(r"FAILED (.+::test\w+)", line_str)
                    if fail_line:
                        _current_test = fail_line.group(1).strip()
                        _current_error_lines = []
                    elif _current_test and line_str.startswith("E "):
                        _current_error_lines.append(line_str[2:])
                    elif _current_test and line_str.startswith("_ "):
                        if _current_error_lines:
                            failed_tests.append({
                                "test_id": _current_test,
                                "error_msg": " | ".join(_current_error_lines[:5]),
                            })
                        _current_test = None
                        _current_error_lines = []

            if _current_test and _current_error_lines:
                failed_tests.append({
                    "test_id": _current_test,
                    "error_msg": " | ".join(_current_error_lines[:5]),
                })

            watchdog_stop.set()
            try:
                proc.wait(timeout=_REAP_GRACE_S)
            except subprocess.TimeoutExpired:
                logger.warning("Proc reap %ss içinde bitmedi, zorla kapatılıyor.", _REAP_GRACE_S)
                proc.kill()
                proc.wait(timeout=5)

            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            _record_test_run(r_id, m_str or "all", passed, failed, duration)

            if failed > 0:
                _auto_heal_failures(q_ref, r_id, failed_tests)

            allure_bin = shutil.which("allure")
            if allure_bin:
                try:
                    subprocess.run(
                        [allure_bin, "generate", str(settings.ALLURE_RESULTS_DIR),
                         "-o", str(settings.ALLURE_REPORT_DIR), "--clean"],
                        check=False, timeout=60,
                    )
                except subprocess.TimeoutExpired:
                    logger.warning("Allure generate 60 sn içinde tamamlanamadı; atlandı.")

            returncode = proc.returncode if proc.returncode is not None else 124
            q_ref.put({"type": "done", "returncode": returncode, "timed_out": timed_out["flag"]})
        except Exception as e:
            try:
                watchdog_stop.set()  # type: ignore[name-defined]
            except NameError:
                pass
            q_ref.put({"type": "error", "text": str(e)})
            q_ref.put({"type": "done", "returncode": 1})

    threading.Thread(
        target=_worker,
        args=(q, run_id, markers, feature, features_list, browser),
        daemon=True,
    ).start()

    return {"run_id": run_id, "browser": browser}


@router.post("/nexus/run")
def run_nexus_execution(body: NexusRunRequest):
    """TSPM execution runner — senaryo bazlı koşu.

    mode:
      "simulation" (default) — deterministik senaryo hash simülasyonu.
      "playwright"            — gerçek pytest + Playwright.
    """
    settings = _get_settings()
    scenarios = body.scenarios
    browser = body.browser.lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"

    mode = (body.mode or _DEFAULT_RUN_MODE).lower()
    if mode not in _VALID_RUN_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz mode: {mode!r}. Beklenen: {sorted(_VALID_RUN_MODES)}",
        )

    if not scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scenarios listesi zorunludur",
        )

    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[run_id] = q

    if mode == "playwright":
        def _pw_worker():
            _run_playwright_worker(q, run_id, scenarios, browser, body.base_url or "", settings)

        threading.Thread(target=_pw_worker, daemon=True).start()
        return {"run_id": run_id, "browser": browser, "mode": "playwright"}

    def _sim_worker(q_ref, r_id: str, scenario_items: list[dict], _browser: str, base_url: str):
        failed = passed = skipped = 0
        q_ref.put({
            "type": "output",
            "text": (
                f"Nexus execution başladı "
                f"({len(scenario_items)} senaryo, browser={_browser}, mode=simulation)"
            ),
            "mode": "simulation",
        })
        q_ref.put({
            "type": "mode_notice",
            "mode": "simulation",
            "text": (
                "Simülasyon modu: Bu koşum gerçek tarayıcı çalıştırmaz; "
                "sonuçlar senaryo hash'inden üretilir. Gerçek koşum için "
                "`mode=playwright` parametresi kullanın."
            ),
        })
        if base_url:
            q_ref.put({"type": "output", "text": f"Base URL: {base_url}"})

        for index, scenario in enumerate(scenario_items, 1):
            if r_id in _cancelled_runs:
                q_ref.put({"type": "output", "text": "Koşum iptal edildi."})
                q_ref.put({"type": "done", "returncode": -2, "cancelled": True})
                with _run_lock:
                    _cancelled_runs.discard(r_id)
                return

            title = scenario.get("title") or f"Scenario {index}"
            scenario_id = scenario.get("id", "")
            q_ref.put({"type": "output", "text": f"[{index}/{len(scenario_items)}] {title} işleniyor"})
            time.sleep(0.2)

            sc_status, error = _nexus_status_for_scenario(scenario)
            if sc_status == "passed":
                passed += 1
            elif sc_status == "failed":
                failed += 1
            else:
                skipped += 1

            q_ref.put({
                "type": "test_result",
                "scenario_id": scenario_id,
                "result_id": scenario.get("result_id"),
                "title": title,
                "status": sc_status,
                "error": error,
            })

        _record_test_run(r_id, "nexus-execution", passed, failed, len(scenario_items) * 200)
        q_ref.put({
            "type": "output",
            "text": f"Nexus execution tamamlandı: geçti={passed}, kaldı={failed}, atlandı={skipped}",
        })
        q_ref.put({
            "type": "done",
            "returncode": 0 if failed == 0 else 1,
            "mode": "simulation",
        })

    threading.Thread(
        target=_sim_worker,
        args=(q, run_id, scenarios, browser, body.base_url or ""),
        daemon=True,
    ).start()
    return {"run_id": run_id, "browser": browser, "mode": "simulation"}


def _run_playwright_worker(
    q_ref: queue.Queue,
    r_id: str,
    scenario_items: list[dict],
    _browser: str,
    base_url: str,
    settings,
) -> None:
    try:
        from core.scenario_to_feature import (  # type: ignore
            cleanup_feature_package,
            generate_feature_package,
        )
    except ImportError as exc:
        q_ref.put({"type": "error", "text": f"core.scenario_to_feature import hatası: {exc}"})
        q_ref.put({"type": "done", "returncode": 1, "mode": "playwright"})
        return

    try:
        pkg = generate_feature_package(
            base_dir=settings.BASE_DIR,
            run_id=r_id,
            scenarios=scenario_items,
        )
    except Exception as exc:
        q_ref.put({"type": "error", "text": f"Feature üretim hatası: {exc}"})
        q_ref.put({"type": "done", "returncode": 1, "mode": "playwright"})
        return

    q_ref.put({
        "type": "output",
        "text": f"Playwright koşumu başlıyor (browser={_browser}, scenarios={len(scenario_items)})",
        "mode": "playwright",
    })

    cmd = [
        sys.executable, "-m", "pytest",
        "--alluredir", str(settings.ALLURE_RESULTS_DIR),
        "--tb=short", "-v", "--color=no",
        "--import-mode=importlib",
        f"--browser={_browser}",
        str(pkg.test_file),
    ]
    env = os.environ.copy()
    if base_url:
        env["BASE_URL"] = base_url

    start_time = datetime.now()
    passed = failed = scenario_index = 0

    try:
        proc = subprocess.Popen(
            cmd, cwd=str(settings.BASE_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=env,
        )
        timed_out = {"flag": False}

        def _on_timeout() -> None:
            timed_out["flag"] = True
            q_ref.put({
                "type": "error",
                "text": f"Koşum {_DEFAULT_RUN_TIMEOUT_S // 60} dk'da tamamlanamadı, sonlandırıldı.",
            })

        stop_wd = _spawn_timeout_watchdog(proc, _DEFAULT_RUN_TIMEOUT_S, _on_timeout)

        for line in proc.stdout:
            line_str = line.rstrip()
            q_ref.put({"type": "output", "text": line_str})
            m_pass = re.search(r"PASSED\s+.+::test_(\w+)", line_str)
            m_fail = re.search(r"FAILED\s+.+::test_(\w+)", line_str)
            if m_pass and scenario_index < len(scenario_items):
                sc = scenario_items[scenario_index]
                q_ref.put({
                    "type": "test_result",
                    "scenario_id": sc.get("id", ""),
                    "result_id": sc.get("result_id"),
                    "title": sc.get("title") or "",
                    "status": "passed",
                    "error": "",
                })
                passed += 1
                scenario_index += 1
            elif m_fail and scenario_index < len(scenario_items):
                sc = scenario_items[scenario_index]
                q_ref.put({
                    "type": "test_result",
                    "scenario_id": sc.get("id", ""),
                    "result_id": sc.get("result_id"),
                    "title": sc.get("title") or "",
                    "status": "failed",
                    "error": "pytest failure — trace Allure raporunda",
                })
                failed += 1
                scenario_index += 1

        stop_wd.set()
        try:
            proc.wait(timeout=_REAP_GRACE_S)
        except subprocess.TimeoutExpired:
            proc.kill()

        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _record_test_run(r_id, "nexus-execution-playwright", passed, failed, duration)

        allure_bin = shutil.which("allure")
        if allure_bin:
            try:
                subprocess.run(
                    [allure_bin, "generate", str(settings.ALLURE_RESULTS_DIR),
                     "-o", str(settings.ALLURE_REPORT_DIR), "--clean"],
                    check=False, timeout=60,
                )
            except subprocess.TimeoutExpired:
                pass

        q_ref.put({
            "type": "output",
            "text": f"Playwright koşumu tamamlandı: geçti={passed}, kaldı={failed}",
        })
        q_ref.put({
            "type": "done",
            "returncode": 0 if failed == 0 else 1,
            "mode": "playwright",
            "timed_out": timed_out["flag"],
        })
    except Exception as exc:
        logger.exception("Playwright worker hatası")
        q_ref.put({"type": "error", "text": f"Playwright hatası: {exc}"})
        q_ref.put({"type": "done", "returncode": 1, "mode": "playwright"})
    finally:
        try:
            from core.scenario_to_feature import cleanup_feature_package  # type: ignore
            cleanup_feature_package(settings.BASE_DIR, r_id)
        except Exception:
            pass


@router.get("/run/{run_id}/stream")
def stream_run(run_id: str):
    def generate():
        q = _run_queues.get(run_id)
        if not q:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Session closed or ID invalid'})}\n\n"
            return
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f"data: {json.dumps(msg)}\n\n"
                    if msg.get("type") == "done":
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


@router.delete("/run/{run_id}/cancel", status_code=status.HTTP_200_OK)
@router.post("/run/{run_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_run(run_id: str):
    """Çalışan bir koşumu iptal eder. Worker bir sonraki döngüde çıkar."""
    with _run_lock:
        if run_id not in _run_queues:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="run_id bulunamadı veya zaten bitti",
            )
        _cancelled_runs.add(run_id)
    return {"ok": True, "run_id": run_id}


@router.post("/run-maven")
def run_maven_tests(body: MavenRunRequest):
    settings = _get_settings()
    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    maven_path = _resolve_maven_project_path(body.maven_path, settings)
    if maven_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="maven_path izinli kök dizinlerinin dışında",
        )

    q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[run_id] = q

    def _maven_worker(q_ref, r_id, p_path):
        if not p_path.exists():
            q_ref.put({"type": "error", "text": f"Maven proje dizini bulunamadı: {p_path}"})
            q_ref.put({"type": "done", "returncode": 1})
            return
        cmd = ["mvn", "clean", "test"]
        try:
            passed = failed = 0
            start_time = datetime.now()
            proc = subprocess.Popen(
                cmd, cwd=str(p_path),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in proc.stdout:
                line_str = line.rstrip()
                q_ref.put({"type": "output", "text": line_str})
                if "Tests run:" in line_str and "Failures:" in line_str:
                    try:
                        parts = line_str.split(",")
                        total = fails = errors = 0
                        for part in parts:
                            if "Tests run:" in part:
                                total = int(part.split(":")[1].strip())
                            elif "Failures:" in part:
                                fails = int(part.split(":")[1].strip())
                            elif "Errors:" in part:
                                errors = int(part.split(":")[1].strip())
                        failed += fails + errors
                        passed += total - failed
                    except Exception as exc:
                        logger.debug("Maven Surefire satırı parse edilemedi: %s", exc)
            proc.wait()
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            _record_test_run(r_id, "maven-neurex", passed, failed, duration)
            q_ref.put({"type": "done", "returncode": proc.returncode})
        except FileNotFoundError:
            q_ref.put({"type": "error", "text": "Maven ('mvn') komutu bulunamadı."})
            q_ref.put({"type": "done", "returncode": 1})
        except Exception as e:
            q_ref.put({"type": "error", "text": str(e)})
            q_ref.put({"type": "done", "returncode": 1})

    threading.Thread(target=_maven_worker, args=(q, run_id, maven_path), daemon=True).start()
    return {"run_id": run_id}


@router.post("/projects/create", status_code=status.HTTP_201_CREATED)
def create_project(body: CreateProjectRequest):
    settings = _get_settings()
    project_name = body.name.strip()
    platform = body.platform
    if not project_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proje adı gereklidir")

    import re as _re
    project_name = _re.sub(r"[^\w\s-]", "", project_name).strip()
    project_path = Path(settings.BASE_DIR) / "Test Otomasyon" / project_name

    if project_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu isimde bir proje zaten mevcut",
        )

    try:
        project_path.mkdir(parents=True, exist_ok=True)
        folders = ["features", "steps", "bodies", "settings", "reports", "screenshots"]
        if platform == "mobile":
            folders.append("drivers/mobile")
        elif platform == "desktop":
            folders.append("drivers/desktop")
        elif platform == "service":
            folders = ["features", "steps", "payloads", "responses", "reports"]
        elif platform == "batch":
            folders = ["jobs", "input", "output", "logs", "config"]

        for f in folders:
            (project_path / f).mkdir(parents=True, exist_ok=True)

        with open(project_path / "features" / "init.feature", "w") as f_file:
            f_file.write(
                f"Feature: {project_name} Baslangic\n  Scenario: Ilk Adim\n    Given ornek adim"
            )
        return {"message": f"'{project_name}' ({platform}) projesi başarıyla oluşturuldu", "name": project_name}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/list")
def list_projects():
    settings = _get_settings()
    projects_dir = Path(settings.BASE_DIR) / "Test Otomasyon"
    if not projects_dir.exists():
        return []
    return [{"name": d.name} for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]


@router.get("/projects/files/{project_name:path}")
def list_project_files(project_name: str):
    settings = _get_settings()
    project_path = Path(settings.BASE_DIR) / "Test Otomasyon" / project_name
    if not project_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")

    def get_tree(path: Path) -> list[dict]:
        tree = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if item.name.startswith(".") or item.name in {
                    "target", "node_modules", "bin", "obj", "allure-results", "allure-report"
                }:
                    continue
                node: dict = {"name": item.name, "path": str(item.relative_to(project_path))}
                if item.is_dir():
                    node["type"] = "folder"
                    node["children"] = get_tree(item)
                else:
                    node["type"] = "file"
                tree.append(node)
        except Exception as exc:
            logger.debug("Proje dosya ağacı okunamadı %s: %s", path, exc)
        return tree

    return get_tree(project_path)


@router.get("/projects/read-file")
def read_project_file(project: str, path: str):
    settings = _get_settings()
    if not project or not path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proje ve yol gereklidir")
    file_path = Path(settings.BASE_DIR) / "Test Otomasyon" / project / path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dosya bulunamadı")
    try:
        content = file_path.read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/projects/setup")
def setup_everything():
    return {"message": "Sistem kurulumu arka planda başlatıldı."}


@router.post("/projects/start-services")
def start_services():
    return {"message": "Servisler (N8N, Backend) başlatılıyor..."}


@router.get("/projects/status")
def get_system_status():
    import socket

    def is_port_open(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    return {"backend": True, "n8n": is_port_open(5678), "db": True}


@router.post("/runner/run-feature")
def run_feature_file(body: RunFeatureRequest):
    settings = _get_settings()
    feature_path = body.feature_path.strip()
    browser = body.browser.strip().lower()
    if browser not in ("chromium", "firefox", "webkit"):
        browser = "chromium"
    if not feature_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="feature_path zorunludur")

    path_obj = Path(feature_path)
    candidate_paths: list[Path] = []
    if path_obj.is_absolute():
        candidate_paths.append(path_obj)
    else:
        candidate_paths.extend([
            settings.BASE_DIR / feature_path,
            settings.FEATURES_DIR / feature_path,
            settings.FEATURES_DIR / path_obj.name,
        ])

    abs_path = next((c for c in candidate_paths if c.exists()), None)
    if abs_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dosya bulunamadı: {feature_path}",
        )

    target_path = abs_path
    if abs_path.suffix == ".feature":
        safe_name = feature_path.replace("/", "_").replace("\\", "_")
        glue_path = settings.TESTS_DIR / f"test_{Path(safe_name).stem}.py"
        if not glue_path.exists():
            glue_path.parent.mkdir(parents=True, exist_ok=True)
            relative_feature = os.path.relpath(abs_path, settings.TESTS_DIR).replace(os.sep, "/")
            glue_path.write_text(
                _build_glue_file_content(relative_feature, settings), encoding="utf-8"
            )
        target_path = glue_path

    allure_dir = settings.ALLURE_RESULTS_DIR
    allure_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "pytest",
        str(target_path),
        "--alluredir", str(allure_dir),
        "--tb=short", "-q",
        "--import-mode=importlib",
    ]

    try:
        start = datetime.now()
        env = os.environ.copy()
        env["BROWSER"] = browser
        proc = subprocess.run(
            cmd, cwd=str(settings.BASE_DIR),
            capture_output=True, text=True, timeout=120, env=env,
        )
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)

        output = (proc.stdout + proc.stderr).strip()
        passed = failed = 0
        p_match = re.search(r"(\d+) passed", output)
        f_match = re.search(r"(\d+) failed", output)
        if p_match:
            passed = int(p_match.group(1))
        if f_match:
            failed = int(f_match.group(1))

        run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        _record_test_run(run_id, str(feature_path), passed, failed, duration_ms)

        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "passed": passed,
            "failed": failed,
            "duration_ms": duration_ms,
            "output": output[-4000:],
            "allure_report_url": "/reports/allure-report/",
            "allure_results_dir": str(allure_dir),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Test zaman aşımına uğradı (>120s)",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
