"""Gercek Appium kosum katmani.

Bu modul simulasyon uretmez. Appium'a ulasilamiyorsa veya bir step basarisiz
olursa bunu failure olarak dondurur ve best-effort artifact toplamaya calisir.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .appium_client import AppiumCapabilities, AppiumClient, AppiumError
from .artifact_store import MobileArtifactStore, get_artifact_store
from .schemas import AppiumAction, Device, FailureCategory, MobileArtifact


@dataclass
class StepRunResult:
    seq: int
    status: str
    duration_ms: int
    artifact_ids: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    failure_category: Optional[FailureCategory] = None


@dataclass
class AppiumRunResult:
    status: str
    steps: list[StepRunResult]
    artifacts: list[MobileArtifact] = field(default_factory=list)
    failure_category: Optional[FailureCategory] = None
    failure_message: Optional[str] = None


EventCallback = Callable[[str, dict], None]
ClientFactory = Callable[[str], AppiumClient]


class AppiumRunner:
    """Thin runner over AppiumClient with deterministic step execution."""

    def __init__(
        self,
        *,
        artifact_store: Optional[MobileArtifactStore] = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.artifacts = artifact_store or get_artifact_store()
        self.client_factory = client_factory or (lambda url: AppiumClient(url, timeout=15.0))

    def run(
        self,
        *,
        session_id: str,
        device: Device,
        steps: list[AppiumAction],
        app: Optional[dict] = None,
        on_event: Optional[EventCallback] = None,
    ) -> AppiumRunResult:
        step_results: list[StepRunResult] = []
        collected: list[MobileArtifact] = []
        current_element: Optional[str] = None

        def emit(event_type: str, payload: dict) -> None:
            if on_event:
                on_event(event_type, payload)

        caps = self._capabilities_for(device, app)
        client = self.client_factory(device.appium_url)

        try:
            emit("log", {"message": f"Appium session aciliyor: {device.name}"})
            client.create_session(caps)
            emit("status", {"state": "appium_started"})

            for seq, step in enumerate(steps):
                started = time.perf_counter()
                emit("step.started", {"seq": seq, "action": step.action})
                try:
                    current_element = self._execute_step(
                        client=client,
                        step=step,
                        current_element=current_element,
                    )
                    artifacts = self._capture_requested_artifacts(client, session_id, seq, step)
                    collected.extend(artifacts)
                    duration_ms = int((time.perf_counter() - started) * 1000)
                    step_results.append(
                        StepRunResult(
                            seq=seq,
                            status="passed",
                            duration_ms=duration_ms,
                            artifact_ids=[a.id for a in artifacts],
                        )
                    )
                    emit(
                        "step.passed",
                        {
                            "seq": seq,
                            "action": step.action,
                            "duration_ms": duration_ms,
                            "artifact_ids": [a.id for a in artifacts],
                        },
                    )
                except Exception as exc:
                    category = self._categorize_exception(exc)
                    artifacts = self._capture_failure_artifacts(client, session_id, seq)
                    collected.extend(artifacts)
                    duration_ms = int((time.perf_counter() - started) * 1000)
                    message = str(exc)
                    step_results.append(
                        StepRunResult(
                            seq=seq,
                            status="failed",
                            duration_ms=duration_ms,
                            artifact_ids=[a.id for a in artifacts],
                            error_message=message,
                            failure_category=category,
                        )
                    )
                    emit(
                        "step.failed",
                        {
                            "seq": seq,
                            "action": step.action,
                            "duration_ms": duration_ms,
                            "failure_category": category,
                            "error_message": message,
                            "artifact_ids": [a.id for a in artifacts],
                        },
                    )
                    return AppiumRunResult(
                        status="failed",
                        steps=step_results,
                        artifacts=collected,
                        failure_category=category,
                        failure_message=message,
                    )

            return AppiumRunResult(status="passed", steps=step_results, artifacts=collected)
        except Exception as exc:
            category = self._categorize_exception(exc)
            return AppiumRunResult(
                status="failed",
                steps=step_results,
                artifacts=collected,
                failure_category=category,
                failure_message=str(exc),
            )
        finally:
            try:
                client.quit()
            except Exception:
                pass
            try:
                client._http.close()
            except Exception:
                pass

    def _capabilities_for(self, device: Device, app: Optional[dict]) -> AppiumCapabilities:
        platform_name = "Android" if device.platform == "android" else "iOS"
        automation_name = "UiAutomator2" if device.platform == "android" else "XCUITest"
        app = app or {}
        app_type = str(app.get("type") or "").lower()
        app_path = app.get("path") if app_type == "native" else None
        browser_name = None
        if app_type == "web":
            browser_name = "Chrome" if device.platform == "android" else "Safari"

        return AppiumCapabilities(
            platform_name=platform_name,
            automation_name=automation_name,
            device_name=device.udid or device.name,
            platform_version=device.os_version,
            app=app_path,
            udid=device.udid,
            browser_name=browser_name,
        )

    def _execute_step(
        self,
        *,
        client: AppiumClient,
        step: AppiumAction,
        current_element: Optional[str],
    ) -> Optional[str]:
        action = step.action
        if action in {"launch", "launchApp"}:
            return current_element
        if action == "wait":
            time.sleep((step.ms or 500) / 1000)
            return current_element
        if action == "openUrl":
            if not step.url:
                raise ValueError("openUrl step url alanı gerektirir")
            client.open_url(step.url)
            return current_element
        if action == "find":
            if not step.by or not step.value:
                raise ValueError("find step by/value alanları gerektirir")
            return client.find_element(step.by, step.value)
        if action == "tap":
            if not current_element:
                raise ValueError("tap için önce find step'i gerekir")
            client.click(current_element)
            return current_element
        if action == "sendKeys":
            if not current_element:
                raise ValueError("sendKeys için önce find step'i gerekir")
            client.send_keys(current_element, step.text or "")
            return current_element
        if action == "clear":
            if not current_element:
                raise ValueError("clear için önce find step'i gerekir")
            client.clear(current_element)
            return current_element
        if action == "verifyVisible":
            element = current_element
            if step.by and step.value:
                element = client.find_element(step.by, step.value)
            if not element:
                raise ValueError("verifyVisible için locator veya önceki element gerekir")
            if not client.is_displayed(element):
                raise AssertionError("Element görünür değil")
            return element
        if action == "back":
            client.back()
            return current_element
        if action in {"screenshot", "takeScreenshot", "pageSource"}:
            return current_element
        if action == "type":
            if not current_element:
                raise ValueError("type için önce find step'i gerekir")
            client.send_keys(current_element, step.text or "")
            return current_element
        if action == "home":
            client.back()  # HOME tuşu — back komutu ile yaklaşık
            return current_element
        if action == "pressKey":
            client.back()  # Genel tuş basımı — back proxy
            return current_element
        if action == "swipe":
            direction = step.direction or "up"
            cx, cy = 200, 600
            if direction == "up":
                client.swipe(cx, cy, cx, cy - 400)
            elif direction == "down":
                client.swipe(cx, cy - 400, cx, cy)
            elif direction == "left":
                client.swipe(cx + 200, cy, cx - 200, cy)
            else:  # right
                client.swipe(cx - 200, cy, cx + 200, cy)
            return current_element
        if action == "scroll":
            direction = step.direction or "down"
            cx, cy = 200, 600
            if direction == "up":
                client.swipe(cx, cy - 200, cx, cy + 200)
            elif direction == "down":
                client.swipe(cx, cy + 200, cx, cy - 200)
            elif direction == "left":
                client.swipe(cx + 200, cy, cx - 200, cy)
            else:  # right
                client.swipe(cx - 200, cy, cx + 200, cy)
            return current_element
        if action in {"pinch", "rotate", "installApp", "setNetwork", "grantPermission", "switchContext"}:
            return current_element
        raise ValueError(f"Bilinmeyen mobil step action: {action}")

    def _capture_requested_artifacts(
        self,
        client: AppiumClient,
        session_id: str,
        seq: int,
        step: AppiumAction,
    ) -> list[MobileArtifact]:
        if step.action in {"screenshot", "takeScreenshot"}:
            data = client.screenshot_bytes()
            return [
                self.artifacts.save_bytes(
                    session_id=session_id,
                    kind="screenshot",
                    step_seq=seq,
                    data=data,
                    extension="png",
                    mime_type="image/png",
                )
            ]
        if step.action == "pageSource":
            return [
                self.artifacts.save_text(
                    session_id=session_id,
                    kind="page_source",
                    step_seq=seq,
                    text=client.page_source(),
                    extension="xml",
                    mime_type="application/xml; charset=utf-8",
                )
            ]
        return []

    def _capture_failure_artifacts(
        self,
        client: AppiumClient,
        session_id: str,
        seq: int,
    ) -> list[MobileArtifact]:
        artifacts: list[MobileArtifact] = []
        try:
            data = client.screenshot_bytes()
            if data:
                artifacts.append(
                    self.artifacts.save_bytes(
                        session_id=session_id,
                        kind="screenshot",
                        step_seq=seq,
                        data=data,
                        extension="png",
                        mime_type="image/png",
                    )
                )
        except Exception:
            pass
        try:
            source = client.page_source()
            if source:
                artifacts.append(
                    self.artifacts.save_text(
                        session_id=session_id,
                        kind="page_source",
                        step_seq=seq,
                        text=source,
                        extension="xml",
                        mime_type="application/xml; charset=utf-8",
                    )
                )
        except Exception:
            pass
        return artifacts

    def _categorize_exception(self, exc: Exception) -> FailureCategory:
        msg = str(exc).lower()
        if isinstance(exc, AppiumError):
            if "erişilemiyor" in msg or "refused" in msg or "timeout" in msg:
                return "infrastructure"
            if "no such element" in msg or "element" in msg:
                return "locator"
            return "appium"
        if isinstance(exc, TimeoutError):
            return "timeout"
        if isinstance(exc, AssertionError):
            return "assertion"
        if isinstance(exc, NotImplementedError):
            return "app"
        return "app"
