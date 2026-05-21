"""
User aggregate root + value objects.

Domain layer = pure business logic. Persistence detayı yok.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.contexts._shared.kernel import AggregateRoot, EntityId, ValueObject

from .events import (
    UserDeactivated,
    UserEmailChanged,
    UserLoggedIn,
    UserRegistered,
)


# ─── Value Objects ───────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class UserId(EntityId):
    """Strongly-typed user ID."""
    pass


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True, slots=True)
class Email(ValueObject):
    value: str

    def __post_init__(self):
        if not _EMAIL_RE.match(self.value):
            raise ValueError(f"Geçersiz e-posta: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class HashedPassword(ValueObject):
    """Always hashed — never raw."""
    hash: str

    def __post_init__(self):
        if len(self.hash) < 32:
            raise ValueError("Hash çok kısa — gerçek hash mı?")


# ─── Aggregate ───────────────────────────────────────────────────────────

class User(AggregateRoot[UserId]):
    """User aggregate root.

    Invariants:
      - Email unique within tenant (DB constraint)
      - Active user has password
      - Deactivated user cannot login
    """

    def __init__(
        self,
        id: UserId,
        email: Email,
        password: HashedPassword,
        display_name: str,
        is_active: bool = True,
    ):
        super().__init__(id)
        self.email = email
        self.password = password
        self.display_name = display_name
        self.is_active = is_active

    # ─── Factory: yeni kullanıcı kayıt ───────────────────────────────
    @classmethod
    def register(
        cls,
        email: Email,
        password: HashedPassword,
        display_name: str,
    ) -> "User":
        user = cls(
            id=UserId.new(),
            email=email,
            password=password,
            display_name=display_name,
            is_active=True,
        )
        user._record_event(UserRegistered(
            aggregate_id=user.id.value,
            email=str(email),
            display_name=display_name,
        ))
        return user

    # ─── Behavior ────────────────────────────────────────────────────
    def change_email(self, new_email: Email) -> None:
        if new_email == self.email:
            return
        old = self.email
        self.email = new_email
        self._record_event(UserEmailChanged(
            aggregate_id=self.id.value,
            old_email=str(old),
            new_email=str(new_email),
        ))

    def deactivate(self, reason: str) -> None:
        if not self.is_active:
            return
        self.is_active = False
        self._record_event(UserDeactivated(
            aggregate_id=self.id.value,
            reason=reason,
        ))

    def login(self, ip: str | None = None) -> None:
        if not self.is_active:
            raise ValueError("Inaktif kullanıcı login olamaz")
        self._record_event(UserLoggedIn(
            aggregate_id=self.id.value,
            ip=ip or "unknown",
        ))
