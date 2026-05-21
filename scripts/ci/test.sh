#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

SUITE="${1:-smoke}"

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://test_user:test_password@localhost:${CI_POSTGRES_PORT}/syndata_test}"
export REDIS_URL="${REDIS_URL:-redis://localhost:${CI_REDIS_PORT}/0}"
export TESTING="${TESTING:-true}"
export HEADLESS="${HEADLESS:-true}"
export TEST_ENV="${TEST_ENV:-ci}"
export CI="${CI:-true}"
export JWT_SECRET="${JWT_SECRET:-ci-test-secret-ci-test-secret-ci-test-secret}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$ROOT_DIR/.pw-browsers}"
export API_PORT="${API_PORT:-$CI_BACKEND_PORT}"
export APP_PORT="${APP_PORT:-$CI_APP_PORT}"
export ENGINE_PORT="${ENGINE_PORT:-$CI_ENGINE_PORT}"
export APP_URL="${APP_URL:-http://127.0.0.1:${APP_PORT}}"

backend_python() {
  venv_python backend
}

engine_python() {
  venv_python engine
}

run_frontend_checks() {
  log "Running frontend type check and build"
  install_node_deps

  (
    cd "$ROOT_DIR/apps/web"
    npx tsc --noEmit
    NEXT_PUBLIC_API_BASE="http://localhost:${API_PORT}" \
    NEXT_PUBLIC_ENGINE_URL="http://localhost:${ENGINE_PORT}" \
    npm run build
  )
}

run_backend_lint() {
  log "Running backend lint"
  install_backend_deps

  (
    cd "$ROOT_DIR/backend"
    "$(backend_python)" -m ruff check app/
    "$(backend_python)" -m mypy app/ --strict --ignore-missing-imports || true
  )
}

run_backend_smoke() {
  log "Running backend smoke tests"
  (
    cd "$ROOT_DIR/backend"
    PYTHONPATH=. "$(backend_python)" -m pytest -m smoke -v --tb=short \
      --junit-xml="$REPORTS_DIR/backend-smoke.xml"
  )
}

run_backend_service() {
  log "Running backend service tests"
  (
    cd "$ROOT_DIR/backend"
    PYTHONPATH=. "$(backend_python)" -m pytest \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=xml:"$REPORTS_DIR/backend-coverage.xml" \
      --cov-fail-under=50 \
      --junit-xml="$REPORTS_DIR/backend-service.xml" \
      -v
  )
}

run_backend_api() {
  log "Running backend API/RBAC/contract/security tests"
  (
    cd "$ROOT_DIR/backend"
    PYTHONPATH=. "$(backend_python)" -m pytest tests/api/ -v --tb=short \
      --junit-xml="$REPORTS_DIR/backend-api.xml"
    PYTHONPATH=. "$(backend_python)" -m pytest tests/rbac/ -v --tb=short \
      --junit-xml="$REPORTS_DIR/backend-rbac.xml"
    PYTHONPATH=. "$(backend_python)" -m pytest tests/contract/ -v --tb=short \
      --junit-xml="$REPORTS_DIR/backend-contract.xml"
    PYTHONPATH=. "$(backend_python)" -m pytest tests/security/ -v --tb=short \
      --junit-xml="$REPORTS_DIR/backend-security.xml"
  )
}

run_engine_unit() {
  log "Running engine unit tests"
  install_engine_deps

  (
    cd "$ROOT_DIR/engine"
    TEST_ENV=test HEADLESS=true "$(engine_python)" -m pytest tests/unit/ -v --tb=short \
      -m "not ai" \
      --junit-xml="$REPORTS_DIR/engine-unit.xml"
  )
}

run_bdd_api() {
  local pid_file="$REPORTS_DIR/backend.pid"

  log "Starting backend for BDD API tests"
  (
    cd "$ROOT_DIR/backend"
    PYTHONPATH=. JWT_SECRET="$JWT_SECRET" \
      "$(backend_python)" -m uvicorn app.main:app --host 127.0.0.1 --port "$CI_BACKEND_PORT" \
      >"$REPORTS_DIR/backend.log" 2>&1 &
    echo $! >"$pid_file"
  )

  wait_for_http "http://127.0.0.1:${CI_BACKEND_PORT}/health" 30 2

  log "Running BDD API tests"
  (
    cd "$ROOT_DIR/engine"
    BGTS_API_URL="http://127.0.0.1:${CI_BACKEND_PORT}" \
    TEST_ENV=test \
    HEADLESS=true \
    "$(engine_python)" -m pytest steps/api/ -v --tb=short \
      -m "not ai" \
      --alluredir="$REPORTS_DIR/allure-results" \
      --junit-xml="$REPORTS_DIR/bdd-api.xml"
  )

  cleanup_background_pid "$pid_file"
}

run_e2e() {
  local project="${1:-smoke}"

  log "Running Playwright project: $project"
  install_playwright

  (
    cd "$ROOT_DIR"
    TEST_ENV=ci \
    CI=true \
    DATABASE_URL="$DATABASE_URL" \
    API_PORT="$API_PORT" \
    APP_PORT="$APP_PORT" \
    ENGINE_PORT="$ENGINE_PORT" \
    APP_URL="$APP_URL" \
    npx playwright test --project="$project"
  )
}

main() {
  ensure_reports_dir

  case "$SUITE" in
    start-services)
      install_backend_deps
      start_ci_services
      wait_for_postgres
      ;;
    stop-services)
      stop_ci_services
      ;;
    prepare-db)
      install_backend_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      ;;
    smoke)
      run_frontend_checks
      run_backend_lint
      start_ci_services
      wait_for_postgres
      prepare_database
      run_backend_smoke
      run_engine_unit
      run_e2e smoke
      ;;
    standard)
      run_frontend_checks
      run_backend_lint
      start_ci_services
      wait_for_postgres
      prepare_database
      run_backend_smoke
      run_backend_service
      run_backend_api
      run_engine_unit
      run_bdd_api
      run_e2e smoke
      ;;
    full)
      run_frontend_checks
      run_backend_lint
      start_ci_services
      wait_for_postgres
      prepare_database
      run_backend_smoke
      run_backend_service
      run_backend_api
      run_engine_unit
      run_bdd_api
      run_e2e smoke
      run_e2e regression
      ;;
    frontend)
      run_frontend_checks
      ;;
    lint)
      run_backend_lint
      ;;
    engine-unit)
      run_engine_unit
      ;;
    backend-smoke)
      install_backend_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      run_backend_smoke
      ;;
    backend-service)
      install_backend_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      run_backend_service
      ;;
    backend-api)
      install_backend_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      run_backend_api
      ;;
    bdd-api)
      install_backend_deps
      install_engine_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      run_bdd_api
      ;;
    e2e-smoke)
      install_backend_deps
      install_engine_deps
      install_node_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      run_e2e smoke
      ;;
    e2e-regression)
      install_backend_deps
      install_engine_deps
      install_node_deps
      start_ci_services
      wait_for_postgres
      prepare_database
      run_e2e regression
      ;;
    *)
      echo "Unknown suite: $SUITE"
      echo "Usage: $0 [smoke|standard|full|frontend|lint|engine-unit|backend-smoke|backend-service|backend-api|bdd-api|e2e-smoke|e2e-regression|start-services|stop-services|prepare-db]"
      exit 1
      ;;
  esac
}

trap 'cleanup_background_pid "$REPORTS_DIR/backend.pid"; stop_ci_services' EXIT

main "$@"
