"""SQLAlchemy engine ve oturum fabrikası (senkron)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base — taban sınıfıdır, ek metot gerektirmez."""


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Stale bağlantıları otomatik yenile
    future=True,
    # ── Bağlantı havuzu ayarları ─────────────────────────────────────
    pool_size=20,          # Kalıcı bağlantı sayısı (varsayılan: 5)
    max_overflow=10,       # Pool doluysa ek açılabilecek bağlantı
    pool_recycle=3600,     # 1 saatte bir bağlantıyı yenile (MySQL/PgBouncer timeout'larına karşı)
    pool_timeout=30,       # Bağlantı beklemek için maks süre (saniye)
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
