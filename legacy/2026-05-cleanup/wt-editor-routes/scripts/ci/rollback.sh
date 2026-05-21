#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

TARGET_ENV="${1:-}"

if [[ -z "$TARGET_ENV" ]]; then
  echo "Usage: $0 [staging|production]"
  exit 1
fi

if [[ "$TARGET_ENV" != "staging" && "$TARGET_ENV" != "production" ]]; then
  echo "TARGET_ENV must be staging or production"
  exit 1
fi

: "${DEPLOY_HOST:?DEPLOY_HOST is required}"
: "${DEPLOY_USER:?DEPLOY_USER is required}"
: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${ROLLBACK_IMAGE_TAG:?ROLLBACK_IMAGE_TAG is required}"

if [[ "$ROLLBACK_IMAGE_TAG" == "latest" ]]; then
  echo "ROLLBACK_IMAGE_TAG=latest is not allowed for rollback"
  exit 1
fi

if [[ "$ROLLBACK_IMAGE_TAG" =~ [[:space:]] ]]; then
  echo "ROLLBACK_IMAGE_TAG must not contain whitespace"
  exit 1
fi

HEALTHCHECK_URL="${HEALTHCHECK_URL:-https://$DEPLOY_HOST/health}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE:-docker-compose.prod.yml}"
REMOTE_PULL_SERVICES="${REMOTE_PULL_SERVICES:-backend worker engine web ai-gateway}"
SKIP_HEALTHCHECK="${SKIP_HEALTHCHECK:-false}"
ROLLBACK_REASON="${ROLLBACK_REASON:-manual rollback}"
ROLLBACK_METADATA_FILE="${ROLLBACK_METADATA_FILE:-$REPORTS_DIR/rollback-metadata.json}"

ensure_reports_dir

log "Rolling back $TARGET_ENV to image tag $ROLLBACK_IMAGE_TAG"

mkdir -p "$HOME/.ssh"
ssh-keyscan -H "$DEPLOY_HOST" >> "$HOME/.ssh/known_hosts" 2>/dev/null

ssh "$DEPLOY_USER@$DEPLOY_HOST" "
  set -e
  cd '$DEPLOY_PATH' &&
  docker compose -f '$REMOTE_COMPOSE_FILE' up -d postgres redis &&
  IMAGE_TAG='$ROLLBACK_IMAGE_TAG' docker compose -f '$REMOTE_COMPOSE_FILE' pull $REMOTE_PULL_SERVICES &&
  IMAGE_TAG='$ROLLBACK_IMAGE_TAG' docker compose -f '$REMOTE_COMPOSE_FILE' up -d --remove-orphans
"

if [[ "$SKIP_HEALTHCHECK" == "true" ]]; then
  log "Skipping health check because SKIP_HEALTHCHECK=true"
else
  log "Waiting for $TARGET_ENV health check"
  wait_for_http "$HEALTHCHECK_URL" 30 10
fi

python3 - <<'PY' "$ROLLBACK_METADATA_FILE" "$TARGET_ENV" "$ROLLBACK_IMAGE_TAG" "$ROLLBACK_REASON" "$HEALTHCHECK_URL" "$SKIP_HEALTHCHECK"
import json
import os
import sys
from datetime import datetime, timezone

path, target_env, image_tag, reason, healthcheck_url, skip_healthcheck = sys.argv[1:]
payload = {
    "action": "rollback",
    "target_env": target_env,
    "image_tag": image_tag,
    "reason": reason,
    "healthcheck_url": healthcheck_url,
    "skip_healthcheck": skip_healthcheck == "true",
    "job_name": os.environ.get("JOB_NAME", "local"),
    "build_number": os.environ.get("BUILD_NUMBER", "0"),
    "build_url": os.environ.get("BUILD_URL", ""),
    "git_commit": os.environ.get("GIT_COMMIT", ""),
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
}

with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
    fh.write("\n")
PY

log "Rollback metadata written to $ROLLBACK_METADATA_FILE"
