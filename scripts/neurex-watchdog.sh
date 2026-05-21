#!/usr/bin/env bash
# =============================================================================
# NeurexQA Watchdog — Servis İzleyici & Otomatik Kurtarıcı
# =============================================================================
# Yaptıkları:
#   1. Her 30 saniyede backend (8000) ve engine (5001) health kontrolü
#   2. Servis düşmüşse → otomatik yeniden başlat
#   3. Her 10 dakikada Playwright zombie'lerini temizle (>20 dk çalışanlar)
#   4. macOS bildirimi gönder (servis ölünce + kurtarılınca)
#   5. /tmp/neurex-watchdog.log dosyasına kayıt
#
# Manuel kullanım:
#   scripts/neurex-watchdog.sh           # ön planda çalıştır
#   scripts/neurex-watchdog.sh &         # arka planda çalıştır
#
# LaunchAgent ile otomatik kurulum:
#   scripts/neurex install               # tek komutla kur
# =============================================================================

set -uo pipefail

# ── Sabitler ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
LOG_FILE="/tmp/neurex-watchdog.log"
PID_FILE="/tmp/neurex-watchdog.pid"

BACKEND_PORT=8000
ENGINE_PORT=5001
CHECK_INTERVAL=30          # saniye — servis kontrol periyodu
PLAYWRIGHT_CHECK_INTERVAL=600  # saniye — zombie temizleme periyodu (10 dk)
PLAYWRIGHT_MAX_AGE=1200    # saniye — bu süreden uzun çalışan chrome öldür (20 dk)

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
SYSTEM_PYTHON="/opt/homebrew/bin/python3.11"

# Renk kodları
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Log ───────────────────────────────────────────────────────────────────────
log() {
    local level="$1"; shift
    local msg="$*"
    local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$ts] [$level] $msg" >> "$LOG_FILE"
    case "$level" in
        INFO)  echo -e "${GREEN}[$ts]${NC} $msg" ;;
        WARN)  echo -e "${YELLOW}[$ts] ⚠️  $msg${NC}" ;;
        ERROR) echo -e "${RED}[$ts] ❌ $msg${NC}" ;;
        OK)    echo -e "${CYAN}[$ts] ✅ $msg${NC}" ;;
    esac
}

# ── macOS bildirimi ───────────────────────────────────────────────────────────
notify() {
    local title="$1"
    local msg="$2"
    osascript -e "display notification \"$msg\" with title \"$title\" sound name \"Basso\"" 2>/dev/null || true
}

# ── .env yükle ────────────────────────────────────────────────────────────────
load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$ENV_FILE"
        set +a
    else
        log WARN ".env dosyası bulunamadı: $ENV_FILE"
    fi
}

# ── Health check ──────────────────────────────────────────────────────────────
is_healthy() {
    local port="$1"
    local path="${2:-/health}"
    curl -sf --max-time 5 "http://localhost:${port}${path}" > /dev/null 2>&1
}

# ── Backend başlat ────────────────────────────────────────────────────────────
start_backend() {
    log INFO "Backend başlatılıyor (port $BACKEND_PORT)..."
    local python_bin="$SYSTEM_PYTHON"

    # .venv varsa onu tercih et
    if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
        python_bin="$VENV_PYTHON"
    fi

    cd "$PROJECT_ROOT/backend" || return 1

    nohup "$python_bin" -m uvicorn app.main:app \
        --host 127.0.0.1 \
        --port "$BACKEND_PORT" \
        >> "/tmp/neurex-backend.log" 2>&1 &

    local pid=$!
    echo "$pid" > "/tmp/neurex-backend.pid"
    log INFO "Backend PID: $pid — log: /tmp/neurex-backend.log"

    # Hazır olana kadar bekle (max 20 sn)
    local i=0
    while [ $i -lt 20 ]; do
        sleep 1
        if is_healthy "$BACKEND_PORT"; then
            log OK "Backend hazır (port $BACKEND_PORT)"
            notify "NeurexQA" "Backend yeniden başlatıldı ✅"
            return 0
        fi
        i=$((i+1))
    done

    log ERROR "Backend başlatılamadı — log: /tmp/neurex-backend.log"
    notify "NeurexQA ⚠️" "Backend başlatılamadı! Log: /tmp/neurex-backend.log"
    return 1
}

