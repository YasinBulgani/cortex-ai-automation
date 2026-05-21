"""
Projects context domain events.
"""

from __future__ import annotations
from dataclasses import dataclass

from app.contexts._shared.kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class ProjectCreated(DomainEvent):
    name: str = ""
    product_family: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectRenamed(DomainEvent):
    old_name: str = ""
    new_name: str = ""


@dataclass(frozen=True, slots=True)
class ProjectArchived(DomainEvent):
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ProjectRestored(DomainEvent):
    pass


@dataclass(frozen=True, slots=True)
class ProjectProductFamilyAssigned(DomainEvent):
    old_family: str | None = None
    new_family: str = ""
