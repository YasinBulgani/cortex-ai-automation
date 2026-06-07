#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/restore.sh — Restore Postgres from a .sql.gz backup file
#
# Usage (from project root):
#   bash scripts/restore.sh <path/to/backup.sql.gz>
#
# WARNING: This will DROP and re-create the target database.
#          All existing data will be lost. Confirm the prompt before proceeding.
# Requires:  docker, docker compose, and .env with POSTGRES_* vars.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present.
if [ -f "${PROJECT_ROOT}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${PROJECT_ROOT}/.env"
  set +a
fi

BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
  echo "Usage: $0 <path/to/backup.sql.gz>" >&2
  exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_DB:?POSTGRES_DB is not set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"

echo "========================================================"
echo "  Restore target : ${POSTGRES_DB}"
echo "  Backup file    : ${BACKUP_FILE}"
echo "========================================================"
read -r -p "This will DESTROY all existing data in '${POSTGRES_DB}'. Continue? [y/N] " CONFIRM
case "${CONFIRM}" in
  [yY][eE][sS]|[yY]) ;;
  *)
    echo "Aborted."
    exit 0
    ;;
esac

echo "[restore] Dropping and re-creating database '${POSTGRES_DB}' …"
docker compose -f "${PROJECT_ROOT}/docker-compose.prod.yml" \
  exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres \
  psql -U "${POSTGRES_USER}" -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE IF EXISTS \"${POSTGRES_DB}\";" \
  -c "CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\";"

echo "[restore] Restoring from ${BACKUP_FILE} …"
gunzip -c "${BACKUP_FILE}" \
  | docker compose -f "${PROJECT_ROOT}/docker-compose.prod.yml" \
      exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres \
      psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "[restore] Restore complete. Database '${POSTGRES_DB}' is ready."
