"""
Use case: Change a user's email address.

İş kuralı:
- Kullanıcı bulunamazsa 404
- Yeni e-posta başka kullanıcıda varsa çakışma hatası
- Aynı e-posta ise no-op (idempotent)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxEntry, OutboxRepository
from app.contexts.identity.domain import Email, UserId

from .register_user import UserRepository


@dataclass(frozen=True, slots=True)
class ChangeEmailCommand:
    user_id: UserId
    new_email: str


class UserNotFoundError(Exception):
    """Kullanıcı bulunamadı."""


class EmailConflictError(Exception):
    """E-posta başka bir kullanıcıda kullanımda."""


class ChangeEmailHandler:
    def __init__(self, users: UserRepository, outbox: OutboxRepository):
        self.users = users
        self.outbox = outbox

    async def handle(self, cmd: ChangeEmailCommand) -> None:
        new_email = Email(cmd.new_email)

        user = await self.users.get(cmd.user_id)
        if user is None:
            raise UserNotFoundError(str(cmd.user_id))

        if new_email == user.email:
            return  # No-op

        conflict = await self.users.get_by_email(new_email)
        if conflict is not None and conflict.id != user.id:
            raise EmailConflictError(f"E-posta başka bir hesapta: {new_email}")

        user.change_email(new_email)

        await self.users.save(user)
        for event in user.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))
