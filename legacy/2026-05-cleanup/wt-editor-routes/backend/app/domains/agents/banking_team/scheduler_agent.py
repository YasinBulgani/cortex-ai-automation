"""
SchedulerAgent — Ekibi Periyodik Olarak Otomatik Tetikler

Görevi:
  Backend başladığında APScheduler ile kayıt olur.
  Varsayılan: Her gece 02:00'da pipeline'ı otomatik başlatır.
  Ayrıca git push hook veya manuel tetikleme de desteklenir.

  Çalışma döngüsü:
    1. ProjectScannerAgent → projeyi tara
    2. Banking pipeline → analiz, senaryo, regülasyon, otomasyon, kod
    3. OutputWriterAgent → diske yaz
    4. TestRunnerAgent → çalıştır
    5. SelfImproving → öğren
    6. Uyu → tekrar başa dön
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# APScheduler job ID
BANKING_JOB_ID = "banking_qa_team_nightly"


def start_scheduler(app=None) -> None:
    """
    APScheduler'a banking pipeline job'ını kaydet.
    FastAPI lifespan'inden çağrılır.
    """
    global _banking_scheduler
    if _banking_scheduler is not None and getattr(_banking_scheduler, "running", False):
        logger.info("Banking QA scheduler zaten calisiyor, tekrar baslatma atlandi.")
        return

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        if _banking_scheduler is not None:
            try:
                _banking_scheduler.remove_all_jobs()
                _banking_scheduler.shutdown(wait=False)
            except Exception:
                logger.debug("Eski banking scheduler temizlenirken hata alindi.", exc_info=True)

        scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

        # Her gece 02:00'da çalış
        scheduler.add_job(
            _scheduled_run,
            trigger=CronTrigger(hour=2, minute=0),
            id=BANKING_JOB_ID,
            name="Banking QA Ekibi — Nightly",
            replace_existing=True,
            misfire_grace_time=3600,  # 1 saat geç çalışmaya izin ver
        )

        scheduler.start()
        logger.info("Banking QA scheduler başlatıldı (her gece 02:00)")

        _banking_scheduler = scheduler

    except Exception as e:
        logger.warning("Scheduler başlatılamadı: %s", e)


_banking_scheduler = None


async def _scheduled_run() -> None:
    """APScheduler tarafından çağrılan otomatik pipeline çalıştırıcı."""
    from app.domains.agents.banking_orchestrator import banking_pipeline, run_banking_team

    if banking_pipeline.running:
        logger.info("Banking pipeline zaten çalışıyor, scheduled run atlandı.")
        return

    run_id = f"nightly-{uuid.uuid4().hex[:8]}"
    logger.info("Scheduled banking run başlıyor: %s", run_id)

    banking_pipeline.reset()

    # ProjectScanner ile otomatik input topla
    input_data = _auto_collect_input()

    await run_banking_team(run_id, input_data, total_cycles=2)
    logger.info("Scheduled banking run tamamlandı: %s", run_id)


def _auto_collect_input() -> dict:
    """ProjectScannerAgent'ı kullanarak otomatik input topla."""
    try:
        from app.domains.agents.banking_team.project_scanner import ProjectScannerAgent
        scanner = ProjectScannerAgent()
        result = scanner.safe_run({})
        if result.success:
            return result.data
    except Exception as e:
        logger.warning("Auto input toplama hatası: %s", e)

    # Fallback: minimal input
    return {
        "description": "TestwrightAI bankacılık test platformu",
        "regulations": ["BDDK", "PCI-DSS", "MASAK", "KYC", "KVKK"],
    }


def trigger_now(cycles: int = 2) -> str:
    """
    Manuel tetikleme — API endpoint'ten çağrılır.
    Pipeline'ı hemen başlatır, run_id döndürür.
    """
    import asyncio
    from app.domains.agents.banking_orchestrator import banking_pipeline, run_banking_team

    if banking_pipeline.running:
        return banking_pipeline.run_id or "already_running"

    run_id = f"manual-{uuid.uuid4().hex[:8]}"
    banking_pipeline.reset()
    input_data = _auto_collect_input()

    # Thread-safe async task oluşturma — APScheduler ve uvicorn uyumlu
    try:
        loop = asyncio.get_running_loop()
        # Zaten bir event loop çalışıyor (uvicorn içinden)
        loop.create_task(run_banking_team(run_id, input_data, total_cycles=cycles))
    except RuntimeError:
        # Çalışan loop yok — yeni thread'de event loop oluştur
        import threading

        def _run_in_thread():
            asyncio.run(run_banking_team(run_id, input_data, total_cycles=cycles))

        threading.Thread(target=_run_in_thread, daemon=True, name=f"trigger-{run_id}").start()

    return run_id


def get_next_run_time() -> str | None:
    """Bir sonraki scheduled run zamanını döndür."""
    try:
        scheduler = _banking_scheduler
        if scheduler:
            job = scheduler.get_job(BANKING_JOB_ID)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
    except Exception:
        pass
    return None


def stop_banking_scheduler() -> None:
    """Banking scheduler'i güvenli şekilde durdur."""
    global _banking_scheduler

    scheduler = _banking_scheduler
    if scheduler is None:
        return

    try:
        if getattr(scheduler, "running", False):
            scheduler.shutdown(wait=False)
            logger.info("Banking scheduler durduruldu.")
    except Exception as exc:
        logger.debug("Banking scheduler shutdown hatasi: %s", exc, exc_info=True)
    finally:
        _banking_scheduler = None
