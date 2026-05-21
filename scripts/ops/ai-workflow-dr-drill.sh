#!/usr/bin/env bash

set -euo pipefail

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-twai_user}"
SOURCE_DB="${SOURCE_DB:-neurex_soak}"
RESTORE_DB="${RESTORE_DB:-neurex_restore}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-/tmp/neurex-soak-artifacts}"
RESTORE_ARTIFACTS_DIR="${RESTORE_ARTIFACTS_DIR:-/tmp/neurex-restore-artifacts}"
OUT_DIR="${OUT_DIR:-/tmp/neurex-dr-drill}"
CONFIRM_RESTORE="${CONFIRM_RESTORE:-false}"

if [[ "$CONFIRM_RESTORE" != "true" ]]; then
  echo "Restore drill target DB yeniden olusturulur. CONFIRM_RESTORE=true zorunlu." >&2
  exit 1
fi

if [[ "$SOURCE_DB" == "$RESTORE_DB" ]]; then
  echo "SOURCE_DB ve RESTORE_DB farkli olmali." >&2
  exit 1
fi

if [[ "$ARTIFACTS_DIR" == "$RESTORE_ARTIFACTS_DIR" ]]; then
  echo "ARTIFACTS_DIR ve RESTORE_ARTIFACTS_DIR farkli olmali." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_DUMP="$OUT_DIR/${SOURCE_DB}-${STAMP}.dump"
ARTIFACT_TGZ="$OUT_DIR/${SOURCE_DB}-artifacts-${STAMP}.tgz"
MANIFEST="$OUT_DIR/${SOURCE_DB}-manifest-${STAMP}.json"

pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$SOURCE_DB" -Fc > "$DB_DUMP"
tar czf "$ARTIFACT_TGZ" -C "$ARTIFACTS_DIR" .

dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" --if-exists "$RESTORE_DB"
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$RESTORE_DB"
pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$RESTORE_DB" --clean --if-exists --no-owner "$DB_DUMP"

rm -rf "$RESTORE_ARTIFACTS_DIR"
mkdir -p "$RESTORE_ARTIFACTS_DIR"
tar xzf "$ARTIFACT_TGZ" -C "$RESTORE_ARTIFACTS_DIR"

RUN_COUNT="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$RESTORE_DB" -Atc "select count(*) from sd_agent_v2_runs")"
EVENT_COUNT="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$RESTORE_DB" -Atc "select count(*) from sd_agent_v2_run_events")"
ARTIFACT_COUNT="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$RESTORE_DB" -Atc "select count(*) from sd_agent_v2_run_artifacts")"
FILE_COUNT="$(find "$RESTORE_ARTIFACTS_DIR" -type f | wc -l | tr -d ' ')"

python3 - <<'PY' "$MANIFEST" "$DB_DUMP" "$ARTIFACT_TGZ" "$RUN_COUNT" "$EVENT_COUNT" "$ARTIFACT_COUNT" "$FILE_COUNT" "$RESTORE_DB" "$RESTORE_ARTIFACTS_DIR"
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

manifest, db_dump, artifact_tgz, run_count, event_count, artifact_count, file_count, restore_db, restore_artifacts = sys.argv[1:]

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

payload = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "restore_db": restore_db,
    "restore_artifacts_dir": restore_artifacts,
    "counts": {
        "runs": int(run_count),
        "events": int(event_count),
        "artifacts": int(artifact_count),
        "artifact_files": int(file_count),
    },
    "files": {
        "postgres": {"path": db_dump, "sha256": sha256(db_dump), "bytes": os.path.getsize(db_dump)},
        "artifacts": {"path": artifact_tgz, "sha256": sha256(artifact_tgz), "bytes": os.path.getsize(artifact_tgz)},
    },
}
if payload["counts"]["runs"] < 20 or payload["counts"]["artifacts"] < 20 or payload["counts"]["artifact_files"] < 20:
    raise SystemExit(f"DR drill counts too low: {payload['counts']}")
with open(manifest, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
