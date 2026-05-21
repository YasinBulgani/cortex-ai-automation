"""SQLAlchemy engine ve oturum fabrikası (senkron)."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base — taban sınıfıdır, ek metot gerektirmez."""


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_timeout=30,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    class_=Session,
)


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a DB session with Postgres RLS tenant context set for every transaction.

    TenantMiddleware stores the validated tenant_id on request.state.
    We propagate it via SET LOCAL so Postgres RLS policies filter rows automatically.
    Using set_config(..., TRUE) makes the setting transaction-local (reverts on COMMIT/ROLLBACK).
    """
    tenant_id = getattr(request.state, "tenant_id", _DEFAULT_TENANT)
    db = SessionLocal()
    try:
        db.execute(
            text("SELECT set_config('app.current_tenant', :t, TRUE)"),
            {"t": tenant_id},
        )
        yield db
    finally:
        db.close()


def get_db_no_tenant() -> Generator[Session, None, None]:
    """Yield a DB session WITHOUT tenant context — for migrations, admin tasks, health checks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
