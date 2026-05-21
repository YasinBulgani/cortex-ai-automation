#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  pipeline/stage.sh — 25-rollü agent pipeline driver (dep-graph tabanlı)
#
#  Tek kaynak gerçek: docs/ai/pipeline/state.json
#  Dep graph:        docs/ai/pipeline/stages.json
#
#  Komutlar: init | claim | complete | reject | skip | loop-back | status
#            orphan-reset | scope | run-check
#
#  Dependency: jq (brew install jq)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="${REPO_ROOT}/docs/ai/pipeline/state.json"
STAGES_CFG="${REPO_ROOT}/docs/ai/pipeline/stages.json"
LOCK="${REPO_ROOT}/docs/ai/pipeline/.state.lock"
ITEMS_DIR="${REPO_ROOT}/docs/ai/pipeline/items"
TEMPLATES_DIR="${REPO_ROOT}/docs/ai/pipeline/templates"

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
  C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_RED=$'\e[31m'; C_BLUE=$'\e[34m'; C_CYAN=$'\e[36m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_BLUE=""; C_CYAN=""
fi

# ─── Utils ───────────────────────────────────────────────────────────────────
die() { echo "${C_RED}✗ $*${C_RESET}" >&2; exit 1; }
info() { echo "${C_CYAN}→ $*${C_RESET}"; }
ok() { echo "${C_GREEN}✓ $*${C_RESET}"; }
warn() { echo "${C_YELLOW}! $*${C_RESET}"; }

check_deps() {
  command -v jq >/dev/null 2>&1 || die "jq required. brew install jq"
  [[ -f "$STAGES_CFG" ]] || die "stages.json missing: $STAGES_CFG"
}

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

with_lock() {
  local waited=0
  while ! mkdir "$LOCK" 2>/dev/null; do
    sleep 1
    waited=$((waited+1))
    [[ $waited -ge 30 ]] && die "state.json lock timeout (30s). Stale lock? rm -rf $LOCK"
  done
  trap 'rm -rf "$LOCK"' EXIT
}

ensure_state() {
  if [[ ! -f "$STATE" ]]; then
    mkdir -p "$(dirname "$STATE")"
    cat > "$STATE" <<EOF
{
  "version": "2.0",
  "updated_at": "$(now_iso)",
  "next_ids": { "GAP": 1, "FEAT": 1, "BUG": 1 },
  "items": []
}
EOF
  fi
}

write_state() {
  local tmp
  tmp=$(mktemp)
  jq --arg t "$(now_iso)" '.updated_at = $t' > "$tmp"
  mv "$tmp" "$STATE"
}

# ─── Graph helpers (jq-based) ────────────────────────────────────────────────

all_stage_names() {
  jq -r '.stages | keys[]' "$STAGES_CFG"
}

stage_deps() {
  local stage="$1"
  jq -r --arg s "$stage" '.stages[$s].depends_on[]?' "$STAGES_CFG"
}

stage_default_on() {
  local stage="$1"
  jq -r --arg s "$stage" '.stages[$s].default_on // "always"' "$STAGES_CFG"
}

validate_role() {
  local role="$1"
  local exists
  exists=$(jq -r --arg s "$role" '.stages[$s] != null' "$STAGES_CFG")
  [[ "$exists" == "true" ]] || die "Invalid role: $role. Valid: $(all_stage_names | tr '\n' ' ')"
  return 0
}

# Get item's stage status; returns "absent" if stage not in item's stages
item_stage_status() {
  local id="$1" stage="$2"
  jq -r --arg id "$id" --arg s "$stage" \
    '.items[] | select(.id==$id) | .stages[$s].status // "absent"' "$STATE"
}

item_scope_flag() {
  local id="$1" flag="$2"
  # NOTE: can't use `// true` because jq's // treats false as null.
  jq -r --arg id "$id" --arg f "$flag" \
    '.items[] | select(.id==$id) | (if (.scope | has($f)) then .scope[$f] else true end) | tostring' "$STATE"
}

