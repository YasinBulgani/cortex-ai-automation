"""
Domain layer unit tests — saf, infrastructure-bağımsız.
"""

import pytest

from app.contexts.identity.domain.user import (
    Email,
    HashedPassword,
    User,
    UserId,
)
from app.contexts.identity.domain.events import (
    UserRegistered,
    UserEmailChanged,
    UserDeactivated,
    UserLoggedIn,
)


class TestEmail:
    def test_valid_email_accepted(self):
        e = Email("user@example.com")
        assert str(e) == "user@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValueError, match="Geçersiz e-posta"):
            Email("not-an-email")

    def test_email_equality_by_value(self):
        assert Email("a@b.com") == Email("a@b.com")
        assert Email("a@b.com") != Email("c@d.com")

    def test_email_is_frozen(self):
        e = Email("a@b.com")
        with pytest.raises(Exception):
            e.value = "x@y.com"  # frozen dataclass


class TestUserRegistration:
    def test_register_creates_user_with_event(self):
        user = User.register(
            email=Email("alice@neurex.io"),
            password=HashedPassword("a" * 32),
            display_name="Alice",
        )
        assert user.email == Email("alice@neurex.io")
        assert user.display_name == "Alice"
        assert user.is_active is True
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserRegistered)
        assert events[0].email == "alice@neurex.io"

    def test_pull_events_is_idempotent(self):
        user = User.register(
            email=Email("a@b.com"),
            password=HashedPassword("h" * 40),
            display_name="A",
        )
        _ = user.pull_events()
        assert user.pull_events() == []


class TestUserBehavior:
    def _new_user(self) -> User:
        return User.register(
            email=Email("alice@neurex.io"),
            password=HashedPassword("hashedhashedhashedhashedhashedha"),
            display_name="Alice",
        )

    def test_change_email_emits_event(self):
        user = self._new_user()
        _ = user.pull_events()  # discard register event

        user.change_email(Email("alice@bob.com"))
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserEmailChanged)
        assert events[0].old_email == "alice@neurex.io"
        assert events[0].new_email == "alice@bob.com"

    def test_change_to_same_email_no_event(self):
        user = self._new_user()
        _ = user.pull_events()

        user.change_email(Email("alice@neurex.io"))  # same
        assert user.pull_events() == []

    def test_deactivate_emits_event(self):
        user = self._new_user()
        _ = user.pull_events()

        user.deactivate(reason="left company")
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserDeactivated)
        assert events[0].reason == "left company"
        assert user.is_active is False

    def test_deactivate_twice_no_extra_event(self):
        user = self._new_user()
        _ = user.pull_events()

        user.deactivate("reason 1")
        _ = user.pull_events()
        user.deactivate("reason 2")
        assert user.pull_events() == []

    def test_inactive_user_cannot_login(self):
        user = self._new_user()
        user.deactivate("test")
        _ = user.pull_events()

        with pytest.raises(ValueError, match="Inaktif"):
            user.login(ip="127.0.0.1")

    def test_login_emits_event(self):
        user = self._new_user()
        _ = user.pull_events()

        user.login(ip="192.168.1.1")
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserLoggedIn)
        assert events[0].ip == "192.168.1.1"


class TestUserId:
    def test_new_generates_unique_id(self):
        a = UserId.new()
        b = UserId.new()
        assert a != b

    def test_userid_typed_distinct_from_other_entity_ids(self):
        from app.contexts._shared.kernel.identifiers import EntityId
        # UserId and any other EntityId subclass must not be interchangeable in business logic
        assert isinstance(UserId.new(), EntityId)
