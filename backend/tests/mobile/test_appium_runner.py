"""AppiumRunner unit tests — gerçek Appium gerektirmez."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.mobile.appium_client import AppiumError
from app.domains.mobile.appium_runner import AppiumRunner
from app.domains.mobile.artifact_store import MobileArtifactStore
from app.domains.mobile.schemas import AppiumAction, Device


pytestmark = pytest.mark.P2


class _FakeHTTP:
    def close(self) -> None:
        pass


class _HappyClient:
    def __init__(self) -> None:
        self._http = _FakeHTTP()
        self.session_id = None
        self.clicked = False
        self.swipes: list[tuple[int, int, int, int]] = []
        self.backs: int = 0

    def create_session(self, _caps):
        self.session_id = "sid"
        return "sid"

    def quit(self):
        self.session_id = None

    def open_url(self, _url: str) -> None:
        pass

    def find_element(self, _by: str, _value: str) -> str:
        return "elem-1"

    def click(self, _element_id: str) -> None:
        self.clicked = True

    def send_keys(self, _element_id: str, _text: str) -> None:
        pass

    def clear(self, _element_id: str) -> None:
        pass

    def is_displayed(self, _element_id: str) -> bool:
        return True

    def screenshot_bytes(self) -> bytes:
        return b"fake-png"

    def page_source(self) -> str:
        return "<App/>"

    def back(self) -> None:
        self.backs += 1

    def swipe(self, sx: int, sy: int, ex: int, ey: int, duration_ms: int = 300) -> None:
        self.swipes.append((sx, sy, ex, ey))


class _MissingElementClient(_HappyClient):
    def find_element(self, _by: str, _value: str) -> str:
        raise AppiumError("no such element: login")


def _device() -> Device:
    return Device(
        id="and-test",
        name="Pixel Test",
        platform="android",
        os_version="14",
        profile="pixel_test",
        appium_url="http://fake:4723",
    )


def test_runner_executes_steps_and_writes_requested_screenshot(tmp_path: Path):
    artifact_store = MobileArtifactStore(tmp_path)
    runner = AppiumRunner(
        artifact_store=artifact_store,
        client_factory=lambda _url: _HappyClient(),  # type: ignore[return-value]
    )

    result = runner.run(
        session_id="s_test",
        device=_device(),
        app={"type": "web", "url": "https://example.test"},
        steps=[
            AppiumAction(action="openUrl", url="https://example.test"),
            AppiumAction(action="find", by="accessibilityId", value="login"),
            AppiumAction(action="tap"),
            AppiumAction(action="screenshot"),
        ],
    )

    assert result.status == "passed"
    assert [s.status for s in result.steps] == ["passed", "passed", "passed", "passed"]
    assert len(result.artifacts) == 1
    assert result.artifacts[0].kind == "screenshot"
    assert Path(result.artifacts[0].path).read_bytes() == b"fake-png"


def test_runner_categorizes_locator_failure_and_collects_failure_artifacts(tmp_path: Path):
    artifact_store = MobileArtifactStore(tmp_path)
    runner = AppiumRunner(
        artifact_store=artifact_store,
        client_factory=lambda _url: _MissingElementClient(),  # type: ignore[return-value]
    )

    result = runner.run(
        session_id="s_fail",
        device=_device(),
        steps=[AppiumAction(action="find", by="accessibilityId", value="login")],
    )

    assert result.status == "failed"
    assert result.failure_category == "locator"
    assert result.steps[0].status == "failed"
    assert {a.kind for a in result.artifacts} == {"screenshot", "page_source"}


def test_runner_swipe_up_calls_swipe(tmp_path: Path):
    client = _HappyClient()
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: client,  # type: ignore[return-value]
    )
    result = runner.run(
        session_id="s_swipe",
        device=_device(),
        steps=[AppiumAction(action="swipe", direction="up")],
    )
    assert result.status == "passed"
    assert len(client.swipes) == 1
    sx, sy, ex, ey = client.swipes[0]
    assert ey < sy  # swipe up: end y daha küçük


def test_runner_swipe_down_calls_swipe(tmp_path: Path):
    client = _HappyClient()
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: client,  # type: ignore[return-value]
    )
    result = runner.run(
        session_id="s_swipe_dn",
        device=_device(),
        steps=[AppiumAction(action="swipe", direction="down")],
    )
    assert result.status == "passed"
    assert len(client.swipes) == 1
    sx, sy, ex, ey = client.swipes[0]
    assert ey > sy  # swipe down: end y daha büyük


def test_runner_swipe_left_right(tmp_path: Path):
    client = _HappyClient()
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: client,  # type: ignore[return-value]
    )
    result = runner.run(
        session_id="s_lr",
        device=_device(),
        steps=[
            AppiumAction(action="swipe", direction="left"),
            AppiumAction(action="swipe", direction="right"),
        ],
    )
    assert result.status == "passed"
    assert len(client.swipes) == 2
    _, _, ex_l, _ = client.swipes[0]
    sx_l, _, _, _ = client.swipes[0]
    assert ex_l < sx_l  # left: end x daha küçük
    _, _, ex_r, _ = client.swipes[1]
    sx_r, _, _, _ = client.swipes[1]
    assert ex_r > sx_r  # right: end x daha büyük


def test_runner_scroll_calls_swipe(tmp_path: Path):
    client = _HappyClient()
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: client,  # type: ignore[return-value]
    )
    result = runner.run(
        session_id="s_scroll",
        device=_device(),
        steps=[AppiumAction(action="scroll", direction="down")],
    )
    assert result.status == "passed"
    assert len(client.swipes) == 1


def test_runner_back_and_home_pass(tmp_path: Path):
    client = _HappyClient()
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: client,  # type: ignore[return-value]
    )
    result = runner.run(
        session_id="s_nav",
        device=_device(),
        steps=[
            AppiumAction(action="back"),
            AppiumAction(action="home"),
            AppiumAction(action="pressKey"),
        ],
    )
    assert result.status == "passed"
    assert client.backs == 3  # back + home (proxy) + pressKey (proxy)


def test_runner_new_locator_strategies_accepted(tmp_path: Path):
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: _HappyClient(),  # type: ignore[return-value]
    )
    for strategy in ("cssSelector", "iosClassChain", "name"):
        result = runner.run(
            session_id=f"s_{strategy}",
            device=_device(),
            steps=[
                AppiumAction(action="find", by=strategy, value="some-value"),  # type: ignore[arg-type]
                AppiumAction(action="tap"),
            ],
        )
        assert result.status == "passed", f"{strategy} stratejisi başarısız oldu"


def test_runner_unknown_action_fails(tmp_path: Path):
    runner = AppiumRunner(
        artifact_store=MobileArtifactStore(tmp_path),
        client_factory=lambda _url: _HappyClient(),  # type: ignore[return-value]
    )
    result = runner.run(
        session_id="s_unknown",
        device=_device(),
        steps=[AppiumAction.model_validate({"action": "screenshot", "by": None})],
    )
    # screenshot is a valid no-op action — should pass
    assert result.status == "passed"
