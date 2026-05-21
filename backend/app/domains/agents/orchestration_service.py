"""Service helpers for agent orchestration endpoints."""

from __future__ import annotations

import uuid

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.domains.agents.banking_orchestrator import banking_pipeline, run_banking_team
from app.domains.agents.orchestrator import Phase, pipeline, run_all_agents


def start_all_agents_run(bg: BackgroundTasks, project_id: str | None = None) -> dict:
    """Start the lightweight multi-agent orchestrator."""
    if pipeline.running:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Bir pipeline zaten çalışıyor. Bitmesini bekleyin.",
        )
    pipeline.reset()
    run_id = uuid.uuid4().hex[:12]
    bg.add_task(run_all_agents, run_id, project_id)
    return {"run_id": run_id, "message": "Pipeline başlatıldı"}


def get_all_agents_status() -> dict:
    return pipeline.snapshot()


def get_all_agents_logs(since: int = 0) -> dict:
    logs = pipeline.logs[since:]
    return {
        "run_id": pipeline.run_id,
        "phase": pipeline.phase.value,
        "running": pipeline.running,
        "progress": pipeline.progress,
        "logs": [entry.dict() for entry in logs],
        "total": len(pipeline.logs),
    }


def cancel_all_agents_run() -> dict:
    if not pipeline.running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Çalışan pipeline yok")
    pipeline.phase = Phase.FAILED
    pipeline.running = False
    pipeline.log("cancelled", "Orkestratör", "Pipeline kullanıcı tarafından iptal edildi", "warning")
    return {"message": "İptal edildi"}


def start_banking_team_run(
    bg: BackgroundTasks,
    *,
    input_data: dict,
    total_cycles: int,
) -> dict:
    """Start the banking QA team pipeline."""
    if banking_pipeline.running:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Banking pipeline zaten çalışıyor.",
        )
    banking_pipeline.reset()
    run_id = uuid.uuid4().hex[:12]
    bg.add_task(run_banking_team, run_id, input_data, total_cycles)
    return {
        "run_id": run_id,
        "message": f"Banking QA ekibi başlatıldı. {total_cycles} döngü çalışacak.",
        "total_cycles": total_cycles,
    }


def get_banking_pipeline_status() -> dict:
    return banking_pipeline.snapshot()


def get_banking_pipeline_logs(since: int = 0) -> dict:
    logs = banking_pipeline.logs[since:]
    return {
        "run_id": banking_pipeline.run_id,
        "phase": banking_pipeline.phase.value,
        "running": banking_pipeline.running,
        "current_cycle": banking_pipeline.current_cycle,
        "total_cycles": banking_pipeline.total_cycles,
        "progress": banking_pipeline.progress,
        "logs": [entry.dict() for entry in logs],
        "total_log_count": len(banking_pipeline.logs),
    }


def get_banking_pipeline_report() -> dict:
    if banking_pipeline.running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Pipeline hâlâ çalışıyor.")
    if not banking_pipeline.final_report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Henüz tamamlanmış rapor yok.")
    return banking_pipeline.final_report


def cancel_banking_team_run() -> dict:
    if not banking_pipeline.running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Çalışan pipeline yok.")

    from app.domains.agents.banking_orchestrator import BankingPhase

    banking_pipeline.set_phase(BankingPhase.FAILED)
    banking_pipeline.running = False
    banking_pipeline.log("orchestrator", "Orkestratör", "Pipeline iptal edildi.", "warning")
    return {"message": "İptal edildi."}


def trigger_banking_team_now(bg: BackgroundTasks, cycles: int = 2) -> dict:
    """Start the banking QA team with auto-discovered input."""
    if banking_pipeline.running:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Zaten çalışıyor.")

    from app.domains.agents.banking_team.project_scanner import ProjectScannerAgent

    banking_pipeline.reset()
    run_id = f"auto-{uuid.uuid4().hex[:8]}"
    scanner = ProjectScannerAgent()
    scan = scanner.safe_run({})
    input_data = scan.data if scan.success else {}

    bg.add_task(run_banking_team, run_id, input_data, cycles)
    return {
        "run_id": run_id,
        "message": "Ekip sıfır müdahale ile başlatıldı.",
        "scanned": {
            "regulations": input_data.get("regulations", []),
            "description": input_data.get("description", ""),
            "api_count": len(input_data.get("api_docs", "").splitlines()),
        },
    }


def get_banking_scheduler_info() -> dict:
    from app.domains.agents.banking_team.scheduler_agent import get_next_run_time

    return {
        "next_run": get_next_run_time(),
        "schedule": "Her gece 02:00 (Europe/Istanbul)",
        "job_id": "banking_qa_team_nightly",
    }


def get_banking_system_health() -> dict:
    import requests as _req

    health: dict = {
        "backend": "ok",
        "ollama": "unknown",
        "models": [],
        "pipeline": {
            "running": banking_pipeline.running,
            "phase": banking_pipeline.phase.value,
            "last_run": banking_pipeline.completed_at,
        },
        "scheduler": None,
    }

    try:
        from app.config import settings as _settings

        ollama_host = _settings.ollama_base_url.replace("/v1", "").replace("localhost", "host.docker.internal")
        response = _req.get(f"{ollama_host}/api/tags", timeout=3)
        if response.status_code == 200:
            health["ollama"] = "ok"
            health["models"] = [item["name"] for item in response.json().get("models", [])]
        else:
            health["ollama"] = "error"
    except Exception:
        health["ollama"] = "unreachable"

    try:
        from app.domains.agents.banking_team.scheduler_agent import get_next_run_time

        health["scheduler"] = get_next_run_time()
    except Exception:
        pass

    try:
        from app.domains.agents.banking_team.circuit_breaker import ollama_breaker

        health["circuit_breaker"] = {
            "state": ollama_breaker.state,
            "failures": ollama_breaker.failure_count,
        }
    except Exception:
        pass

    health["status"] = "healthy" if health["backend"] == "ok" and health["ollama"] == "ok" else "degraded"
    return health


