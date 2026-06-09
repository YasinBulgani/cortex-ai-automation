"""SQLAlchemy engine ve oturum fabrikası (senkron + async)."""

import threading
from collections.abc import AsyncGenerator, Generator
from typing import Optional

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
    pool_size=30,                 # +50% eşzamanlı bağlantı havuzu (perf opt 1.1)
    max_overflow=20,              # pike'ta ek bağlantı izni (+100%)
    pool_recycle=1800,            # 30 min rotation (firewall drop önlemi, prod optimized)
    pool_timeout=10,              # bağlantı bekleme süre aşımı (fail fast)
    echo_pool=False,              # disable pool echo logging (production)
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    } if "postgresql" in settings.database_url else {},
)


@event.listens_for(engine, "connect")
def _set_pg_session_defaults(dbapi_conn, connection_record):
    """Her yeni bağlantıda oturum bazlı Postgres performans ayarları.

    work_mem: Sıralama (ORDER BY) ve hash join için ayrılan bellek.
    Varsayılan 4MB çok düşük; dashboard GROUP BY sorgularında geçici disk
    yazımını önlemek için 16MB'a çıkarıldı (perf opt 1.6).
    """
    with dbapi_conn.cursor() as cur:
        cur.execute("SET work_mem = '16MB'")  # +100% from 8MB
        cur.execute("SET maintenance_work_mem = '256MB'")  # for indexes
        cur.execute("SET effective_cache_size = '2GB'")  # hint planner
        cur.execute("SET random_page_cost = 1.1")  # SSD-aware (not 4.0)
        cur.execute("SET effective_io_concurrency = 200")  # parallel seq scan


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
_async_init_lock = threading.Lock()
_async_engine = None
AsyncSessionLocal = None

# ── Async read-replica engine (Faz 3.1) ───────────────────────────────────────
# Read-only replica for scaling: ~100ms lag, sticky read-after-write pattern.
_async_read_init_lock = threading.Lock()
_async_read_engine = None
AsyncReadSessionLocal = None

# Module-level async initialization with lock (single engine per process)
with _async_init_lock:
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
            pool_size=30,  # perf opt 1.1
            max_overflow=20,  # perf opt 1.1
            echo_pool=False,  # no pool logging
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
    Lazy initialization with thread-safe double-check locking.
    """
    global _async_engine, AsyncSessionLocal

    # Lazy initialization if not already created
    if AsyncSessionLocal is None:
        with _async_init_lock:
            # Double-check inside lock to prevent race
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
    Lazy initialization with thread-safe double-check locking.
    """
    from app.infra.read_replica import should_force_primary

    global _async_engine, _async_read_engine, AsyncSessionLocal, AsyncReadSessionLocal

    # Lazy initialization if not already created (primary)
    if AsyncSessionLocal is None:
        with _async_init_lock:
            # Double-check inside lock to prevent race
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
            with _async_read_init_lock:
                # Double-check inside lock to prevent race
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


def get_sync_session(tenant_id: Optional[str] = None) -> Session:
    """Create an isolated sync DB session for background/executor threads.

    Use this in run_in_executor() callbacks to ensure per-thread session isolation.
    Each thread gets its own session from the pool, avoiding deadlocks from
    shared session state across async/sync boundaries.

    Args:
        tenant_id: Optional tenant ID for RLS context. If None, uses default.

    Returns:
        A new Session from the pool. Caller MUST close() it.

    Example:
        def sync_task(project_id: str):
            db = get_sync_session("tenant-123")
            try:
                # Use db in this thread
                db.query(...).filter(...)
            finally:
                db.close()

        loop.run_in_executor(None, sync_task, "proj-456")
    """
    if tenant_id is None:
        tenant_id = _DEFAULT_TENANT

    db = SessionLocal()
    try:
        # Set RLS tenant context (transaction-local)
        db.execute(
            text("SELECT set_config('app.current_tenant', :t, TRUE)"),
            {"t": tenant_id},
        )
        return db
    except Exception:
        db.close()
        raise
