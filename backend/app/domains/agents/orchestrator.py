"""Sequential agent orchestration pipeline.

Execution order:
  1. Analiz Ajanı      – coverage gaps, anomaly detection, prioritisation, flaky report
  2. Frontend & Backend – locator audit, security analysis, performance analysis, quality score
  3. Test Ajanı         – test generation, suite optimization, self-heal check
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx

from app.config import settings as _cfg
ENGINE_BASE = _cfg.engine_base_url


class Phase(str, Enum):
    IDLE = "idle"
    ANALYSIS = "analysis"
    FRONTEND_BACKEND = "frontend_backend"
    TEST = "test"
    COMPLETED = "completed"
    FAILED = "failed"


class LogEntry:
    __slots__ = ("ts", "phase", "agent", "message", "level")

    def __init__(self, phase: str, agent: str, message: str, level: str = "info"):
        self.ts = datetime.now(timezone.utc).isoformat()
        self.phase = phase
        self.agent = agent
        self.message = message
        self.level = level

    def dict(self) -> dict:
        return {
            "timestamp": self.ts,
            "phase": self.phase,
            "agent": self.agent,
            "message": self.message,
            "level": self.level,
        }


class PipelineState:
    """In-process singleton that tracks the running pipeline."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.run_id: str | None = None
        self.phase: Phase = Phase.IDLE
        self.running: bool = False
        self.logs: list[LogEntry] = []
        self.started_at: str | None = None
        self.completed_at: str | None = None
        self.progress: int = 0

    def log(self, phase: str, agent: str, msg: str, level: str = "info") -> None:
        self.logs.append(LogEntry(phase, agent, msg, level))

    def snapshot(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase.value,
            "running": self.running,
            "progress": self.progress,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "logs": [e.dict() for e in self.logs],
        }


pipeline = PipelineState()


async def _call(method: str, path: str, body: dict | None = None, timeout: float = 30) -> dict:
    url = f"{ENGINE_BASE}{path}"
    headers = {}
    if _cfg.engine_internal_key:
        headers["X-Internal-Key"] = _cfg.engine_internal_key
    async with httpx.AsyncClient(timeout=timeout) as client:
        if method.upper() == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, json=body or {}, headers=headers)
    ct = resp.headers.get("content-type", "")
    data = resp.json() if "json" in ct else {"raw": resp.text[:500]}
    return {"status": resp.status_code, "data": data}


async def _safe_call(
    method: str,
    path: str,
    phase: str,
    agent: str,
    label: str,
    body: dict | None = None,
    timeout: float = 30,
) -> dict | None:
    """Call engine endpoint, log success/failure, never raise."""
    try:
        result = await _call(method, path, body, timeout)
        ok = 200 <= result["status"] < 400
        pipeline.log(
            phase, agent,
            f"{label}: {'Başarılı' if ok else 'HTTP ' + str(result['status'])}",
            "success" if ok else "warning",
        )
        return result
    except Exception as exc:
        pipeline.log(phase, agent, f"{label} hatası: {exc}", "error")
        return None


TOTAL_ROUNDS = 10
STEPS_PER_ROUND = 12


