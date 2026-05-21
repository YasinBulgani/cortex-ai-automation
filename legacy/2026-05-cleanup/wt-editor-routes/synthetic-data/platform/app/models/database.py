"""
Veritabanı bağlantı ve oturum yönetimi.

SQLAlchemy engine, session factory ve FastAPI dependency injection
fonksiyonlarını içerir.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ── SQLAlchemy Engine ────────────────────────────────────────────────
# Senkron engine — veritabanı türüne göre yapılandırılır
_db_url = settings.database_url

if _db_url.startswith("sqlite"):
    # SQLite için pool parametreleri desteklenmez
    engine = create_engine(
        _db_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL / diğer veritabanları için tam yapılandırma
    engine = create_engine(
        _db_url,
        echo=settings.DEBUG,           # DEBUG modunda SQL sorgularını logla
        pool_size=10,                  # Bağlantı havuzu boyutu
        max_overflow=20,               # Taşma durumunda ek bağlantı sayısı
        pool_pre_ping=True,            # Bağlantı canlılık kontrolü
        pool_recycle=3600,             # 1 saat sonra bağlantıları yenile
    )


# ── Session Factory ──────────────────────────────────────────────────
# Her veritabanı işlemi için yeni bir oturum oluşturur
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Declarative Base ─────────────────────────────────────────────────
# Tüm ORM modelleri bu sınıftan türetilir
class Base(DeclarativeBase):
    """
    SQLAlchemy ORM temel sınıfı.

    Tüm veritabanı modelleri bu sınıfı miras alır.
    Tablo oluşturma ve migration işlemleri için kullanılır.
    """
    pass


# ── FastAPI Dependency ───────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection için veritabanı oturumu sağlar.

    Her istek için yeni bir oturum açılır ve istek tamamlandığında
    otomatik olarak kapatılır. Hata durumunda rollback yapılır.

    Kullanım:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """
    Veritabanında tanımlı tüm tabloları oluşturur.

    Geliştirme ortamı için kullanılır.
    Production'da Alembic migration tercih edilmelidir.
    """
    Base.metadata.create_all(bind=engine)
