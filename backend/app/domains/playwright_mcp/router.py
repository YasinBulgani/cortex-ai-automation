"""Playwright MCP — FastAPI router for browser automation endpoints."""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user
from app.infra.models import User

from .schemas import (
    ActionRequest,
    ActionResponse,
    BrowserSessionCreate,
    BrowserSessionInfo,
    DOMSnapshotRequest,
    DOMSnapshotResponse,
    HealVerifyRequest,
    HealVerifyResponse,
    NavigateRequest,
    NavigateResponse,
    ScreenshotRequest,
    ScreenshotResponse,
    SelectorSuggestRequest,
    SelectorSuggestResponse,
    SelectorValidateRequest,
    SelectorValidateResponse,
)

logger = logging.getLogger(__name__)

# ── Graceful Playwright import ───────────────────────────────────────────────
try:
    from .browser_manager import (
        BrowserManager,
        PlaywrightNotInstalledError,
        _PW_AVAILABLE,
    )

    _manager: Optional[BrowserManager] = None
    PLAYWRIGHT_AVAILABLE = _PW_AVAILABLE
except ImportError:
    _manager = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False
    logger.info(
        "Playwright paketi bulunamadi. /playwright-mcp endpoint'leri devre disi."
    )

router = APIRouter(prefix="/playwright-mcp", tags=["playwright-mcp"])

CurrentUser = Annotated[User, Depends(get_current_user)]


def _is_admin_user(user: User) -> bool:
    for role in user.roles:
        for role_permission in role.permissions:
            if role_permission.permission == "admin.*":
                return True
    return False


def _require_playwright() -> None:
    """Raise 503 if Playwright is not installed."""
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Playwright servisi kulanilamiyor. "
                "Kurmak için: pip install playwright && python -m playwright install chromium"
            ),
        )


def _get_manager() -> BrowserManager:
    _require_playwright()
    global _manager
    if _manager is None:
        _manager = BrowserManager()
    return _manager


async def _ensure_session_access(session_id: str, user: User) -> dict:
    info = await _get_manager().get_session(session_id)
    if _is_admin_user(user):
        return info
    if info.get("owner_user_id") != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu browser oturumuna erisim yetkiniz yok",
        )
    return info


# ── Session Management ───────────────────────────────────────────────────────


@router.post("/sessions", response_model=BrowserSessionInfo, status_code=201)
async def create_session(body: BrowserSessionCreate, user: CurrentUser):
    """Yeni browser oturumu oluştur."""
    _require_playwright()
    try:
        info = await manager.create_session(
            owner_user_id=str(user.id),
            headless=body.headless,
            viewport_width=body.viewport_width,
            viewport_height=body.viewport_height,
            locale=body.locale,
            timezone=body.timezone,
        )
        return BrowserSessionInfo(**info)
    except PlaywrightNotInstalledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Playwright session creation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Playwright session acilamadi: {str(exc)[:200]}",
        ) from exc