# Check if all deps satisfied (done or skipped)
deps_satisfied() {
  local id="$1" stage="$2"
  local deps all_done=true
  deps=$(stage_deps "$stage")
  if [[ -z "$deps" ]]; then
    return 0
  fi
  while IFS= read -r d; do
    [[ -z "$d" ]] && continue
    local st
    st=$(item_stage_status "$id" "$d")
    if [[ "$st" != "done" && "$st" != "skipped" ]]; then
      all_done=false
      break
    fi
  done <<< "$deps"
  [[ "$all_done" == "true" ]]
}

# Decide if a stage should auto-skip based on scope flags
should_auto_skip() {
  local id="$1" stage="$2"
  local rule
  rule=$(stage_default_on "$stage")
  case "$rule" in
    always) return 1 ;;
    scope.*)
      local flag="${rule#scope.}"
      local val
      val=$(item_scope_flag "$id" "$flag")
      [[ "$val" == "false" ]] && return 0
      return 1
      ;;
    on_approve)
      # validator approved?
      local decision
      decision=$(jq -r --arg id "$id" '.items[] | select(.id==$id) | .stages.validator.approval.decision // "approve"' "$STATE")
      [[ "$decision" == "approve" ]] && return 1
      return 0
      ;;
    *) return 1 ;;
  esac
}

