"""Public service facade for the mobile domain.

Wraps the session orchestrator and Appium runner so that callers outside this
domain only need to import from here.
"""
from __future__ import annotations

import logging

from app.domains.mobile.appium_runner import (
    AppiumRunResult,
    AppiumRunner,
    StepRunResult,
)
from app.domains.mobile.orchestrator import (
    SessionStore,
    get_store,
)

logger = logging.getLogger(__name__)

__all__ = [
    # orchestrator
    "SessionStore",
    "get_store",
    # appium_runner
    "AppiumRunner",
    "AppiumRunResult",
    "StepRunResult",
    # stubs
    "list_devices",
    "run_mobile_test",
]


def list_devices(*, project_id: str | None = None) -> list[dict]:
    """Return the current device inventory from the device broker.

    Args:
        project_id: Optional project scope — some deployments partition devices
            per project.

    Returns:
        List of device dicts with ``id``, ``platform``, ``version``, and
        ``available`` keys.

    Raises:
        NotImplementedError: Until device broker listing is exposed here.
    """
    raise NotImplementedError(
        "TODO: implement list_devices — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def run_mobile_test(
    scenario_name: str,
    *,
    device_id: str,
    project_id: str,
    mode: str = "simulation",
) -> dict:
    """Run a mobile test scenario on the specified device.

    Args:
        scenario_name: Name of the scenario to execute.
        device_id: Target device identifier from the broker.
        project_id: The owning project's identifier.
        mode: ``"simulation"`` (default) or ``"appium"`` for a real run.

    Returns:
        A dict with ``session_id``, ``status``, and ``artifact_ids``.

    Raises:
        NotImplementedError: Until end-to-end mobile test execution is wired up.
    """
    raise NotImplementedError(
        "TODO: implement run_mobile_test — see docs/planning/END_USER_GAPS_PLAN.md"
    )
