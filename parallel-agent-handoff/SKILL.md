---
name: parallel-agent-handoff
description: >-
  Coordinate concurrent Codex/agent sessions in one repository through a
  SQLite-backed shared task queue under tmp/shared_ctx with Markdown task
  mirrors. Use when multiple agents need to split backend/frontend or
  cross-module work, hand off API contracts, claim pending tasks, avoid
  duplicate implementation, verify shared_ctx gitignore safety before commits,
  or mark inter-agent tasks as pending/progress/done. Also use for Russian
  prompts about "параллельная работа агентов", "передай доку фронту/бэку",
  "контракт для другого агента", "sqlite shared_ctx", or "shared_ctx".
---

# Parallel Agent Handoff

Use a project-local SQLite queue so independent Codex sessions can exchange implementation contracts without reading each other's whole context. Keep Markdown as a human-readable mirror, but treat SQLite as the source of truth.

## Protocol

- Treat `--root` as the repository/project root where implementation work happens, not as the `tmp/shared_ctx` directory.
- Prefer running helper commands from the project root with `--root .`; if the current directory is inside a git worktree, the helper resolves the git root automatically.
- Never create a second queue under `tmp/shared_ctx/tmp/shared_ctx`.
- Store state in `tmp/shared_ctx/shared_ctx.sqlite`.
- Store Markdown mirrors in `tmp/shared_ctx/tasks/{task-id}.md`.
- Use task ids with lowercase letters, digits, underscores, or hyphens: `price_api_doc`, `auth-contract`, `checkout_api`.
- Use only these task statuses in SQLite: `pending`, `progress`, `done`.
- Treat the database row as the lock. Only `pending` rows are available to claim.
- Do not infer status from Markdown if the SQLite database exists.
- Do not read task bodies from Markdown or SQLite before a successful claim unless the user explicitly asks for audit or context recovery.

Use the bundled helper instead of writing SQL manually:

```bash
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py init --root .
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py list --root . --status pending
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py claim price_api_doc --root . --agent frontend
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py done price_api_doc --root . --agent frontend
```

## SQLite State

The helper creates a `tasks` table with task metadata, Markdown body, ownership, timestamps, and status. It also creates one `project_state` row with:

- `is_gitignore_checked`: whether `.gitignore` has been checked for this project.
- `is_project_in_gitignore`: whether `tmp/shared_ctx/` is ignored.
- `user_asked`: whether the user has already been asked about adding `tmp/shared_ctx/` to `.gitignore`.

Keep `tmp/shared_ctx/` in `tmp/` and usually out of git. The SQLite database, WAL files, and Markdown mirrors are runtime coordination state, not source code.

## Writer Workflow

Use this when the current agent receives a task that another agent should implement, for example backend defining an API contract for frontend.

1. Run `init` once for the project if the queue does not exist.
2. Write a complete Markdown handoff body before starting your own implementation.
3. Create the task with `create`, passing the body via `--body-file` or `--body`.
4. Then continue your own implementation.

Example:

```bash
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py create price_api_doc \
  --root . \
  --title "Price API contract" \
  --created-by backend \
  --target-owner frontend \
  --body-file /tmp/price_api_doc.md
```

Use the template in `assets/task-template.md` for handoff structure. Include enough detail for the receiving agent to start without asking the writer to restate context.

## Reader Workflow

Use this when the user tells the current agent to implement a contract or task from another agent.

1. List only pending task metadata with `list --status pending`.
2. Claim the selected task with `claim {task-id} --agent {agent-name}`.
3. Read and implement the body only after `claim` succeeds.
4. Add a completion note if useful.
5. Mark the task done with `done {task-id} --agent {agent-name}`.

If claiming fails because the status is not `pending`, assume another agent took or completed the task. Do not read the body.

## Commit Guard

Before making a commit in a project that uses this skill, run:

```bash
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py precommit-check --root .
```

If it prints `ASK_USER`, ask the user whether to add `tmp/shared_ctx/` to `.gitignore`. If the user agrees, run:

```bash
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py add-gitignore --root .
```

If the user declines, run:

```bash
python ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py mark-user-asked --root .
```

Do not ask again when `user_asked=1`; keep warning in the final response if `tmp/shared_ctx/` remains unignored.

## Document Contents

Every handoff document should include:

- Objective: what the receiving agent must build or change.
- Contract: API routes, request/response schemas, events, state shape, generated types, or shared interfaces.
- Ownership: which side owns each file or module if backend and frontend work happen in parallel.
- Compatibility notes: migrations, feature flags, fallback behavior, auth, validation, error cases.
- Acceptance criteria: concrete checks that define done.
- Artifact paths: files already changed or files the receiving agent should modify.
- Risks or blockers: anything that can break integration.

Keep the document concise but executable. Do not include broad project background unless the receiving agent needs it to implement the task.

## Failure Handling

- If implementation is blocked after claiming, leave the task as `progress` and add a `## Blocked` section to the Markdown body in SQLite or the completion/final response.
- Do not move a blocked task back to `pending` unless the user asks or you are certain no implementation work started.
- If a `progress` task appears stale, report it instead of taking it silently.
- If Markdown and SQLite disagree, trust SQLite and refresh the mirror with `export-md`.
