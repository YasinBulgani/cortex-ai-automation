"""
SQLAlchemy implementation of ScenarioRepository.

Postgres-backed. ORM <-> domain çeviri burada izole. Domain layer SQLAlchemy
hakkında hiçbir şey bilmez.

Steps JSONB sütununda saklanır — her step {type, text, order} dict.

Migration: alembic revision (yeni tablo `scn_scenarios`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Column, DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.contexts.scenarios.application import ScenarioRepository
from app.contexts.scenarios.domain import (
    Scenario,
    ScenarioId,
    ScenarioStatus,
    ScenarioStep,
    ScenarioTitle,
    StepType,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


Base = declarative_base()


class ScenarioRow(Base):
    """
    Scenarios tablosu.

    Index'ler:
      - id (pk)
      - project_id (list_for_project sorgusu için)
      - status (filtering için)
    """

    __tablename__ = "scn_scenarios"

    id          = Column(PG_UUID(as_uuid=True), primary_key=True)
    project_id  = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    title       = Column(String(500), nullable=False)
    status      = Column(String(20), nullable=False, default=ScenarioStatus.DRAFT.value, index=True)
    steps       = Column(JSONB, nullable=False, default=list)
    version     = Column("agg_version", String(20), nullable=False, default="0")
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    @classmethod
    def from_aggregate(cls, scenario: Scenario) -> "ScenarioRow":
        return cls(
            id=scenario.id.value,
            project_id=scenario.project_id,
            title=str(scenario.title),
            status=scenario.status.value,
            steps=_steps_to_json(scenario.steps),
            version=str(scenario.version),
        )

    def update_from_aggregate(self, scenario: Scenario) -> None:
        self.title = str(scenario.title)
        self.status = scenario.status.value
        self.steps = _steps_to_json(scenario.steps)
        self.version = str(scenario.version)

    def to_aggregate(self) -> Scenario:
        return Scenario(
            id=ScenarioId(self.id),
            project_id=self.project_id,
            title=ScenarioTitle(self.title),
            status=ScenarioStatus(self.status),
            steps=_json_to_steps(self.steps or []),
        )


def _steps_to_json(steps: list[ScenarioStep]) -> list[dict[str, Any]]:
    return [{"type": s.type.value, "text": s.text, "order": s.order} for s in steps]


def _json_to_steps(data: list[dict[str, Any]]) -> list[ScenarioStep]:
    return [ScenarioStep(type=StepType(d["type"]), text=d["text"], order=d["order"]) for d in data]


class SqlAlchemyScenarioRepository(ScenarioRepository):
    """ScenarioRepository PostgreSQL implementation (async)."""

    def __init__(self, session: "AsyncSession"):
        self.session = session

    async def get(self, scenario_id: ScenarioId) -> Scenario | None:
        row = await self.session.get(ScenarioRow, scenario_id.value)
        return row.to_aggregate() if row else None

    async def list_for_project(self, project_id: UUID, *, limit: int = 50) -> list[Scenario]:
        stmt = (
            select(ScenarioRow)
            .where(ScenarioRow.project_id == project_id)
            .order_by(ScenarioRow.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row.to_aggregate() for row in result.scalars().all()]

    async def save(self, scenario: Scenario) -> None:
        """Upsert — yoksa insert, varsa update.

        Commit caller'ın sorumluluğunda (outbox entry'leriyle aynı tx'te
        olabilsin diye).
        """
        existing = await self.session.get(ScenarioRow, scenario.id.value)
        if existing is None:
            self.session.add(ScenarioRow.from_aggregate(scenario))
        else:
            existing.update_from_aggregate(scenario)
