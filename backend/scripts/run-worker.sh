#!/bin/sh
# RQ, REDIS_URL ortam değişkenini tek başına okumaz; -u ile verilmeli.
# macOS'ta fork uyarısı için: https://github.com/rq/rq/issues/921
cd "$(dirname "$0")/.."
export PYTHONPATH=.
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY="${OBJC_DISABLE_INITIALIZE_FORK_SAFETY:-YES}"
exec rq worker -u "${REDIS_URL:-redis://127.0.0.1:6379/0}" syndata_jobs
