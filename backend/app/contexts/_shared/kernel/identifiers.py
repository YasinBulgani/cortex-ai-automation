"""
Strongly-typed entity identifiers.

Hata: `def get_user(id: str)` — herhangi bir string geçilebilir.
Doğru: `def get_user(id: UserId)` — sadece UserId geçer, compile-time güvenlik.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar
from uuid import UUID, uuid4

T = TypeVar("T", bound="EntityId")


@dataclass(frozen=True, slots=True)
class EntityId:
    """
    Base class for strongly-typed entity IDs.

    Kullanım:
        class UserId(EntityId): pass
        class ProjectId(EntityId): pass

        # Bu çalışmaz (compile-time hata):
        user_id: UserId = ProjectId(uuid4())  # type error
    """

    value: UUID

    def __post_init__(self) -> None:
        if isinstance(self.value, EntityId):
            object.__setattr__(self, "value", self.value.value)

    @classmethod
    def new(cls: type[T]) -> T:
        return cls(value=uuid4())

    @classmethod
    def from_str(cls: type[T], value: str) -> T:
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)