def start_full_pipeline_run(
    bg: BackgroundTasks,
    db: Session,
    *,
    project_name: str,
    target_url: str | None = None,
    description: str = "",
    cycles: int = 2,
    regulations: list[str] | None = None,
    generate_bdd: bool = True,
    generate_playwright: bool = True,
    generate_api_tests: bool = True,
    run_tests: bool = True,
    auto_heal: bool = True,
    crawl_max_pages: int = 10,
    max_quality_retries: int = 2,
) -> dict:
    """Start the end-to-end pipeline service."""
    from app.domains.agents.pipeline_service import (
        PipelineConfig,
        PipelineService,
        get_active_pipeline,
        set_active_pipeline,
    )

    active = get_active_pipeline()
    if active and active.state.running:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Bir pipeline zaten çalışıyor. Bitmesini bekleyin veya iptal edin.",
        )

    config = PipelineConfig(
        project_name=project_name,
        target_url=target_url,
        description=description,
        cycles=cycles,
        regulations=regulations or ["BDDK", "KVKK"],
        generate_bdd=generate_bdd,
        generate_playwright=generate_playwright,
        generate_api_tests=generate_api_tests,
        run_tests=run_tests,
        auto_heal=auto_heal,
        crawl_max_pages=crawl_max_pages,
        max_quality_retries=max_quality_retries,
    )
    service = PipelineService(db)
    set_active_pipeline(service)

    async def _run():
        try:
            await service.run(config)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception("Pipeline çalışma hatası: %s", exc)

    bg.add_task(_run)
    return {
        "run_id": service.state.run_id,
        "project_name": project_name,
        "message": f"Pipeline başlatıldı — {cycles} döngü, hedef: {target_url or 'kod tabanı'}",
        "total_cycles": cycles,
    }


def get_full_pipeline_status() -> dict:
    from app.domains.agents.pipeline_service import get_active_pipeline

    active = get_active_pipeline()
    if not active:
        return {"running": False, "phase": "idle", "message": "Aktif pipeline yok"}
    return active.snapshot()


def get_full_pipeline_logs(since: int = 0) -> dict:
    from app.domains.agents.pipeline_service import get_active_pipeline

    active = get_active_pipeline()
    if not active:
        return {"logs": [], "total": 0, "running": False}

    state = active.state
    logs = state.logs[since:]
    return {
        "run_id": state.run_id,
        "phase": state.phase.value,
        "running": state.running,
        "progress": state.progress,
        "current_cycle": state.current_cycle,
        "total_cycles": state.total_cycles,
        "logs": [
            {"ts": log.ts, "phase": log.phase, "level": log.level, "message": log.message}
            for log in logs
        ],
        "total": len(state.logs),
    }


def get_full_pipeline_report() -> dict:
    from app.domains.agents.pipeline_service import PipelinePhase, get_active_pipeline

    active = get_active_pipeline()
    if not active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aktif pipeline yok")

    state = active.state
    if state.running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Pipeline hâlâ çalışıyor")

    if state.phase == PipelinePhase.FAILED:
        return {
            "success": False,
            "error": state.error,
            "run_id": state.run_id,
            "phase": state.phase.value,
        }

    return {
        "success": state.phase == PipelinePhase.COMPLETED,
        "run_id": state.run_id,
        "project_id": state.project_id,
        "duration_seconds": round(state.finished_at - state.started_at, 1) if state.finished_at else 0,
        "summary": {
            "scenarios_generated": len(state.scenarios),
            "scenarios_saved": len(state.tspm_scenario_ids),
            "quality_score": round(state.quality_score, 1),
            "tests_passed": state.test_results.get("total_passed", 0),
            "tests_failed": state.test_results.get("total_failed", 0),
            "tests_healed": state.healing_results.get("healed", 0),
        },
        "scenarios": state.scenarios,
        "test_results": state.test_results,
        "learning": state.learning,
        "tspm": {
            "project_id": state.project_id,
            "scenario_ids": state.tspm_scenario_ids,
            "execution_id": state.tspm_execution_id,
        },
    }


def cancel_full_pipeline_run() -> dict:
    from app.domains.agents.pipeline_service import get_active_pipeline

    active = get_active_pipeline()
    if not active or not active.state.running:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Çalışan pipeline yok")

    active.cancel()
    return {"message": "Pipeline iptal istendi", "run_id": active.state.run_id}


def quick_start_full_pipeline(
    bg: BackgroundTasks,
    db: Session,
    *,
    project_name: str = "Otomatik Keşif",
    target_url: str | None = None,
) -> dict:
    """Start the full pipeline with minimal configuration."""
    return start_full_pipeline_run(
        bg,
        db,
        project_name=project_name,
        target_url=target_url,
        cycles=2,
    )
