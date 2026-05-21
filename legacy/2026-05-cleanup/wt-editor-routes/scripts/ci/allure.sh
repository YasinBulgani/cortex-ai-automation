#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$SCRIPT_DIR/common.sh"

ALLURE_RESULTS_DIR="${ALLURE_RESULTS_DIR:-$REPORTS_DIR/allure-results}"
ALLURE_REPORT_DIR="${ALLURE_REPORT_DIR:-$REPORTS_DIR/allure-report}"

ensure_reports_dir

if [[ ! -d "$ALLURE_RESULTS_DIR" ]] || ! find "$ALLURE_RESULTS_DIR" -type f | read -r _; then
  log "No Allure results found under $ALLURE_RESULTS_DIR"
  exit 0
fi

rm -rf "$ALLURE_REPORT_DIR"
mkdir -p "$ALLURE_REPORT_DIR"

if command -v allure >/dev/null 2>&1; then
  log "Generating Allure report with installed allure binary"
  allure generate "$ALLURE_RESULTS_DIR" --clean -o "$ALLURE_REPORT_DIR"
elif command -v npx >/dev/null 2>&1 && command -v java >/dev/null 2>&1; then
  log "Generating Allure report with npx allure-commandline"
  (cd "$ROOT_DIR" && npx --yes allure-commandline@latest generate "$ALLURE_RESULTS_DIR" --clean -o "$ALLURE_REPORT_DIR")
else
  log "Allure generation skipped: install allure binary or ensure java + npx are available"
  exit 1
fi

if [[ -f "$ALLURE_REPORT_DIR/index.html" ]]; then
  log "Allure report generated at $ALLURE_REPORT_DIR/index.html"
else
  log "Allure report generation did not produce index.html"
  exit 1
fi
