"""Scenarios context domain events."""

from __future__ import annotations
from dataclasses import dataclass

from app.contexts._shared.kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class ScenarioCreated(DomainEvent):
    project_id: str = ""
    title: str = ""


@dataclass(frozen=True, slots=True)
class ScenarioStepAdded(DomainEvent):
    step_type: str = ""
    text: str = ""
    order: int = 0


@dataclass(frozen=True, slots=True)
class ScenarioStepRemoved(DomainEvent):
    order: int = 0


@dataclass(frozen=True, slots=True)
class ScenarioApproved(DomainEvent):
    approver: str = ""


@dataclass(frozen=True, slots=True)
class ScenarioRejected(DomainEvent):
    reviewer: str = ""
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ScenarioPublished(DomainEvent):
    step_count: int = 0


@dataclass(frozen=True, slots=True)
class ScenarioArchived(DomainEvent):
    pass