# Open any stages whose deps are satisfied & currently absent
open_ready_stages() {
  local id="$1"
  local opened=()
  local skipped_auto=()
  local stage

  while IFS= read -r stage; do
    [[ -z "$stage" ]] && continue
    local cur
    cur=$(item_stage_status "$id" "$stage")
    if [[ "$cur" == "absent" ]]; then
      if deps_satisfied "$id" "$stage"; then
        if should_auto_skip "$id" "$stage"; then
          # Mark skipped
          jq --arg id "$id" --arg s "$stage" --arg now "$(now_iso)" \
            '.items |= map(if .id==$id then .stages[$s] = {"status":"skipped","completed_at":$now,"handoff_notes":"auto-skipped by scope"} else . end)' \
            "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
          skipped_auto+=("$stage")
        else
          jq --arg id "$id" --arg s "$stage" \
            '.items |= map(if .id==$id then .stages[$s] = {"status":"waiting"} else . end)' \
            "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
          opened+=("$stage")
        fi
      fi
    fi
  done < <(all_stage_names)

  # Skipped stages might have unlocked further — recurse if we skipped any
  if [[ ${#skipped_auto[@]} -gt 0 ]]; then
    open_ready_stages "$id"
  fi

  # Update current_stage + status
  local any_waiting any_progress
  any_waiting=$(jq -r --arg id "$id" '[.items[] | select(.id==$id) | .stages | to_entries[] | select(.value.status=="waiting") | .key] | length' "$STATE")
  any_progress=$(jq -r --arg id "$id" '[.items[] | select(.id==$id) | .stages | to_entries[] | select(.value.status=="in_progress") | .key] | length' "$STATE")

  if [[ "$any_progress" -gt 0 ]]; then
    # keep current_stage as first in_progress
    local first_prog
    first_prog=$(jq -r --arg id "$id" '[.items[] | select(.id==$id) | .stages | to_entries[] | select(.value.status=="in_progress") | .key] | .[0]' "$STATE")
    jq --arg id "$id" --arg s "$first_prog" '.items |= map(if .id==$id then .current_stage=$s | .status="in_progress" else . end)' "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
  elif [[ "$any_waiting" -gt 0 ]]; then
    local first_wait
    first_wait=$(jq -r --arg id "$id" '[.items[] | select(.id==$id) | .stages | to_entries[] | select(.value.status=="waiting") | .key] | .[0]' "$STATE")
    jq --arg id "$id" --arg s "$first_wait" '.items |= map(if .id==$id then .current_stage=$s | .status="waiting" else . end)' "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
  else
    # Nothing waiting or in_progress — check if all terminal stage done → item done
    local retro_status
    retro_status=$(item_stage_status "$id" retrospective)
    if [[ "$retro_status" == "done" ]]; then
      jq --arg id "$id" '.items |= map(if .id==$id then .current_stage="done" | .status="done" else . end)' "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
    fi
  fi

  jq --arg t "$(now_iso)" '.updated_at = $t' "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"

  if [[ ${#opened[@]} -gt 0 ]]; then
    echo "${C_DIM}  → opened: ${opened[*]}${C_RESET}"
  fi
  if [[ ${#skipped_auto[@]} -gt 0 ]]; then
    echo "${C_DIM}  → auto-skipped: ${skipped_auto[*]}${C_RESET}"
  fi
}

require_item() {
  local id="$1"
  local exists
  exists=$(jq -r --arg id "$id" '[.items[] | select(.id==$id)] | length' "$STATE")
  if [[ "$exists" == "0" ]]; then
    die "Item not found: $id"
  fi
  return 0
}

# ─── Sub-commands ────────────────────────────────────────────────────────────

cmd_init() {
  local type="${1:-}" title="${2:-}"
  [[ -z "$type" || -z "$title" ]] && die "Usage: stage.sh init <GAP|FEAT|BUG> \"<title>\" [--scope fe=true,be=true,data=false,infra=false,perf_sensitive=false]"
  case "$type" in GAP|FEAT|BUG) ;; *) die "type must be GAP | FEAT | BUG" ;; esac

  shift 2
  local scope_spec=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --scope) scope_spec="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  with_lock
  ensure_state

  local next_num
  next_num=$(jq -r ".next_ids.$type" "$STATE")
  local id
  id=$(printf "%s-%03d" "$type" "$next_num")

  mkdir -p "$ITEMS_DIR/$id/evidence"

  # Build default scope
  local scope_json='{"fe":true,"be":true,"data":false,"infra":false,"perf_sensitive":false}'
  if [[ -n "$scope_spec" ]]; then
    scope_json='{}'
    local IFS=,
    for kv in $scope_spec; do
      local k="${kv%%=*}" v="${kv#*=}"
      scope_json=$(echo "$scope_json" | jq --arg k "$k" --argjson v "$v" '. + {($k): $v}')
    done
  fi

  jq \
    --arg id "$id" \
    --arg type "$type" \
    --arg title "$title" \
    --arg now "$(now_iso)" \
    --argjson next "$((next_num+1))" \
    --arg t "$type" \
    --argjson scope "$scope_json" \
    '
    .next_ids[$t] = $next
    | .items += [{
        "id": $id,
        "type": $type,
        "title": $title,
        "priority": "medium",
        "created_at": $now,
        "current_stage": "analyzer",
        "status": "waiting",
        "needs_human": false,
        "feedback_loops": [],
        "scope": $scope,
        "stages": {
          "analyzer": { "status": "waiting" }
        }
      }]
    ' "$STATE" | write_state

  # Seed gap-analysis template for GAP items
  if [[ "$type" == "GAP" && ! -f "$ITEMS_DIR/$id/gap-analysis.md" ]]; then
    sed "s/{{ID}}/$id/g; s/{{TITLE}}/$title/g; s/{{agent_id}}/TBD/g; s/{{date}}/$(date +%Y-%m-%d)/g" \
      "$TEMPLATES_DIR/gap-analysis.template.md" > "$ITEMS_DIR/$id/gap-analysis.md"
  fi

  ok "Created $id — \"$title\" (waiting for analyzer)"
  echo "${C_DIM}  scope: $scope_json${C_RESET}"
  echo "${C_DIM}  folder: $ITEMS_DIR/$id${C_RESET}"
}

cmd_scope() {
  local id="${1:-}" kv="${2:-}"
  [[ -z "$id" || -z "$kv" ]] && die "Usage: stage.sh scope <ID> <flag>=<true|false>"
  validate_role_skip_check "$id"

  local k="${kv%%=*}" v="${kv#*=}"
  with_lock
  ensure_state
  require_item "$id"

  jq --arg id "$id" --arg k "$k" --argjson v "$v" \
    '.items |= map(if .id==$id then .scope[$k] = $v else . end)' "$STATE" | write_state

  ok "Scope updated: $id $k=$v"
  # Auto-open ready stages based on new scope
  open_ready_stages "$id"
}

# stub to keep signature consistent
validate_role_skip_check() { :; }

cmd_claim() {
  local id="${1:-}" role="${2:-}"
  [[ -z "$id" || -z "$role" ]] && die "Usage: stage.sh claim <ID> <ROLE>"
  validate_role "$role"

  with_lock
  ensure_state
  require_item "$id"

  local cur; cur=$(item_stage_status "$id" "$role")
  if [[ "$cur" != "waiting" ]]; then
    warn "Stage $role is '$cur' for $id (expected waiting); proceeding anyway"
  fi

  jq \
    --arg id "$id" \
    --arg role "$role" \
    --arg now "$(now_iso)" \
    '
    .items |= map(
      if .id == $id then
        .current_stage = $role
        | .status = "in_progress"
        | .stages[$role] = ((.stages[$role] // {}) + {
            "status": "in_progress",
            "started_at": $now
          })
      else . end
    )
    ' "$STATE" | write_state

  ok "Claimed $id for $role"
}

cmd_complete() {
  local id="${1:-}" role="${2:-}"
  [[ -z "$id" || -z "$role" ]] && die "Usage: stage.sh complete <ID> <ROLE> [flags]"
  validate_role "$role"
  shift 2

  local artifact="" branch="" commit="" notes=""
  local approval_decision="" approval_reason="" confidence=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --artifact) artifact="$2"; shift 2 ;;
      --branch) branch="$2"; shift 2 ;;
      --commit) commit="$2"; shift 2 ;;
      --notes) notes="$2"; shift 2 ;;
      --approve) approval_decision="approve"; shift ;;
      --reject) approval_decision="reject"; shift ;;
      --revise) approval_decision="revise"; shift ;;
      --reason) approval_reason="$2"; shift 2 ;;
      --confidence) confidence="$2"; shift 2 ;;
      *) die "Unknown flag: $1" ;;
    esac
  done

  with_lock
  ensure_state
  require_item "$id"

  jq \
    --arg id "$id" \
    --arg role "$role" \
    --arg now "$(now_iso)" \
    --arg artifact "$artifact" \
    --arg branch "$branch" \
    --arg commit "$commit" \
    --arg notes "$notes" \
    --arg decision "$approval_decision" \
    --arg reason "$approval_reason" \
    --arg confidence "$confidence" \
    '
    .items |= map(
      if .id == $id then
        .stages[$role] = ((.stages[$role] // {}) + {
            "status": "done",
            "completed_at": $now
          })
        | (if $artifact != "" then .stages[$role].artifact = $artifact else . end)
        | (if $branch != "" then .stages[$role].branch = $branch else . end)
        | (if $commit != "" then .stages[$role].commit = $commit else . end)
        | (if $notes != "" then .stages[$role].handoff_notes = $notes else . end)
        | (if $decision != "" then
            .stages[$role].approval = {
              "decision": $decision,
              "reasoning": $reason,
              "confidence": ($confidence | if . == "" then null else tonumber end)
            }
            | (if ($confidence != "" and ($confidence | tonumber) < 0.7) then .needs_human = true else . end)
          else . end)
      else . end
    )
    ' "$STATE" | write_state

  ok "Completed $role for $id"
  open_ready_stages "$id"
}

