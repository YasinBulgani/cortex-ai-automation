"""
Scenario aggregate — test senaryosu.

State machine:
    DRAFT → REVIEW → APPROVED → PUBLISHED
                  ↘ REJECTED → DRAFT
                                ↘ ARCHIVED

Business rules:
- Boş senaryo publish edilemez
- Approved sonrası içerik değişikliği yeni review gerektirir
- Published senaryo değiştirilemez, sadece yeni versiyon yaratılır
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.contexts._shared.kernel import AggregateRoot, EntityId, ValueObject

from .events import (
    ScenarioApproved,
    ScenarioArchived,
    ScenarioCreated,
    ScenarioPublished,
    ScenarioRejected,
    ScenarioStepAdded,
    ScenarioStepRemoved,
)


@dataclass(frozen=True, slots=True)
class ScenarioId(EntityId):
    pass


class ScenarioStatus(str, Enum):
    DRAFT     = "draft"
    REVIEW    = "review"
    APPROVED  = "approved"
    PUBLISHED = "published"
    REJECTED  = "rejected"
    ARCHIVED  = "archived"


class StepType(str, Enum):
    GIVEN = "given"
    WHEN  = "when"
    THEN  = "then"
    AND   = "and"
    BUT   = "but"


@dataclass(frozen=True, slots=True)
class ScenarioTitle(ValueObject):
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Başlık boş olamaz")
        if len(self.value) > 500:
            raise ValueError("Başlık 500 karakteri aşamaz")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ScenarioStep(ValueObject):
    type: StepType
    text: str
    order: int

    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("Step metni boş olamaz")
        if self.order < 0:
            raise ValueError("Order negatif olamaz")


class Scenario(AggregateRoot[ScenarioId]):
    """Test scenario aggregate."""

    # Allowed state transitions
    _TRANSITIONS: dict[ScenarioStatus, set[ScenarioStatus]] = {
        ScenarioStatus.DRAFT:     {ScenarioStatus.REVIEW, ScenarioStatus.ARCHIVED},
        ScenarioStatus.REVIEW:    {ScenarioStatus.APPROVED, ScenarioStatus.REJECTED, ScenarioStatus.DRAFT},
        ScenarioStatus.APPROVED:  {ScenarioStatus.PUBLISHED, ScenarioStatus.ARCHIVED, ScenarioStatus.DRAFT},
        ScenarioStatus.PUBLISHED: {ScenarioStatus.ARCHIVED},
        ScenarioStatus.REJECTED:  {ScenarioStatus.DRAFT, ScenarioStatus.ARCHIVED},
        ScenarioStatus.ARCHIVED:  set(),  # Terminal
    }

    def __init__(
        self,
        id: ScenarioId,
        project_id: UUID,
        title: ScenarioTitle,
        status: ScenarioStatus = ScenarioStatus.DRAFT,
        steps: list[ScenarioStep] | None = None,
    ):
        super().__init__(id)
        self.project_id = project_id
        self.title = title
        self.status = status
        self.steps: list[ScenarioStep] = steps or []

    # ─── Factory ────────────────────────────────────────────────────
    @classmethod
    def create(cls, project_id: UUID, title: ScenarioTitle) -> "Scenario":
        s = cls(id=ScenarioId.new(), project_id=project_id, title=title)
        s._record_event(ScenarioCreated(
            aggregate_id=s.id.value,
            project_id=str(project_id),
            title=str(title),
        ))
        return s

    # ─── Steps ──────────────────────────────────────────────────────
    def add_step(self, step: ScenarioStep) -> None:
        if self.status not in (ScenarioStatus.DRAFT, ScenarioStatus.REJECTED):
            raise ValueError(f"Step eklenemez, status: {self.status.value}")
        # Order conflict
        if any(s.order == step.order for s in self.steps):
            raise ValueError(f"Order {step.order} kullanımda")
        self.steps.append(step)
        self.steps.sort(key=lambda s: s.order)
        self._record_event(ScenarioStepAdded(
            aggregate_id=self.id.value,
            step_type=step.type.value,
            text=step.text,
            order=step.order,
        ))

    def remove_step(self, order: int) -> None:
        if self.status not in (ScenarioStatus.DRAFT, ScenarioStatus.REJECTED):
            raise ValueError(f"Step silinemez, status: {self.status.value}")
        before = len(self.steps)
        self.steps = [s for s in self.steps if s.order != order]
        if len(self.steps) == before:
            return  # No-op
        self._record_event(ScenarioStepRemoved(
            aggregate_id=self.id.value,
            order=order,
        ))

    # ─── State transitions ──────────────────────────────────────────
    def _transition_to(self, new_status: ScenarioStatus) -> None:
        if new_status not in self._TRANSITIONS.get(self.status, set()):
            raise ValueError(
                f"Geçersiz state transition: {self.status.value} → {new_status.value}"
            )
        self.status = new_status

    def submit_for_review(self) -> None:
        if not self.steps:
            raise ValueError("Step'siz senaryo review'a gönderilemez")
        self._transition_to(ScenarioStatus.REVIEW)

    def approve(self, approver: str) -> None:
        self._transition_to(ScenarioStatus.APPROVED)
        self._record_event(ScenarioApproved(
            aggregate_id=self.id.value,
            approver=approver,
        ))

    def reject(self, reviewer: str, reason: str) -> None:
        self._transition_to(ScenarioStatus.REJECTED)
        self._record_event(ScenarioRejected(
            aggregate_id=self.id.value,
            reviewer=reviewer,
            reason=reason,
        ))

    def publish(self) -> None:
        if self.status != ScenarioStatus.APPROVED:
            raise ValueError("Sadece onaylı senaryo yayımlanabilir")
        if not self.steps:
            raise ValueError("Boş senaryo yayımlanamaz")
        self._transition_to(ScenarioStatus.PUBLISHED)
        self._record_event(ScenarioPublished(
            aggregate_id=self.id.value,
            step_count=len(self.steps),
        ))

    def archive(self) -> None:
        if self.status == ScenarioStatus.ARCHIVED:
            return
        self._transition_to(ScenarioStatus.ARCHIVED)
        self._record_event(ScenarioArchived(
            aggregate_id=self.id.value,
        ))
