"""
Fresh deployment için tüm tabloları SQLAlchemy modelleri üzerinden oluşturur.
Alembic migration geçmişindeki branch çakışmalarını bypass eder.

Kullanım:
  python scripts/init_schema.py          # Fresh DB init
  python scripts/init_schema.py --check  # Sadece tablo sayısını göster
"""

from __future__ import annotations

import os
import sys
import argparse

sys.path.insert(0, "/app")

from sqlalchemy import create_engine, inspect as sa_inspect, text

DATABASE_URL = os.environ["DATABASE_URL"]
FINAL_REVISION = "20260603_0002"


def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def is_fresh_db(engine) -> bool:
    """Tablolar yok veya sadece alembic_version varsa True."""
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names(schema="public")
    real_tables = [t for t in tables if t != "alembic_version"]
    return len(real_tables) == 0


def import_all_models():
    """Tüm domain modellerini import ederek Base.metadata'ya kaydeder."""
    import importlib
    import pkgutil

    # Temel infra import
    import app.infra.database  # noqa: F401

    # Tüm domain modüllerini tara
    errors = []
    for finder, name, ispkg in pkgutil.walk_packages(
        path=["/app/app/domains", "/app/app"],
        prefix="app.",
        onerror=lambda x: None,
    ):
        if "models" in name or "schemas" in name:
            try:
                importlib.import_module(name)
            except Exception as e:
                errors.append(f"{name}: {e}")

    if errors:
        print(f"  Uyarı: {len(errors)} modül import edilemedi (tablo tanımları eksik olabilir)")

    from app.infra.database import Base
    return Base


def stamp_alembic(engine, revision: str):
    """alembic_version tablosunu oluşturup revision'ı kaydet."""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        ))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text(f"INSERT INTO alembic_version VALUES ('{revision}')"))
    print(f"  ✅ Alembic stamped: {revision}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    engine = get_engine()
    inspector = sa_inspect(engine)
    existing_tables = inspector.get_table_names(schema="public")
    real_tables = [t for t in existing_tables if t != "alembic_version"]

    if args.check:
        print(f"Mevcut tablo sayısı: {len(real_tables)}")
        return

    if not is_fresh_db(engine):
        print(f"Mevcut DB: {len(real_tables)} tablo var. init_schema.py atlanıyor.")
        sys.exit(0)

    print("Fresh DB tespit edildi. SQLAlchemy ile şema oluşturuluyor...")
    print("  Modeller import ediliyor...")
    Base = import_all_models()

    print(f"  {len(Base.metadata.tables)} tablo tanımı bulundu.")
    print("  Tablolar oluşturuluyor...")
    Base.metadata.create_all(engine, checkfirst=True)

    created = sa_inspect(engine).get_table_names(schema="public")
    print(f"  ✅ {len(created)} tablo oluşturuldu.")

    stamp_alembic(engine, FINAL_REVISION)
    print("Şema başarıyla oluşturuldu.")


if __name__ == "__main__":
    main()
