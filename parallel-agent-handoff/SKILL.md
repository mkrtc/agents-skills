---
name: parallel-agent-handoff
description: >-
  Coordinate concurrent Codex/agent sessions in one repository through a
  SQLite-backed shared task queue under tmp/shared_ctx with Markdown task
  mirrors. Use when multiple agents need to split backend/frontend or
  cross-module work, hand off API contracts, claim pending tasks, avoid
  duplicate implementation, verify shared_ctx gitignore safety before commits,
  mark inter-agent tasks as pending/progress/done, or spawn OpenCode sessions
  to execute pending tasks. Also use for Russian prompts about "параллельная
  работа агентов", "передай доку фронту/бэку", "контракт для другого агента",
  "отправь агентов на задачи", "sqlite shared_ctx", or "shared_ctx".
---

# Parallel Agent Handoff

Use a project-local SQLite queue so independent Codex sessions can exchange implementation contracts without reading each other's whole context. Keep Markdown as a human-readable mirror, but treat SQLite as the source of truth.

## Protocol

- Treat `--root` as the repository/project root where implementation work happens, not as the `tmp/shared_ctx` directory.
- Prefer running helper commands from the project root with `--root .`; if the current directory is inside a git worktree, the helper resolves the git root automatically.
- Run helper commands only with `python3`.
- Before the final response, run `python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py worktree-info --root .`; if `is_linked_worktree=1`, include the current `worktree_name` and `branch` in the final response.
- Never create a second queue under `tmp/shared_ctx/tmp/shared_ctx`.
- Store state in `tmp/shared_ctx/shared_ctx.sqlite`.
- Store Markdown mirrors in `tmp/shared_ctx/tasks/{task-id}.md`.
- Use task ids with lowercase letters, digits, underscores, or hyphens: `price_api_doc`, `auth-contract`, `checkout_api`.
- Use only these task statuses in SQLite: `pending`, `progress`, `done`.
- Treat the database row as the lock. Only `pending` rows are available to claim.
- Do not infer status from Markdown if the SQLite database exists.
- Do not read task bodies from Markdown or SQLite before a successful claim unless the user explicitly asks for audit or context recovery.
- When running inside OpenCode and asked to send agents to execute tasks, prefer spawning OpenCode sessions instead of doing the tasks in the dispatcher session.

Use the bundled helper instead of writing SQL manually:

```bash
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py init --root .
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py list --root . --status pending
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py claim-next --root . --agent frontend
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py claim price_api_doc --root . --agent frontend
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py done price_api_doc --root . --agent frontend
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py worktree-info --root .
```

## OpenCode Setup

Expected OpenCode integration:

- `opencode-sessions` is installed in global OpenCode config for general session handoff/fork workflows.
- `~/.config/opencode/plugins/parallel-agent-handoff-spawner.js` is a local OpenCode plugin that exposes `shared_ctx_spawn_sessions`. Local plugins in `~/.config/opencode/plugins/` are auto-loaded by OpenCode on startup.
- `shared_ctx_spawn_sessions` creates child sessions immediately but queues their prompts until the dispatcher session emits `session.idle`; this avoids starting child model/API requests while the parent session is still busy.

If OpenCode has just been reconfigured, tell the user to restart OpenCode Desktop/TUI before expecting new tools to appear.

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
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py create price_api_doc \
  --root . \
  --title "Price API contract" \
  --created-by backend \
  --target-owner frontend \
  --body-file /tmp/price_api_doc.md
```

Use the template in `assets/task-template.md` for handoff structure. Include enough detail for the receiving agent to start without asking the writer to restate context.

## OpenCode Dispatch Workflow

Use this when the user asks to send, spawn, or launch agents to execute queued tasks, for example "отправь агентов на выполнение тасков".

1. Run `list --status pending` and inspect metadata only.
2. If the user says to dispatch all pending tasks, select all pending rows. If the user gives task ids, select only those ids. If there are multiple pending tasks and the request does not clearly mean all or name exact ids, ask which task ids to dispatch.
3. Do not claim selected tasks in the dispatcher session.
4. Do not read task bodies in the dispatcher session.
5. If the OpenCode tool `shared_ctx_spawn_sessions` is available, call it once with the selected task ids/titles, `project_root`, and `default_agent: "build"` unless the user requested another OpenCode agent.
6. Expect the tool to create sessions now and send prompts only after the dispatcher session becomes idle. Do not manually resend prompts unless the tool reports a dispatch failure.
7. The spawned session prompt must tell the child agent to claim the exact task id first, then read and implement the body printed by the helper, then mark it done.
8. Report spawned task ids, titles, and session ids.

Preferred OpenCode tool call shape:

```typescript
shared_ctx_spawn_sessions({
  project_root: "/absolute/project/root",
  default_agent: "build",
  initial_delay_ms: 1000,
  stagger_ms: 1500,
  tasks: [
    { task_id: "price_api_doc", title: "Price API contract" }
  ]
})
```

If only the `session` tool from `opencode-sessions` is available, use `session({ mode: "new", agent: "build", text: "<claim-first prompt>" })` once per selected task. Put `Chat title should be: <task title>` at the top of the prompt, but understand that `opencode-sessions` itself does not accept a title argument. If neither OpenCode spawn tool is available, do not claim the task; explain that session spawning is unavailable in the current environment and leave tasks pending.

When creating new handoff tasks and dispatching them immediately, create all pending tasks first, then dispatch those task ids through this workflow.

## Reader Workflow

Use this when the user tells the current agent to implement a contract or task from another agent.

1. List only pending task metadata with `list --status pending`.
2. If the request is to work on or implement a queue task, do not stop after listing.
3. If there is exactly one pending task, claim it immediately with `claim-next --agent {agent-name}` or `claim {task-id} --agent {agent-name}`.
4. If there are multiple pending tasks, do not choose automatically even when one appears to match the current role/session. Ask the user which task id to claim.
5. Read and implement the body only after `claim` succeeds.
6. Add a completion note if useful.
7. Mark the task done with `done {task-id} --agent {agent-name}`.

If claiming fails because the status is not `pending`, assume another agent took or completed the task. Do not read the body.
If `claim-next` reports multiple matching pending tasks, show the candidate task ids/titles and ask the user which one to claim.

Do not list `progress` or `done` before claiming unless the user asks for a queue audit/status report. If the user only asks to list, inspect, or report queue status, list metadata and do not claim.

## Commit Guard

Before making a commit in a project that uses this skill, run:

```bash
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py precommit-check --root .
```

If it prints `ASK_USER`, ask the user whether to add `tmp/shared_ctx/` to `.gitignore`. If the user agrees, run:

```bash
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py add-gitignore --root .
```

If the user declines, run:

```bash
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py mark-user-asked --root .
```

Do not ask again when `user_asked=1`; keep warning in the final response if `tmp/shared_ctx/` remains unignored.

## Final Response

At the end of work using this skill, run `worktree-info`. If it reports `is_linked_worktree=1`, include one concise line in the final response:

```text
Worktree: <worktree_name> (branch: <branch>)
```

If `branch` is empty, use `branch: unknown`. If it reports `is_linked_worktree=0` or `is_git_worktree=0`, do not mention a worktree.

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
