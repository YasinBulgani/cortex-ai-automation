"""Pydantic şemaları — mobil otomasyon."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Platform = Literal["android", "ios"]
DeviceKind = Literal["emulator", "simulator", "physical"]
DeviceStatus = Literal["idle", "running", "booting", "offline", "error"]
SessionStatus = Literal["queued", "running", "passed", "failed", "cancelled"]
StepStatus = Literal["pending", "running", "passed", "failed", "healed", "skipped"]
RunMode = Literal["simulation", "appium"]
FailureCategory = Literal[
    "appium",
    "device",
    "app",
    "assertion",
    "locator",
    "timeout",
    "infrastructure",
    "artifact",
]


# ── Device ─────────────────────────────────────────────────────
class DeviceBase(BaseModel):
    name: str
    platform: Platform
    os_version: str
    profile: str
    kind: DeviceKind = "emulator"
    appium_url: str = "http://127.0.0.1:4723"
    udid: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class Device(DeviceBase):
    id: str
    status: DeviceStatus = "idle"
    battery: int = 100
    cpu_pct: int = 5
    ram_pct: int = 30
    current_step: Optional[str] = None
    steps_done: int = 0
    steps_total: int = 0
    heal_streak: int = 0
    last_seen: Optional[datetime] = None
    last_error: Optional[str] = None

    model_config = {"from_attributes": True}


class PhysicalEnrollRequest(BaseModel):
    name: str = Field(..., description="Okunabilir cihaz adı, örn: 'Lab-01 Samsung S24'")
    platform: Platform
    os_version: str
    udid: str = Field(..., description="Android serial veya iOS UDID")
    appium_url: str
    profile: str = Field(default="", description="Cihaz profili — boşsa name kullanılır")


# ── Appium Action ──────────────────────────────────────────────
class AppiumAction(BaseModel):
    action: Literal[
        "launch",
        "launchApp",
        "openUrl",
        "find",
        "tap",
        "sendKeys",
        "type",
        "clear",
        "verifyVisible",
        "wait",
        "swipe",
        "scroll",
        "pinch",
        "back",
        "home",
        "rotate",
        "pressKey",
        "installApp",
        "setNetwork",
        "grantPermission",
        "switchContext",
        "screenshot",
        "takeScreenshot",
        "pageSource",
    ]
    by: Optional[Literal["accessibilityId", "xpath", "predicate", "id", "className", "androidUiAutomator", "cssSelector", "iosClassChain", "image", "name"]] = None
    value: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    timeout: Optional[int] = None
    ms: Optional[int] = None
    direction: Optional[Literal["up", "down", "left", "right"]] = None


# ── LLM Step Generation ────────────────────────────────────────
class StepGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Doğal dil test senaryosu")
    platform: Platform = "android"
    app_package: Optional[str] = None
    page_source: Optional[str] = Field(
        default=None,
        description="İsteğe bağlı — mevcut sayfanın Appium source XML'i (grounding için)",
    )


class StepGenerationResponse(BaseModel):
    steps: list[AppiumAction]
    model: str
    token_usage: Optional[dict] = None
    fallback_used: bool = False


# ── Session ────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    scenario_name: str
    prompt: str
    platform: Literal["android", "ios", "both"] = "both"
    parallel: int = Field(default=1, ge=1, le=20)
    device_ids: Optional[list[str]] = Field(
        default=None,
        description="İsteğe bağlı deterministik cihaz seçimi. Verilirse platform/parallel havuzu yerine bu cihazlar kullanılır.",
    )
    mode: RunMode = Field(
        default="simulation",
        description="simulation mevcut test/demo modu; appium gerçek WebDriver koşusudur",
    )
    steps: Optional[list[AppiumAction]] = Field(
        default=None,
        description="Deterministik mobil step listesi. Verilirse LLM/heuristic generation kullanılmaz.",
    )
    app: Optional[dict] = Field(
        default=None,
        description="Gerçek Appium koşusu için app/web hedefi: {'type':'web','url':'...'} veya {'type':'native','path':'...'}",
    )
    pass_rate: int = Field(default=80, ge=0, le=100, description="Simülasyon için")
    heal_rate: int = Field(default=30, ge=0, le=100, description="Simülasyon için")


class Step(BaseModel):
    seq: int
    action: str
    locator: Optional[dict] = None
    status: StepStatus = "pending"
    duration_ms: int = 0
    screenshot_url: Optional[str] = None
    llm_reason: Optional[str] = None
    error_message: Optional[str] = None


class Session(BaseModel):
    id: str
    device_id: str
    scenario_name: str
    status: SessionStatus = "queued"
    started_at: datetime
    finished_at: Optional[datetime] = None
    mode: RunMode = "simulation"
    failure_category: Optional[FailureCategory] = None
    failure_message: Optional[str] = None
    healed: int = 0
    steps: list[Step] = Field(default_factory=list)


class SessionEvent(BaseModel):
    """SSE event payload."""

    id: int = 0
    type: Literal["step", "status", "log", "heal", "artifact", "done"]
    session_id: str
    device_id: str
    payload: dict


class MobileArtifact(BaseModel):
    id: str
    session_id: str
    step_seq: Optional[int] = None
    kind: Literal["screenshot", "page_source", "stdout", "appium_log", "video", "junit"]
    path: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    sha256: str = ""
    created_at: datetime


# ── Visual Verification ────────────────────────────────────────
class VisualVerifyRequest(BaseModel):
    screenshot_base64: str
    assertion: str = Field(..., description="Doğrulanacak koşul — örn: 'ana sayfada kullanıcı adı görünür'")


class VisualVerifyResponse(BaseModel):
    passed: bool
    confidence: float = 0.0
    reason: str = ""


# ── Suite stats ────────────────────────────────────────────────
class FarmStats(BaseModel):
    total: int
    online: int
    running: int
    idle: int
    offline: int
    by_platform: dict[str, int]
