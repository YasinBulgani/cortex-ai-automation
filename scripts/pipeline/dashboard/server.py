#!/usr/bin/env python3
"""
dashboard/server.py — Canlı Pipeline Dashboard (FastAPI + SSE).

Çalıştırma:
    python3 -m uvicorn scripts.pipeline.dashboard.server:app --port 8765 --reload

Veya:
    make pipeline-dashboard

Endpoint'ler:
    GET  /                    → HTML dashboard
    GET  /api/state           → state.json
    GET  /api/stages          → stages.json (dep graph)
    GET  /api/metrics         → metrics.py output (JSON)
    GET  /api/events          → SSE stream (state değişimi + agent events)
    GET  /api/hf/status       → HF client ping (token/model/reachable)
    POST /api/run             → paralel pipeline başlat
    POST /api/run/stop        → aktif pipeline'ı durdur
    GET  /api/run/status      → running task durumu
    GET  /api/logs/{item}/{role}  → agent log içeriği
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline"))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    raise SystemExit(
        "fastapi required. Run: pip install fastapi uvicorn"
    )

STATE_PATH = REPO_ROOT / "docs" / "ai" / "pipeline" / "state.json"
STAGES_PATH = REPO_ROOT / "docs" / "ai" / "pipeline" / "stages.json"
EVENTS_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "events"
LOGS_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "logs"
STATIC_DIR = Path(__file__).parent / "static"
METRICS_SCRIPT = REPO_ROOT / "scripts" / "pipeline" / "metrics.py"
RUN_SCRIPT = REPO_ROOT / "scripts" / "pipeline" / "run_pipeline.py"
RUN_LOG = REPO_ROOT / "docs" / "ai" / "pipeline" / "run.log"

app = FastAPI(title="Pipeline Conductor Dashboard", version="1.0")

# ── Static mount ─────────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRACKING (running processes)
# ═══════════════════════════════════════════════════════════════════════════════


_running_task: Dict[str, Any] = {
    "process": None,
    "started_at": None,
    "mode": None,
    "pid": None,
}


# ═══════════════════════════════════════════════════════════════════════════════
# HTML DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════


@app.get("/", response_class=HTMLResponse)
async def index():
    html = STATIC_DIR / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>Dashboard</h1><p>Static dashboard missing. "
        "Expected at <code>scripts/pipeline/dashboard/static/index.html</code></p>"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# API — STATE
# ═══════════════════════════════════════════════════════════════════════════════


@app.get("/api/state")
async def api_state():
    if not STATE_PATH.exists():
        return {"version": "2.0", "items": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


@app.get("/api/stages")
async def api_stages():
    if not STAGES_PATH.exists():
        return {"stages": {}}
    return json.loads(STAGES_PATH.read_text(encoding="utf-8"))


@app.get("/api/metrics")
async def api_metrics():
    if not METRICS_SCRIPT.exists():
        return JSONResponse({"error": "metrics.py missing"}, status_code=404)
    try:
        p = subprocess.run(
            [sys.executable, str(METRICS_SCRIPT), "--format", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if p.returncode != 0:
            return JSONResponse({"error": p.stderr}, status_code=500)
        return json.loads(p.stdout)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# API — HF STATUS
# ═══════════════════════════════════════════════════════════════════════════════


@app.get("/api/hf/status")
async def api_hf_status(quick: bool = True):
    """(Backward compat alias) — /api/llm/status'u çağır."""
    return await api_llm_status(quick=quick)


@app.get("/api/llm/status")
async def api_llm_status(quick: bool = True):
    """Aktif LLM provider durumu (Ollama veya HuggingFace)."""
    try:
        from llm import get_provider
        provider = get_provider()
        result: Dict[str, Any] = {"provider": provider}

        if provider == "ollama":
            from llm.ollama_client import OllamaConfig, ping as ollama_ping
            cfg = OllamaConfig.from_env()
            if quick:
                result.update({
                    "host": cfg.host,
                    "default_model": cfg.default_model,
                    "powerful_model": cfg.powerful_model,
                    "fast_model": cfg.fast_model,
                    "coder_model": cfg.coder_model,
                })
                # Lightweight reachability
                try:
                    import requests  # type: ignore
                    r = requests.get(f"{cfg.host}/api/version", timeout=2)
                    result["reachable"] = r.ok
                    result["version"] = r.json().get("version") if r.ok else None
                except Exception:
                    result["reachable"] = False
                return result
            result.update(ollama_ping())
        else:
            from llm.hf_client import HFConfig, ping as hf_ping
            cfg = HFConfig.from_env()
            if quick:
                result.update({
                    "token_set": bool(cfg.token),
                    "default_model": cfg.default_model,
                    "powerful_model": cfg.powerful_model,
                    "fast_model": cfg.fast_model,
                    "coder_model": cfg.coder_model,
                })
                return result
            result.update(hf_ping())
        return result
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# API — LOGS
# ═══════════════════════════════════════════════════════════════════════════════


@app.get("/api/logs")
async def api_logs_list():
    """Tüm log dosyalarını listele."""
    if not LOGS_DIR.exists():
        return []
    return sorted([
        {
            "name": p.name,
            "size": p.stat().st_size,
            "mtime": p.stat().st_mtime,
        }
        for p in LOGS_DIR.glob("*.log")
    ], key=lambda x: -x["mtime"])[:100]


