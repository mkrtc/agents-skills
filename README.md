# agents-skills

Reusable agent skills and Craft Agent workflow conventions.

## One-command Craft Agent install

Run this on a new machine to install/update the skills repo and apply Craft Agent workflow config:

```bash
curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh | bash
```

What it does:

1. Clones or pulls this repo into `~/.agents/skills`.
2. Installs labels/statuses from:
   - `craft-agent-workflow/references/labels.config.json`
   - `craft-agent-workflow/references/statuses.config.json`
3. Merges the versioned Craft Agent preference note from:
   - `craft-agent-workflow/references/preferences-note.md`
4. Creates timestamped backups before overwriting local labels/statuses/preferences.
5. Runs best-effort validation if `craft-agent` CLI is available.

After install, open a new chat or restart Craft Agent if the new skills/preferences are not visible immediately.

## SSH install

Default installer uses HTTPS clone. To use SSH:

```bash
curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh \
  | REPO_URL=git@github.com:mkrtc/agents-skills.git bash
```

## Skills only

If you only want to pull skills and do not want to touch Craft Agent labels/statuses/preferences:

```bash
curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh \
  | bash -s -- --skills-only
```

## Custom workspace root

If Craft Agent cannot detect the active workspace root:

```bash
curl -fsSL https://raw.githubusercontent.com/mkrtc/agents-skills/main/install-craft-agent-workflow.sh \
  | bash -s -- --workspace-root ~/Desktop/projects
```

## Manual install

```bash
mkdir -p ~/.agents

git clone git@github.com:mkrtc/agents-skills.git ~/.agents/skills

# or update existing clone
git -C ~/.agents/skills pull --ff-only
```

Validate key skills:

```bash
craft-agent skill validate orchestrator --source global
craft-agent skill validate craft-agent-workflow --source global
```

## Important config behavior

The installer overwrites the active workspace labels/statuses config with the reference config from this repo, after creating backups.

Backups look like:

```text
labels/config.json.bak-YYYYMMDD-HHMMSS
statuses/config.json.bak-YYYYMMDD-HHMMSS
~/.craft-agent/preferences.json.bak-YYYYMMDD-HHMMSS
```

Preferences are not fully replaced. The installer adds or updates a managed block inside `notes`:

```text
[agents-skills:craft-agent-workflow]
...
[/agents-skills:craft-agent-workflow]
```

Existing preference notes outside that block are preserved.

## Craft Agent workflow references

Key reference files:

- `craft-agent-workflow/references/craft-session-labeling.md` — labels, statuses, Git/worktree label conventions.
- `craft-agent-workflow/references/planning-audit.md` — orchestrator complexity scoring and mandatory plan-audit protocol.
- `craft-agent-workflow/references/preferences-note.md` — managed preference note merged by the installer.

## Useful installer options

```bash
./install-craft-agent-workflow.sh --help
./install-craft-agent-workflow.sh --dry-run
./install-craft-agent-workflow.sh --skip-config
./install-craft-agent-workflow.sh --skip-preferences
./install-craft-agent-workflow.sh --skills-only
```
