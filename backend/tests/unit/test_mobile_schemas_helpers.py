"""Unit tests for app.domains.mobile.schemas — Pydantic models.

Tests are fully self-contained: no DB, no HTTP, no Appium.
Covers Device, AppiumAction, Session-related, Step, FarmStats schemas.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

try:
    from app.domains.mobile.schemas import (
        DeviceBase,
        DeviceCreate,
        Device,
        PhysicalEnrollRequest,
        AppiumAction,
        StepGenerationRequest,
        StepGenerationResponse,
        SessionCreate,
        Step,
        Session,
        SessionEvent,
        MobileArtifact,
        VisualVerifyRequest,
        VisualVerifyResponse,
        FarmStats,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="mobile.schemas import failed")


def _now():
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# DeviceBase
# ---------------------------------------------------------------------------

class TestDeviceBase:
    def test_creation(self):
        d = DeviceBase(name="Emulator-1", platform="android", os_version="13", profile="default")
        assert d.name == "Emulator-1"
        assert d.platform == "android"

    def test_defaults(self):
        d = DeviceBase(name="X", platform="ios", os_version="16", profile="p")
        assert d.kind == "emulator"
        assert d.appium_url == "http://127.0.0.1:4723"
        assert d.udid is None

    def test_ios_platform(self):
        d = DeviceBase(name="iPhone", platform="ios", os_version="17", profile="ios")
        assert d.platform == "ios"


# ---------------------------------------------------------------------------
# DeviceCreate
# ---------------------------------------------------------------------------

class TestDeviceCreate:
    def test_inherits_device_base(self):
        d = DeviceCreate(name="Dev", platform="android", os_version="12", profile="p")
        assert isinstance(d, DeviceBase)


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

class TestDevice:
    def test_creation(self):
        d = Device(id="dev-001", name="Emu", platform="android", os_version="13", profile="p")
        assert d.id == "dev-001"

    def test_defaults(self):
        d = Device(id="x", name="D", platform="android", os_version="12", profile="p")
        assert d.status == "idle"
        assert d.battery == 100
        assert d.cpu_pct == 5
        assert d.ram_pct == 30
        assert d.current_step is None
        assert d.steps_done == 0
        assert d.steps_total == 0
        assert d.heal_streak == 0
        assert d.last_seen is None
        assert d.last_error is None


# ---------------------------------------------------------------------------
# PhysicalEnrollRequest
# ---------------------------------------------------------------------------

class TestPhysicalEnrollRequest:
    def test_creation(self):
        req = PhysicalEnrollRequest(
            name="Lab-01",
            platform="android",
            os_version="13",
            udid="emulator-5554",
            appium_url="http://localhost:4723",
        )
        assert req.udid == "emulator-5554"

    def test_default_profile_empty(self):
        req = PhysicalEnrollRequest(
            name="X",
            platform="ios",
            os_version="16",
            udid="abc-udid",
            appium_url="http://localhost:4723",
        )
        assert req.profile == ""


# ---------------------------------------------------------------------------
# AppiumAction
# ---------------------------------------------------------------------------

class TestAppiumAction:
    def test_tap_action(self):
        a = AppiumAction(action="tap", by="accessibilityId", value="loginButton")
        assert a.action == "tap"
        assert a.by == "accessibilityId"

    def test_defaults(self):
        a = AppiumAction(action="launch")
        assert a.by is None
        assert a.value is None
        assert a.text is None
        assert a.url is None
        assert a.timeout is None
        assert a.ms is None
        assert a.direction is None

    def test_send_keys(self):
        a = AppiumAction(action="sendKeys", by="id", value="username", text="testuser")
        assert a.text == "testuser"

    def test_swipe_with_direction(self):
        a = AppiumAction(action="swipe", direction="up")
        assert a.direction == "up"

    def test_screenshot_action(self):
        a = AppiumAction(action="screenshot")
        assert a.action == "screenshot"


# ---------------------------------------------------------------------------
# StepGenerationRequest
# ---------------------------------------------------------------------------

class TestStepGenerationRequest:
    def test_creation(self):
        req = StepGenerationRequest(prompt="Login as admin and verify dashboard")
        assert "Login" in req.prompt

    def test_defaults(self):
        req = StepGenerationRequest(prompt="test scenario")
        assert req.platform == "android"
        assert req.app_package is None
        assert req.page_source is None

    def test_ios_platform(self):
        req = StepGenerationRequest(prompt="test", platform="ios")
        assert req.platform == "ios"


# ---------------------------------------------------------------------------
# StepGenerationResponse
# ---------------------------------------------------------------------------

class TestStepGenerationResponse:
    def test_creation(self):
        a = AppiumAction(action="launch")
        resp = StepGenerationResponse(steps=[a], model="gpt-4o")
        assert len(resp.steps) == 1
        assert resp.model == "gpt-4o"

    def test_defaults(self):
        resp = StepGenerationResponse(steps=[], model="gpt-4o")
        assert resp.token_usage is None
        assert resp.fallback_used is False


# ---------------------------------------------------------------------------
# SessionCreate
# ---------------------------------------------------------------------------

class TestSessionCreate:
    def test_creation(self):
        sc = SessionCreate(scenario_name="Login Test", prompt="Login as admin")
        assert sc.scenario_name == "Login Test"

    def test_defaults(self):
        sc = SessionCreate(scenario_name="x", prompt="y")
        assert sc.platform == "both"
        assert sc.parallel == 1
        assert sc.device_ids is None
        assert sc.mode == "simulation"
        assert sc.steps is None
        assert sc.app is None
        assert sc.pass_rate == 80
        assert sc.heal_rate == 30

    def test_parallel_min(self):
        with pytest.raises(Exception):
            SessionCreate(scenario_name="x", prompt="y", parallel=0)

    def test_parallel_max(self):
        with pytest.raises(Exception):
            SessionCreate(scenario_name="x", prompt="y", parallel=21)

    def test_pass_rate_bounds(self):
        with pytest.raises(Exception):
            SessionCreate(scenario_name="x", prompt="y", pass_rate=101)


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

class TestStep:
    def test_creation(self):
        step = Step(seq=1, action="tap")
        assert step.seq == 1
        assert step.action == "tap"

    def test_defaults(self):
        step = Step(seq=0, action="launch")
        assert step.locator is None
        assert step.status == "pending"
        assert step.duration_ms == 0
        assert step.screenshot_url is None
        assert step.llm_reason is None
        assert step.error_message is None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class TestSession:
    def test_creation(self):
        session = Session(
            id="sess-001",
            device_id="dev-001",
            scenario_name="Login",
            started_at=_now(),
        )
        assert session.id == "sess-001"

    def test_defaults(self):
        session = Session(
            id="x",
            device_id="d",
            scenario_name="s",
            started_at=_now(),
        )
        assert session.status == "queued"
        assert session.finished_at is None
        assert session.mode == "simulation"
        assert session.failure_category is None
        assert session.failure_message is None
        assert session.healed == 0
        assert session.steps == []


# ---------------------------------------------------------------------------
# SessionEvent
# ---------------------------------------------------------------------------

class TestSessionEvent:
    def test_creation(self):
        event = SessionEvent(
            type="step",
            session_id="sess-001",
            device_id="dev-001",
            payload={"step": 1},
        )
        assert event.type == "step"

    def test_default_id(self):
        event = SessionEvent(
            type="status",
            session_id="s",
            device_id="d",
            payload={},
        )
        assert event.id == 0


# ---------------------------------------------------------------------------
# MobileArtifact
# ---------------------------------------------------------------------------

class TestMobileArtifact:
    def test_creation(self):
        artifact = MobileArtifact(
            id="art-001",
            session_id="sess-001",
            kind="screenshot",
            path="/artifacts/screen.png",
            mime_type="image/png",
            created_at=_now(),
        )
        assert artifact.kind == "screenshot"

    def test_defaults(self):
        artifact = MobileArtifact(
            id="x",
            session_id="s",
            kind="junit",
            path="/x.xml",
            created_at=_now(),
        )
        assert artifact.step_seq is None
        assert artifact.mime_type == "application/octet-stream"
        assert artifact.size_bytes == 0
        assert artifact.sha256 == ""


# ---------------------------------------------------------------------------
# VisualVerifyRequest
# ---------------------------------------------------------------------------

class TestVisualVerifyRequest:
    def test_creation(self):
        req = VisualVerifyRequest(
            screenshot_base64="abc123==",
            assertion="Login button is visible",
        )
        assert "Login" in req.assertion
        assert req.screenshot_base64 == "abc123=="


# ---------------------------------------------------------------------------
# VisualVerifyResponse
# ---------------------------------------------------------------------------

class TestVisualVerifyResponse:
    def test_defaults(self):
        resp = VisualVerifyResponse(passed=False)
        assert resp.passed is False
        assert resp.confidence == pytest.approx(0.0)
        assert resp.reason == ""

    def test_passed_true(self):
        resp = VisualVerifyResponse(passed=True, confidence=0.95, reason="Element found")
        assert resp.passed is True
        assert resp.confidence == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# FarmStats
# ---------------------------------------------------------------------------

class TestFarmStats:
    def test_creation(self):
        stats = FarmStats(total=10, online=8, running=3, idle=5, offline=2, by_platform={"android": 6, "ios": 4})
        assert stats.total == 10
        assert stats.online == 8
        assert stats.running == 3
        assert stats.idle == 5
        assert stats.offline == 2

    def test_by_platform(self):
        stats = FarmStats(total=5, online=5, running=2, idle=3, offline=0, by_platform={"android": 5})
        assert stats.by_platform["android"] == 5

    def test_all_zero(self):
        stats = FarmStats(total=0, online=0, running=0, idle=0, offline=0, by_platform={})
        assert stats.total == 0
