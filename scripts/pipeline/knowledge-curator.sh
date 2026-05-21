#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  knowledge-curator.sh — rol 23 (Knowledge Curator)
#
#  Retrospective'leri tarar, pattern tespit eder, GROUNDING.md için öneri oluşturur.
#  Bu scripting-based versiyon deterministik kısımları yapar; asıl yorumlayıcı iş
#  AI agent'a bırakılır (knowledge-updates/YYYY-WW.md taslağını doldurur).
#
#  Kullanım:
#    - Haftalık scheduled (Pazar, GitHub Actions)
#    - Manuel: ./scripts/pipeline/knowledge-curator.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

RETROS_DIR="$REPO_ROOT/docs/ai/retros"
UPDATES_DIR="$REPO_ROOT/docs/ai/knowledge-updates"
GROUNDING="$REPO_ROOT/docs/ai/GROUNDING.md"
mkdir -p "$RETROS_DIR" "$UPDATES_DIR"

YEAR=$(date +%G)
WEEK=$(date +%V)
WEEK_FILE="$UPDATES_DIR/${YEAR}-W${WEEK}.md"

if [[ -t 1 ]]; then
  C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'; C_GREEN=$'\e[32m'; C_CYAN=$'\e[36m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_GREEN=""; C_CYAN=""
fi

# Son 7 gün içindeki retrolar
RECENT_RETROS=$(find "$RETROS_DIR" -name "*.md" -type f -mtime -7 2>/dev/null || true)
RETRO_COUNT=$(echo "$RECENT_RETROS" | grep -c '.' 2>/dev/null || echo 0)

echo "${C_CYAN}→ Knowledge Curator — Week $YEAR-W$WEEK${C_RESET}"
echo "${C_DIM}  Recent retros: $RETRO_COUNT${C_RESET}"

# ─── Sentez taslağı (agent dolduracak) ───────────────────────────────────────
{
  echo "# Knowledge Update — $YEAR-W$WEEK"
  echo ""
  echo "> **Generated:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "> **By:** knowledge-curator (automated digest)"
  echo "> **Status:** DRAFT — AI agent bu taslağı tamamlayacak"
  echo ""
  echo "## Kapsam"
  echo ""
  echo "Son 7 gün içindeki retro'lar taranarak pattern ve convention önerileri çıkarıldı."
  echo ""
  echo "## Retrolar ($RETRO_COUNT)"
  echo ""
  if [[ $RETRO_COUNT -gt 0 ]]; then
    echo "| Dosya | Son değişim |"
    echo "|---|---|"
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      name=$(basename "$f")
      mod=$(date -r "$f" "+%Y-%m-%d" 2>/dev/null || stat -c %y "$f" 2>/dev/null | cut -d' ' -f1)
      echo "| \`$name\` | $mod |"
    done <<< "$RECENT_RETROS"
  else
    echo "_Bu hafta retro yok._"
  fi
  echo ""

  echo "## Pattern Analizi (AI agent doldurur)"
  echo ""
  echo "### 3+ retro'da tekrarlayan konular (ADR adayı)"
  echo ""
  echo "<!-- AI agent aşağıdaki şablonu doldur -->"
  echo "- **Pattern:** <özet>"
  echo "  - **Retros:** <retro dosya listesi>"
  echo "  - **Öneri:** ADR yazılsın / GROUNDING'e eklensin / anti-pattern kataloğuna eklensin"
  echo ""
  echo "### Tekrarlayan 'stop doing' çağrıları"
  echo ""
  echo "<!-- agent: \"stop doing\" bölümlerindeki tekrarları çıkar -->"
  echo ""
  echo "### Yeni 'start doing' önerileri (consensus)"
  echo ""
  echo "<!-- agent: 2+ retro'da önerilen yeni practice'leri topla -->"
  echo ""

  echo "## GROUNDING.md Güncellemeleri"
  echo ""
  echo "<!-- agent: her öneri için: -->"
  echo "- [ ] <öneri> — <hangi retro'dan>"
  echo ""

  echo "## ADR Önerileri"
  echo ""
  echo "<!-- 3+ retro'dan pattern varsa burada ADR oluşturulsun -->"
  echo "- [ ] <ADR title> — context, decision, consequences"
  echo ""

  echo "## Anti-pattern Eklenecekler"
  echo ""
  echo "<!-- agent: blocker olmuş uygulama detayları -->"
  echo "- [ ] <anti-pattern>"
  echo ""

  echo "## Metrics — Bu Haftanın Pipeline Özeti"
  echo ""
  if [[ -f "$REPO_ROOT/scripts/pipeline/metrics.py" && -f "$REPO_ROOT/docs/ai/pipeline/state.json" ]]; then
    python3 "$REPO_ROOT/scripts/pipeline/metrics.py" --format markdown --section summary 2>/dev/null || echo "_(metrics unavailable)_"
  else
    echo "_(metrics script yok)_"
  fi
  echo ""

  echo "---"
  echo ""
  echo "[pipeline: knowledge_curator]"
} > "$WEEK_FILE"

echo "${C_GREEN}✓ Draft written:${C_RESET} $WEEK_FILE"
echo "${C_DIM}  Sonraki adım: AI agent bu dosyayı tamamlayıp GROUNDING.md'yi güncellesin${C_RESET}"
echo "${C_DIM}  Agent prompt:${C_RESET}"
echo ""
cat <<EOF
  Sen pipeline'da knowledge_curator rolünü oynuyorsun.
  OKU: docs/ai/pipeline/roles/23-knowledge-curator.md
  Taslak: $WEEK_FILE
  Retros: $RETROS_DIR (son 7 gün)

  YAP:
  - Retrolardaki 'keep/stop/start' ve 'pattern' bölümlerini sentezle
  - Taslaktaki <!-- agent ... --> bölümlerini doldur
  - 3+ retro'da tekrar eden konuları ADR'ye dönüştür
  - GROUNDING.md'yi güncelle (eğer öneri varsa)
  - git checkout test && git checkout -b knowledge/week-$YEAR-W$WEEK
  - Commit + PR test'e
EOF
