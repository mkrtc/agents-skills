#!/usr/bin/env bash
set -euo pipefail

DEFAULT_REPO_URL="https://github.com/mkrtc/agents-skills.git"
REPO_URL_EXPLICIT=0
if [ "${REPO_URL+x}" = "x" ]; then
  REPO_URL_EXPLICIT=1
else
  REPO_URL="$DEFAULT_REPO_URL"
fi
BRANCH="${BRANCH:-main}"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.agents/skills}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-}"
INSTALL_CONFIG=1
INSTALL_PREFERENCES=1
NO_PULL=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Install/update mkrtc agent skills and Craft Agent workflow config.

Default behavior:
  - clone/pull agents-skills into ~/.agents/skills
  - install Craft Agent labels/statuses from craft-agent-workflow references
  - merge craft-agent-workflow preference note into ~/.craft-agent/preferences.json
  - create timestamped backups before overwriting labels/statuses/preferences

One-command install:
  curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh | bash

Options:
  --skills-only          Only clone/pull ~/.agents/skills; skip labels/statuses/preferences
  --skip-config          Skip labels/statuses install
  --skip-preferences     Skip preferences note merge
  --workspace-root PATH  Override active Craft Agent workspace root
  --repo-url URL         Override git repo URL (default: https://github.com/mkrtc/agents-skills.git)
  --branch NAME          Git branch to install (default: main)
  --skills-dir PATH      Override skills install dir (default: ~/.agents/skills)
  --no-pull              Do not fetch/pull when ~/.agents/skills already exists
  --dry-run              Print actions without changing files
  -h, --help             Show this help

Environment overrides:
  REPO_URL, BRANCH, SKILLS_DIR, WORKSPACE_ROOT

Examples:
  # Install using SSH remote instead of HTTPS
  curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh \
    | REPO_URL=git@github.com:mkrtc/agents-skills.git bash

  # Only pull skills, do not touch Craft Agent config
  curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh \
    | bash -s -- --skills-only
EOF
}

log() { printf '[agents-skills] %s\n' "$*"; }
warn() { printf '[agents-skills] WARNING: %s\n' "$*" >&2; }
die() { printf '[agents-skills] ERROR: %s\n' "$*" >&2; exit 1; }

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[agents-skills] DRY-RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skills-only)
      INSTALL_CONFIG=0
      INSTALL_PREFERENCES=0
      shift
      ;;
    --skip-config)
      INSTALL_CONFIG=0
      shift
      ;;
    --skip-preferences)
      INSTALL_PREFERENCES=0
      shift
      ;;
    --workspace-root)
      [ "$#" -ge 2 ] || die "--workspace-root requires a value"
      WORKSPACE_ROOT="$2"
      shift 2
      ;;
    --repo-url)
      [ "$#" -ge 2 ] || die "--repo-url requires a value"
      REPO_URL="$2"
      REPO_URL_EXPLICIT=1
      shift 2
      ;;
    --branch)
      [ "$#" -ge 2 ] || die "--branch requires a value"
      BRANCH="$2"
      shift 2
      ;;
    --skills-dir)
      [ "$#" -ge 2 ] || die "--skills-dir requires a value"
      SKILLS_DIR="$2"
      shift 2
      ;;
    --no-pull)
      NO_PULL=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

expand_path() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.abspath(os.path.expanduser(sys.argv[1])))
PY
}

resolve_workspace_root() {
  if [ -n "$WORKSPACE_ROOT" ]; then
    expand_path "$WORKSPACE_ROOT"
    return
  fi

  python3 - <<'PY'
import json, os, sys
config_path = os.path.expanduser('~/.craft-agent/config.json')
if not os.path.exists(config_path):
    sys.exit('NO_CONFIG')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
active = config.get('activeWorkspaceId')
workspaces = config.get('workspaces') or []
workspace = next((w for w in workspaces if w.get('id') == active), None)
if not workspace and len(workspaces) == 1:
    workspace = workspaces[0]
if not workspace or not workspace.get('rootPath'):
    sys.exit('NO_WORKSPACE')
print(os.path.abspath(os.path.expanduser(workspace['rootPath'])))
PY
}

backup_file() {
  local path="$1"
  if [ -f "$path" ]; then
    local ts
    ts="$(date +%Y%m%d-%H%M%S)"
    run cp "$path" "$path.bak-$ts"
    log "Backup: $path.bak-$ts"
  fi
}

