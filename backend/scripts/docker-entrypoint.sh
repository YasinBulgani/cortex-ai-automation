#!/bin/sh
set -e

export PYTHONPATH=/app
cd /app

if [ "${SKIP_APP_BOOTSTRAP:-}" != "1" ]; then
  PGHOST="${POSTGRES_HOST:-postgres}"
  PGPORT="${POSTGRES_PORT:-5432}"
  PGUSER="${POSTGRES_SUPER_USER:-${POSTGRES_USER:-twai_user}}"

  echo "PostgreSQL bekleniyor ($PGHOST:$PGPORT, db=syndata_db)..."
  until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d syndata_db >/dev/null 2>&1; do
    sleep 1
  done

  alembic upgrade head
  python scripts/seed.py
  if [ "${RUN_SEED_DEMO:-}" = "1" ] || [ "${RUN_SEED_DEMO:-}" = "true" ]; then
    python scripts/seed_demo.py
  fi
fi

exec "$@"
