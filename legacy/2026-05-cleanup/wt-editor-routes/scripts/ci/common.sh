#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORTS_DIR="${REPORTS_DIR:-$ROOT_DIR/reports}"
BUILD_NUMBER_SAFE="${BUILD_NUMBER:-0}"
BUILD_OFFSET="$(( (BUILD_NUMBER_SAFE % 100) * 10 ))"
CI_POSTGRES_PORT="${CI_POSTGRES_PORT:-$((15432 + BUILD_OFFSET))}"
CI_REDIS_PORT="${CI_REDIS_PORT:-$((16379 + BUILD_OFFSET))}"
CI_BACKEND_PORT="${CI_BACKEND_PORT:-$((18000 + BUILD_OFFSET))}"
CI_APP_PORT="${CI_APP_PORT:-$((13000 + BUILD_OFFSET))}"
CI_ENGINE_PORT="${CI_ENGINE_PORT:-$((15001 + BUILD_OFFSET))}"
CI_INSTANCE_ID="${CI_INSTANCE_ID:-${BUILD_TAG:-local}}"
CI_INSTANCE_SLUG="$(printf '%s' "$CI_INSTANCE_ID" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
CI_POSTGRES_CONTAINER="jenkins-postgres-${CI_INSTANCE_SLUG}"
CI_REDIS_CONTAINER="jenkins-redis-${CI_INSTANCE_SLUG}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

ensure_reports_dir() {
  mkdir -p "$REPORTS_DIR"
}

venv_python() {
  local service_dir="$1"
  echo "$ROOT_DIR/$service_dir/.venv/bin/python"
}

ensure_python_venv() {
  local service_dir="$1"
  local requirements_file="$2"
  local venv_dir="$ROOT_DIR/$service_dir/.venv"
  local python_bin

  if [[ ! -d "$venv_dir" ]]; then
    log "Creating virtualenv for $service_dir"
    python3 -m venv "$venv_dir"
  fi

  python_bin="$(venv_python "$service_dir")"
  "$python_bin" -m pip install --upgrade pip
  "$python_bin" -m pip install -r "$ROOT_DIR/$service_dir/$requirements_file"
}

install_backend_deps() {
  ensure_python_venv "backend" "requirements.txt"
  "$(venv_python backend)" -m pip install -r "$ROOT_DIR/backend/requirements-dev.txt"
  "$(venv_python backend)" -m pip install ruff mypy
}

install_engine_deps() {
  ensure_python_venv "engine" "requirements.txt"
}

install_node_deps() {
  log "Installing root npm dependencies"
  (cd "$ROOT_DIR" && npm ci)

  log "Installing web npm dependencies"
  (cd "$ROOT_DIR/apps/web" && npm ci)
}

install_playwright() {
  log "Installing Playwright browser dependencies"
  (cd "$ROOT_DIR" && PLAYWRIGHT_BROWSERS_PATH=.pw-browsers npx playwright install chromium --with-deps)
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  else
    echo "docker-compose"
  fi
}

start_ci_services() {
  log "Starting CI services"
  docker rm -f "$CI_POSTGRES_CONTAINER" "$CI_REDIS_CONTAINER" >/dev/null 2>&1 || true

  docker run -d \
    --name "$CI_POSTGRES_CONTAINER" \
    -e POSTGRES_USER=test_user \
    -e POSTGRES_PASSWORD=test_password \
    -e POSTGRES_DB=syndata_test \
    -p "$CI_POSTGRES_PORT:5432" \
    postgres:16 >/dev/null

  docker run -d \
    --name "$CI_REDIS_CONTAINER" \
    -p "$CI_REDIS_PORT:6379" \
    redis:7-alpine >/dev/null
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-30}"
  local sleep_seconds="${3:-2}"

  for _ in $(seq 1 "$attempts"); do
    if curl -sf "$url" >/dev/null; then
      return 0
    fi
    sleep "$sleep_seconds"
  done

  log "Timed out waiting for $url"
  return 1
}

wait_for_postgres() {
  local python_bin
  python_bin="$(venv_python backend)"

  for _ in $(seq 1 30); do
    if DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://test_user:test_password@localhost:${CI_POSTGRES_PORT}/syndata_test}" \
      "$python_bin" - <<'PY'
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
PY
    then
      return 0
    fi
    sleep 2
  done

  log "Postgres did not become ready in time"
  return 1
}

stop_ci_services() {
  log "Stopping CI services"
  docker rm -f "$CI_POSTGRES_CONTAINER" "$CI_REDIS_CONTAINER" >/dev/null 2>&1 || true
}

prepare_database() {
  local python_bin
  python_bin="$(venv_python backend)"

  log "Running migrations and seed"
  (
    cd "$ROOT_DIR/backend"
    DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://test_user:test_password@localhost:${CI_POSTGRES_PORT}/syndata_test}" \
    PYTHONPATH=. \
    "$python_bin" -m alembic upgrade head

    DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://test_user:test_password@localhost:${CI_POSTGRES_PORT}/syndata_test}" \
    PYTHONPATH=. \
    "$python_bin" scripts/seed.py
  )
}

cleanup_background_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    kill "$(cat "$pid_file")" >/dev/null 2>&1 || true
    rm -f "$pid_file"
  fi
}
