#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_PORT=${APP_PORT:-3417}

cd "$ROOT_DIR/apps/web"

exec npx next start -p "$APP_PORT"
