#!/usr/bin/env bash
set -euo pipefail

OLLAMA_HOST="${TWAI_OLLAMA_HOST:-${OLLAMA_HOST:-http://127.0.0.1:11434}}"
WARM_MODELS_RAW="${TWAI_OLLAMA_WARM_MODELS:-${OLLAMA_MODEL:-llama3.1:8b}}"
KEEP_ALIVE="${TWAI_OLLAMA_KEEP_ALIVE:--1}"
AUTO_START="${TWAI_AUTO_START_OLLAMA:-true}"

STATUS_ONLY=false
START_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --status) STATUS_ONLY=true ;;
    --start-only) START_ONLY=true ;;
    --help|-h)
      cat <<'EOF'
Kullanım: scripts/ollama-warm.sh [--status] [--start-only]

Ortam değişkenleri:
  TWAI_OLLAMA_HOST          Varsayılan: http://127.0.0.1:11434
  TWAI_OLLAMA_WARM_MODELS   Virgülle ayrılmış model listesi
  TWAI_OLLAMA_KEEP_ALIVE    Varsayılan: -1 (bellekte tut)
  TWAI_AUTO_START_OLLAMA    Varsayılan: true
EOF
      exit 0
      ;;
    *)
      echo "[ollama] bilinmeyen argüman: $arg" >&2
      exit 1
      ;;
  esac
done

log() {
  echo "[ollama] $*"
}

warn() {
  echo "[ollama][warn] $*" >&2
}

is_available() {
  curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1
}

wait_for_ollama() {
  local retries="${1:-30}"
  local i=0
  while [ "$i" -lt "$retries" ]; do
    if is_available; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}

start_ollama() {
  if is_available; then
    return 0
  fi

  if [ "$AUTO_START" != "true" ]; then
    warn "Ollama erişilemiyor ve otomatik başlatma kapalı."
    return 1
  fi

  if [[ "$OSTYPE" == darwin* ]] && open -Ra Ollama >/dev/null 2>&1; then
    log "Ollama uygulaması açılıyor..."
    open -ga Ollama
  elif command -v ollama >/dev/null 2>&1; then
    log "Ollama serve arka planda başlatılıyor..."
    nohup ollama serve >/tmp/twai_ollama.log 2>&1 &
    echo $! >/tmp/twai_ollama.pid
  else
    warn "Ollama binary bulunamadı."
    return 1
  fi

  if wait_for_ollama 30; then
    log "Ollama hazır."
    return 0
  fi

  warn "Ollama başlatıldı ama API hazır olmadı: ${OLLAMA_HOST}"
  return 1
}

warm_model() {
  local model="$1"
  local keep_alive_json
  [ -n "$model" ] || return 0

  if [[ "$KEEP_ALIVE" =~ ^-?[0-9]+$ ]]; then
    keep_alive_json="$KEEP_ALIVE"
  else
    keep_alive_json="\"$KEEP_ALIVE\""
  fi

  log "Model ısıtılıyor: ${model} (keep_alive=${KEEP_ALIVE})"
  if ! curl -fsS "${OLLAMA_HOST}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${model}\",\"prompt\":\"ping\",\"stream\":false,\"keep_alive\":${keep_alive_json}}" \
    >/dev/null; then
    warn "Model ısıtılamadı: ${model}"
    return 1
  fi

  log "Model hazır: ${model}"
}

show_status() {
  if command -v ollama >/dev/null 2>&1; then
    ollama ps || true
  else
    curl -fsS "${OLLAMA_HOST}/api/tags" || true
  fi
}

start_ollama

if $STATUS_ONLY; then
  show_status
  exit 0
fi

if $START_ONLY; then
  exit 0
fi

IFS=',' read -r -a MODELS <<<"$WARM_MODELS_RAW"
for raw_model in "${MODELS[@]}"; do
  model="$(echo "$raw_model" | xargs)"
  [ -n "$model" ] || continue
  warm_model "$model" || true
done

show_status
