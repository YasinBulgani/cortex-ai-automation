"""
mobile domain service unit testleri — 14 test.

mobile/service.py; device_broker, orchestrator ve llm_stepper alt
modüllerine delege eder.  Bu testler alt modülleri mock'lar; Appium veya
gerçek bir cihaz gerekmez.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.mobile import service as mobile_service
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK, reason="mobile service import failed"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, MagicMock, patch


def _fake_device(name: str = "emulator-5554") -> MagicMock:
    d = MagicMock()
    d.name = name
    return d


def _fake_session(sid: str = "mob-session-1") -> MagicMock:
    s = MagicMock()
    s.id = sid
    return s


def _fake_step_response() -> MagicMock:
    r = MagicMock()
    r.steps = [MagicMock(action="tap", selector="//button")]
    r.confidence = 0.92
    return r


# ---------------------------------------------------------------------------
# get_device_list
# ---------------------------------------------------------------------------

class TestGetDeviceList:
    def test_delegates_to_broker_list(self):
        devices = [_fake_device("emu-1"), _fake_device("emu-2")]
        broker = MagicMock()
        broker.list.return_value = devices
        with patch.object(mobile_service, "get_broker", return_value=broker):
            result = mobile_service.get_device_list()
        broker.list.assert_called_once()
        assert result == devices

    def test_empty_device_list_returns_empty(self):
        broker = MagicMock()
        broker.list.return_value = []
        with patch.object(mobile_service, "get_broker", return_value=broker):
            result = mobile_service.get_device_list()
        assert result == []

    def test_returns_list_type(self):
        broker = MagicMock()
        broker.list.return_value = [_fake_device()]
        with patch.object(mobile_service, "get_broker", return_value=broker):
            result = mobile_service.get_device_list()
        assert isinstance(result, list)

    def test_multiple_devices_all_returned(self):
        devices = [_fake_device(f"emu-{i}") for i in range(5)]
        broker = MagicMock()
        broker.list.return_value = devices
        with patch.object(mobile_service, "get_broker", return_value=broker):
            result = mobile_service.get_device_list()
        assert len(result) == 5


# ---------------------------------------------------------------------------
# start_mobile_session
# ---------------------------------------------------------------------------

class TestStartMobileSession:
    @pytest.mark.asyncio
    async def test_calls_start_suite_with_config(self):
        sessions = [_fake_session()]
        config = MagicMock()
        with patch.object(mobile_service, "start_suite", AsyncMock(return_value=sessions)) as mock_suite:
            result = await mobile_service.start_mobile_session(config)
        mock_suite.assert_awaited_once_with(config)
        assert result == sessions

    @pytest.mark.asyncio
    async def test_returns_list_of_sessions(self):
        sessions = [_fake_session("s1"), _fake_session("s2")]
        with patch.object(mobile_service, "start_suite", AsyncMock(return_value=sessions)):
            result = await mobile_service.start_mobile_session(MagicMock())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_no_device_available_returns_empty(self):
        with patch.object(mobile_service, "start_suite", AsyncMock(return_value=[])):
            result = await mobile_service.start_mobile_session(MagicMock())
        assert result == []


# ---------------------------------------------------------------------------
# generate_steps_from_prompt
# ---------------------------------------------------------------------------

class TestGenerateStepsFromPrompt:
    def test_delegates_to_generate_steps(self):
        expected = _fake_step_response()
        with patch.object(mobile_service, "generate_steps", return_value=expected) as mock_gs:
            result = mobile_service.generate_steps_from_prompt(
                "login with test user",
                platform="android",
                page_source="<hierarchy/>",
                app_package="com.example.app",
            )
        mock_gs.assert_called_once_with(
            prompt="login with test user",
            platform="android",
            page_source="<hierarchy/>",
            app_package="com.example.app",
        )
        assert result is expected

    def test_default_platform_is_android(self):
        expected = _fake_step_response()
        with patch.object(mobile_service, "generate_steps", return_value=expected) as mock_gs:
            mobile_service.generate_steps_from_prompt("tap submit")
        call_kwargs = mock_gs.call_args.kwargs
        assert call_kwargs.get("platform") == "android"

    def test_returns_step_generation_response(self):
        expected = _fake_step_response()
        with patch.object(mobile_service, "generate_steps", return_value=expected):
            result = mobile_service.generate_steps_from_prompt("tap logout")
        assert result is expected
        assert hasattr(result, "steps")
        assert hasattr(result, "confidence")


# ---------------------------------------------------------------------------
# list_recent_sessions
# ---------------------------------------------------------------------------

class TestListRecentSessions:
    def test_delegates_to_store_list_recent(self):
        sessions = [_fake_session("s10"), _fake_session("s11")]
        store = MagicMock()
        store.list_recent.return_value = sessions
        with patch.object(mobile_service, "get_store", return_value=store):
            result = mobile_service.list_recent_sessions(limit=10)
        store.list_recent.assert_called_once_with(limit=10)
        assert result == sessions

    def test_default_limit_is_40(self):
        store = MagicMock()
        store.list_recent.return_value = []
        with patch.object(mobile_service, "get_store", return_value=store):
            mobile_service.list_recent_sessions()
        store.list_recent.assert_called_once_with(limit=40)

    def test_custom_limit_passed_through(self):
        store = MagicMock()
        store.list_recent.return_value = []
        with patch.object(mobile_service, "get_store", return_value=store):
            mobile_service.list_recent_sessions(limit=5)
        store.list_recent.assert_called_once_with(limit=5)
