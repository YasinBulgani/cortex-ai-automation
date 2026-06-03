#!/bin/sh
set -e

export PYTHONPATH=/app
cd /app

if [ "${SKIP_APP_BOOTSTRAP:-}" != "1" ]; then
  PGHOST="${POSTGRES_HOST:-postgres}"
  PGPORT="${POSTGRES_PORT:-5432}"
  PGUSER="${POSTGRES_SUPER_USER:-${POSTGRES_USER:-twai_user}}"
  PGDB="${POSTGRES_DB:-neondb}"

  echo "PostgreSQL bekleniyor ($PGHOST:$PGPORT, db=$PGDB)..."
  RETRIES=30
  until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" >/dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
      echo "PostgreSQL bağlantısı zaman aşımına uğradı!" >&2
      exit 1
    fi
    sleep 2
  done

  alembic upgrade heads
  python scripts/seed.py || echo "Seed uyarısı: seed.py hata verdi, devam ediliyor..."
  if [ "${RUN_SEED_DEMO:-}" = "1" ] || [ "${RUN_SEED_DEMO:-}" = "true" ]; then
    python scripts/seed_demo.py
  fi
fi

exec "$@"