@router.get("/sessions", response_model=list[BrowserSessionInfo])
async def list_sessions(user: CurrentUser):
    """Aktif browser oturumlarini listele."""
    owner_user_id = None if _is_admin_user(user) else str(user.id)
    sessions = await _get_manager().list_sessions(owner_user_id=owner_user_id)
    return [BrowserSessionInfo(**s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=BrowserSessionInfo)
async def get_session(session_id: str, user: CurrentUser):
    """Belirli bir oturumun bilgilerini getir."""
    try:
        info = await _ensure_session_access(session_id, user)
        return BrowserSessionInfo(**info)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete("/sessions/{session_id}", status_code=204)
async def close_session(session_id: str, user: CurrentUser):
    """Browser oturumunu kapat."""
    try:
        await _ensure_session_access(session_id, user)
        await _get_manager().close_session(session_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Navigation ───────────────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/navigate", response_model=NavigateResponse
)
async def navigate(
    session_id: str, body: NavigateRequest, user: CurrentUser
):
    """Belirtilen URL'ye git."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().navigate(
            session_id,
            body.url,
            wait_until=body.wait_until,
            timeout_ms=body.timeout_ms,
        )
        return NavigateResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Playwright navigate failed for session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Navigasyon hatasi: {str(exc)[:300]}",
        ) from exc


# ── Screenshot ───────────────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/screenshot", response_model=ScreenshotResponse
)
async def take_screenshot(
    session_id: str, body: ScreenshotRequest, user: CurrentUser
):
    """Ekran goruntusu al."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().screenshot(
            session_id,
            selector=body.selector,
            full_page=body.full_page,
            fmt=body.format,
            quality=body.quality,
        )
        return ScreenshotResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# ── DOM Snapshot ─────────────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/dom", response_model=DOMSnapshotResponse
)
async def get_dom_snapshot(
    session_id: str, body: DOMSnapshotRequest, user: CurrentUser
):
    """DOM agacinin snapshot'ini al."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().get_dom_snapshot(
            session_id,
            selector=body.selector,
            max_depth=body.max_depth,
            include_styles=body.include_styles,
            include_hidden=body.include_hidden,
        )
        return DOMSnapshotResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Selector Validation ─────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/selectors/validate",
    response_model=SelectorValidateResponse,
)
async def validate_selectors(
    session_id: str, body: SelectorValidateRequest, user: CurrentUser
):
    """Selector'lari dogrula ve stabilite skoru ver."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().validate_selectors(
            session_id, body.selectors, timeout_ms=body.timeout_ms
        )
        return SelectorValidateResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Selector Suggestion (AI-powered) ────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/selectors/suggest",
    response_model=SelectorSuggestResponse,
)
async def suggest_selectors(
    session_id: str, body: SelectorSuggestRequest, user: CurrentUser
):
    """AI destekli selector onerisi. DOM'u analiz ederek hedef elemente uygun selector'lar olusturur."""
    try:
        await _ensure_session_access(session_id, user)
        suggestions = await _get_manager().suggest_selectors(
            session_id, body.target_description
        )

        # Optionally enrich with LLM analysis via AutoHealerAgent
        ai_analysis: Optional[str] = None
        try:
            from app.domains.agents.banking_team.auto_healer import AutoHealerAgent

            healer = AutoHealerAgent()
            if hasattr(healer, "analyze_selectors"):
                ai_analysis = healer.analyze_selectors(
                    body.target_description, suggestions
                )
        except Exception as exc:
            # Fire-and-forget: LLM enrichment is non-critical
            logger.warning(
                "Selector suggestion enrichment skipped for session %s: %s",
                session_id,
                exc,
            )

        from .schemas import SelectorResult

        return SelectorSuggestResponse(
            suggestions=[SelectorResult(**s) for s in suggestions],
            ai_analysis=ai_analysis,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Browser Action ───────────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/action", response_model=ActionResponse
)
async def execute_action(
    session_id: str, body: ActionRequest, user: CurrentUser
):
    """Browser aksiyonu çalıştır (click, fill, select, hover, press, scroll, wait)."""
    _require_playwright()
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().execute_action(
            session_id,
            body.action,
            body.selector,
            value=body.value,
            timeout_ms=body.timeout_ms,
        )
        return ActionResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Heal Verify ──────────────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/heal/verify",
    response_model=HealVerifyResponse,
)
async def heal_verify(
    session_id: str, body: HealVerifyRequest, user: CurrentUser
):
    """Healing sonrasi dogrulama: orijinal ve heal edilmis selector'i kontrol et."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().heal_verify(
            session_id,
            body.original_selector,
            body.healed_selector,
            expected_tag=body.expected_tag,
            expected_text=body.expected_text,
        )
        return HealVerifyResponse(**result)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── Frontend-compatibility alias endpoints ───────────────────────────────────
# The frontend hook (use-playwright-mcp.ts) uses shorter path conventions.
# These thin aliases keep the canonical paths AND satisfy the frontend.


@router.get(
    "/sessions/{session_id}/screenshot", response_model=ScreenshotResponse
)
async def take_screenshot_get(session_id: str, user: CurrentUser):
    """GET alias — no-body screenshot for live preview (full_page=False default)."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().screenshot(
            session_id, selector=None, full_page=False, fmt="png", quality=None
        )
        return ScreenshotResponse(**result)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/dom-snapshot", response_model=DOMSnapshotResponse
)
async def get_dom_snapshot_alias(
    session_id: str, body: DOMSnapshotRequest, user: CurrentUser
):
    """POST alias for /dom — frontend uses /dom-snapshot path."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().get_dom_snapshot(
            session_id,
            selector=body.selector,
            max_depth=body.max_depth,
            include_styles=body.include_styles,
            include_hidden=body.include_hidden,
        )
        return DOMSnapshotResponse(**result)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/validate-selectors",
    response_model=SelectorValidateResponse,
)
async def validate_selectors_alias(
    session_id: str, body: SelectorValidateRequest, user: CurrentUser
):
    """POST alias for /selectors/validate — frontend uses /validate-selectors path."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().validate_selectors(
            session_id, body.selectors, timeout_ms=body.timeout_ms
        )
        return SelectorValidateResponse(**result)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/suggest-selectors",
    response_model=SelectorSuggestResponse,
)
async def suggest_selectors_alias(
    session_id: str, body: SelectorSuggestRequest, user: CurrentUser
):
    """POST alias for /selectors/suggest — frontend uses /suggest-selectors path."""
    try:
        await _ensure_session_access(session_id, user)
        suggestions = await _get_manager().suggest_selectors(
            session_id, body.target_description
        )
        from .schemas import SelectorResult
        return SelectorSuggestResponse(
            suggestions=[SelectorResult(**s) for s in suggestions],
            ai_analysis=None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/verify-heal",
    response_model=HealVerifyResponse,
)
async def heal_verify_alias(
    session_id: str, body: HealVerifyRequest, user: CurrentUser
):
    """POST alias for /heal/verify — frontend uses /verify-heal path."""
    try:
        await _ensure_session_access(session_id, user)
        result = await _get_manager().heal_verify(
            session_id,
            body.original_selector,
            body.healed_selector,
            expected_tag=body.expected_tag,
            expected_text=body.expected_text,
        )
        return HealVerifyResponse(**result)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Health Check ─────────────────────────────────────────────────────────────


@router.get("/health")
async def playwright_health(user: CurrentUser):
    """Playwright servisinin durumunu kontrol et."""
    return {
        "playwright_available": PLAYWRIGHT_AVAILABLE,
        "status": "ok" if PLAYWRIGHT_AVAILABLE else "unavailable",
        "detail": (
            "Playwright servisi hazır."
            if PLAYWRIGHT_AVAILABLE
            else "Playwright paketi kurulu degil."
        ),
    }
