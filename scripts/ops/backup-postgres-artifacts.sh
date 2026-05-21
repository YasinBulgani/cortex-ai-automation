#!/usr/bin/env bash

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
DB_NAME="${POSTGRES_DB:-${DB_NAME:-}}"
DB_USER="${POSTGRES_USER:-${DB_USER:-}}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -z "$DB_NAME" || -z "$DB_USER" ]]; then
  echo "POSTGRES_DB/POSTGRES_USER veya DB_NAME/DB_USER zorunlu" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

DB_OUT="$BACKUP_DIR/postgres-$STAMP.dump"
ARTIFACT_OUT="$BACKUP_DIR/artifacts-$STAMP.tgz"
MANIFEST_OUT="$BACKUP_DIR/manifest-$STAMP.json"

docker-compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$DB_OUT"

docker-compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SERVICE" \
  tar czf - -C /app/data/artifacts . > "$ARTIFACT_OUT"

python3 - <<'PY' "$MANIFEST_OUT" "$DB_OUT" "$ARTIFACT_OUT" "$COMPOSE_FILE"
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

manifest, db_path, artifact_path, compose_file = sys.argv[1:]

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

payload = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "compose_file": compose_file,
    "rpo_target_minutes": int(os.environ.get("BACKUP_RPO_TARGET_MINUTES", "60")),
    "rto_target_minutes": int(os.environ.get("BACKUP_RTO_TARGET_MINUTES", "120")),
    "files": {
        "postgres": {"path": db_path, "sha256": sha256(db_path), "bytes": os.path.getsize(db_path)},
        "artifacts": {"path": artifact_path, "sha256": sha256(artifact_path), "bytes": os.path.getsize(artifact_path)},
    },
}
with open(manifest, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
    fh.write("\n")
PY

echo "Backup tamam: $MANIFEST_OUT"
