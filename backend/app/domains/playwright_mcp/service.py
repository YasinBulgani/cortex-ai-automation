"""playwright_mcp service — BrowserManager üstü ince facade.

Router'ın doğrudan browser_manager'a erişmesi yerine bu modül üzerinden
çalışması, iş mantığının HTTP katmanından ayrılmasını sağlar.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_manager():
    """BrowserManager singleton'ını döner — Playwright kurulu değilse hata fırlatır."""
    try:
        from app.domains.playwright_mcp.browser_manager import get_browser_manager
        return get_browser_manager()
    except ImportError as exc:
        raise RuntimeError(
            "playwright kurulu değil — 'pip install playwright' çalıştırın"
        ) from exc


async def create_session(config: dict) -> dict:
    """Yeni bir browser session başlatır, session bilgisini döner."""
    manager = _get_manager()
    return await manager.create_session(**config)


async def get_session(session_id: str) -> dict:
    """Session bilgisini döner; bulunamazsa KeyError fırlatır."""
    manager = _get_manager()
    session = await manager.get_session(session_id)
    if session is None:
        raise KeyError(f"Session bulunamadı: {session_id}")
    return session


async def list_sessions(user_id: str | None = None) -> list[dict]:
    """Aktif session'ları listeler. user_id verilirse filtreler."""
    manager = _get_manager()
    sessions = await manager.list_sessions()
    if user_id:
        sessions = [s for s in sessions if s.get("user_id") == user_id]
    return sessions


async def close_session(session_id: str) -> None:
    """Session'ı kapatır ve kaynakları serbest bırakır."""
    manager = _get_manager()
    await manager.close_session(session_id)


async def execute_action(session_id: str, action: dict) -> dict:
    """Verilen session üzerinde bir browser aksiyonu çalıştırır."""
    manager = _get_manager()
    return await manager.execute_action(session_id, action)


async def take_screenshot(session_id: str) -> bytes:
    """Session'ın mevcut sayfasının ekran görüntüsünü alır."""
    manager = _get_manager()
    return await manager.screenshot(session_id)


async def shutdown() -> None:
    """Tüm session'ları ve browser sürecini kapatır (sunucu kapanışı için)."""
    try:
        manager = _get_manager()
        await manager.shutdown()
    except RuntimeError:
        logger.debug("Playwright yüklü değil — shutdown no-op")
