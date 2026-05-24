#!/usr/bin/env bash
# ============================================================
# start-all.sh — TestwrightAI Monorepo Tek Komut Başlatıcı
# ============================================================
# Kullanım:
#   ./start-all.sh            # Tüm Docker servisleri
#   ./start-all.sh --dev      # Docker + frontend dev server
#   ./start-all.sh --ai-ui    # Docker + AI stack + Open WebUI
#   ./start-all.sh --no-ai    # AI stack olmadan başlat
#   ./start-all.sh --stop     # Tüm servisleri durdur
#   ./start-all.sh --status   # Servis durumlarını göster
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Renkler ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()    { echo -e "${GREEN}[TestwrightAI]${NC} $*"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }
header() { echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}"; }

COMPOSE_BIN=()
COMPOSE_FILES=()
COMPOSE_FILES_WITH_AI_UI=()
AI_COMPOSE_FILE="docker-compose.ai.yml"
ROOT_COMPOSE_FILE="docker-compose.yml"
USE_AI="${TWAI_ENABLE_AI_STACK:-true}"
USE_AI_UI="${TWAI_ENABLE_OPEN_WEBUI:-false}"

# ── Port Çakışması Kontrol ───────────────────────────────────
check_port() {
  local port=$1
  local name=$2
  if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    warn "Port $port ($name) zaten kullanımda — mevcut process devam eder."
    return 1
  fi
  return 0
}

# ── Yardım ───────────────────────────────────────────────────
usage() {
  echo "Kullanım: ./start-all.sh [--dev | --ai-ui | --no-ai | --stop | --status | --help]"
  echo ""
  echo "  (argümansız)   Docker servisleri başlat (postgres, redis, backend, engine)"
  echo "  --dev          Docker + frontend geliştirme sunucusu (port 3000)"
  echo "  --ai-ui        AI stack + Open WebUI ile başlat"
  echo "  --no-ai        AI stack olmadan başlat"
  echo "  --stop         Tüm servisleri durdur"
  echo "  --status       Çalışan servisleri göster"
  echo "  --help         Bu yardım mesajı"
  exit 0
}

compose_cmd() {
  "${COMPOSE_BIN[@]}" "${COMPOSE_FILES[@]}" "$@"
}

compose_cmd_with_ui() {
  "${COMPOSE_BIN[@]}" "${COMPOSE_FILES_WITH_AI_UI[@]}" "$@"
}

bool_true() {
  case "${1:-}" in
    true|TRUE|1|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_compose() {
  if docker compose version &>/dev/null; then
    COMPOSE_BIN=(docker compose)
  elif command -v docker-compose &>/dev/null; then
    COMPOSE_BIN=(docker-compose)
  else
    error "Docker Compose bulunamadı."
    exit 1
  fi

  COMPOSE_FILES=(-f "$ROOT_COMPOSE_FILE")
  COMPOSE_FILES_WITH_AI_UI=(-f "$ROOT_COMPOSE_FILE")

  if bool_true "$USE_AI" && [ -f "$AI_COMPOSE_FILE" ]; then
    COMPOSE_FILES+=(-f "$AI_COMPOSE_FILE")
    COMPOSE_FILES_WITH_AI_UI+=(-f "$AI_COMPOSE_FILE" --profile ui)
  fi
}

load_env_file() {
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
}

ensure_ollama_stack() {
  if ! bool_true "$USE_AI"; then
    return 0
  fi

  if [ ! -f scripts/ollama-warm.sh ]; then
    warn "scripts/ollama-warm.sh bulunamadı."
    return 1
  fi

  log "Ollama durumu kontrol ediliyor..."
  bash scripts/ollama-warm.sh || warn "Ollama warm-up tamamlanamadı."
}

# ── Durdur ───────────────────────────────────────────────────
stop_all() {
  header "Servisler Durduruluyor"
  load_env_file
  resolve_compose
  compose_cmd_with_ui down --remove-orphans
  log "Tüm Docker servisleri durduruldu."
  # Frontend dev server varsa durdur
  if [ -f /tmp/twai_frontend.pid ]; then
    kill "$(cat /tmp/twai_frontend.pid)" 2>/dev/null && rm /tmp/twai_frontend.pid && log "Frontend dev server durduruldu."
  fi
  exit 0
}

# ── Durum ────────────────────────────────────────────────────
show_status() {
  header "Servis Durumu"
  load_env_file
  resolve_compose
  compose_cmd_with_ui ps
  echo ""
  echo -e "${BLUE}Port Kontrolleri:${NC}"
  local entries=(
    "3000:Frontend"
    "8000:Backend-API"
    "5001:Engine"
    "5432:PostgreSQL"
    "6379:Redis"
    "8080:AI Gateway"
    "11434:Ollama"
  )
  if bool_true "$USE_AI_UI"; then
    entries+=("3001:Open WebUI")
  fi
  for entry in "${entries[@]}"; do
    port="${entry%%:*}"
    name="${entry##*:}"
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo -e "  ${GREEN}●${NC} $name (port $port) — ÇALIŞIYOR"
    else
      echo -e "  ${RED}○${NC} $name (port $port) — DURDU"
    fi
  done
  exit 0
}

# ── Argüman İşleme ───────────────────────────────────────────
DEV_MODE=false
for arg in "$@"; do
  case $arg in
    --dev)    DEV_MODE=true ;;
    --ai-ui)  USE_AI_UI=true; USE_AI=true ;;
    --no-ai)  USE_AI=false ;;
    --stop)   stop_all ;;
    --status) show_status ;;
    --help|-h) usage ;;
    *) error "Bilinmeyen argüman: $arg"; usage ;;
  esac
