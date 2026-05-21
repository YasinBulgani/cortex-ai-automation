#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  check-conflicts.sh — conflict_resolver rolünün otomasyon kardeşi
#
#  Aktif pipeline branch'leri arasında dosya çakışmasını tespit eder.
#  Kullanım:
#    - Manuel: ./scripts/pipeline/check-conflicts.sh [--json]
#    - Pre-commit hook: .githooks/pre-commit → bu scripti çağırır (warn-only)
#    - Pre-push hook: .githooks/pre-push → blocking mode (--strict flag ile)
#    - Scheduled: saatlik GitHub Actions veya cron
#
#  Çıktı:
#    - Çakışma yok → exit 0, "OK"
#    - Çakışma var (warn mode) → exit 0, rapor
#    - Çakışma var (--strict) → exit 1, rapor
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

STRICT=0
JSON=0
BASE_BRANCH="test"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --json) JSON=1; shift ;;
    --base) BASE_BRANCH="$2"; shift 2 ;;
    -h|--help)
      cat <<EOF
Usage: check-conflicts.sh [--strict] [--json] [--base BRANCH]
  --strict    Çakışma varsa exit 1 (pre-push için uygun)
  --json      JSON çıktı (CI için)
  --base      Karşılaştırma base'i (default: test)
EOF
      exit 0
      ;;
    *) echo "Unknown: $1"; exit 2 ;;
  esac
done

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 && $JSON -eq 0 ]]; then
  C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
  C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_RED=$'\e[31m'; C_CYAN=$'\e[36m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_CYAN=""
fi

# ─── Prep ────────────────────────────────────────────────────────────────────
# Fetch base silently (ignore failures, e.g. offline)
git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null || true

# Resolve base SHA
BASE_SHA=$(git rev-parse "origin/$BASE_BRANCH" 2>/dev/null || git rev-parse "$BASE_BRANCH" 2>/dev/null || echo "")
if [[ -z "$BASE_SHA" ]]; then
  echo "${C_YELLOW}! $BASE_BRANCH branch not found, skipping conflict check${C_RESET}" >&2
  exit 0
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# ─── Discover active pipeline branches ───────────────────────────────────────
PIPELINE_BRANCH_PATTERNS=(
  "analyze/" "propose/" "design/" "arch/"
  "feat/fe-" "feat/be-" "feat/data-" "feat/infra-"
  "integrate/" "qa/" "sec/" "a11y/" "perf/" "retro/"
)

declare -a active_branches
while IFS= read -r branch; do
  [[ -z "$branch" ]] && continue
  # Only branches ahead of base (have commits relative to base)
  ahead=$(git rev-list --count "$BASE_SHA..$branch" 2>/dev/null || echo 0)
  [[ "$ahead" -gt 0 ]] && active_branches+=("$branch")
done < <(
  for pattern in "${PIPELINE_BRANCH_PATTERNS[@]}"; do
    git for-each-ref --format='%(refname:short)' "refs/heads/${pattern}*" 2>/dev/null
    git for-each-ref --format='%(refname:short)' "refs/remotes/origin/${pattern}*" 2>/dev/null | sed 's|^origin/||' | sort -u
  done | sort -u
)