# ── Engine başlat ─────────────────────────────────────────────────────────────
start_engine() {
    log INFO "Engine başlatılıyor (port $ENGINE_PORT)..."
    local python_bin="$VENV_PYTHON"

    # .venv yoksa sistem Python'unu dene
    if [ ! -f "$python_bin" ]; then
        python_bin="$SYSTEM_PYTHON"
        log WARN ".venv bulunamadı, sistem Python kullanılıyor: $python_bin"
    fi

    cd "$PROJECT_ROOT/engine" || return 1

    nohup "$python_bin" app.py \
        >> "/tmp/neurex-engine.log" 2>&1 &

    local pid=$!
    echo "$pid" > "/tmp/neurex-engine.pid"
    log INFO "Engine PID: $pid — log: /tmp/neurex-engine.log"

    local i=0
    while [ $i -lt 20 ]; do
        sleep 1
        if is_healthy "$ENGINE_PORT"; then
            log OK "Engine hazır (port $ENGINE_PORT)"
            notify "NeurexQA" "Engine yeniden başlatıldı ✅"
            return 0
        fi
        i=$((i+1))
    done

    log ERROR "Engine başlatılamadı — log: /tmp/neurex-engine.log"
    notify "NeurexQA ⚠️" "Engine başlatılamadı! Log: /tmp/neurex-engine.log"
    return 1
}

# ── Playwright zombie temizliği ───────────────────────────────────────────────
cleanup_playwright_zombies() {
    local now; now=$(date +%s)
    local killed=0

    # $PLAYWRIGHT_MAX_AGE saniyeden uzun çalışan chrome-headless-shell'leri öldür
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue

        # Process'in başlangıç zamanını al
        local start_time
        start_time=$(ps -o lstart= -p "$pid" 2>/dev/null) || continue
        local start_epoch
        start_epoch=$(date -j -f "%a %b %d %T %Y" "$start_time" +%s 2>/dev/null) || continue

        local age=$(( now - start_epoch ))
        if [ "$age" -gt "$PLAYWRIGHT_MAX_AGE" ]; then
            local age_min=$(( age / 60 ))
            log WARN "Playwright zombie bulundu — PID: $pid, yaş: ${age_min} dakika → öldürülüyor"
            kill -9 "$pid" 2>/dev/null || true
            killed=$((killed+1))
        fi
    done < <(pgrep -f "chrome-headless-shell" 2>/dev/null || true)

    # Orphan Playwright node driver'larını da temizle (parent'ı ölmüş)
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        local ppid
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ') || continue
        # Parent process yoksa orphan
        if ! kill -0 "$ppid" 2>/dev/null; then
            log WARN "Orphan Playwright driver — PID: $pid → temizleniyor"
            kill -9 "$pid" 2>/dev/null || true
            killed=$((killed+1))
        fi
    done < <(pgrep -f "playwright/driver/node" 2>/dev/null || true)

    if [ "$killed" -gt 0 ]; then
        log OK "$killed adet Playwright zombie temizlendi"
        notify "NeurexQA" "$killed Playwright zombie temizlendi 🧹"
    fi
}

# ── Servis kontrol döngüsü ────────────────────────────────────────────────────
check_services() {
    # Backend
    if ! is_healthy "$BACKEND_PORT"; then
        log WARN "Backend yanıt vermiyor (port $BACKEND_PORT)"
        notify "NeurexQA ⚠️" "Backend çöktü — yeniden başlatılıyor..."
        # Eski process varsa öldür
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        sleep 2
        start_backend || true
    fi

    # Engine
    if ! is_healthy "$ENGINE_PORT"; then
        log WARN "Engine yanıt vermiyor (port $ENGINE_PORT)"
        notify "NeurexQA ⚠️" "Engine çöktü — yeniden başlatılıyor..."
        pkill -f "python app.py" 2>/dev/null || true
        sleep 2
        start_engine || true
    fi
}

# ── Ana döngü ─────────────────────────────────────────────────────────────────
main() {
    # Çakışma önle — zaten çalışıyor mu?
    if [ -f "$PID_FILE" ]; then
        local old_pid; old_pid=$(cat "$PID_FILE")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "Watchdog zaten çalışıyor (PID: $old_pid)"
            exit 0
        fi
    fi
    echo $$ > "$PID_FILE"

    load_env

    log INFO "=========================================="
    log INFO "NeurexQA Watchdog başladı (PID: $$)"
    log INFO "Proje: $PROJECT_ROOT"
    log INFO "Kontrol aralığı: ${CHECK_INTERVAL}s"
    log INFO "Playwright temizleme: her ${PLAYWRIGHT_CHECK_INTERVAL}s"
    log INFO "=========================================="

    local last_playwright_check=0

    while true; do
        # Servis sağlık kontrolü
        check_services

        # Periyodik Playwright zombie temizliği
        local now; now=$(date +%s)
        if [ $(( now - last_playwright_check )) -ge "$PLAYWRIGHT_CHECK_INTERVAL" ]; then
            cleanup_playwright_zombies
            last_playwright_check=$now
        fi

        sleep "$CHECK_INTERVAL"
    done
}

# Temiz kapatma
trap 'log INFO "Watchdog durduruldu (PID: $$)"; rm -f "$PID_FILE"; exit 0' SIGTERM SIGINT SIGQUIT

main
