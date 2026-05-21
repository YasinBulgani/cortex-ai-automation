#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <url> [max_attempts] [sleep_seconds]" >&2
  exit 1
fi

URL=$1
MAX_ATTEMPTS=${2:-30}
SLEEP_SECONDS=${3:-2}
ATTEMPT=1

while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
  if curl --fail --silent --show-error "$URL" >/dev/null 2>&1; then
    exit 0
  fi

  echo "Waiting for $URL ($ATTEMPT/$MAX_ATTEMPTS)..." >&2
  sleep "$SLEEP_SECONDS"
  ATTEMPT=$((ATTEMPT + 1))
done

echo "Timed out waiting for $URL" >&2
exit 1
