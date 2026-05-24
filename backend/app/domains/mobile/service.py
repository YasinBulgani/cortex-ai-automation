"""Mobile automation domain service facade.

Thin facade over the mobile sub-modules (``device_broker``,
``orchestrator``, ``llm_stepper``, ``artifact_store``).  Non-HTTP
callers (tests, background tasks, other domains) import from here.

Exposed API
-----------
get_device_list() -> list[Device]
    Return all registered virtual and physical devices.

start_mobile_session(req) -> list[Session]
    Start a parallel Appium session suite; returns running Session objects.

generate_steps_from_prompt(prompt, platform, page_source, app_package)
    -> StepGenerationResponse
    Call the LLM stepper to convert a natural-language prompt into
    Appium test steps.

list_recent_sessions(limit) -> list[Session]
    Return the most recent session records from the in-memory store.
"""
from __future__ import annotations

from typing import List, Optional

from .device_broker import get_broker
from .llm_stepper import generate_steps
from .orchestrator import get_store, start_suite
from .schemas import Device, Session, SessionCreate, StepGenerationResponse


def get_device_list() -> List[Device]:
    """Return all registered devices (virtual + physical).

    Delegates to ``DeviceBroker.list``.  The list reflects the current
    state stored in the in-memory broker; call ``probe_devices()`` first
    if you need live Appium readiness data.
    """
    return get_broker().list()


async def start_mobile_session(config: SessionCreate) -> List[Session]:
    """Start a parallel Appium session suite.

    Args:
        config: ``SessionCreate`` schema that specifies the scenario set,
                desired device filters, and parallelism settings.

    Returns:
        List of ``Session`` objects for the launched sessions.  Returns
        an empty list if no suitable device was available.
    """
    return await start_suite(config)


def generate_steps_from_prompt(
    prompt: str,
    platform: str = "android",
    page_source: Optional[str] = None,
    app_package: Optional[str] = None,
) -> StepGenerationResponse:
    """Convert a natural-language prompt into Appium test steps via LLM.

    Args:
        prompt:      Free-text description of the test flow (Turkish or English).
        platform:    ``"android"`` or ``"ios"``.
        page_source: Optional XML page source to give the LLM layout context.
        app_package: Optional app package/bundle identifier.

    Returns:
        ``StepGenerationResponse`` with a list of ``AppiumStep`` objects
        and a ``confidence`` score.
    """
    return generate_steps(
        prompt=prompt,
        platform=platform,
        page_source=page_source,
        app_package=app_package,
    )


def list_recent_sessions(limit: int = 40) -> List[Session]:
    """Return the most recent session records from the session store.

    Args:
        limit: Maximum number of records to return (default 40).
    """
    return get_store().list_recent(limit=limit)
