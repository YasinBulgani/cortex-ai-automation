"""Background loop for Nexus AI Autopilot."""

from __future__ import annotations

import logging
import threading
import time

from sqlalchemy import select

from app.config import settings
from app.domains.ai.autopilot import NexusAutopilot
from app.domains.tspm.models import TspmProject
from app.infra.database import SessionLocal

logger = logging.getLogger(__name__)
VALID_BACKGROUND_MODES = {"observe", "assist", "autonomous"}

_stop_event = threading.Event()
_thread: threading.Thread | None = None


def _run_once() -> None:
    with SessionLocal() as db:
        projects = list(
            db.scalars(
                select(TspmProject)
                .where(TspmProject.archived == False)  # noqa: E712
                .order_by(TspmProject.last_opened_at.desc().nullslast(), TspmProject.created_at.desc())
                .limit(settings.nexus_autopilot_max_projects_per_tick)
            )
        )

        for project in projects:
            if _stop_event.is_set():
                return
            try:
                mode = settings.nexus_autopilot_background_mode
                if mode not in VALID_BACKGROUND_MODES:
                    mode = "observe"
                NexusAutopilot(db=db, project_id=project.id).run(
                    mode=mode,  # type: ignore[arg-type]
                    apply_safe_actions=settings.nexus_autopilot_apply_safe_actions,
                    trigger="background",
                )
            except Exception as exc:
                logger.warning("Nexus Autopilot project tick failed: project=%s error=%s", project.id, exc)


def _loop() -> None:
    if settings.nexus_autopilot_start_delay_seconds > 0:
        _stop_event.wait(settings.nexus_autopilot_start_delay_seconds)

    while not _stop_event.is_set():
        try:
            _run_once()
        except Exception as exc:
            logger.warning("Nexus Autopilot background tick failed: %s", exc)
        _stop_event.wait(max(settings.nexus_autopilot_interval_seconds, 60))


def start_autopilot_worker() -> None:
    global _thread
    if not settings.nexus_autopilot_enabled:
        logger.info("Nexus Autopilot worker disabled.")
        return
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="nexus-autopilot", daemon=True)
    _thread.start()
    logger.info(
        "Nexus Autopilot worker started: interval=%ss mode=%s safe_actions=%s",
        settings.nexus_autopilot_interval_seconds,
        settings.nexus_autopilot_background_mode,
        settings.nexus_autopilot_apply_safe_actions,
    )


def stop_autopilot_worker() -> None:
    _stop_event.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)
