"""SQLAlchemy engine ve oturum fabrikası (senkron)."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base — taban sınıfıdır, ek metot gerektirmez."""


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,           # bağlantı sağlığını doğrula
    future=True,
    pool_size=20,                 # eşzamanlı bağlantı havuzu
    max_overflow=10,              # pike'ta ek bağlantı izni
    pool_recycle=3600,            # 1 saatte bir bağlantıları yenile (firewall drop önlemi)
    pool_timeout=30,              # bağlantı bekleme süre aşımı
)


@event.listens_for(engine, "connect")
def _set_pg_session_defaults(dbapi_conn, connection_record):
    """Her yeni bağlantıda oturum bazlı Postgres performans ayarları.

    work_mem: Sıralama (ORDER BY) ve hash join için ayrılan bellek.
    Varsayılan 4MB çok düşük; dashboard GROUP BY sorgularında geçici disk
    yazımını önlemek için 8MB'a çıkarıldı.
    """
    with dbapi_conn.cursor() as cur:
        cur.execute("SET work_mem = '8MB'")


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