done

# ── Ön Koşul Kontrol ─────────────────────────────────────────
header "TestwrightAI Platformu Başlatılıyor"

if ! command -v docker &>/dev/null; then
  error "Docker bulunamadı. https://docs.docker.com/get-docker/ adresinden kur."
  exit 1
fi

# .env dosyası kontrolü
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    warn ".env dosyası yok — .env.example kopyalanıyor..."
    cp .env.example .env
    warn ".env dosyasını düzenle: OPENAI_API_KEY ve ANTHROPIC_API_KEY ekle"
  else
    warn ".env dosyası bulunamadı. Ortam değişkenlerini kontrol et."
  fi
fi

load_env_file
resolve_compose

# ── Port Kontrolleri ─────────────────────────────────────────
log "Port kontrolleri yapılıyor..."
check_port 5432 "PostgreSQL" || true
check_port 6379 "Redis"      || true
check_port 8000 "Backend"    || true
check_port 5001 "Engine"     || true
if bool_true "$USE_AI"; then
  check_port 8080 "AI Gateway" || true
fi
if bool_true "$USE_AI_UI"; then
  check_port 3001 "Open WebUI" || true
fi

# ── Docker Servisleri Başlat ─────────────────────────────────
ensure_ollama_stack
log "Docker servisleri başlatılıyor..."
if bool_true "$USE_AI_UI"; then
  compose_cmd_with_ui up -d --build
else
  compose_cmd up -d --build
fi

# ── Sağlık Kontrolleri ───────────────────────────────────────
log "Servisler hazır olana kadar bekleniyor..."

wait_for_service() {
  local name=$1
  local url=$2
  local retries=${3:-20}
  local i=0
  while [ $i -lt $retries ]; do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo -e "  ${GREEN}✓${NC} $name hazır"
      return 0
    fi
    i=$((i+1))
    sleep 2
  done
  warn "$name henüz hazır değil — arka planda başlıyor olabilir."
}

# PostgreSQL HTTP konuşmaz — pg_isready ile TCP sağlık kontrolü yap
if command -v pg_isready >/dev/null 2>&1; then
  echo -n "  PostgreSQL bekliyor..."
  for _i in $(seq 1 15); do
    pg_isready -h 127.0.0.1 -p 5432 -q && echo " ✓" && break
    sleep 2
  done
  pg_isready -h 127.0.0.1 -p 5432 -q || warn "PostgreSQL henüz hazır değil."
else
  warn "pg_isready bulunamadı — PostgreSQL sağlık kontrolü atlandı (Docker health check bekleniyor)."
fi
wait_for_service "Backend API" "http://localhost:8000/health" 20
wait_for_service "Engine"      "http://localhost:5001/health" 15
if bool_true "$USE_AI"; then
  wait_for_service "AI Gateway" "http://localhost:8080/ai/health" 20
fi
if bool_true "$USE_AI_UI"; then
  wait_for_service "Open WebUI" "http://localhost:3001" 20
fi

# ── Frontend Dev Server (--dev modunda) ──────────────────────
if $DEV_MODE; then
  log "Frontend geliştirme sunucusu başlatılıyor (port 3000)..."
  if [ -d apps/web ]; then
    cd apps/web
    if [ ! -d node_modules ]; then
      log "npm install çalıştırılıyor..."
      npm install --silent
    fi
    nohup npm run dev > /tmp/twai_frontend.log 2>&1 &
    echo $! > /tmp/twai_frontend.pid
    cd "$SCRIPT_DIR"
    sleep 3
    log "Frontend başlatıldı — log: /tmp/twai_frontend.log"
  else
    warn "apps/web dizini bulunamadı, frontend başlatılamadı."
  fi
fi

# ── Özet ─────────────────────────────────────────────────────
header "Servisler Hazır"
echo -e "  ${GREEN}●${NC} Backend API   → http://localhost:8000"
echo -e "  ${GREEN}●${NC} Swagger Docs  → http://localhost:8000/docs"
echo -e "  ${GREEN}●${NC} Engine        → http://localhost:5001"
echo -e "  ${GREEN}●${NC} PostgreSQL    → localhost:5432/twai_db"
echo -e "  ${GREEN}●${NC} Redis         → localhost:6379"
if bool_true "$USE_AI"; then
  echo -e "  ${GREEN}●${NC} AI Gateway    → http://localhost:8080"
  echo -e "  ${GREEN}●${NC} Ollama API    → http://localhost:11434"
  echo -e "  ${GREEN}●${NC} Ops Agent     → backend içinde planlı çalışır"
fi
if bool_true "$USE_AI_UI"; then
  echo -e "  ${GREEN}●${NC} Open WebUI    → http://localhost:3001"
fi
if $DEV_MODE; then
  echo -e "  ${GREEN}●${NC} Frontend      → http://localhost:3000"
fi
echo ""
echo -e "  Durdurmak için: ${YELLOW}./start-all.sh --stop${NC}"
echo -e "  Durum için:     ${YELLOW}./start-all.sh --status${NC}"
echo -e "  Testler için:   ${YELLOW}make test-smoke${NC}"
