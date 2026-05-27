"""
Agent Trio – FastAPI Server (SSE + WebSocket real-time updates)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("agent_trio.server")

# ── Uygulama ─────────────────────────────────────────────────────────────

app = FastAPI(title="Agent Trio", docs_url="/docs")

_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:7890"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Global event queue – tüm SSE subscriber'ları buradan okur
_event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

# Orchestrator task
_orchestrator_task: asyncio.Task | None = None
_session_start: float = 0.0
_DURATION_SECONDS = 20 * 60  # 20 dakika

# Log dosyası
_log_dir = Path(__file__).parent / "logs"
_log_dir.mkdir(exist_ok=True)
_session_log = _log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"


def _write_log(event: dict) -> None:
    try:
        with open(_session_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


async def _broadcast(event: dict) -> None:
    event["server_ts"] = datetime.now().isoformat()
    _write_log(event)
    try:
        _event_queue.put_nowait(event)
    except asyncio.QueueFull:
        # Kuyruğu temizle (en eski olayları at)
        try:
            _event_queue.get_nowait()
            _event_queue.put_nowait(event)
        except Exception:
            pass


# ── Orchestrator ─────────────────────────────────────────────────────────

async def run_orchestrator() -> None:
    """Ajan döngüsünü 20 dakika boyunca çalıştır."""
    global _session_start
    from agents import IdeaAgent, DevAgent, TestAgent, _detect_models

    _session_start = time.monotonic()

    await _broadcast({
        "type": "session_start",
        "message": "🚀 Agent Trio oturumu başladı! 20 dakika boyunca çalışacak.",
        "duration_seconds": _DURATION_SECONDS,
    })

    # Model tespiti
    models = await _detect_models()
    await _broadcast({
        "type": "models_detected",
        "models": models,
        "message": f"✅ {len(models)} Ollama modeli tespit edildi: {', '.join(models[:3])}",
    })

    if not models:
        await _broadcast({
            "type": "error",
            "message": "❌ Ollama bulunamadı veya model yok! Lütfen Ollama'yı başlatın ve en az bir model çekin.",
            "hint": "ollama pull mistral:latest",
        })
        return

    idea_agent = IdeaAgent()
    dev_agent = DevAgent()
    test_agent = TestAgent()

    round_num = 0
    results_summary = []

    while (time.monotonic() - _session_start) < _DURATION_SECONDS:
        round_num += 1
        elapsed = time.monotonic() - _session_start
        remaining = _DURATION_SECONDS - elapsed

        await _broadcast({
            "type": "round_start",
            "round": round_num,
            "elapsed_seconds": int(elapsed),
            "remaining_seconds": int(remaining),
            "message": f"🔄 Round {round_num} başlıyor! (Kalan: {int(remaining//60)}dk {int(remaining%60)}sn)",
        })

        try:
            # ── Aşama 1: Fikir Üretimi ─────────────────────────────────
            await _broadcast({"type": "phase_start", "phase": "idea", "round": round_num})
            idea = await idea_agent.generate(round_num, _event_queue)

            # ── Aşama 2: Geliştirme ────────────────────────────────────
            await _broadcast({"type": "phase_start", "phase": "develop", "round": round_num})
            impl = await dev_agent.implement(idea, round_num, _event_queue)

            # ── Aşama 3: Test ──────────────────────────────────────────
            await _broadcast({"type": "phase_start", "phase": "test", "round": round_num})
            report = await test_agent.test(impl, round_num, _event_queue)

            # Özet
            summary = {
                "round": round_num,
                "idea_title": idea.title,
                "module": idea.module,
                "complexity": idea.complexity,
                "verdict": report.verdict,
                "bugs": len(report.bugs_found),
                "coverage": report.coverage_estimate,
            }
            results_summary.append(summary)

            await _broadcast({
                "type": "round_complete",
                "round": round_num,
                "summary": summary,
                "message": f"✅ Round {round_num} tamamlandı! Fikir: {idea.title} | Verdict: {report.verdict.upper()}",
            })

            # Sonuç dosyasına kaydet
            _save_round_result(round_num, idea, impl, report)

            # Kısa bekleme
            await asyncio.sleep(3)

        except Exception as exc:
            logger.exception(f"Round {round_num} hata: {exc}")
            await _broadcast({
                "type": "round_error",
                "round": round_num,
                "error": str(exc),
                "message": f"⚠️ Round {round_num} hata: {exc}",
            })
            await asyncio.sleep(10)  # Hata sonrası bekle

    # Oturum sonu
    await _broadcast({
        "type": "session_end",
        "total_rounds": round_num,
        "results": results_summary,
        "message": f"🏁 20 dakika tamamlandı! Toplam {round_num} round çalıştı.",
    })


def _save_round_result(round_num, idea, impl, report) -> None:
    """Her round'un sonuçlarını dosyaya kaydet."""
    out_dir = _log_dir / f"round_{round_num:03d}_{idea.module}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Fikir
    with open(out_dir / "idea.md", "w", encoding="utf-8") as f:
        f.write(f"# {idea.title}\n\n")
        f.write(f"**Modül:** {idea.module}\n")
        f.write(f"**Karmaşıklık:** {idea.complexity}\n")
        f.write(f"**Etiketler:** {', '.join(idea.tags)}\n\n")
        f.write(f"## Açıklama\n{idea.description}\n")

    # Kod
    ext = "py" if impl.language == "python" else "ts"
    with open(out_dir / f"implementation.{ext}", "w", encoding="utf-8") as f:
        f.write(f"# {impl.file_path}\n\n")
        f.write(impl.code)

    # Test raporu
    with open(out_dir / "test_report.md", "w", encoding="utf-8") as f:
        f.write(f"# Test Raporu – Round {round_num}\n\n")
        f.write(f"**Verdict:** {report.verdict.upper()}\n")
        f.write(f"**Coverage Tahmini:** %{report.coverage_estimate}\n\n")
        if report.bugs_found:
            f.write("## 🐛 Bulunan Hatalar\n")
            for bug in report.bugs_found:
                f.write(f"- {bug}\n")
            f.write("\n")
        if report.improvements:
            f.write("## 💡 İyileştirme Önerileri\n")
            for imp in report.improvements:
                f.write(f"- {imp}\n")
            f.write("\n")
        if report.test_code:
            f.write("## 🧪 Test Kodu\n```python\n")
            f.write(report.test_code)
            f.write("\n```\n")


