#!/usr/bin/env bash

set -euo pipefail

PIPELINE_NAME="${1:-jenkins}"
BUILD_STATUS="${2:-UNKNOWN}"
DETAIL_URL="${3:-}"

JOB_NAME_VALUE="${JOB_NAME:-local-job}"
BUILD_NUMBER_VALUE="${BUILD_NUMBER:-0}"
GIT_BRANCH_VALUE="${BRANCH_NAME:-${GIT_BRANCH:-unknown}}"
GIT_COMMIT_VALUE="${GIT_COMMIT:-unknown}"
IMAGE_TAG_VALUE="${IMAGE_TAG:-}"
TARGET_ENV_VALUE="${TARGET_ENV:-}"
TEST_SUITE_VALUE="${TEST_SUITE:-}"
ROLLBACK_REASON_VALUE="${ROLLBACK_REASON:-}"
WEBHOOK_URL="${NOTIFY_WEBHOOK_URL:-}"

message="[$PIPELINE_NAME] $BUILD_STATUS
Job: $JOB_NAME_VALUE #$BUILD_NUMBER_VALUE
Branch: $GIT_BRANCH_VALUE
Commit: $GIT_COMMIT_VALUE"

if [[ -n "$TEST_SUITE_VALUE" ]]; then
  message="$message
Test suite: $TEST_SUITE_VALUE"
fi

if [[ -n "$TARGET_ENV_VALUE" ]]; then
  message="$message
Target env: $TARGET_ENV_VALUE"
fi

if [[ -n "$IMAGE_TAG_VALUE" ]]; then
  message="$message
Image tag: $IMAGE_TAG_VALUE"
fi

if [[ -n "$ROLLBACK_REASON_VALUE" ]]; then
  message="$message
Rollback reason: $ROLLBACK_REASON_VALUE"
fi

if [[ -n "$DETAIL_URL" ]]; then
  message="$message
Build URL: $DETAIL_URL"
fi

if [[ -z "$WEBHOOK_URL" ]]; then
  printf '%s\n' "Notification skipped: NOTIFY_WEBHOOK_URL is not set"
  exit 0
fi

if [[ "$WEBHOOK_URL" == *"office.com"* ]] || [[ "$WEBHOOK_URL" == *"office365.com"* ]]; then
  payload=$(python3 - <<'PY' "$message"
import json
import sys

print(json.dumps({"text": sys.argv[1]}))
PY
)
else
  payload=$(python3 - <<'PY' "$message"
import json
import sys

print(json.dumps({"text": sys.argv[1]}))
PY
)
fi

curl -fsS -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$payload" >/dev/null

printf '%s\n' "Notification sent: $PIPELINE_NAME / $BUILD_STATUS"
