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

: "${DEPLOY_HOST:?DEPLOY_HOST is required}"
: "${DEPLOY_USER:?DEPLOY_USER is required}"
: "${DEPLOY_PATH:?DEPLOY_PATH is required}"

IMAGE_TAG="${IMAGE_TAG:-${GIT_COMMIT:-latest}}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-https://$DEPLOY_HOST/health}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE:-docker-compose.prod.yml}"
REMOTE_PULL_SERVICES="${REMOTE_PULL_SERVICES:-backend worker engine web ai-gateway}"

log "Deploying $TARGET_ENV with image tag $IMAGE_TAG"

mkdir -p "$HOME/.ssh"
ssh-keyscan -H "$DEPLOY_HOST" >> "$HOME/.ssh/known_hosts" 2>/dev/null

ssh "$DEPLOY_USER@$DEPLOY_HOST" "
  set -e
  cd '$DEPLOY_PATH' &&
  docker compose -f '$REMOTE_COMPOSE_FILE' up -d postgres redis &&
  IMAGE_TAG='$IMAGE_TAG' docker compose -f '$REMOTE_COMPOSE_FILE' pull $REMOTE_PULL_SERVICES &&
  IMAGE_TAG='$IMAGE_TAG' docker compose -f '$REMOTE_COMPOSE_FILE' run --rm backend alembic upgrade head &&
  IMAGE_TAG='$IMAGE_TAG' docker compose -f '$REMOTE_COMPOSE_FILE' up -d --remove-orphans
"

log "Waiting for $TARGET_ENV health check"
wait_for_http "$HEALTHCHECK_URL" 30 10