# ── SSE Endpoint ──────────────────────────────────────────────────────────

@app.get("/events")
async def sse_endpoint():
    """Server-Sent Events – real-time ajan güncellemeleri."""

    async def event_generator() -> AsyncIterator[str]:
        # Bağlantı bildirimi
        yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE bağlantısı kuruldu'})}\n\n"

        # Durum gönder
        elapsed = time.monotonic() - _session_start if _session_start else 0
        yield f"data: {json.dumps({'type': 'status', 'running': _orchestrator_task is not None and not _orchestrator_task.done(), 'elapsed': int(elapsed)})}\n\n"

        while True:
            try:
                event = await asyncio.wait_for(_event_queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat', 'ts': datetime.now().isoformat()})}\n\n"
            except Exception as e:
                logger.warning(f"SSE hata: {e}")
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/status")
async def status():
    running = _orchestrator_task is not None and not _orchestrator_task.done()
    elapsed = time.monotonic() - _session_start if _session_start else 0
    return {
        "running": running,
        "elapsed_seconds": int(elapsed),
        "remaining_seconds": max(0, _DURATION_SECONDS - int(elapsed)),
        "log_file": str(_session_log),
    }


@app.post("/start")
async def start_session():
    global _orchestrator_task
    if _orchestrator_task and not _orchestrator_task.done():
        return {"status": "already_running"}
    _orchestrator_task = asyncio.create_task(run_orchestrator())
    return {"status": "started"}


@app.get("/logs")
async def list_logs():
    logs = sorted(_log_dir.glob("round_*"), key=lambda p: p.name)
    return {"rounds": [d.name for d in logs if d.is_dir()]}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_file = Path(__file__).parent / "dashboard.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>dashboard.html bulunamadı</h1>")


# ── Başlat ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=7890,
        reload=False,
        log_level="info",
    )
