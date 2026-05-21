#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
ENGINE_PORT=${ENGINE_PORT:-5001}

cd "$ROOT_DIR/engine"
export PYTHONPATH=.
export ENGINE_PORT
export APP_ENV=${APP_ENV:-ci}
export CI=${CI:-true}
export DEBUG=0
export ENGINE_DEBUG=0

if [ "$APP_ENV" = "ci" ] || [ "$APP_ENV" = "staging" ] || [ "$APP_ENV" = "production" ]; then
  : "${ENGINE_SECRET_KEY:?ENGINE_SECRET_KEY must be set for managed runtime}"
  : "${ENGINE_INTERNAL_KEY:?ENGINE_INTERNAL_KEY must be set for managed runtime}"
fi

exec "$PYTHON_BIN" app.py
