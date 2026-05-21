#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TestwrightAI Watchdog — 7/24 Sistem İzleyici
#
# Her 60 saniyede kontrol eder:
#   1. Ollama çalışıyor mu?         → değilse başlat
#   2. Docker container'lar UP mu?  → değilse restart et
#   3. Backend health endpoint OK?  → değilse restart et
#   4. Gece sessiz saatlerde (00-06) pipeline tetikle
#
# Kurulum (bir kez):
#   chmod +x scripts/twai_watchdog.sh
#   ./scripts/twai_watchdog.sh &
#   echo $! > /tmp/twai_watchdog.pid
#
# macOS servisi olarak kurmak için:
#   sudo cp scripts/com.testwrightai.watchdog.plist /Library/LaunchDaemons/
#   sudo launchctl load /Library/LaunchDaemons/com.testwrightai.watchdog.plist
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

BACKEND_URL="http://localhost:8000"
BACKEND_TOKEN=""          # İlk çalışmada otomatik alınır
LOG_FILE="/tmp/twai_watchdog.log"
CHECK_INTERVAL=60         # saniye
TRIGGER_HOUR_START=2      # Pipeline tetikleme başlangıcı (02:00)
TRIGGER_HOUR_END=3        # Pipeline tetikleme bitişi (03:00)
LAST_TRIGGER_DATE=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ── Token al ─────────────────────────────────────────────────────────────────
get_token() {
    local response
    response=$(curl -s -X POST "${BACKEND_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' 2>/dev/null)
    echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo ""
}

# ── Ollama kontrol ────────────────────────────────────────────────────────────
check_ollama() {
    if ! curl -sf "http://localhost:11434/api/tags" > /dev/null 2>&1; then
        log "⚠️  Ollama yanıt vermiyor — başlatılıyor..."
        # Launchd servisi varsa yeniden yükle, yoksa direkt başlat
        if sudo launchctl list com.testwrightai.ollama &>/dev/null; then
            sudo launchctl kickstart -k system/com.testwrightai.ollama 2>/dev/null || true
        else
            ollama serve &>/dev/null &
            sleep 5
        fi
        log "✅  Ollama yeniden başlatıldı."
        return 1
    fi
    return 0
}

# ── Docker container kontrol ─────────────────────────────────────────────────
check_docker() {
    local failed=0
    for container in twai_backend twai_postgres twai_redis; do
        local status
        status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
        if [ "$status" != "running" ]; then
            log "⚠️  Container $container durumu: $status — yeniden başlatılıyor..."
            docker start "$container" 2>/dev/null || true
            failed=1
        fi
    done
    return $failed
}

# ── Backend health kontrol ────────────────────────────────────────────────────
check_backend() {
    local response
    response=$(curl -sf "${BACKEND_URL}/health" 2>/dev/null || echo "error")
    if [ "$response" = "error" ]; then
        log "⚠️  Backend yanıt vermiyor — restart ediliyor..."
        docker restart twai_backend 2>/dev/null || true
        sleep 10
        return 1
    fi
    return 0
}

# ── Nightly pipeline tetikle ─────────────────────────────────────────────────
maybe_trigger_pipeline() {
    local current_hour
    current_hour=$(date +%H | sed 's/^0//')  # 0 padding kaldır
    local today
    today=$(date +%Y-%m-%d)

    # Sadece belirtilen saat aralığında ve günde bir kez tetikle
    if [ "$current_hour" -ge "$TRIGGER_HOUR_START" ] && \
       [ "$current_hour" -lt "$TRIGGER_HOUR_END" ] && \
       [ "$LAST_TRIGGER_DATE" != "$today" ]; then

        log "🚀 Nightly pipeline tetikleniyor..."

        # Token yoksa al
        if [ -z "$BACKEND_TOKEN" ]; then
            BACKEND_TOKEN=$(get_token)
        fi

        if [ -n "$BACKEND_TOKEN" ]; then
            local response
            response=$(curl -sf -X POST \
                "${BACKEND_URL}/api/v1/agents/banking/trigger-now?cycles=3" \
                -H "Authorization: Bearer ${BACKEND_TOKEN}" \
                -H "Content-Type: application/json" \
                -d '{}' 2>/dev/null || echo "error")

            if [ "$response" != "error" ]; then
                LAST_TRIGGER_DATE="$today"
                log "✅  Pipeline başlatıldı: $response"
            else
                log "❌  Pipeline tetiklenemedi"
            fi
        else
            log "❌  Token alınamadı, pipeline tetiklenemedi"
        fi
    fi
}

# ── Mac uyku engelleme ────────────────────────────────────────────────────────
prevent_sleep() {
    # caffeinate: Mac'i uyku moduna geçmekten engeller
    # -d: display sleep engelle, -i: system idle sleep engelle
    if ! pgrep -f "caffeinate" > /dev/null; then
        caffeinate -di &
        log "☕ Mac uyku modu engellendi (caffeinate)"
    fi
}

# ── Ana döngü ─────────────────────────────────────────────────────────────────
main() {
    log "🟢 TestwrightAI Watchdog başladı (PID: $$)"
    log "   Backend: ${BACKEND_URL}"
    log "   Kontrol aralığı: ${CHECK_INTERVAL}s"
    log "   Nightly trigger: ${TRIGGER_HOUR_START}:00 - ${TRIGGER_HOUR_END}:00"

    # Mac'i uyutma
    prevent_sleep

    while true; do
        # Ollama sağlık kontrolü
        check_ollama || sleep 5

        # Docker container kontrolü
        check_docker || sleep 10

        # Backend sağlık kontrolü
        check_backend || sleep 15

        # Nightly pipeline tetikleme
        maybe_trigger_pipeline

        sleep "$CHECK_INTERVAL"
    done
}

# Sinyal yakala — düzgün kapat
trap 'log "🔴 Watchdog durduruldu."; pkill -f caffeinate 2>/dev/null; exit 0' SIGTERM SIGINT

main
