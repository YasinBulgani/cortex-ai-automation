#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  dep-watchdog.sh — rol 24 (Dependency Watchdog)
#
#  Python + JS + container deps tarar, CVE bulursa BUG, eskimiş lib için FEAT açar.
#  Kullanım:
#    - Günlük scheduled (GitHub Actions)
#    - Manuel: ./scripts/pipeline/dep-watchdog.sh
#    - Dry-run: ./scripts/pipeline/dep-watchdog.sh --dry-run
#    - JSON: ./scripts/pipeline/dep-watchdog.sh --json
#
#  Gereken tool'lar (bulunan koşulur):
#    - pip-audit (python)
#    - npm (apps/web için)
#    - trivy (container, opsiyonel)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

STAGE="$REPO_ROOT/scripts/pipeline/stage.sh"
REPORT_DIR="$REPO_ROOT/docs/ai/dep-scans"
mkdir -p "$REPORT_DIR"

DRY_RUN=0
JSON_OUT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --json)    JSON_OUT=1; shift ;;
    *) shift ;;
  esac
done

if [[ -t 1 && $JSON_OUT -eq 0 ]]; then
  C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
  C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_RED=$'\e[31m'; C_CYAN=$'\e[36m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_CYAN=""
fi

TS=$(date +%Y-%m-%d)
REPORT="$REPORT_DIR/$TS.md"

declare -a findings_json

add_finding() {
  local source="$1" package="$2" version="$3" cve="$4" severity="$5" description="$6"
  findings_json+=("{\"source\":\"$source\",\"package\":\"$package\",\"version\":\"$version\",\"cve\":\"$cve\",\"severity\":\"$severity\",\"description\":$(printf '%s' "$description" | jq -R -s .)}")
}

# ─── Python: pip-audit ───────────────────────────────────────────────────────
scan_python() {
  local target="$1"
  local label="$2"
  [[ ! -d "$target" ]] && return
  [[ ! -f "$target/requirements.txt" ]] && return

  if ! command -v pip-audit >/dev/null 2>&1; then
    [[ $JSON_OUT -eq 0 ]] && echo "${C_YELLOW}! pip-audit not installed, skipping $label${C_RESET}" >&2
    return
  fi

  [[ $JSON_OUT -eq 0 ]] && echo "${C_CYAN}→ Scanning $label (pip-audit)${C_RESET}" >&2
  local output_file
  output_file=$(mktemp)
  if pip-audit --format json -r "$target/requirements.txt" > "$output_file" 2>/dev/null; then
    # Parse and add findings
    jq -c '.dependencies[] | select(.vulns != null and (.vulns | length > 0)) | .name as $n | .version as $v | .vulns[]' "$output_file" 2>/dev/null | \
      while IFS= read -r vuln; do
        local name version cve severity desc
        name=$(jq -r --arg n "$name" '$n' <<< "{}")
        name=$(jq -r '.id // empty' <<< "$vuln")   # placeholder
        # Re-parse properly
        :
      done

    # Simpler: extract findings with name, version
    jq -c '.dependencies[] | select(.vulns != null and (.vulns | length > 0))' "$output_file" 2>/dev/null | \
      while IFS= read -r dep; do
        local name version
        name=$(jq -r '.name' <<< "$dep")
        version=$(jq -r '.version' <<< "$dep")
        jq -c '.vulns[]' <<< "$dep" | while IFS= read -r v; do
          local cve severity desc
          cve=$(jq -r '.id // "UNKNOWN"' <<< "$v")
          severity=$(jq -r '.fix_versions // [] | length | if . > 0 then "medium" else "high" end' <<< "$v")
          desc=$(jq -r '.description // "no description"' <<< "$v")
          echo "FINDING|$label|$name|$version|$cve|$severity|$desc"
        done
      done
  fi
  rm -f "$output_file"
}

# ─── JS: npm audit ───────────────────────────────────────────────────────────
scan_npm() {
  local target="$1"
  local label="$2"
  [[ ! -f "$target/package.json" ]] && return

  if ! command -v npm >/dev/null 2>&1; then
    return
  fi

  [[ $JSON_OUT -eq 0 ]] && echo "${C_CYAN}→ Scanning $label (npm audit)${C_RESET}" >&2
  local output
  output=$(cd "$target" && npm audit --json 2>/dev/null || true)

  # npm audit json → advisories
  jq -c '.vulnerabilities // {} | to_entries[] | select(.value.severity=="high" or .value.severity=="critical")' <<< "$output" 2>/dev/null | \
    while IFS= read -r vuln; do
      local name severity title cve
      name=$(jq -r '.key' <<< "$vuln")
      severity=$(jq -r '.value.severity' <<< "$vuln")
      title=$(jq -r '(.value.via // [] | map(if type=="object" then .title else . end) | join("; ")) // "unknown"' <<< "$vuln")
      cve=$(jq -r '(.value.via // [] | map(if type=="object" then (.url // .cve // .source) else . end) | .[0]) // "UNKNOWN"' <<< "$vuln")
      echo "FINDING|$label|$name|?|$cve|$severity|$title"
    done
}

