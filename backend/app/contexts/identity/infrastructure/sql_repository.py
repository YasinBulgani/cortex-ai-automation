"""
SQLAlchemy implementation of UserRepository.

Postgres-backed async. ORM <-> domain çeviri burada izole.
Domain layer SQLAlchemy hakkında hiçbir şey bilmez.

Migration: alembic revision (yeni tablo `iam_users`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, String, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.contexts.identity.application.register_user import UserRepository
from app.contexts.identity.domain import Email, User, UserId
from app.contexts.identity.domain.user import HashedPassword

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


Base = declarative_base()


class UserRow(Base):
    """
    Users tablosu.

    Index'ler:
      - id (pk)
      - email (unique — global, tenant_id kolonu sonra eklenir)
      - is_active (login sorgusu için)
    """

    __tablename__ = "iam_users"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True)
    email        = Column(String(320), nullable=False, unique=True, index=True)
    password_hash = Column(String(512), nullable=False)
    display_name = Column(String(255), nullable=False, default="")
    is_active    = Column(Boolean, nullable=False, default=True)
    version      = Column("agg_version", String(20), nullable=False, default="0")
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    @classmethod
    def from_aggregate(cls, user: User) -> "UserRow":
        return cls(
            id=user.id.value,
            email=str(user.email),
            password_hash=user.password.hash,
            display_name=user.display_name,
            is_active=user.is_active,
            version=str(user.version),
        )

    def update_from_aggregate(self, user: User) -> None:
        self.email = str(user.email)
        self.password_hash = user.password.hash
        self.display_name = user.display_name
        self.is_active = user.is_active
        self.version = str(user.version)

    def to_aggregate(self) -> User:
        return User(
            id=UserId(self.id),
            email=Email(self.email),
            password=HashedPassword(self.password_hash),
            display_name=self.display_name,
            is_active=self.is_active,
        )


class SqlAlchemyUserRepository(UserRepository):
    """UserRepository PostgreSQL implementation (async)."""

    def __init__(self, session: "AsyncSession"):
        self.session = session

    async def get(self, user_id: UserId) -> User | None:
        row = await self.session.get(UserRow, user_id.value)
        return row.to_aggregate() if row else None

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserRow).where(UserRow.email == str(email))
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row.to_aggregate() if row else None

    async def save(self, user: User) -> None:
        """Upsert — commit caller'ın sorumluluğunda."""
        existing = await self.session.get(UserRow, user.id.value)
        if existing is None:
            self.session.add(UserRow.from_aggregate(user))
        else:
            existing.update_from_aggregate(user)