cmd_skip() {
  local id="${1:-}" role="${2:-}" reason="${3:-manual skip}"
  [[ -z "$id" || -z "$role" ]] && die "Usage: stage.sh skip <ID> <ROLE> [reason]"
  validate_role "$role"

  with_lock
  ensure_state
  require_item "$id"

  jq \
    --arg id "$id" \
    --arg role "$role" \
    --arg now "$(now_iso)" \
    --arg reason "$reason" \
    '
    .items |= map(
      if .id == $id then
        .stages[$role] = ((.stages[$role] // {}) + {
            "status": "skipped",
            "completed_at": $now,
            "handoff_notes": $reason
          })
      else . end
    )
    ' "$STATE" | write_state

  warn "Skipped $role for $id: $reason"
  open_ready_stages "$id"
}

cmd_reject() {
  local id="${1:-}" role="${2:-}" reason="${3:-}"
  [[ -z "$id" || -z "$role" || -z "$reason" ]] && die "Usage: stage.sh reject <ID> <ROLE> \"<reason>\""
  validate_role "$role"

  with_lock
  ensure_state
  require_item "$id"

  jq \
    --arg id "$id" \
    --arg role "$role" \
    --arg now "$(now_iso)" \
    --arg reason "$reason" \
    '
    .items |= map(
      if .id == $id then
        .current_stage = "rejected"
        | .status = "rejected"
        | .stages[$role] = ((.stages[$role] // {}) + {
            "status": "rejected",
            "completed_at": $now,
            "approval": { "decision": "reject", "reasoning": $reason }
          })
      else . end
    )
    ' "$STATE" | write_state

  warn "Rejected $id at $role: $reason"
}

