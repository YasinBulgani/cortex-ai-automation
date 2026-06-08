"""Mobile Automation API router.

Uç noktalar:
    GET    /api/v1/mobile/devices                       → cihaz listesi
    GET    /api/v1/mobile/devices/{id}
    POST   /api/v1/mobile/devices/{id}/reboot
    POST   /api/v1/mobile/enroll-physical               → fiziksel cihaz kayıt
    GET    /api/v1/mobile/stats                         → farm istatistikleri
    POST   /api/v1/mobile/generate-from-prompt          → NL → Appium adımları
    POST   /api/v1/mobile/sessions                      → paralel koşu başlat
    GET    /api/v1/mobile/sessions                      → son koşular
    GET    /api/v1/mobile/sessions/{id}
    GET    /api/v1/mobile/sessions/{id}/stream          → SSE canlı stream
    POST   /api/v1/mobile/visual-verify                 → görsel doğrulama
"""
from __future__ import annotations
from typing import Annotated

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.deps import get_current_user
from app.infra.models import User
from .artifact_store import get_artifact_store
from .device_broker import get_broker
from .llm_stepper import generate_steps
from .orchestrator import get_store, start_suite, stream_events
from .schemas import (
    Device,
    FarmStats,
    MobileArtifact,
    PhysicalEnrollRequest,
    Session,
    SessionCreate,
    StepGenerationRequest,
    StepGenerationResponse,
    VisualVerifyRequest,
    VisualVerifyResponse,
)
from .seed_scenarios import (
    SeedCategory,
    SeedDifficulty,
    SeedScenario,
    get_seed_scenario,
    list_seed_scenarios,
    seed_categories,
)
from .visual_verifier import verify as visual_verify

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["mobile"])


# ── Devices ────────────────────────────────────────────────────
@router.get("/devices", response_model=list[Device])
def list_devices(_user: Annotated[User, Depends(get_current_user)]) -> list[Device]:
    return get_broker().list()


@router.get("/devices/{device_id}", response_model=Device)
def get_device(device_id: str, _user: Annotated[User, Depends(get_current_user)]) -> Device:
    dev = get_broker().get(device_id)
    if not dev:
        raise HTTPException(404, "Cihaz bulunamadı")
    return dev


@router.post("/devices/probe", response_model=list[Device])
def probe_devices(_user: Annotated[User, Depends(get_current_user)]) -> list[Device]:
    """Appium /status probe — cihaz kartlarındaki ready bilgisini gerçek kaynaktan günceller."""
    return get_broker().probe_all_appium()


@router.post("/devices/{device_id}/reboot", response_model=Device)
def reboot_device(device_id: str, user: Annotated[User, Depends(get_current_user)]) -> Device:
    dev = get_broker().reboot(device_id)
    if not dev:
        raise HTTPException(404, "Cihaz bulunamadı")
    return dev


@router.post("/enroll-physical", response_model=Device)
def enroll_physical(req: PhysicalEnrollRequest, user: Annotated[User, Depends(get_current_user)]) -> Device:
    return get_broker().enroll_physical(req)


@router.get("/stats", response_model=FarmStats)
def farm_stats(_user: Annotated[User, Depends(get_current_user)]) -> FarmStats:
    return FarmStats(**get_broker().stats())


# ── LLM Stepper ────────────────────────────────────────────────
@router.post("/generate-from-prompt", response_model=StepGenerationResponse)
def generate_from_prompt(req: StepGenerationRequest, user: Annotated[User, Depends(get_current_user)]) -> StepGenerationResponse:
    return generate_steps(
        prompt=req.prompt,
        platform=req.platform,
        page_source=req.page_source,
        app_package=req.app_package,
    )


# ── Sessions ───────────────────────────────────────────────────
@router.post("/sessions", response_model=list[Session])
async def create_session(req: SessionCreate, user: Annotated[User, Depends(get_current_user)]) -> list[Session]:
    sessions = await start_suite(req)
    if not sessions:
        raise HTTPException(409, "Uygun cihaz yok (hepsi busy veya offline)")
    return sessions


@router.get("/sessions", response_model=list[Session])
def list_sessions(_user: Annotated[User, Depends(get_current_user)], limit: int = 40) -> list[Session]:
    return get_store().list_recent(limit=limit)


@router.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str, _user: Annotated[User, Depends(get_current_user)]) -> Session:
    s = get_store().get(session_id)
    if not s:
        raise HTTPException(404, "Session bulunamadı")
    return s


