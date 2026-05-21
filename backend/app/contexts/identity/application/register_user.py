"""
Use case: Register a new user.

Command/Handler pattern (CQRS write side).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.contexts._shared.outbox import OutboxRepository, OutboxEntry
from app.contexts.identity.domain import Email, User, UserId
from app.contexts.identity.domain.user import HashedPassword


# ─── Command ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password_plain: str
    display_name: str


# ─── Dependencies (Protocols) ────────────────────────────────────────────

class UserRepository(Protocol):
    async def get_by_email(self, email: Email) -> User | None: ...
    async def save(self, user: User) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...


# ─── Handler ─────────────────────────────────────────────────────────────

class RegisterUserHandler:
    """
    Use case orchestrator.

    Test'te mock'lanabilir:
        handler = RegisterUserHandler(
            users=InMemoryUserRepo(),
            hasher=FakeHasher(),
            outbox=InMemoryOutbox(),
        )
        await handler.handle(RegisterUserCommand(...))
    """

    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        outbox: OutboxRepository,
    ):
        self.users = users
        self.hasher = hasher
        self.outbox = outbox

    async def handle(self, cmd: RegisterUserCommand) -> UserId:
        # Validation
        email = Email(cmd.email)

        # Business rule: email unique
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise ValueError(f"E-posta zaten kayıtlı: {email}")

        # Domain logic
        user = User.register(
            email=email,
            password=HashedPassword(self.hasher.hash(cmd.password_plain)),
            display_name=cmd.display_name,
        )

        # Persistence + outbox in same transaction
        await self.users.save(user)
        for event in user.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))

        return user.id
