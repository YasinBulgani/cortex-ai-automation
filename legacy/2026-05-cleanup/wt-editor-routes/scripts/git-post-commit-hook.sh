#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Git Post-Commit Hook — Code Change Learning
#
# Her commit sonrası değişen dosyaları ve commit mesajını KnowledgeStore'a
# ingest eder. LLM, kod değişikliklerinden otomatik olarak öğrenir.
#
# Kurulum:
#   cp scripts/git-post-commit-hook.sh .git/hooks/post-commit
#   chmod +x .git/hooks/post-commit
# ─────────────────────────────────────────────────────────────────────────────

set -e

# Backend container'ına gönder (Docker içinden çalışır)
BACKEND_URL="${TWAI_BACKEND_URL:-http://localhost:8000}"

# Son commit bilgileri
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=format:"%s")
COMMIT_AUTHOR=$(git log -1 --pretty=format:"%an")
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD | head -20)
DIFF_STAT=$(git diff --stat HEAD~1..HEAD 2>/dev/null || echo "İlk commit")

# Bilgiyi JSON'a dönüştür
PAYLOAD=$(cat <<EOF
{
  "text": "Commit: ${COMMIT_HASH} — ${COMMIT_MSG}\nYazar: ${COMMIT_AUTHOR}\nDeğişen dosyalar:\n${CHANGED_FILES}\n\nDiff istatistiği:\n${DIFF_STAT}",
  "source": "code_change",
  "metadata": {
    "commit_hash": "${COMMIT_HASH}",
    "author": "${COMMIT_AUTHOR}",
    "type": "post_commit_hook"
  }
}
EOF
)

# Backend API'ye gönder (başarısız olursa sessizce geç — commit'i engelleme)
curl -s -X POST "${BACKEND_URL}/api/v1/knowledge/ingest" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" \
  --connect-timeout 2 \
  --max-time 5 \
  > /dev/null 2>&1 || true

echo "[TestwrightAI] Commit ${COMMIT_HASH} bilgisi KnowledgeStore'a gönderildi."
