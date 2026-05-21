"""
Use case: Deactivate a user account.

Domain'de idempotent — zaten deaktifse no-op, event emit etmez.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxEntry, OutboxRepository
from app.contexts.identity.domain import UserId

from .change_email import UserNotFoundError
from .register_user import UserRepository


@dataclass(frozen=True, slots=True)
class DeactivateUserCommand:
    user_id: UserId
    reason: str = ""


class DeactivateUserHandler:
    def __init__(self, users: UserRepository, outbox: OutboxRepository):
        self.users = users
        self.outbox = outbox

    async def handle(self, cmd: DeactivateUserCommand) -> None:
        user = await self.users.get(cmd.user_id)
        if user is None:
            raise UserNotFoundError(str(cmd.user_id))

        already_inactive = not user.is_active
        user.deactivate(cmd.reason)
        if already_inactive:
            return  # No event emitted by domain

        await self.users.save(user)
        for event in user.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))