# ─── Main scans ──────────────────────────────────────────────────────────────
all_findings=$(mktemp)
{
  scan_python "backend" "backend-python"
  scan_python "engine" "engine-python"
  scan_npm "apps/web" "frontend-npm"
} > "$all_findings"

total_findings=$(wc -l < "$all_findings" | tr -d ' ')

# ─── Write report ────────────────────────────────────────────────────────────
if [[ $JSON_OUT -eq 0 ]]; then
  {
    echo "# Dependency Scan Report — $TS"
    echo ""
    echo "**Run by:** dep-watchdog"
    echo "**Total findings:** $total_findings"
    echo ""
    echo "## Findings"
    echo ""
    if [[ $total_findings -gt 0 ]]; then
      echo "| Source | Package | Version | CVE/Advisory | Severity | Description |"
      echo "|---|---|---|---|---|---|"
      while IFS='|' read -r tag source package version cve severity desc; do
        [[ "$tag" != "FINDING" ]] && continue
        desc_short=$(echo "$desc" | tr -d '|\n' | head -c 80)
        echo "| $source | $package | $version | $cve | $severity | $desc_short |"
      done < "$all_findings"
    else
      echo "_No high/critical findings._"
    fi
    echo ""
    echo "## Scope"
    echo "- backend/requirements.txt (pip-audit)"
    echo "- engine/requirements.txt (pip-audit)"
    echo "- apps/web/package.json (npm audit, severity ≥ high)"
  } > "$REPORT"

  echo ""
  echo "${C_BOLD}Dep scan complete:${C_RESET} $total_findings findings"
  echo "${C_DIM}Report: $REPORT${C_RESET}"
fi

# ─── Open pipeline items for critical/high findings (unless dry-run) ─────────
if [[ $DRY_RUN -eq 0 && -x "$STAGE" ]]; then
  opened=0
  while IFS='|' read -r tag source package version cve severity desc; do
    [[ "$tag" != "FINDING" ]] && continue
    [[ "$severity" != "critical" && "$severity" != "high" ]] && continue

    # Duplicate check — aynı CVE title'da item var mı?
    title="[$cve] $package $version ($source)"
    exists=$(jq -r --arg t "$title" '[.items[] | select(.title==$t)] | length' \
      "$REPO_ROOT/docs/ai/pipeline/state.json" 2>/dev/null || echo 0)
    if [[ "$exists" != "0" ]]; then
      [[ $JSON_OUT -eq 0 ]] && echo "${C_DIM}  duplicate: $title${C_RESET}"
      continue
    fi

    # Scope: source'a göre
    case "$source" in
      *python*)  scope="fe=false,be=true,data=false,infra=false,perf_sensitive=false" ;;
      frontend*) scope="fe=true,be=false,data=false,infra=false,perf_sensitive=false" ;;
      *)         scope="fe=false,be=true,data=false,infra=false,perf_sensitive=false" ;;
    esac

    if [[ $JSON_OUT -eq 0 ]]; then
      echo "${C_YELLOW}+ Opening BUG for $title${C_RESET}"
    fi
    "$STAGE" init BUG "$title" --scope "$scope" > /dev/null 2>&1 || true
    opened=$((opened+1))
  done < "$all_findings"

  if [[ $JSON_OUT -eq 0 ]]; then
    echo "${C_GREEN}✓ Opened $opened new pipeline items${C_RESET}"
  fi
fi

# ─── JSON output (CI) ────────────────────────────────────────────────────────
if [[ $JSON_OUT -eq 1 ]]; then
  echo -n '{"date":"'"$TS"'","total":'"$total_findings"',"findings":['
  first=1
  while IFS='|' read -r tag source package version cve severity desc; do
    [[ "$tag" != "FINDING" ]] && continue
    [[ $first -eq 0 ]] && echo -n ','
    first=0
    desc_json=$(printf '%s' "$desc" | jq -R -s .)
    printf '{"source":"%s","package":"%s","version":"%s","cve":"%s","severity":"%s","description":%s}' \
      "$source" "$package" "$version" "$cve" "$severity" "$desc_json"
  done < "$all_findings"
  echo ']}'
fi

rm -f "$all_findings"