if [[ ${#active_branches[@]} -eq 0 ]]; then
  [[ $JSON -eq 1 ]] && echo '{"conflicts":[],"branches":[]}' || echo "${C_GREEN}✓ No active pipeline branches${C_RESET}"
  exit 0
fi

# ─── Build branch → changed-files map ────────────────────────────────────────
declare -A branch_files
for branch in "${active_branches[@]}"; do
  files=$(git diff --name-only "$BASE_SHA...$branch" 2>/dev/null || echo "")
  branch_files["$branch"]="$files"
done

# For current uncommitted work (unstaged + staged + untracked)
current_uncommitted=$(git diff --name-only HEAD 2>/dev/null; git diff --cached --name-only 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null)
current_uncommitted=$(echo "$current_uncommitted" | sort -u | grep -v '^$' || true)
if [[ -n "$current_uncommitted" ]]; then
  branch_files["__uncommitted__($CURRENT_BRANCH)"]="$current_uncommitted"
fi

# ─── Detect overlaps ─────────────────────────────────────────────────────────
declare -a conflict_entries
branches_list=("${!branch_files[@]}")
n=${#branches_list[@]}

for ((i=0; i<n; i++)); do
  for ((j=i+1; j<n; j++)); do
    b1="${branches_list[i]}"
    b2="${branches_list[j]}"
    files1="${branch_files[$b1]}"
    files2="${branch_files[$b2]}"
    # Intersection
    overlap=$(comm -12 <(echo "$files1" | sort -u) <(echo "$files2" | sort -u) | grep -v '^$' || true)
    if [[ -n "$overlap" ]]; then
      # Store as "branch1|branch2|file1,file2,..."
      overlap_flat=$(echo "$overlap" | tr '\n' ',' | sed 's/,$//')
      conflict_entries+=("$b1|$b2|$overlap_flat")
    fi
  done
done

# ─── Output ──────────────────────────────────────────────────────────────────
if [[ ${#conflict_entries[@]} -eq 0 ]]; then
  if [[ $JSON -eq 1 ]]; then
    branches_json=$(printf '%s\n' "${active_branches[@]}" | jq -R -s -c 'split("\n") | map(select(length>0))')
    echo "{\"conflicts\":[],\"branches\":$branches_json}"
  else
    echo "${C_GREEN}✓ No conflicts across ${#active_branches[@]} active pipeline branches${C_RESET}"
    echo "${C_DIM}  Branches checked:${C_RESET}"
    for b in "${active_branches[@]}"; do
      echo "${C_DIM}    - $b${C_RESET}"
    done
  fi
  exit 0
fi

# There are conflicts
if [[ $JSON -eq 1 ]]; then
  echo -n '{"conflicts":['
  first=1
  for entry in "${conflict_entries[@]}"; do
    IFS='|' read -r b1 b2 files <<< "$entry"
    [[ $first -eq 0 ]] && echo -n ','
    first=0
    files_json=$(echo "$files" | tr ',' '\n' | jq -R -s -c 'split("\n") | map(select(length>0))')
    printf '{"branch_a":"%s","branch_b":"%s","files":%s}' "$b1" "$b2" "$files_json"
  done
  echo -n '],"branches":'
  printf '%s\n' "${active_branches[@]}" | jq -R -s -c 'split("\n") | map(select(length>0))'
  echo '}'
else
  echo ""
  echo "${C_BOLD}${C_YELLOW}⚠  Branch Conflict Detection${C_RESET}"
  echo "${C_DIM}  Base: $BASE_BRANCH | Active branches: ${#active_branches[@]} | Conflicts: ${#conflict_entries[@]}${C_RESET}"
  echo ""
  for entry in "${conflict_entries[@]}"; do
    IFS='|' read -r b1 b2 files <<< "$entry"
    echo "${C_YELLOW}  ⚠  $b1 ↔ $b2${C_RESET}"
    echo "$files" | tr ',' '\n' | sed 's/^/       /'
    echo ""
  done
  echo "${C_DIM}  Öneriler (conflict_resolver rol kartı için bkz. docs/ai/pipeline/roles/25-conflict-resolver.md):${C_RESET}"
  echo "${C_DIM}  • Sınıf A (farklı satır): auto-resolve, bilgilendirme yeterli${C_RESET}"
  echo "${C_DIM}  • Sınıf B (aynı fonksiyon): owner rebase etsin${C_RESET}"
  echo "${C_DIM}  • Sınıf C (mimari çelişki): approver'a götür${C_RESET}"
fi

if [[ $STRICT -eq 1 ]]; then
  exit 1
fi
exit 0
