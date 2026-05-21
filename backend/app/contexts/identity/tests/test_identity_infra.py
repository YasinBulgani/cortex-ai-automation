"""Infrastructure tests for InMemoryUserRepository + FakePasswordHasher."""

from __future__ import annotations

import pytest

from app.contexts.identity.domain import Email, User, UserId
from app.contexts.identity.domain.user import HashedPassword
from app.contexts.identity.infrastructure import InMemoryUserRepository
from app.contexts.identity.infrastructure.bcrypt_hasher import FakePasswordHasher


def _make_user(email: str = "alice@example.com") -> User:
    return User.register(
        email=Email(email),
        password=HashedPassword("h" * 32),
        display_name="Alice",
    )


# ─── InMemoryUserRepository ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_get_by_email():
    repo = InMemoryUserRepository()
    user = _make_user()
    await repo.save(user)

    found = await repo.get_by_email(Email("alice@example.com"))
    assert found is user


@pytest.mark.asyncio
async def test_get_by_email_missing_returns_none():
    repo = InMemoryUserRepository()
    assert await repo.get_by_email(Email("missing@example.com")) is None


@pytest.mark.asyncio
async def test_get_by_id_returns_user():
    repo = InMemoryUserRepository()
    user = _make_user()
    await repo.save(user)

    found = await repo.get(user.id)
    assert found is user


@pytest.mark.asyncio
async def test_get_by_id_missing_returns_none():
    repo = InMemoryUserRepository()
    assert await repo.get(UserId.new()) is None


@pytest.mark.asyncio
async def test_save_updates_existing():
    repo = InMemoryUserRepository()
    user = _make_user()
    await repo.save(user)

    user.deactivate("test")
    await repo.save(user)

    found = await repo.get(user.id)
    assert found.is_active is False


@pytest.mark.asyncio
async def test_email_change_updates_index():
    repo = InMemoryUserRepository()
    user = _make_user("old@example.com")
    await repo.save(user)

    user.change_email(Email("new@example.com"))
    await repo.save(user)

    assert await repo.get_by_email(Email("old@example.com")) is None
    assert await repo.get_by_email(Email("new@example.com")) is user


@pytest.mark.asyncio
async def test_clear_removes_all():
    repo = InMemoryUserRepository()
    await repo.save(_make_user("a@example.com"))
    await repo.save(_make_user("b@example.com"))
    assert len(repo) == 2

    repo.clear()
    assert len(repo) == 0


# ─── FakePasswordHasher ───────────────────────────────────────────────────────

def test_fake_hasher_hash_produces_deterministic_result():
    h = FakePasswordHasher()
    assert h.hash("secret") == h.hash("secret")


def test_fake_hasher_verify_correct_password():
    h = FakePasswordHasher()
    assert h.verify("secret", h.hash("secret")) is True


def test_fake_hasher_verify_wrong_password():
    h = FakePasswordHasher()
    assert h.verify("wrong", h.hash("secret")) is False


def test_fake_hasher_hash_length_at_least_32():
    h = FakePasswordHasher()
    assert len(h.hash("x")) >= 32
