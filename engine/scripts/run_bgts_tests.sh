#!/usr/bin/env bash
#
# run_bgts_tests.sh — BGTS E2E test koşu betiği
#
# Kullanım:
#   ./engine/scripts/run_bgts_tests.sh --smoke
#   ./engine/scripts/run_bgts_tests.sh --regression --parallel
#   ./engine/scripts/run_bgts_tests.sh --api
#   ./engine/scripts/run_bgts_tests.sh --all --headed
#   ./engine/scripts/run_bgts_tests.sh --feature login
#   ./engine/scripts/run_bgts_tests.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$ENGINE_DIR/.." && pwd)"

# Varsayılan değerler
SCOPE=""
FEATURE=""
PARALLEL=0
HEADED=false
RETRY=0
REPORT=true
OPEN_REPORT=false
JSON_OUTPUT=""
EXTRA_ARGS=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    echo ""
    echo -e "${CYAN}BGTS E2E Test Runner${NC}"
    echo ""
    echo "Kullanım: $0 [SEÇENEKLER]"
    echo ""
    echo "Test Kapsamı (biri zorunlu):"
    echo "  --smoke              Smoke testlerini çalıştır"
    echo "  --regression         Regresyon testlerini çalıştır"
    echo "  --api                API testlerini çalıştır"
    echo "  --all                Tüm testleri çalıştır"
    echo "  --feature NAME       Belirli feature'ı çalıştır (ör: login, projects)"
    echo ""
    echo "Seçenekler:"
    echo "  --parallel [N]       Paralel çalıştır (varsayılan: 4 worker)"
    echo "  --headed             Tarayıcıyı görünür modda aç"
    echo "  --retry N            Başarısız testleri N kez yeniden dene"
    echo "  --no-report          Allure raporu üretme"
    echo "  --open               Raporu tarayıcıda aç"
    echo "  --json PATH          Sonuçları JSON'a kaydet"
    echo "  --help               Bu yardım mesajını göster"
    echo ""
    echo "Örnekler:"
    echo "  $0 --smoke"
    echo "  $0 --regression --parallel 4 --retry 2"
    echo "  $0 --feature login --headed"
    echo "  $0 --all --json /tmp/sonuc.json"
    echo ""
}

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           BGTS E2E Test Runner                  ║${NC}"
    echo -e "${CYAN}║           $(date '+%d.%m.%Y %H:%M:%S')                     ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Argüman ayrıştırma
while [[ $# -gt 0 ]]; do
    case $1 in
        --smoke)
            SCOPE="smoke"
            shift
            ;;
        --regression)
            SCOPE="regression"
            shift
            ;;
        --api)
            SCOPE="api"
            shift
            ;;
        --all)
            SCOPE="all"
            shift
            ;;
        --feature)
            SCOPE="feature"
            FEATURE="${2:-}"
            if [ -z "$FEATURE" ]; then
                echo -e "${RED}Hata: --feature parametresi bir isim gerektirir${NC}"
                exit 1
            fi
            shift 2
            ;;
        --parallel)
            if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
                PARALLEL=$2
                shift 2
            else
                PARALLEL=4
                shift
            fi
            ;;
        --headed)
            HEADED=true
            shift
            ;;
        --retry)
            RETRY="${2:-2}"
            shift 2
            ;;
        --no-report)
            REPORT=false
            shift
            ;;
        --open)
            OPEN_REPORT=true
            shift
            ;;
        --json)
            JSON_OUTPUT="${2:-}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

if [ -z "$SCOPE" ]; then
    echo -e "${RED}Hata: Test kapsamı belirtilmedi.${NC}"
    usage
    exit 1
fi

print_header

# Ortam ayarları
export HEADLESS="true"
if [ "$HEADED" = true ]; then
    export HEADLESS="false"
    echo -e "${YELLOW}Tarayıcı: Headed mod (görünür)${NC}"
else
    echo -e "${CYAN}Tarayıcı: Headless mod${NC}"
fi

export TEST_ENV="${TEST_ENV:-test}"
export BASE_URL="${BASE_URL:-http://localhost:3000}"

echo -e "${CYAN}Ortam: $TEST_ENV${NC}"
echo -e "${CYAN}Base URL: $BASE_URL${NC}"
echo ""

# Runner komutu oluştur
RUNNER_CMD="python bgts_runner.py"

case $SCOPE in
    smoke)
        RUNNER_CMD="$RUNNER_CMD --smoke"
        echo -e "${GREEN}Kapsam: Smoke Testleri${NC}"
        ;;
    regression)
        RUNNER_CMD="$RUNNER_CMD --regression"
        echo -e "${GREEN}Kapsam: Regresyon Testleri${NC}"
        ;;
    api)
        RUNNER_CMD="$RUNNER_CMD --api"
        echo -e "${GREEN}Kapsam: API Testleri${NC}"
        ;;
    all)
        RUNNER_CMD="$RUNNER_CMD --all"
        echo -e "${GREEN}Kapsam: Tüm Testler${NC}"
        ;;
    feature)
        RUNNER_CMD="$RUNNER_CMD --feature $FEATURE"
        echo -e "${GREEN}Kapsam: Feature — $FEATURE${NC}"
        ;;
esac

if [ "$PARALLEL" -gt 0 ]; then
    RUNNER_CMD="$RUNNER_CMD --parallel $PARALLEL"
    echo -e "${CYAN}Paralel: $PARALLEL worker${NC}"
fi

if [ "$RETRY" -gt 0 ]; then
    RUNNER_CMD="$RUNNER_CMD --retry $RETRY"
    echo -e "${CYAN}Retry: $RETRY deneme${NC}"
fi

if [ "$REPORT" = true ]; then
    RUNNER_CMD="$RUNNER_CMD --report"
fi

if [ -n "$JSON_OUTPUT" ]; then
    RUNNER_CMD="$RUNNER_CMD --json-output $JSON_OUTPUT"
fi

echo ""
echo -e "${YELLOW}Komut: $RUNNER_CMD${NC}"
echo ""

START_TIME=$(date +%s)

cd "$ENGINE_DIR"
EXIT_CODE=0
eval "$RUNNER_CMD" || EXIT_CODE=$?

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Sonuç: BAŞARILI${NC}"
else
    echo -e "${RED}Sonuç: BAŞARISIZ (çıkış kodu: $EXIT_CODE)${NC}"
fi

echo -e "${CYAN}Süre: ${MINUTES}dk ${SECONDS}sn${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

# Raporu tarayıcıda aç
if [ "$OPEN_REPORT" = true ] && [ "$REPORT" = true ]; then
    ALLURE_REPORT_DIR="$ENGINE_DIR/allure-report"
    if [ -d "$ALLURE_REPORT_DIR" ]; then
        echo -e "${CYAN}Allure raporu açılıyor...${NC}"
        if command -v allure &>/dev/null; then
            allure open "$ALLURE_REPORT_DIR" &
        elif command -v open &>/dev/null; then
            open "$ALLURE_REPORT_DIR/index.html"
        elif command -v xdg-open &>/dev/null; then
            xdg-open "$ALLURE_REPORT_DIR/index.html"
        fi
    fi
fi

exit $EXIT_CODE
