#!/usr/bin/env bash
# ==============================================
#  Cortex Dashboard - macOS / Linux starter
# ==============================================
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null; then
  echo "HATA: python3 kurulu degil."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r python_server/requirements.txt

export DASHBOARD_PORT="${DASHBOARD_PORT:-5001}"
( sleep 2 && (command -v xdg-open >/dev/null && xdg-open "http://localhost:${DASHBOARD_PORT}" \
            || command -v open >/dev/null && open "http://localhost:${DASHBOARD_PORT}" \
            || true) ) &

python python_server/flask_api.py
