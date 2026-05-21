"""
In-memory user repository — testler ve local dev için.

Thread-safe değil, persistence yok. Production'da SqlAlchemyUserRepository
kullan.
"""

from __future__ import annotations

from app.contexts.identity.domain import Email, User, UserId
from app.contexts.identity.application.register_user import UserRepository


class InMemoryUserRepository(UserRepository):
    """UserRepository in-memory implementasyonu."""

    def __init__(self):
        self._by_id: dict[UserId, User] = {}
        self._by_email: dict[str, UserId] = {}

    async def get_by_email(self, email: Email) -> User | None:
        uid = self._by_email.get(str(email))
        return self._by_id.get(uid) if uid else None

    async def save(self, user: User) -> None:
        # Email değişmişse eski indeksi temizle
        for email, uid in list(self._by_email.items()):
            if uid == user.id and email != str(user.email):
                del self._by_email[email]
        self._by_id[user.id] = user
        self._by_email[str(user.email)] = user.id

    async def get(self, user_id: UserId) -> User | None:
        return self._by_id.get(user_id)

    # Yardımcı (test'ler için)
    def clear(self) -> None:
        self._by_id.clear()
        self._by_email.clear()

    def __len__(self) -> int:
        return len(self._by_id)
