#!/usr/bin/env bash

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
DB_NAME="${POSTGRES_DB:-${DB_NAME:-}}"
DB_USER="${POSTGRES_USER:-${DB_USER:-}}"
DB_DUMP="${DB_DUMP:-}"
ARTIFACT_TGZ="${ARTIFACT_TGZ:-}"
CONFIRM_RESTORE="${CONFIRM_RESTORE:-false}"

if [[ "$CONFIRM_RESTORE" != "true" ]]; then
  echo "Restore destructive olabilir. CONFIRM_RESTORE=true ayarlayın." >&2
  exit 1
fi

if [[ -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_DUMP" || -z "$ARTIFACT_TGZ" ]]; then
  echo "DB_NAME/DB_USER/DB_DUMP/ARTIFACT_TGZ zorunlu" >&2
  exit 1
fi

test -f "$DB_DUMP"
test -f "$ARTIFACT_TGZ"

docker-compose -f "$COMPOSE_FILE" up -d "$POSTGRES_SERVICE" "$BACKEND_SERVICE"

cat "$DB_DUMP" | docker-compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
  pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner

cat "$ARTIFACT_TGZ" | docker-compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SERVICE" \
  sh -lc 'mkdir -p /app/data/artifacts && tar xzf - -C /app/data/artifacts'

echo "Restore tamamlandı"
