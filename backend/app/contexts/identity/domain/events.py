"""
Identity bounded context — domain events.

Bu event'leri başka context'ler subscribe edebilir:
- Audit context: UserLoggedIn → audit log entry
- Notifications context: UserRegistered → welcome email
- Onboarding context: UserRegistered → onboarding flow başlat
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    email: str = ""
    display_name: str = ""


@dataclass(frozen=True, slots=True)
class UserEmailChanged(DomainEvent):
    old_email: str = ""
    new_email: str = ""


@dataclass(frozen=True, slots=True)
class UserDeactivated(DomainEvent):
    reason: str = ""


@dataclass(frozen=True, slots=True)
class UserLoggedIn(DomainEvent):
    ip: str = ""
