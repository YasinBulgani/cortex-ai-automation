#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
HOST=${HOST:-127.0.0.1}
API_PORT=${API_PORT:-8875}

cd "$ROOT_DIR/backend"
export PYTHONPATH=.
export APP_ENV=${APP_ENV:-ci}

if [ "$APP_ENV" = "ci" ] || [ "$APP_ENV" = "staging" ] || [ "$APP_ENV" = "production" ]; then
  : "${JWT_SECRET:?JWT_SECRET must be set for managed runtime}"
fi

exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$API_PORT"