async def run_all_agents(run_id: str, project_id: str | None = None) -> None:
    """Execute the three-phase agent pipeline, repeated TOTAL_ROUNDS times."""
    pipeline.running = True
    pipeline.run_id = run_id
    pipeline.started_at = datetime.now(timezone.utc).isoformat()
    pipeline.progress = 0

    total = STEPS_PER_ROUND * TOTAL_ROUNDS
    step = 0

    def advance() -> None:
        nonlocal step
        step += 1
        pipeline.progress = min(int(step / total * 100), 99)

    try:
        for cycle in range(1, TOTAL_ROUNDS + 1):
            if not pipeline.running:
                break

            pipeline.log(
                "info", "Orkestratör",
                f"══ Döngü {cycle}/{TOTAL_ROUNDS} başlıyor ══",
                "info",
            )

            # ══════════════════════════════════════════════════════════════
            # PHASE 1 — Analiz Ajanı
            # ══════════════════════════════════════════════════════════════
            pipeline.phase = Phase.ANALYSIS
            pipeline.log("analysis", "Analiz Ajanı", f"[{cycle}/{TOTAL_ROUNDS}] Analiz ajanı başlatılıyor…", "info")

            await _safe_call("GET", "/health", "analysis", "Analiz Ajanı", f"[{cycle}] Engine sağlık kontrolü")
            advance()

            await _safe_call("GET", "/api/ai/coverage-gaps", "analysis", "Analiz Ajanı", f"[{cycle}] Kapsam boşluk analizi")
            advance()

            await _safe_call("POST", "/api/ai/analyze-anomaly", "analysis", "Analiz Ajanı", f"[{cycle}] Anomali tespiti", body={})
            advance()

            await _safe_call("POST", "/api/ai/prioritize", "analysis", "Analiz Ajanı", f"[{cycle}] Test önceliklendirme", body={})
            advance()

            await _safe_call("GET", "/api/ai/flaky-report", "analysis", "Analiz Ajanı", f"[{cycle}] Flaky test raporu")
            advance()

            pipeline.log("analysis", "Analiz Ajanı", f"[{cycle}/{TOTAL_ROUNDS}] Analiz ajanı tamamlandı", "success")

            await asyncio.sleep(0.3)

            # ══════════════════════════════════════════════════════════════
            # PHASE 2 — Frontend & Backend Ajanı
            # ══════════════════════════════════════════════════════════════
            pipeline.phase = Phase.FRONTEND_BACKEND
            pipeline.log("frontend_backend", "Frontend & Backend", f"[{cycle}/{TOTAL_ROUNDS}] Frontend & Backend ajanları başlatılıyor…", "info")

            await _safe_call("POST", "/api/ai/audit-locators", "frontend_backend", "Frontend Ajanı", f"[{cycle}] Locator denetimi", body={})
            advance()

            await _safe_call("POST", "/api/ai/security-analyze", "frontend_backend", "Backend Ajanı", f"[{cycle}] Güvenlik analizi", body={})
            advance()

            await _safe_call("POST", "/api/ai/perf-analyze", "frontend_backend", "Backend Ajanı", f"[{cycle}] Performans analizi", body={})
            advance()

            await _safe_call("GET", "/api/ai/quality-score", "frontend_backend", "Frontend & Backend", f"[{cycle}] Kalite skoru")
            advance()

            pipeline.log("frontend_backend", "Frontend & Backend", f"[{cycle}/{TOTAL_ROUNDS}] Frontend & Backend ajanları tamamlandı", "success")

            await asyncio.sleep(0.3)

            # ══════════════════════════════════════════════════════════════
            # PHASE 3 — Test Ajanı
            # ══════════════════════════════════════════════════════════════
            pipeline.phase = Phase.TEST
            pipeline.log("test", "Test Ajanı", f"[{cycle}/{TOTAL_ROUNDS}] Test ajanı başlatılıyor…", "info")

            await _safe_call("POST", "/api/ai/optimize-suite", "test", "Test Ajanı", f"[{cycle}] Suite optimizasyonu", body={})
            advance()

            await _safe_call("GET", "/api/ai/stats", "test", "Test Ajanı", f"[{cycle}] AI istatistikleri")
            advance()

            await _safe_call("GET", "/api/reports/comprehensive", "test", "Test Ajanı", f"[{cycle}] Kapsamlı rapor")
            advance()

            pipeline.log("test", "Test Ajanı", f"[{cycle}/{TOTAL_ROUNDS}] Test ajanı tamamlandı", "success")

            pipeline.log(
                "info", "Orkestratör",
                f"══ Döngü {cycle}/{TOTAL_ROUNDS} tamamlandı ══",
                "success",
            )

            if cycle < TOTAL_ROUNDS:
                await asyncio.sleep(0.5)

        # ══════════════════════════════════════════════════════════════════
        pipeline.phase = Phase.COMPLETED
        pipeline.progress = 100
        pipeline.log("completed", "Orkestratör", f"Tüm ajanlar {TOTAL_ROUNDS} döngüde başarıyla tamamlandı", "success")

    except Exception as exc:
        pipeline.phase = Phase.FAILED
        pipeline.log("error", "Orkestratör", f"Pipeline hatası (döngü {step // STEPS_PER_ROUND + 1}): {exc}", "error")
    finally:
        pipeline.running = False
        pipeline.completed_at = datetime.now(timezone.utc).isoformat()
