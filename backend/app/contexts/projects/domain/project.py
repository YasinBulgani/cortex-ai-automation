"""
Project aggregate.

Business rules:
- Project name not empty (1-255 chars)
- Once archived, immutable (except restore)
- Product family tied to project lifecycle
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.contexts._shared.kernel import AggregateRoot, EntityId, ValueObject

from .events import (
    ProjectArchived,
    ProjectCreated,
    ProjectProductFamilyAssigned,
    ProjectRenamed,
    ProjectRestored,
)


@dataclass(frozen=True, slots=True)
class ProjectId(EntityId):
    """Strongly-typed project ID."""
    pass


class ProductFamily(str, Enum):
    ONE          = "one"
    STUDIO       = "studio"
    SERVICE      = "service"
    WEB          = "web"
    MOBILE       = "mobile"
    DATA         = "data"
    INTELLIGENCE = "intelligence"
    NEXUS_CODE   = "nexus-code"


class ProjectStatus(str, Enum):
    ACTIVE   = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ProjectName(ValueObject):
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Proje adı boş olamaz")
        if len(self.value) > 255:
            raise ValueError("Proje adı 255 karakteri aşamaz")

    def __str__(self) -> str:
        return self.value


class Project(AggregateRoot[ProjectId]):
    """Project aggregate root."""

    def __init__(
        self,
        id: ProjectId,
        name: ProjectName,
        description: str = "",
        base_url: str = "",
        product_family: ProductFamily | None = None,
        status: ProjectStatus = ProjectStatus.ACTIVE,
    ):
        super().__init__(id)
        self.name = name
        self.description = description
        self.base_url = base_url
        self.product_family = product_family
        self.status = status

    # ─── Factory ────────────────────────────────────────────────────
    @classmethod
    def create(
        cls,
        name: ProjectName,
        description: str = "",
        base_url: str = "",
        product_family: ProductFamily | None = None,
    ) -> "Project":
        project = cls(
            id=ProjectId.new(),
            name=name,
            description=description,
            base_url=base_url,
            product_family=product_family,
            status=ProjectStatus.ACTIVE,
        )
        project._record_event(ProjectCreated(
            aggregate_id=project.id.value,
            name=str(name),
            product_family=product_family.value if product_family else None,
        ))
        return project

    # ─── Behavior ────────────────────────────────────────────────────
    def rename(self, new_name: ProjectName) -> None:
        if new_name == self.name:
            return
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Arşivlenmiş proje yeniden adlandırılamaz")
        old = self.name
        self.name = new_name
        self._record_event(ProjectRenamed(
            aggregate_id=self.id.value,
            old_name=str(old),
            new_name=str(new_name),
        ))

    def archive(self, reason: str = "") -> None:
        if self.status == ProjectStatus.ARCHIVED:
            return
        self.status = ProjectStatus.ARCHIVED
        self._record_event(ProjectArchived(
            aggregate_id=self.id.value,
            reason=reason,
        ))

    def restore(self) -> None:
        if self.status == ProjectStatus.ACTIVE:
            return
        self.status = ProjectStatus.ACTIVE
        self._record_event(ProjectRestored(
            aggregate_id=self.id.value,
        ))

    def assign_product_family(self, family: ProductFamily) -> None:
        if self.product_family == family:
            return
        if self.status == ProjectStatus.ARCHIVED:
            raise ValueError("Arşivlenmiş projede ürün ailesi değiştirilemez")
        old = self.product_family
        self.product_family = family
        self._record_event(ProjectProductFamilyAssigned(
            aggregate_id=self.id.value,
            old_family=old.value if old else None,
            new_family=family.value,
        ))
