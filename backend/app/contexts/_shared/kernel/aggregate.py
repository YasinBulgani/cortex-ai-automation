"""
Aggregate Root pattern.

Aggregate = consistency boundary. Domain logic'i içerir.
Event collect eder, repository commit'inde event bus'a yayınlar.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from .events import DomainEvent
from .identifiers import EntityId

TId = TypeVar("TId", bound=EntityId)


class AggregateRoot(Generic[TId]):
    """
    Aggregate root base class.

    Kullanım:
        class User(AggregateRoot[UserId]):
            def __init__(self, id: UserId, email: str):
                super().__init__(id)
                self.email = email

            def change_email(self, new_email: str) -> None:
                old = self.email
                self.email = new_email
                self._record_event(UserEmailChanged(
                    aggregate_id=self.id.value,
                    old_email=old,
                    new_email=new_email,
                ))

        # Repository.save() içinde:
        events = user.pull_events()
        outbox.publish(events)
    """

    def __init__(self, id: TId):
        self.id: TId = id
        self._events: list[DomainEvent] = []
        self._version: int = 0

    def _record_event(self, event: DomainEvent) -> None:
        """Subclass'lar domain logic içinden çağırır."""
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Repository commit'te çağrılır — event'leri toplar ve listeyi temizler."""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def version(self) -> int:
        """Optimistic concurrency control için."""
        return self._version

    def _increment_version(self) -> None:
        self._version += 1