@app.get("/api/logs/{filename}")
async def api_log_content(filename: str, tail: int = 500):
    """Log dosyasının son N satırı."""
    p = LOGS_DIR / filename
    if not p.exists() or ".." in filename:
        raise HTTPException(404)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"lines": lines[-tail:], "total": len(lines)}


@app.get("/api/run/log")
async def api_run_log(tail: int = 200):
    """run.log (pipeline events)"""
    if not RUN_LOG.exists():
        return {"lines": []}
    lines = RUN_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"lines": lines[-tail:], "total": len(lines)}


# ═══════════════════════════════════════════════════════════════════════════════
# API — SSE (live events)
# ═══════════════════════════════════════════════════════════════════════════════


@app.get("/api/events")
async def api_events(request: Request):
    """Server-Sent Events stream — state değişimi + agent events."""

    async def event_gen():
        last_state_mtime: Optional[float] = None
        last_event_max_ts: int = int(time.time() * 1000)

        while True:
            if await request.is_disconnected():
                break

            # 1. state.json değişimi
            try:
                if STATE_PATH.exists():
                    mtime = STATE_PATH.stat().st_mtime
                    if last_state_mtime is None:
                        last_state_mtime = mtime
                    elif mtime > last_state_mtime:
                        last_state_mtime = mtime
                        try:
                            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
                            yield f"event: state\ndata: {json.dumps(state, default=str)}\n\n"
                        except Exception:
                            pass
            except Exception:
                pass

            # 2. Events dir — yeni event'leri yayınla
            try:
                if EVENTS_DIR.exists():
                    new_events = []
                    for p in EVENTS_DIR.glob("*.json"):
                        try:
                            ts_part = int(p.stem.split("-", 1)[0])
                            if ts_part > last_event_max_ts:
                                data = json.loads(p.read_text(encoding="utf-8"))
                                new_events.append((ts_part, data))
                        except Exception:
                            pass
                    new_events.sort(key=lambda x: x[0])
                    for ts_part, data in new_events:
                        yield f"event: agent\ndata: {json.dumps(data, default=str)}\n\n"
                        last_event_max_ts = max(last_event_max_ts, ts_part)
            except Exception:
                pass

            # Heartbeat
            yield f": heartbeat {int(time.time())}\n\n"

            await asyncio.sleep(1.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ═══════════════════════════════════════════════════════════════════════════════
# API — RUN CONTROL
# ═══════════════════════════════════════════════════════════════════════════════


@app.post("/api/run")
async def api_run_start(req: Request):
    """Pipeline'ı başlat. Body: {mode: "once"|"watch", max_concurrent: 3, filter_role: null}"""
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass

    if _running_task.get("process") and _running_task["process"].poll() is None:
        return JSONResponse(
            {"error": "Another pipeline run is already active", "pid": _running_task["pid"]},
            status_code=409,
        )

    mode = body.get("mode", "once")
    max_concurrent = int(body.get("max_concurrent", 3))
    filter_role = body.get("filter_role")
    filter_item = body.get("filter_item")
    max_tokens = int(body.get("max_tokens", 2500))
    idle_exit = body.get("idle_exit_after_s")

    cmd = [sys.executable, "-u", str(RUN_SCRIPT), mode,
           "--max-concurrent", str(max_concurrent),
           "--max-tokens", str(max_tokens)]
    if filter_role:
        cmd += ["--filter-role", filter_role]
    if mode == "once" and filter_item:
        cmd += ["--filter-item", filter_item]
    if mode == "watch" and idle_exit:
        cmd += ["--idle-exit-after", str(idle_exit)]

    log_file = REPO_ROOT / "docs" / "ai" / "pipeline" / "run-stdout.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fp = open(log_file, "w")

    try:
        p = subprocess.Popen(
            cmd,
            stdout=fp, stderr=subprocess.STDOUT,
            cwd=str(REPO_ROOT),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    _running_task.update({
        "process": p,
        "started_at": time.time(),
        "mode": mode,
        "pid": p.pid,
        "log": str(log_file.relative_to(REPO_ROOT)),
    })
    return {
        "ok": True,
        "mode": mode,
        "pid": p.pid,
        "started_at": _running_task["started_at"],
        "log": _running_task["log"],
    }


@app.post("/api/run/stop")
async def api_run_stop():
    p = _running_task.get("process")
    if not p or p.poll() is not None:
        return {"ok": True, "message": "No active run"}
    try:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return {"ok": True, "pid": p.pid, "returncode": p.returncode}


@app.get("/api/run/status")
async def api_run_status():
    p = _running_task.get("process")
    running = bool(p and p.poll() is None)
    return {
        "running": running,
        "pid": _running_task.get("pid") if running else None,
        "mode": _running_task.get("mode") if running else None,
        "started_at": _running_task.get("started_at") if running else None,
        "returncode": p.returncode if p and not running else None,
        "log": _running_task.get("log"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    print(f"🚀 Pipeline Dashboard → http://{args.host}:{args.port}")
    uvicorn.run(
        "scripts.pipeline.dashboard.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
