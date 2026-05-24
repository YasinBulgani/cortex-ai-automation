"""External Device Farm Adapters.

Provides pluggable integration with cloud device farm providers:
  - AWS Device Farm
  - BrowserStack App Automate
  - Sauce Labs (Sauce Real Device Cloud)
  - Local / in-process (default — existing DeviceBroker)

Each adapter implements the ``DeviceFarmAdapter`` protocol.  The
``DeviceFarmRouter`` selects the active provider via the ``DEVICE_FARM_PROVIDER``
environment variable (default: ``local``).

Environment variables
---------------------
DEVICE_FARM_PROVIDER      "local" | "aws" | "browserstack" | "saucelabs"

AWS Device Farm:
  AWS_DEVICE_FARM_PROJECT_ARN   AWS Device Farm project ARN
  AWS_DEFAULT_REGION            e.g. "us-west-2"
  (Uses boto3 — must be installed and credentials configured)

BrowserStack:
  BROWSERSTACK_USERNAME         BrowserStack username
  BROWSERSTACK_ACCESS_KEY       BrowserStack access key
  BROWSERSTACK_APP_URL          bs://... app URL uploaded to BrowserStack

Sauce Labs:
  SAUCE_USERNAME                Sauce Labs username
  SAUCE_ACCESS_KEY              Sauce Labs access key
  SAUCE_REGION                  "us-west-1" | "eu-central-1" | "apac-southeast-1"
  SAUCE_APP_ID                  storage:filename=...  app ID
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


# ── Device record (provider-agnostic) ────────────────────────────────────────


@dataclass
class FarmDevice:
    """A device available on an external farm."""
    id: str
    name: str
    platform: str          # "android" | "ios"
    os_version: str
    provider: str          # "aws" | "browserstack" | "saucelabs" | "local"
    available: bool = True
    extra: dict = field(default_factory=dict)


@dataclass
class FarmSession:
    """An active test session on an external farm."""
    session_id: str
    device_id: str
    provider: str
    status: str            # "queued" | "running" | "passed" | "failed" | "error"
    appium_endpoint: Optional[str] = None
    video_url: Optional[str] = None
    report_url: Optional[str] = None
    extra: dict = field(default_factory=dict)


# ── Protocol ──────────────────────────────────────────────────────────────────


class DeviceFarmAdapter(Protocol):
    """Interface all farm adapters must satisfy."""

    @property
    def name(self) -> str: ...

    def list_devices(
        self,
        platform: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> list[FarmDevice]:
        """Return available devices, optionally filtered."""
        ...

    def start_session(
        self,
        device_id: str,
        app_path: str,
        capabilities: dict[str, Any],
    ) -> FarmSession:
        """Start a test session on the given device. Returns immediately."""
        ...

    def get_session(self, session_id: str) -> FarmSession:
        """Return current session state."""
        ...

    def stop_session(self, session_id: str) -> None:
        """Terminate a running session."""
        ...

    def health(self) -> dict[str, Any]:
        """Return provider health info."""
        ...


# ── AWS Device Farm adapter ───────────────────────────────────────────────────


class AWSDeviceFarmAdapter:
    """AWS Device Farm integration.

    Requires:
      - boto3 installed (``pip install boto3``)
      - AWS credentials configured (env vars / ~/.aws/credentials / IAM role)
      - AWS_DEVICE_FARM_PROJECT_ARN set

    Note: AWS Device Farm is only available in us-west-2.
    """

    name = "aws"

    def __init__(self) -> None:
        self._project_arn = os.getenv("AWS_DEVICE_FARM_PROJECT_ARN", "")
        self._region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("devicefarm", region_name="us-west-2")
            except ImportError as exc:
                raise RuntimeError("boto3 is required for AWS Device Farm adapter") from exc
        return self._client

    def list_devices(
        self,
        platform: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> list[FarmDevice]:
        try:
            client = self._get_client()
            response = client.list_devices()
            devices: list[FarmDevice] = []
            for d in response.get("devices", []):
                plat = d.get("platform", "").lower()
                if platform and plat != platform.lower():
                    continue
                ver = d.get("os", "")
                if os_version and ver != os_version:
                    continue
                devices.append(FarmDevice(
                    id=d["arn"],
                    name=d.get("name", "Unknown"),
                    platform=plat,
                    os_version=ver,
                    provider=self.name,
                    available=d.get("availability") == "AVAILABLE",
                    extra={"form_factor": d.get("formFactor"), "arn": d["arn"]},
                ))
            return devices
        except Exception as exc:
            logger.warning("AWSDeviceFarm.list_devices failed: %s", exc)
            return []

    def start_session(
        self,
        device_id: str,
        app_path: str,
        capabilities: dict[str, Any],
    ) -> FarmSession:
        try:
            client = self._get_client()
            # Upload app if local path
            app_arn = app_path
            if not app_path.startswith("arn:"):
                upload = client.create_upload(
                    projectArn=self._project_arn,
                    name=os.path.basename(app_path),
                    type="ANDROID_APP" if app_path.endswith(".apk") else "IOS_APP",
                )
                import urllib.request
                urllib.request.urlretrieve(app_path, upload["upload"]["url"])  # type: ignore[no-untyped-call]
                app_arn = upload["upload"]["arn"]

            run = client.schedule_run(
                projectArn=self._project_arn,
                appArn=app_arn,
                devicePoolArn=device_id,  # In AWS, device_id is the pool ARN
                name=capabilities.get("name", "Cortex Run"),
                test={"type": "APPIUM_PYTHON"},
            )
            run_arn = run["run"]["arn"]
            return FarmSession(
                session_id=run_arn,
                device_id=device_id,
                provider=self.name,
                status="queued",
                report_url=f"https://us-west-2.console.aws.amazon.com/devicefarm/home#/runs/{run_arn}",
                extra={"arn": run_arn},
            )
        except Exception as exc:
            logger.error("AWSDeviceFarm.start_session failed: %s", exc)
            return FarmSession(
                session_id="error",
                device_id=device_id,
                provider=self.name,
                status="error",
                extra={"error": str(exc)},
            )

    def get_session(self, session_id: str) -> FarmSession:
        try:
            client = self._get_client()
            run = client.get_run(arn=session_id)["run"]
            aws_status = run.get("status", "UNKNOWN")
            status_map = {
                "PENDING": "queued", "PENDING_CONCURRENCY": "queued",
                "RUNNING": "running", "COMPLETED": "passed",
                "ERRORED": "error", "FAILED": "failed",
            }
            return FarmSession(
                session_id=session_id,
                device_id=run.get("devicePoolArn", ""),
                provider=self.name,
                status=status_map.get(aws_status, "unknown"),
                extra={"aws_status": aws_status},
            )
        except Exception as exc:
            return FarmSession(session_id=session_id, device_id="", provider=self.name,
                               status="error", extra={"error": str(exc)})

    def stop_session(self, session_id: str) -> None:
        try:
            self._get_client().stop_run(arn=session_id)
        except Exception as exc:
            logger.warning("AWSDeviceFarm.stop_session failed: %s", exc)

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "project_arn": self._project_arn,
            "configured": bool(self._project_arn),
        }


# ── BrowserStack App Automate adapter ────────────────────────────────────────


class BrowserStackAdapter:
    """BrowserStack App Automate integration.

    Uses the REST API — no extra SDK required.
    """

    name = "browserstack"
    _BASE_URL = "https://api-cloud.browserstack.com/app-automate"

    def __init__(self) -> None:
        self._user = os.getenv("BROWSERSTACK_USERNAME", "")
        self._key = os.getenv("BROWSERSTACK_ACCESS_KEY", "")
        self._app_url = os.getenv("BROWSERSTACK_APP_URL", "")

    def _auth(self) -> tuple[str, str]:
        return (self._user, self._key)

    def list_devices(
        self,
        platform: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> list[FarmDevice]:
        try:
            import urllib.request
            import json as _json
            import base64

            token = base64.b64encode(f"{self._user}:{self._key}".encode()).decode()
            req = urllib.request.Request(
                f"{self._BASE_URL}/devices.json",
                headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: list[dict] = _json.loads(resp.read())

            devices: list[FarmDevice] = []
            for d in data:
                plat = "ios" if d.get("os") == "ios" else "android"
                if platform and plat != platform.lower():
                    continue
                ver = d.get("os_version", "")
                if os_version and ver != os_version:
                    continue
                devices.append(FarmDevice(
                    id=f"{d['device']}-{ver}",
                    name=d["device"],
                    platform=plat,
                    os_version=ver,
                    provider=self.name,
                    extra={"browser": d.get("browser"), "browser_version": d.get("browser_version")},
                ))
            return devices
        except Exception as exc:
            logger.warning("BrowserStack.list_devices failed: %s", exc)
            return []

    def start_session(
        self,
        device_id: str,
        app_path: str,
        capabilities: dict[str, Any],
    ) -> FarmSession:
        """Returns Appium endpoint URL for BrowserStack session."""
        try:
            device_name, os_version = device_id.rsplit("-", 1)
            appium_caps = {
                "app": self._app_url or app_path,
                "device": device_name,
                "os_version": os_version,
                "browserstack.user": self._user,
                "browserstack.key": self._key,
                **capabilities,
            }
            # BrowserStack sessions are initiated by pointing Appium at their hub
            endpoint = f"https://hub-cloud.browserstack.com/wd/hub"
            import uuid as _uuid
            session_id = str(_uuid.uuid4())
            return FarmSession(
                session_id=session_id,
                device_id=device_id,
                provider=self.name,
                status="queued",
                appium_endpoint=endpoint,
                extra={"capabilities": appium_caps},
            )
        except Exception as exc:
            return FarmSession(session_id="error", device_id=device_id, provider=self.name,
                               status="error", extra={"error": str(exc)})

    def get_session(self, session_id: str) -> FarmSession:
        try:
            import urllib.request
            import json as _json
            import base64

            token = base64.b64encode(f"{self._user}:{self._key}".encode()).decode()
            req = urllib.request.Request(
                f"{self._BASE_URL}/sessions/{session_id}.json",
                headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())

            automation_session = data.get("automation_session", {})
            status_map = {
                "running": "running", "passed": "passed", "failed": "failed",
                "timeout": "error", "error": "error",
            }
            return FarmSession(
                session_id=session_id,
                device_id=automation_session.get("device", ""),
                provider=self.name,
                status=status_map.get(automation_session.get("status", ""), "unknown"),
                video_url=automation_session.get("video_url"),
                report_url=f"https://app-automate.browserstack.com/builds/{automation_session.get('hashed_id')}",
                extra=automation_session,
            )
        except Exception as exc:
            return FarmSession(session_id=session_id, device_id="", provider=self.name,
                               status="error", extra={"error": str(exc)})

    def stop_session(self, session_id: str) -> None:
        try:
            import urllib.request
            import json as _json
            import base64

            token = base64.b64encode(f"{self._user}:{self._key}".encode()).decode()
            data = _json.dumps({"status": "passed", "reason": "stopped by cortex"}).encode()
            req = urllib.request.Request(
                f"{self._BASE_URL}/sessions/{session_id}.json",
                data=data,
                method="PUT",
                headers={
                    "Authorization": f"Basic {token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as exc:
            logger.warning("BrowserStack.stop_session failed: %s", exc)

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": bool(self._user and self._key),
            "app_url": self._app_url,
        }


# ── Sauce Labs adapter ────────────────────────────────────────────────────────


class SauceLabsAdapter:
    """Sauce Labs Real Device Cloud integration."""

    name = "saucelabs"

    def __init__(self) -> None:
        self._user = os.getenv("SAUCE_USERNAME", "")
        self._key = os.getenv("SAUCE_ACCESS_KEY", "")
        self._region = os.getenv("SAUCE_REGION", "us-west-1")
        self._app_id = os.getenv("SAUCE_APP_ID", "")

    @property
    def _api_base(self) -> str:
        return f"https://api.{self._region}.saucelabs.com"

    def list_devices(
        self,
        platform: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> list[FarmDevice]:
        try:
            import urllib.request
            import json as _json
            import base64

            token = base64.b64encode(f"{self._user}:{self._key}".encode()).decode()
            req = urllib.request.Request(
                f"{self._api_base}/v1/rdc/devices",
                headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())

            devices: list[FarmDevice] = []
            for d in data.get("entities", []):
                plat = d.get("os", "").lower()
                if platform and plat != platform:
                    continue
                devices.append(FarmDevice(
                    id=d["id"],
                    name=d.get("name", "Unknown"),
                    platform=plat,
                    os_version=d.get("osVersion", ""),
                    provider=self.name,
                    available=d.get("available", True),
                ))
            return devices
        except Exception as exc:
            logger.warning("SauceLabs.list_devices failed: %s", exc)
            return []

    def start_session(
        self,
        device_id: str,
        app_path: str,
        capabilities: dict[str, Any],
    ) -> FarmSession:
        import uuid as _uuid
        session_id = str(_uuid.uuid4())
        endpoint = (
            f"https://ondemand.{self._region}.saucelabs.com/wd/hub"
        )
        caps = {
            "platformName": "Android",
            "appium:app": self._app_id or app_path,
            "appium:deviceName": device_id,
            "sauce:options": {
                "username": self._user,
                "accessKey": self._key,
            },
            **capabilities,
        }
        return FarmSession(
            session_id=session_id,
            device_id=device_id,
            provider=self.name,
            status="queued",
            appium_endpoint=endpoint,
            extra={"capabilities": caps},
        )

    def get_session(self, session_id: str) -> FarmSession:
        try:
            import urllib.request
            import json as _json
            import base64

            token = base64.b64encode(f"{self._user}:{self._key}".encode()).decode()
            req = urllib.request.Request(
                f"{self._api_base}/v1/rdc/jobs/{session_id}",
                headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())

            status_map = {
                "in progress": "running", "complete": "passed",
                "error": "error", "failed": "failed",
            }
            return FarmSession(
                session_id=session_id,
                device_id=data.get("device_type", ""),
                provider=self.name,
                status=status_map.get(data.get("status", ""), "unknown"),
                video_url=data.get("video_url"),
                report_url=f"https://app.saucelabs.com/tests/{session_id}",
            )
        except Exception as exc:
            return FarmSession(session_id=session_id, device_id="", provider=self.name,
                               status="error", extra={"error": str(exc)})

    def stop_session(self, session_id: str) -> None:
        try:
            import urllib.request
            import json as _json
            import base64

            token = base64.b64encode(f"{self._user}:{self._key}".encode()).decode()
            data = _json.dumps({"passed": False}).encode()
            req = urllib.request.Request(
                f"{self._api_base}/v1/rdc/jobs/{session_id}",
                data=data,
                method="PUT",
                headers={
                    "Authorization": f"Basic {token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as exc:
            logger.warning("SauceLabs.stop_session failed: %s", exc)

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": bool(self._user and self._key),
            "region": self._region,
        }


# ── Farm router ───────────────────────────────────────────────────────────────


class DeviceFarmRouter:
    """Selects the active device farm adapter based on environment configuration.

    Usage:
        farm = get_device_farm()
        devices = farm.list_devices(platform="android")
        session = farm.start_session("device-id", "app.apk", {"name": "My Run"})
    """

    def __init__(self) -> None:
        self._provider = os.getenv("DEVICE_FARM_PROVIDER", "local").lower()
        self._adapter: DeviceFarmAdapter | None = None

    def _build_adapter(self) -> DeviceFarmAdapter:
        if self._provider == "aws":
            return AWSDeviceFarmAdapter()  # type: ignore[return-value]
        if self._provider == "browserstack":
            return BrowserStackAdapter()  # type: ignore[return-value]
        if self._provider == "saucelabs":
            return SauceLabsAdapter()  # type: ignore[return-value]
        # "local" — return a thin wrapper around the existing DeviceBroker
        return _LocalFarmAdapter()  # type: ignore[return-value]

    @property
    def adapter(self) -> DeviceFarmAdapter:
        if self._adapter is None:
            self._adapter = self._build_adapter()
        return self._adapter

    # Delegate to adapter
    def list_devices(self, platform=None, os_version=None) -> list[FarmDevice]:
        return self.adapter.list_devices(platform=platform, os_version=os_version)

    def start_session(self, device_id: str, app_path: str,
                      capabilities: dict) -> FarmSession:
        return self.adapter.start_session(device_id, app_path, capabilities)

    def get_session(self, session_id: str) -> FarmSession:
        return self.adapter.get_session(session_id)

    def stop_session(self, session_id: str) -> None:
        self.adapter.stop_session(session_id)

    def health(self) -> dict[str, Any]:
        return {"provider": self._provider, **self.adapter.health()}


class _LocalFarmAdapter:
    """Thin wrapper that exposes the in-process DeviceBroker as a FarmAdapter."""

    name = "local"

    def list_devices(self, platform=None, os_version=None) -> list[FarmDevice]:
        from .device_broker import get_broker

        broker = get_broker()
        devices = broker.list_devices()
        result = []
        for d in devices:
            if platform and d.platform != platform:
                continue
            if os_version and d.os_version != os_version:
                continue
            result.append(FarmDevice(
                id=d.id,
                name=d.name,
                platform=d.platform,
                os_version=d.os_version,
                provider=self.name,
                available=d.status.value == "idle",
            ))
        return result

    def start_session(self, device_id: str, app_path: str,
                      capabilities: dict) -> FarmSession:
        from .device_broker import get_broker

        broker = get_broker()
        dev = broker.get_device(device_id)
        if not dev:
            return FarmSession(session_id="error", device_id=device_id,
                               provider=self.name, status="error",
                               extra={"error": f"Device {device_id} not found"})
        return FarmSession(
            session_id=f"local-{device_id}",
            device_id=device_id,
            provider=self.name,
            status="running",
            appium_endpoint=f"http://localhost:{dev.appium_port}/wd/hub",
        )

    def get_session(self, session_id: str) -> FarmSession:
        return FarmSession(
            session_id=session_id,
            device_id=session_id.removeprefix("local-"),
            provider=self.name,
            status="running",
        )

    def stop_session(self, session_id: str) -> None:
        pass  # In-process sessions are ephemeral

    def health(self) -> dict[str, Any]:
        from .device_broker import get_broker

        broker = get_broker()
        devices = broker.list_devices()
        idle = sum(1 for d in devices if d.status.value == "idle")
        return {
            "provider": self.name,
            "total_devices": len(devices),
            "idle_devices": idle,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_farm_router: DeviceFarmRouter | None = None


def get_device_farm() -> DeviceFarmRouter:
    global _farm_router
    if _farm_router is None:
        _farm_router = DeviceFarmRouter()
    return _farm_router