cmd_loop_back() {
  local id="${1:-}" from_stage="${2:-}" to_stage="${3:-}" reason="${4:-}"
  [[ -z "$id" || -z "$from_stage" || -z "$to_stage" || -z "$reason" ]] && \
    die "Usage: stage.sh loop-back <ID> <FROM> <TO> \"<reason>\""
  validate_role "$from_stage"
  validate_role "$to_stage"

  with_lock
  ensure_state
  require_item "$id"

  local loop_count
  loop_count=$(jq -r --arg id "$id" --arg to "$to_stage" \
    '[.items[] | select(.id==$id) | .feedback_loops[] | select(.to_stage==$to)] | length' "$STATE")

  if [[ "$loop_count" -ge 3 ]]; then
    warn "3+ loop-backs to $to_stage for $id — marking needs_human"
    jq --arg id "$id" '.items |= map(if .id==$id then .needs_human = true | .status = "blocked" else . end)' "$STATE" | write_state
    die "Pipeline blocked: too many feedback loops, human intervention required"
  fi

  jq \
    --arg id "$id" \
    --arg from "$from_stage" \
    --arg to "$to_stage" \
    --arg reason "$reason" \
    --arg now "$(now_iso)" \
    '
    .items |= map(
      if .id == $id then
        .current_stage = $to
        | .status = "feedback_loop"
        | .feedback_loops += [{
            "from_stage": $from,
            "to_stage": $to,
            "reason": $reason,
            "at": $now
          }]
        | .stages[$to] = { "status": "waiting" }
      else . end
    )
    ' "$STATE" | write_state

  warn "Loop-back $id: $from_stage → $to_stage ($reason)"
}

cmd_status() {
  local id="${1:-}"
  ensure_state

  if [[ -n "$id" ]]; then
    jq --arg id "$id" '.items[] | select(.id==$id)' "$STATE"
    return
  fi

  echo "${C_BOLD}📋 Pipeline Status${C_RESET}  ${C_DIM}(state: $STATE)${C_RESET}"
  echo

  local count
  count=$(jq '.items | length' "$STATE")
  if [[ "$count" == "0" ]]; then
    echo "  ${C_DIM}No items yet. Start with: stage.sh init GAP \"title\"${C_RESET}"
    return
  fi

  printf "  %-10s %-38s %-20s %-14s %s\n" "ID" "Title" "Stage" "Status" "Needs Human"
  printf "  %-10s %-38s %-20s %-14s %s\n" "──────────" "──────────────────────────────────────" "────────────────────" "──────────────" "───────────"
  jq -r '.items[] | [.id, .title, .current_stage, .status, (.needs_human | tostring)] | @tsv' "$STATE" | \
    while IFS=$'\t' read -r id title stage status human; do
      local color="$C_RESET"
      case "$status" in
        in_progress) color="$C_BLUE" ;;
        done) color="$C_GREEN" ;;
        rejected|blocked) color="$C_RED" ;;
        waiting|feedback_loop) color="$C_YELLOW" ;;
      esac
      local human_flag=""
      [[ "$human" == "true" ]] && human_flag="${C_RED}⚠ yes${C_RESET}"
      printf "  %-10s %-38s %-20s ${color}%-14s${C_RESET} %s\n" "$id" "${title:0:38}" "$stage" "$status" "$human_flag"
    done
  echo

  echo "${C_BOLD}Waiting stages (ready to claim):${C_RESET}"
  jq -r '
    .items[]
    | . as $item
    | .stages
    | to_entries[]
    | select(.value.status == "waiting")
    | "\($item.id) → \(.key)"
  ' "$STATE" | head -20 | sed 's/^/  /'
}

