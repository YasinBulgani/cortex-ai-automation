"""Application use-case tests: RegisterUser, ChangeEmail, DeactivateUser."""

from __future__ import annotations

import pytest

from app.contexts.identity.application import (
    ChangeEmailCommand,
    ChangeEmailHandler,
    DeactivateUserCommand,
    DeactivateUserHandler,
    EmailConflictError,
    RegisterUserCommand,
    RegisterUserHandler,
    UserNotFoundError,
)
from app.contexts.identity.domain import Email, UserId
from app.contexts.identity.infrastructure import InMemoryUserRepository
from app.contexts.identity.infrastructure.bcrypt_hasher import FakePasswordHasher


class _InMemoryOutbox:
    def __init__(self):
        self.entries = []

    async def append(self, entry) -> None:
        self.entries.append(entry)


@pytest.fixture()
def repo():
    return InMemoryUserRepository()


@pytest.fixture()
def outbox():
    return _InMemoryOutbox()


@pytest.fixture()
def hasher():
    return FakePasswordHasher()


# ─── RegisterUser ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_user_succeeds(repo, outbox, hasher):
    handler = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    uid = await handler.handle(RegisterUserCommand(
        email="alice@neurex.io",
        password_plain="secret123",
        display_name="Alice",
    ))

    user = await repo.get(uid)
    assert user is not None
    assert str(user.email) == "alice@neurex.io"
    assert len(outbox.entries) == 1
    assert outbox.entries[0].event_type == "user.registered"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(repo, outbox, hasher):
    handler = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    cmd = RegisterUserCommand(email="dup@x.com", password_plain="p", display_name="Dup")
    await handler.handle(cmd)
    with pytest.raises(ValueError, match="zaten kayıtlı"):
        await handler.handle(cmd)


@pytest.mark.asyncio
async def test_register_invalid_email_raises(repo, outbox, hasher):
    handler = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    with pytest.raises(ValueError, match="Geçersiz"):
        await handler.handle(RegisterUserCommand(email="bad", password_plain="p", display_name="X"))


# ─── ChangeEmail ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_email_succeeds(repo, outbox, hasher):
    reg = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    uid = await reg.handle(RegisterUserCommand(email="old@x.com", password_plain="p", display_name="U"))
    outbox.entries.clear()

    handler = ChangeEmailHandler(users=repo, outbox=outbox)
    await handler.handle(ChangeEmailCommand(user_id=uid, new_email="new@x.com"))

    user = await repo.get(uid)
    assert str(user.email) == "new@x.com"
    assert len(outbox.entries) == 1
    assert outbox.entries[0].event_type == "user.email_changed"


@pytest.mark.asyncio
async def test_change_email_to_same_is_noop(repo, outbox, hasher):
    reg = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    uid = await reg.handle(RegisterUserCommand(email="same@x.com", password_plain="p", display_name="U"))
    outbox.entries.clear()

    handler = ChangeEmailHandler(users=repo, outbox=outbox)
    await handler.handle(ChangeEmailCommand(user_id=uid, new_email="same@x.com"))
    assert outbox.entries == []


@pytest.mark.asyncio
async def test_change_email_conflict_raises(repo, outbox, hasher):
    reg = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    await reg.handle(RegisterUserCommand(email="taken@x.com", password_plain="p", display_name="A"))
    uid = await reg.handle(RegisterUserCommand(email="other@x.com", password_plain="p", display_name="B"))

    handler = ChangeEmailHandler(users=repo, outbox=outbox)
    with pytest.raises(EmailConflictError):
        await handler.handle(ChangeEmailCommand(user_id=uid, new_email="taken@x.com"))


@pytest.mark.asyncio
async def test_change_email_user_not_found_raises(repo, outbox):
    handler = ChangeEmailHandler(users=repo, outbox=outbox)
    with pytest.raises(UserNotFoundError):
        await handler.handle(ChangeEmailCommand(user_id=UserId.new(), new_email="x@x.com"))


# ─── DeactivateUser ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deactivate_user_succeeds(repo, outbox, hasher):
    reg = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    uid = await reg.handle(RegisterUserCommand(email="bye@x.com", password_plain="p", display_name="Bye"))
    outbox.entries.clear()

    handler = DeactivateUserHandler(users=repo, outbox=outbox)
    await handler.handle(DeactivateUserCommand(user_id=uid, reason="left"))

    user = await repo.get(uid)
    assert user.is_active is False
    assert len(outbox.entries) == 1
    assert outbox.entries[0].event_type == "user.deactivated"


@pytest.mark.asyncio
async def test_deactivate_already_inactive_is_noop(repo, outbox, hasher):
    reg = RegisterUserHandler(users=repo, hasher=hasher, outbox=outbox)
    uid = await reg.handle(RegisterUserCommand(email="bye2@x.com", password_plain="p", display_name="B"))
    handler = DeactivateUserHandler(users=repo, outbox=outbox)
    await handler.handle(DeactivateUserCommand(user_id=uid, reason="once"))
    outbox.entries.clear()

    await handler.handle(DeactivateUserCommand(user_id=uid, reason="twice"))
    assert outbox.entries == []


@pytest.mark.asyncio
async def test_deactivate_missing_user_raises(repo, outbox):
    handler = DeactivateUserHandler(users=repo, outbox=outbox)
    with pytest.raises(UserNotFoundError):
        await handler.handle(DeactivateUserCommand(user_id=UserId.new()))
