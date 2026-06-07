#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/backup.sh — Manual Postgres backup via docker compose exec
#
# Usage (from project root):
#   bash scripts/backup.sh [output-dir]
#
# Default output directory: ./backups
# Requires:  docker, docker compose, and .env with POSTGRES_* vars.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present so POSTGRES_* vars are available in this shell.
if [ -f "${PROJECT_ROOT}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${PROJECT_ROOT}/.env"
  set +a
fi

OUTPUT_DIR="${1:-${PROJECT_ROOT}/backups}"
mkdir -p "${OUTPUT_DIR}"

TIMESTAMP="$(date +%Y-%m-%dT%H-%M-%S)"
FILENAME="${OUTPUT_DIR}/${TIMESTAMP}.sql.gz"

: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_DB:?POSTGRES_DB is not set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"

echo "[backup] Dumping database '${POSTGRES_DB}' → ${FILENAME}"

docker compose -f "${PROJECT_ROOT}/docker-compose.prod.yml" \
  exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "${FILENAME}"

FILESIZE="$(du -h "${FILENAME}" | awk '{print $1}')"
echo "[backup] Done. File: ${FILENAME} (${FILESIZE})"

# Prune backups older than 7 days in the output directory.
echo "[backup] Pruning backups older than 7 days in ${OUTPUT_DIR} …"
find "${OUTPUT_DIR}" -maxdepth 1 -name "*.sql.gz" -mtime +7 -delete
echo "[backup] Pruning complete."
