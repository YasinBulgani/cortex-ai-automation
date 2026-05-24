#!/usr/bin/env bash
# validate-prod-env.sh — Production deployment öncesi zorunlu ENV kontrolü.
#
# Kullanım:
#   ./scripts/validate-prod-env.sh          # .env dosyasını okur
#   ./scripts/validate-prod-env.sh .env.staging  # farklı dosya
#
# Çıkış kodu:
#   0 — tüm zorunlu değişkenler mevcut
#   1 — eksik veya CHANGEME kalmış değişken var

set -euo pipefail

ENV_FILE="${1:-.env}"

# ── .env dosyasını yükle ──────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  # export ile yükle; yorumları ve boş satırları atla
  set -a
  # shellcheck disable=SC1090
  source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
  set +a
else
  echo "⚠  $ENV_FILE bulunamadı — sadece shell ortamı kontrol ediliyor"
fi

# ── Zorunlu değişkenler ──────────────────────────────────────────────────────
REQUIRED_VARS=(
  # Kimlik doğrulama
  JWT_SECRET
  ENGINE_INTERNAL_KEY
  GATEWAY_INTERNAL_KEY
  ENGINE_SECRET_KEY

  # Veritabanı
  DATABASE_URL
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_DB

  # Redis
  REDIS_URL
  REDIS_PASSWORD

  # Webhook güvenliği
  GITHUB_WEBHOOK_SECRET
  GITLAB_WEBHOOK_TOKEN
  JENKINS_WEBHOOK_TOKEN
  N8N_CALLBACK_TOKEN

  # AI
  OLLAMA_BASE_URL
)

# ── Opsiyonel ama boş bırakılmaması önerilen değişkenler ────────────────────
RECOMMENDED_VARS=(
  SENTRY_DSN
  CORS_ORIGINS
  GRAFANA_ADMIN_PASSWORD
)

# ── Kontrol ──────────────────────────────────────────────────────────────────
ERRORS=0
WARNINGS=0

echo "🔍 Production ENV doğrulaması: $ENV_FILE"
echo ""

echo "── Zorunlu değişkenler ──"
for var in "${REQUIRED_VARS[@]}"; do
  val="${!var:-}"
  if [[ -z "$val" ]]; then
    echo "  ❌ $var — EKSIK"
    ((ERRORS++))
  elif echo "$val" | grep -qiE 'CHANGEME|changeme|change_me|example|your[-_]'; then
    echo "  ❌ $var — CHANGEME yer tutucusu kaldırılmamış: '${val:0:20}...'"
    ((ERRORS++))
  else
    echo "  ✅ $var"
  fi
done

echo ""
echo "── Önerilen değişkenler ──"
for var in "${RECOMMENDED_VARS[@]}"; do
  val="${!var:-}"
  if [[ -z "$val" ]]; then
    echo "  ⚠  $var — boş (opsiyonel ama önerilen)"
    ((WARNINGS++))
  else
    echo "  ✅ $var"
  fi
done

# ── Özet ─────────────────────────────────────────────────────────────────────
echo ""
echo "── Sonuç ──"
if [[ $ERRORS -gt 0 ]]; then
  echo "❌ $ERRORS zorunlu değişken eksik veya geçersiz. Deployment engellendi."
  echo "   .env.example dosyasını kopyalayın ve tüm CHANGEME değerlerini doldurun:"
  echo "   cp .env.example .env && nano .env"
  exit 1
else
  if [[ $WARNINGS -gt 0 ]]; then
    echo "⚠  Tüm zorunlu değişkenler mevcut. $WARNINGS opsiyonel değişken boş."
  else
    echo "✅ Tüm zorunlu ve önerilen değişkenler mevcut. Deployment güvenli."
  fi
  exit 0
fi
