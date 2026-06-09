"""SQLAlchemy engine ve oturum fabrikası (senkron + async)."""

from collections.abc import AsyncGenerator, Generator

from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
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

# ── Async engine + sessionmaker (Faz 1 hot-path) ───────────────────────────────
# AsyncSession ile non-blocking I/O. SQLite/in-memory test'ler için sqlite+aiosqlite,
# prod Postgres için postgresql+asyncpg otomatik detect edilir.
_async_engine = None
AsyncSessionLocal = None

# ── Async read-replica engine (Faz 3.1) ───────────────────────────────────────
# Read-only replica for scaling: ~100ms lag, sticky read-after-write pattern.
_async_read_engine = None
AsyncReadSessionLocal = None

try:
    _async_url = settings.database_url
    if "postgresql://" in _async_url:
        _async_url = _async_url.replace("postgresql://", "postgresql+asyncpg://")
    elif "postgresql+psycopg2://" in _async_url:
        _async_url = _async_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    _async_engine = create_async_engine(
        _async_url,
        pool_pre_ping=True,
        future=True,
        pool_size=20,
        max_overflow=10,
    )

    AsyncSessionLocal = sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        future=True,
        expire_on_commit=False,
    )

    # Initialize read-replica engine if configured
    if settings.read_replica_enabled and settings.read_replica_url:
        _read_replica_url = settings.read_replica_url
        if "postgresql://" in _read_replica_url:
            _read_replica_url = _read_replica_url.replace("postgresql://", "postgresql+asyncpg://")
        elif "postgresql+psycopg2://" in _read_replica_url:
            _read_replica_url = _read_replica_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

        _async_read_engine = create_async_engine(
            _read_replica_url,
            pool_pre_ping=True,
            future=True,
            pool_size=20,
            max_overflow=10,
            # Replica is read-only; don't hold transactions open
            pool_recycle=1800,
        )

        AsyncReadSessionLocal = sessionmaker(
            bind=_async_read_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            future=True,
            expire_on_commit=False,
        )
except Exception as _e:
    # If async engine creation fails (e.g., asyncpg not installed),
    # set a lazy placeholder. get_async_db will initialize on first use.
    pass


async def get_async_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Async session with RLS tenant context (async routes için).

    Aynı tenant isolation logic ama async I/O non-blocking.
    Yazılı işlemler için her zaman primary DB kullanır.
    """
    global _async_engine, AsyncSessionLocal

    # Lazy initialization if not already created
    if AsyncSessionLocal is None:
        try:
            _async_url = settings.database_url
            if "postgresql://" in _async_url:
                _async_url = _async_url.replace("postgresql://", "postgresql+asyncpg://")
            elif "postgresql+psycopg2://" in _async_url:
                _async_url = _async_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

            _async_engine = create_async_engine(
                _async_url,
                pool_pre_ping=True,
                future=True,
                pool_size=20,
                max_overflow=10,
            )

            AsyncSessionLocal = sessionmaker(
                bind=_async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                future=True,
                expire_on_commit=False,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize async database session: {e}") from e

    tenant_id = getattr(request.state, "tenant_id", _DEFAULT_TENANT)
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, TRUE)"),
            {"t": tenant_id},
        )
        yield db


async def get_read_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Async read session (Faz 3.1).

    Replica'dan okur, replication lag kaynaklı stale data'yı sticky
    read-after-write pattern ile önler: write sonrası 5s içinde
    yapılan okumalar primary'den yapılır.

    Eğer read_replica disabled veya configured değilse, primary'ye fallback.
    """
    from app.infra.read_replica import should_force_primary

    global _async_engine, _async_read_engine, AsyncSessionLocal, AsyncReadSessionLocal

    # Lazy initialization if not already created
    if AsyncSessionLocal is None:
        try:
            _async_url = settings.database_url
            if "postgresql://" in _async_url:
                _async_url = _async_url.replace("postgresql://", "postgresql+asyncpg://")
            elif "postgresql+psycopg2://" in _async_url:
                _async_url = _async_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

            _async_engine = create_async_engine(
                _async_url,
                pool_pre_ping=True,
                future=True,
                pool_size=20,
                max_overflow=10,
            )

            AsyncSessionLocal = sessionmaker(
                bind=_async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                future=True,
                expire_on_commit=False,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize async database session: {e}") from e

    tenant_id = getattr(request.state, "tenant_id", _DEFAULT_TENANT)

    # Check if we should use primary (sticky read-after-write)
    use_primary = should_force_primary(request)

    # Fallback to primary if replica not configured or sticky flag set
    if not settings.read_replica_enabled or not settings.read_replica_url or use_primary:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('app.current_tenant', :t, TRUE)"),
                {"t": tenant_id},
            )
            yield db
    else:
        # Use read replica
        if AsyncReadSessionLocal is None:
            try:
                _read_replica_url = settings.read_replica_url
                if "postgresql://" in _read_replica_url:
                    _read_replica_url = _read_replica_url.replace("postgresql://", "postgresql+asyncpg://")
                elif "postgresql+psycopg2://" in _read_replica_url:
                    _read_replica_url = _read_replica_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

                _async_read_engine = create_async_engine(
                    _read_replica_url,
                    pool_pre_ping=True,
                    future=True,
                    pool_size=20,
                    max_overflow=10,
                    pool_recycle=1800,
                )

                AsyncReadSessionLocal = sessionmaker(
                    bind=_async_read_engine,
                    class_=AsyncSession,
                    autocommit=False,
                    autoflush=False,
                    future=True,
                    expire_on_commit=False,
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize read replica session: {e}") from e

        async with AsyncReadSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('app.current_tenant', :t, TRUE)"),
                {"t": tenant_id},
            )
            yield db


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
