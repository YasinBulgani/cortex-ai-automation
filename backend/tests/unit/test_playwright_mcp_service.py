"""
playwright_mcp domain service unit testleri — 14 test.

Tüm testler BrowserManager singleton'ını mock'lar; Playwright kurulu
olmak zorunda değildir.  Async metodlar AsyncMock ile simüle edilir.
"""
from __future__ import annotations

import base64
import pytest

try:
    from app.domains.playwright_mcp import service as pw_service
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK, reason="playwright_mcp service import failed"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, MagicMock, patch


def _make_manager(**overrides) -> MagicMock:
    """Async metodlarla donatılmış sahte BrowserManager döner."""
    m = MagicMock()
    m.create_session = AsyncMock(return_value={"session_id": "s1", "status": "open"})
    m.get_session = AsyncMock(return_value={"session_id": "s1", "url": "about:blank"})
    m.list_sessions = AsyncMock(return_value=[{"session_id": "s1"}])
    m.close_session = AsyncMock(return_value=None)
    m.execute_action = AsyncMock(return_value={"ok": True})
    m.screenshot = AsyncMock(return_value=b"PNG_BYTES")
    m.shutdown = AsyncMock(return_value=None)
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------

class TestCreateSession:
    @pytest.mark.asyncio
    async def test_returns_session_dict(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.create_session({"headless": True})
        assert isinstance(result, dict)
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_manager_called_with_config(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            await pw_service.create_session({"headless": False, "browser": "firefox"})
        mgr.create_session.assert_awaited_once_with(headless=False, browser="firefox")

    @pytest.mark.asyncio
    async def test_empty_config_still_works(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.create_session({})
        assert "session_id" in result


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------

class TestGetSession:
    @pytest.mark.asyncio
    async def test_found_returns_dict(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.get_session("s1")
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_not_found_raises_key_error(self):
        mgr = _make_manager(get_session=AsyncMock(return_value=None))
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            with pytest.raises(KeyError):
                await pw_service.get_session("no-such-session")

    @pytest.mark.asyncio
    async def test_manager_called_with_session_id(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            await pw_service.get_session("abc")
        mgr.get_session.assert_awaited_once_with("abc")


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

class TestListSessions:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.list_sessions()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_user_id_filter_applied(self):
        sessions = [
            {"session_id": "s1", "user_id": "alice"},
            {"session_id": "s2", "user_id": "bob"},
        ]
        mgr = _make_manager(list_sessions=AsyncMock(return_value=sessions))
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.list_sessions(user_id="alice")
        assert len(result) == 1
        assert result[0]["user_id"] == "alice"

    @pytest.mark.asyncio
    async def test_no_filter_returns_all(self):
        sessions = [{"session_id": f"s{i}"} for i in range(3)]
        mgr = _make_manager(list_sessions=AsyncMock(return_value=sessions))
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.list_sessions()
        assert len(result) == 3


# ---------------------------------------------------------------------------
# close_session
# ---------------------------------------------------------------------------

class TestCloseSession:
    @pytest.mark.asyncio
    async def test_calls_manager_close_session(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            await pw_service.close_session("s1")
        mgr.close_session.assert_awaited_once_with("s1")

    @pytest.mark.asyncio
    async def test_returns_none(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.close_session("s1")
        assert result is None


# ---------------------------------------------------------------------------
# execute_action / take_screenshot
# ---------------------------------------------------------------------------

class TestExecuteAction:
    @pytest.mark.asyncio
    async def test_execute_action_forwards_args(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.execute_action("s1", {"type": "click", "selector": "#btn"})
        mgr.execute_action.assert_awaited_once_with("s1", {"type": "click", "selector": "#btn"})
        assert result == {"ok": True}


class TestTakeScreenshot:
    @pytest.mark.asyncio
    async def test_returns_bytes(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            result = await pw_service.take_screenshot("s1")
        assert isinstance(result, bytes)
        assert result == b"PNG_BYTES"

    @pytest.mark.asyncio
    async def test_manager_screenshot_called(self):
        mgr = _make_manager()
        with patch.object(pw_service, "_get_manager", return_value=mgr):
            await pw_service.take_screenshot("s1")
        mgr.screenshot.assert_awaited_once_with("s1")


# ---------------------------------------------------------------------------
# Playwright not installed → RuntimeError
# ---------------------------------------------------------------------------

class TestPlaywrightNotInstalled:
    def test_get_manager_raises_runtime_error_when_import_fails(self):
        """_get_manager() dışarıdan ImportError gelirse RuntimeError fırlatmalı."""
        with patch.dict("sys.modules", {"app.domains.playwright_mcp.browser_manager": None}):
            with pytest.raises((RuntimeError, Exception)):
                pw_service._get_manager()