cmd_run_check() {
  # Dry-run: show what would be opened
  local id="${1:-}"
  ensure_state
  if [[ -n "$id" ]]; then
    require_item "$id"
    echo "${C_BOLD}Run-check for $id:${C_RESET}"
    local stage
    while IFS= read -r stage; do
      [[ -z "$stage" ]] && continue
      local cur
      cur=$(item_stage_status "$id" "$stage")
      if [[ "$cur" == "absent" ]]; then
        if deps_satisfied "$id" "$stage"; then
          if should_auto_skip "$id" "$stage"; then
            echo "  ${C_DIM}$stage: would auto-skip (scope)${C_RESET}"
          else
            echo "  ${C_YELLOW}$stage: ready to open${C_RESET}"
          fi
        fi
      fi
    done < <(all_stage_names)
  else
    jq -r '.items[].id' "$STATE" | while read -r i; do
      "$0" run-check "$i"
    done
  fi
}

cmd_orphan_reset() {
  local id="${1:-}" role="${2:-}"
  [[ -z "$id" || -z "$role" ]] && die "Usage: stage.sh orphan-reset <ID> <ROLE>"
  validate_role "$role"

  with_lock
  ensure_state
  require_item "$id"

  jq \
    --arg id "$id" \
    --arg role "$role" \
    '
    .items |= map(
      if .id == $id then
        .stages[$role] = { "status": "waiting" }
        | .current_stage = $role
        | .status = "waiting"
      else . end
    )
    ' "$STATE" | write_state

  warn "Reset $id @ $role to waiting (orphan recovery)"
}

# ─── Main dispatcher ─────────────────────────────────────────────────────────

check_deps

case "${1:-}" in
  init)         shift; cmd_init "$@" ;;
  scope)        shift; cmd_scope "$@" ;;
  claim)        shift; cmd_claim "$@" ;;
  complete)     shift; cmd_complete "$@" ;;
  skip)         shift; cmd_skip "$@" ;;
  reject)       shift; cmd_reject "$@" ;;
  loop-back)    shift; cmd_loop_back "$@" ;;
  status)       shift; cmd_status "$@" ;;
  run-check)    shift; cmd_run_check "$@" ;;
  orphan-reset) shift; cmd_orphan_reset "$@" ;;
  help|-h|--help|"")
    cat <<EOF
${C_BOLD}pipeline/stage.sh${C_RESET} — 25-rollü agent pipeline driver (dep-graph)

${C_BOLD}USAGE${C_RESET}
  stage.sh <command> [args...]

${C_BOLD}ITEM LIFECYCLE${C_RESET}
  init <TYPE> "<title>" [--scope fe=true,be=true,data=false,...]
  scope <ID> <flag>=<true|false>         Scope bayrağını güncelle (auto-open/skip)
  claim <ID> <ROLE>                      Role'ü in_progress'e çek
  complete <ID> <ROLE> [flags]           Aşamayı done + sonrakileri aç
  skip <ID> <ROLE> [reason]              Aşamayı manuel skip et
  reject <ID> <ROLE> "<reason>"          Item'ı reddet (arşivle)
  loop-back <ID> <FROM> <TO> "<reason>"  Feedback loop (max 3)

${C_BOLD}COMPLETE FLAGS${C_RESET}
  --artifact PATH | --branch NAME | --commit SHA | --notes "..."
  --approve | --reject | --revise | --reason "..." | --confidence 0.N

${C_BOLD}INSPECTION${C_RESET}
  status [<ID>]             Tüm item'lar | tek item JSON
  run-check [<ID>]           Hangi aşamalar açılmaya hazır (dry-run)

${C_BOLD}RECOVERY${C_RESET}
  orphan-reset <ID> <ROLE>  Takılmış aşamayı waiting'e döndür

${C_BOLD}EXAMPLES${C_RESET}
  stage.sh init GAP "A11y eksikliği" --scope fe=true,be=false,data=false
  stage.sh claim GAP-001 analyzer
  stage.sh complete GAP-001 analyzer --artifact docs/.../gap-analysis.md
  stage.sh complete GAP-001 validator --approve --confidence 0.9
  stage.sh skip GAP-001 backend "A11y-only, backend dokunulmuyor"
  stage.sh scope GAP-001 perf_sensitive=true
  stage.sh run-check GAP-001
  stage.sh loop-back GAP-001 qa frontend "E2E kırmızı"

${C_BOLD}STATE / GRAPH${C_RESET}
  $STATE
  $STAGES_CFG
EOF
    ;;
  *)
    die "Unknown command: $1. Try: stage.sh help"
    ;;
esac