install_or_update_repo() {
  local skills_dir
  skills_dir="$(expand_path "$SKILLS_DIR")"
  SKILLS_DIR="$skills_dir"

  require_cmd git
  require_cmd python3

  if [ -d "$SKILLS_DIR/.git" ]; then
    log "Updating skills repo: $SKILLS_DIR"
    if [ "$NO_PULL" -eq 0 ]; then
      local current_url
      current_url="$(git -C "$SKILLS_DIR" remote get-url origin 2>/dev/null || true)"
      if [ -z "$current_url" ]; then
        run git -C "$SKILLS_DIR" remote add origin "$REPO_URL"
      elif [ "$REPO_URL_EXPLICIT" -eq 1 ] || printf '%s' "$current_url" | grep -q 'claude_skils'; then
        run git -C "$SKILLS_DIR" remote set-url origin "$REPO_URL"
      else
        log "Keeping existing origin remote: $current_url"
      fi
      run git -C "$SKILLS_DIR" fetch origin "$BRANCH"
      run git -C "$SKILLS_DIR" checkout "$BRANCH"
      run git -C "$SKILLS_DIR" pull --ff-only origin "$BRANCH"
    else
      log "Skipping pull because --no-pull was set"
    fi
  else
    if [ -e "$SKILLS_DIR" ] && [ -n "$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 2>/dev/null || true)" ]; then
      die "$SKILLS_DIR exists and is not an empty git repository"
    fi
    log "Cloning skills repo: $REPO_URL -> $SKILLS_DIR"
    run mkdir -p "$(dirname "$SKILLS_DIR")"
    run git clone --branch "$BRANCH" "$REPO_URL" "$SKILLS_DIR"
  fi
}

install_config() {
  [ "$INSTALL_CONFIG" -eq 1 ] || return 0

  local workspace_root labels_src statuses_src labels_dst statuses_dst
  if ! workspace_root="$(resolve_workspace_root)"; then
    die "Cannot resolve Craft Agent workspace root. Use --workspace-root PATH or --skills-only."
  fi

  labels_src="$SKILLS_DIR/craft-agent-workflow/references/labels.config.json"
  statuses_src="$SKILLS_DIR/craft-agent-workflow/references/statuses.config.json"
  labels_dst="$workspace_root/labels/config.json"
  statuses_dst="$workspace_root/statuses/config.json"

  [ -f "$labels_src" ] || die "Missing labels reference: $labels_src"
  [ -f "$statuses_src" ] || die "Missing statuses reference: $statuses_src"

  log "Installing labels/statuses into workspace: $workspace_root"
  run mkdir -p "$workspace_root/labels" "$workspace_root/statuses"
  backup_file "$labels_dst"
  backup_file "$statuses_dst"
  run cp "$labels_src" "$labels_dst"
  run cp "$statuses_src" "$statuses_dst"
}

install_preferences() {
  [ "$INSTALL_PREFERENCES" -eq 1 ] || return 0

  local prefs_path note_path
  prefs_path="$HOME/.craft-agent/preferences.json"
  note_path="$SKILLS_DIR/craft-agent-workflow/references/preferences-note.md"

  [ -f "$note_path" ] || die "Missing preferences note: $note_path"

  log "Merging Craft Agent preferences note"
  run mkdir -p "$HOME/.craft-agent"
  backup_file "$prefs_path"

  if [ "$DRY_RUN" -eq 1 ]; then
    log "DRY-RUN: would merge managed preference block from $note_path into $prefs_path"
    return 0
  fi

  python3 - "$prefs_path" "$note_path" <<'PY'
import json, os, re, sys, time
prefs_path, note_path = sys.argv[1], sys.argv[2]
start = '[agents-skills:craft-agent-workflow]'
end = '[/agents-skills:craft-agent-workflow]'
with open(note_path, 'r', encoding='utf-8') as f:
    note = f.read().strip()
block = f'{start}\n{note}\n{end}'
if os.path.exists(prefs_path):
    with open(prefs_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
else:
    data = {}
existing = data.get('notes') or ''
if start in existing and end in existing:
    pattern = re.escape(start) + r'.*?' + re.escape(end)
    notes = re.sub(pattern, block, existing, flags=re.S)
elif existing.strip():
    notes = existing.rstrip() + '\n\n' + block
else:
    notes = block
data['notes'] = notes
data['updatedAt'] = int(time.time() * 1000)
with open(prefs_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')
PY
}

validate_install() {
  log "Validating installed files"
  run python3 -m json.tool "$SKILLS_DIR/craft-agent-workflow/references/labels.config.json" >/dev/null
  run python3 -m json.tool "$SKILLS_DIR/craft-agent-workflow/references/statuses.config.json" >/dev/null

  if command -v craft-agent >/dev/null 2>&1; then
    log "Running best-effort Craft Agent CLI validation"
    craft-agent skill validate orchestrator --source global || warn "craft-agent skill validate orchestrator failed"
    craft-agent skill validate craft-agent-workflow --source global || warn "craft-agent skill validate craft-agent-workflow failed"
    craft-agent skill validate craft-agent-executor --source global || warn "craft-agent skill validate craft-agent-executor failed"
    craft-agent skill validate craft-agent-auditor --source global || warn "craft-agent skill validate craft-agent-auditor failed"
    craft-agent skill validate craft-agent-designer --source global || warn "craft-agent skill validate craft-agent-designer failed"
    craft-agent skill validate craft-agent-tester --source global || warn "craft-agent skill validate craft-agent-tester failed"
    craft-agent skill validate plan-auditor --source global || warn "craft-agent skill validate plan-auditor failed"
    craft-agent label list >/dev/null || warn "craft-agent label list failed"
  else
    warn "craft-agent CLI not found; skipped Craft Agent validation"
  fi
}

main() {
  install_or_update_repo
  install_config
  install_preferences
  validate_install

  log "Done. Open a new chat or restart Craft Agent if updated skills/preferences are not visible immediately."
}

main
