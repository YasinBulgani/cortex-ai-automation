#!/bin/bash
# BGTS Test Automation Engine — Startup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════╗"
echo "║  BGTS Test Automation Engine                 ║"
echo "╚══════════════════════════════════════════════╝"

cd "$SCRIPT_DIR"

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
if [ -f "$ROOT_DIR/.env" ]; then
    export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
fi

ENGINE_PORT=${ENGINE_PORT:-5001}
EXECUTOR_PORT=${EXECUTOR_PORT:-5002}

echo ""
echo "▶ Starting Flask Engine on port $ENGINE_PORT..."
python app.py &
ENGINE_PID=$!

echo "▶ Starting Test Executor on port $EXECUTOR_PORT..."
PORT=$EXECUTOR_PORT python test_executor_server.py &
EXECUTOR_PID=$!

echo ""
echo "✅ Services started:"
echo "   Engine:   http://127.0.0.1:$ENGINE_PORT"
echo "   Executor: http://127.0.0.1:$EXECUTOR_PORT"
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $ENGINE_PID $EXECUTOR_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