@router.get("/sessions/{session_id}/stream")
async def session_stream(session_id: str, _user: Annotated[User, Depends(get_current_user)]) -> StreamingResponse:
    """SSE stream — session bitene kadar canlı event'ler.

    Frontend: `new EventSource('/api/v1/mobile/sessions/{id}/stream')`
    """
    s = get_store().get(session_id)
    if not s:
        raise HTTPException(404, "Session bulunamadı")

    async def event_gen() -> AsyncIterator[bytes]:
        try:
            async for event in stream_events(session_id):
                data = json.dumps(event.model_dump(), default=str)
                yield f"event: {event.type}\ndata: {data}\n\n".encode("utf-8")
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/artifacts", response_model=list[MobileArtifact])
def list_session_artifacts(session_id: str, _user: Annotated[User, Depends(get_current_user)]) -> list[MobileArtifact]:
    s = get_store().get(session_id)
    if not s:
        raise HTTPException(404, "Session bulunamadı")
    return get_artifact_store().list_for_session(session_id)


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, _user: Annotated[User, Depends(get_current_user)]) -> FileResponse:
    artifact = get_artifact_store().get(artifact_id)
    if not artifact:
        raise HTTPException(404, "Artifact bulunamadı")
    path = Path(artifact.path)
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Artifact dosyası bulunamadı")
    return FileResponse(
        path,
        media_type=artifact.mime_type,
        filename=path.name,
    )


# ── Visual Verifier ────────────────────────────────────────────
@router.post("/visual-verify", response_model=VisualVerifyResponse)
def visual_verification(req: VisualVerifyRequest, user: Annotated[User, Depends(get_current_user)]) -> VisualVerifyResponse:
    return visual_verify(req)


# ── Seed Scenarios ─────────────────────────────────────────────
@router.get("/scenarios/seed", response_model=list[SeedScenario])
def list_seeds(
    _user: Annotated[User, Depends(get_current_user)],
    category: SeedCategory | None = None,
    platform: str | None = None,
    difficulty: SeedDifficulty | None = None,
) -> list[SeedScenario]:
    """Hazır mobil senaryo galerisi — UI seçicisi için."""
    return list_seed_scenarios(category=category, platform=platform, difficulty=difficulty)


@router.get("/scenarios/seed/categories", response_model=list[str])
def list_seed_categories(_user: Annotated[User, Depends(get_current_user)]) -> list[str]:
    return list(seed_categories())


@router.get("/scenarios/seed/{scenario_id}", response_model=SeedScenario)
def get_seed(scenario_id: str, _user: Annotated[User, Depends(get_current_user)]) -> SeedScenario:
    s = get_seed_scenario(scenario_id)
    if not s:
        raise HTTPException(404, "Seed senaryo bulunamadı")
    return s


# ── Device Farm (external cloud providers) ─────────────────────────────────────

@router.get("/farm/devices", summary="List devices from active farm provider")
def list_farm_devices(
    _user: Annotated[User, Depends(get_current_user)],
    platform: str | None = None,
    os_version: str | None = None,
) -> list[dict]:
    """Return available devices from the configured external device farm.

    Provider is determined by the DEVICE_FARM_PROVIDER env var:
    ``local`` (default), ``aws``, ``browserstack``, or ``saucelabs``.
    """
    from dataclasses import asdict

    from .device_farm_adapters import get_device_farm

    farm = get_device_farm()
    devices = farm.list_devices(platform=platform, os_version=os_version)
    return [asdict(d) for d in devices]


@router.post("/farm/sessions", summary="Start a farm session on an external device")
def start_farm_session(
    device_id: str,
    app_path: str,
    _user: Annotated[User, Depends(get_current_user)],
    capabilities: dict = {},
) -> dict:
    """Start a test session on the specified device via the active farm provider.

    Returns session details including the Appium endpoint URL (if applicable).
    """
    from dataclasses import asdict

    from .device_farm_adapters import (
        AppPathValidationError,
        get_device_farm,
        validate_app_path,
    )

    # SSRF guard: reject file://, internal hosts and private IPs before any
    # server-side fetch of the app_path (see AWSDeviceFarmAdapter.start_session).
    try:
        validate_app_path(app_path)
    except AppPathValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid app_path: {exc}") from exc

    farm = get_device_farm()
    session = farm.start_session(device_id, app_path, capabilities)
    return asdict(session)


@router.get("/farm/sessions/{session_id}", summary="Get farm session status")
def get_farm_session(session_id: str, _user: Annotated[User, Depends(get_current_user)]) -> dict:
    from dataclasses import asdict

    from .device_farm_adapters import get_device_farm

    farm = get_device_farm()
    session = farm.get_session(session_id)
    return asdict(session)


@router.delete("/farm/sessions/{session_id}", summary="Stop a farm session")
def stop_farm_session(session_id: str, _user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
    from .device_farm_adapters import get_device_farm

    farm = get_device_farm()
    farm.stop_session(session_id)
    return {"status": "stopped", "session_id": session_id}


@router.get("/farm/health", summary="External device farm provider health")
def farm_health(_user: Annotated[User, Depends(get_current_user)]) -> dict:
    from .device_farm_adapters import get_device_farm

    return get_device_farm().health()
