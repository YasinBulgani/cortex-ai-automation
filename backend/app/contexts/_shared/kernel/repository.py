"""
Repository pattern.

Aggregate persistence abstraction. SQLAlchemy detayını domain'den gizler.
Domain layer Repository protocol'ünü kullanır, infrastructure implementasyonu enjekte edilir.
"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar
from .aggregate import AggregateRoot
from .identifiers import EntityId

TId = TypeVar("TId", bound=EntityId)
TAggregate = TypeVar("TAggregate", bound=AggregateRoot)


class Repository(Protocol, Generic[TId, TAggregate]):
    """
    Generic repository contract.

    Kullanım:
        class UserRepository(Repository[UserId, User], Protocol):
            async def find_by_email(self, email: Email) -> User | None: ...

        # Infrastructure layer'da concrete implementation:
        class SqlAlchemyUserRepository:
            async def get(self, id: UserId) -> User | None:
                row = await self.session.scalar(
                    select(UserRow).where(UserRow.id == id.value)
                )
                return row.to_aggregate() if row else None
    """

    async def get(self, id: TId) -> TAggregate | None: ...
    async def save(self, aggregate: TAggregate) -> None: ...
    async def delete(self, id: TId) -> None: ...
