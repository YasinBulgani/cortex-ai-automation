#!/usr/bin/env bash
# validate-prod-env.sh — Production env değişken doğrulaması (P1 #34)
# Kullanım: ./scripts/validate-prod-env.sh
# Tüm zorunlu env değişkenlerinin .env dosyasında tanımlı olduğunu doğrular.

set -euo pipefail

REQUIRED_VARS=(
  "POSTGRES_USER"
  "POSTGRES_PASSWORD"
  "POSTGRES_DB"
  "DATABASE_URL"
  "REDIS_URL"
  "JWT_SECRET"
  "BACKEND_SECRET_KEY"
  "GITHUB_REPOSITORY"
  "IMAGE_TAG"
)

OPTIONAL_VARS=(
  "OPENAI_API_KEY"
  "ANTHROPIC_API_KEY"
  "REDIS_PASSWORD"
  "SEMGREP_APP_TOKEN"
)

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE bulunamadı. '.env.example'dan kopyalayın: cp .env.example .env"
  exit 1
fi

source "$ENV_FILE" 2>/dev/null || true

ERRORS=0
echo "=== Production Environment Validation ==="
echo ""

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "❌ ZORUNLU: $var tanımlı değil veya boş"
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ $var: OK"
  fi
done

echo ""
for var in "${OPTIONAL_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "⚠️  OPSİYONEL: $var tanımlı değil (AI özellikleri çalışmaz)"
  else
    echo "✅ $var: OK (opsiyonel)"
  fi
done

echo ""
if [ $ERRORS -gt 0 ]; then
  echo "❌ $ERRORS zorunlu değişken eksik. Prod deployment durduruldu."
  exit 1
else
  echo "✅ Tüm zorunlu değişkenler tanımlı. Deployment devam edebilir."
fi
