#!/usr/bin/env bash
#
# BGTS Test Otomasyon Framework — Test Calistirma Komutlari
#
# Kullanim:
#   ./run_tests.sh unit          # Unit testler
#   ./run_tests.sh ui            # UI BDD testleri (Playwright)
#   ./run_tests.sh api           # API BDD testleri
#   ./run_tests.sh smoke         # Smoke testler
#   ./run_tests.sh all           # Tum testler
#   ./run_tests.sh tag critical  # Belirli tag'a gore
#   ./run_tests.sh allure        # Allure rapor goruntule
#
set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${CYAN}[BGTS]${NC} $*"; }

case "${1:-help}" in

  unit)
    log "Unit testler calistiriliyor..."
    python -m pytest tests/unit/ -v --tb=short -m "not ai" --noconftest \
      --junit-xml=reports/unit-results.xml
    ;;

  ui)
    log "UI BDD testleri calistiriliyor (Playwright)..."
    python -m pytest steps/ -v --tb=short \
      --alluredir=allure-results \
      -k "not api" \
      "${@:2}"
    ;;

  api)
    log "API BDD testleri calistiriliyor..."
    python -m pytest steps/api/ -v --tb=short \
      --alluredir=allure-results \
      "${@:2}"
    ;;

  smoke)
    log "Smoke testler calistiriliyor..."
    python -m pytest steps/ -v --tb=short \
      -m smoke \
      --alluredir=allure-results
    ;;

  critical)
    log "Critical testler calistiriliyor..."
    python -m pytest steps/ -v --tb=short \
      -m critical \
      --alluredir=allure-results
    ;;

  tag)
    TAG="${2:-smoke}"
    log "Tag: '${TAG}' testleri calistiriliyor..."
    python -m pytest steps/ -v --tb=short \
      -m "${TAG}" \
      --alluredir=allure-results \
      "${@:3}"
    ;;

  feature)
    FEATURE="${2:-login}"
    log "Feature: '${FEATURE}' calistiriliyor..."
    python -m pytest steps/ -v --tb=short \
      -k "${FEATURE}" \
      --alluredir=allure-results
    ;;

  all)
    log "Tum testler calistiriliyor..."
    python -m pytest tests/unit/ steps/ -v --tb=short \
      -m "not ai" \
      --alluredir=allure-results \
      --junit-xml=reports/all-results.xml \
      "${@:2}"
    ;;

  allure)
    log "Allure raporu olusturuluyor..."
    if command -v allure &>/dev/null; then
      allure serve allure-results
    else
      log "${YELLOW}Allure yuklu degil. Kurulum: brew install allure${NC}"
      log "Alternatif: allure-results/ dizinini allure.io'ya yukleyin"
    fi
    ;;

  env)
    ENV="${2:-test}"
    log "Ortam: '${ENV}' ile testler calistiriliyor..."
    TEST_ENV="${ENV}" python -m pytest steps/ -v --tb=short \
      --alluredir=allure-results \
      "${@:3}"
    ;;

  domain)
    DOMAIN="${2:-default}"
    log "Domain: '${DOMAIN}' ile testler calistiriliyor..."
    TEST_DOMAIN="${DOMAIN}" python -m pytest steps/ -v --tb=short \
      --alluredir=allure-results \
      "${@:3}"
    ;;

  multi-domain)
    DOMAINS="${2:-default,staging}"
    log "Multi-domain kosusu: '${DOMAINS}'"
    IFS=',' read -ra DOMAIN_ARR <<< "${DOMAINS}"
    for d in "${DOMAIN_ARR[@]}"; do
      log "Domain: ${d} calistiriliyor..."
      TEST_DOMAIN="${d}" python -m pytest steps/ -v --tb=short \
        --alluredir="allure-results-${d}" \
        "${@:3}" || true
    done
    log "Tum domain'ler tamamlandi."
    ;;

  help|*)
    echo ""
    echo -e "${GREEN}BGTS Test Otomasyon Framework — Komutlar${NC}"
    echo ""
    echo "  unit              Unit testleri calistir"
    echo "  ui                UI BDD testleri (Playwright)"
    echo "  api               API BDD testleri (httpx)"
    echo "  smoke             Smoke testleri calistir"
    echo "  critical          Critical oncelikli testler"
    echo "  tag <TAG>         Belirli tag ile calistir (ornek: tag regression)"
    echo "  feature <NAME>    Belirli feature calistir (ornek: feature login)"
    echo "  all               Tum testleri calistir"
    echo "  allure            Allure raporunu goruntule"
    echo "  env <ENV>         Belirli ortamda calistir (test/staging/prod)"
    echo "  domain <DOMAIN>   Belirli domain ile calistir"
    echo "  multi-domain <D>  Virgullu domain listesiyle calistir (ornek: default,staging)"
    echo "  help              Bu yardim mesaji"
    echo ""
    echo "Ornekler:"
    echo "  ./run_tests.sh unit"
    echo "  ./run_tests.sh ui -k login"
    echo "  ./run_tests.sh tag critical --headed"
    echo "  ./run_tests.sh env staging"
    echo "  ./run_tests.sh domain girit"
    echo ""
    ;;
esac
