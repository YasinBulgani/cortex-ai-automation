#!/usr/bin/env bash
# =============================================================
#  setup-env — interactive .env bootstrap for Cortex
#
#  Run once after a fresh clone. Generates a 16-char AES key if
#  CORTEX_AES_KEY is missing, copies .env.example -> .env, and
#  asks for the cortex test credentials.
# =============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo "[setup-env] .env already exists — leaving it alone."
  echo "             To reset, delete .env and re-run."
  exit 0
fi

cp .env.example .env
echo "[setup-env] .env created from .env.example"

# Generate a 16-char AES key (alphanumeric)
gen_key() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 16 | tr -dc 'A-Za-z0-9' | head -c 16
  else
    LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16
  fi
}

AES=$(gen_key)
# Replace the line in .env (cross-platform sed)
if grep -q '^CORTEX_AES_KEY=' .env; then
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^CORTEX_AES_KEY=.*|CORTEX_AES_KEY=${AES}|" .env
  else
    sed -i "s|^CORTEX_AES_KEY=.*|CORTEX_AES_KEY=${AES}|" .env
  fi
else
  echo "CORTEX_AES_KEY=${AES}" >> .env
fi

echo
echo "============================================================"
echo "  CORTEX_AES_KEY generated and written to .env"
echo "  Value: ${AES}"
echo
echo "  Next steps:"
echo "    1. Edit .env and set CORTEX_USERNAME / CORTEX_PASSWORD"
echo "       (the actual Cortex test-env credentials)"
echo "    2. Encrypt the password as alias 'cortexUser':"
echo "         ./scripts/cortex feature \\"
echo "           src/test/resources/scratch/setup-password.feature"
echo "       (see scripts/encrypt-password.sh helper)"
echo "    3. Run smoke: ./scripts/cortex smoke"
echo "============================================================"
