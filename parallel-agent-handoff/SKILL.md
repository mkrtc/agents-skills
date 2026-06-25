---
name: parallel-agent-handoff
description: >-
  Coordinate concurrent Codex/OpenCode agent sessions in one repository through
  a SQLite-backed shared task queue under tmp/shared_ctx with Markdown task
  mirrors. Use when multiple agents need orchestrator/executor roles, detailed
  handoff plans, split backend/frontend or cross-module work, hand off API
  contracts, claim pending tasks, write executor result reports, delete one or
  all queued tasks with their files, avoid duplicate implementation, verify
  shared_ctx gitignore safety before commits, mark tasks as pending/progress/done,
  or spawn OpenCode sessions to execute pending tasks.
  Also use for Russian prompts about "параллельная работа агентов",
  "оркестратор", "оректор", "арекстор", "исполнитель", "передай доку
  фронту/бэку", "контракт для другого агента", "отправь агентов на задачи",
  "sqlite shared_ctx", or "shared_ctx".
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
- Store executor result reports in `tmp/shared_ctx/results/{task-id}.md`; the task row keeps `result_md_path` and `result_summary`.
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
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py done price_api_doc --root . --agent frontend --result-file /tmp/price_api_result.md --summary "Implemented price API UI"
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py show-result price_api_doc --root .
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py delete price_api_doc --root .
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py delete-all --root .
python3 ~/.agents/skills/parallel-agent-handoff/scripts/shared_ctx.py worktree-info --root .
```

## Role Modes

Use explicit role words in the user prompt to select the workflow:

- Treat `orchestrator`, `оркестратор`, `оректор`, `арекстор`, and `орекстор` as the orchestrator role.
- Treat `executor` and `исполнитель` as the executor role.
- If no role is explicit, use the existing writer, reader, or dispatch workflow that matches the request.

An orchestrator plans and creates tasks. An executor claims and implements tasks. Do not mix roles in one session unless the user explicitly asks.

## Orchestrator Workflow

Use this when the prompt says the current agent is an orchestrator.

1. Inspect only the project context needed to plan safely.
2. Create a detailed implementation plan before creating tasks.
3. Split the plan into independently claimable executor tasks. Prefer tasks that can run in parallel without writing the same files or relying on unfinished outputs from another task.
4. If a task depends on another task, write the dependency in the task body and do not dispatch it as parallel work until the dependency is done.
5. For each executor task, write a complete handoff body with role, objective, ownership boundaries, dependencies, required changes, acceptance criteria, validation commands, and risks.
6. Create tasks with `create`; leave them in `pending`.
7. Do not claim or implement executor tasks from the orchestrator session.
8. If the user asks to send agents after planning, create all tasks first, then use the OpenCode Dispatch Workflow for the independent pending tasks.
9. When checking completed work, list done task metadata and read the `result_md_path` files or use `show-result`; do not rely on status alone.
10. Use result reports to decide whether follow-up tasks, corrections, or new executor direction are needed.
11. Report the created task ids and any dependency ordering.

The orchestrator may write `tmp/shared_ctx` queue state and Markdown handoff documents. It must not edit product/source files unless the user explicitly stops the orchestration workflow and asks this session to implement.

## Executor Workflow

Use this when the prompt says the current agent is an executor.

1. If the prompt names an exact task id, claim that task id.
2. If no task id is named, follow the Reader Workflow.
3. Read and implement the task body only after a successful claim.
4. Use the task's ownership boundaries and acceptance criteria as the implementation contract.
5. Before marking done, write a concise Markdown result report for the orchestrator. Create the parent directory if needed.
6. Mark the task done only after implementation and reasonable verification are complete, passing `--result-file` and `--summary`.

If the executor is blocked after claiming, leave the task in `progress`, explain the blocker, and do not silently return it to `pending`.

## OpenCode Setup

Expected OpenCode integration:

- `opencode-sessions` is installed in global OpenCode config for general session handoff/fork workflows.
- `~/.config/opencode/plugins/parallel-agent-handoff-spawner.js` is a local OpenCode plugin that exposes `shared_ctx_spawn_sessions`. Local plugins in `~/.config/opencode/plugins/` are auto-loaded by OpenCode on startup.
- `shared_ctx_spawn_sessions` creates child sessions immediately, inherits the parent session model and variant when possible, and queues prompts until the dispatcher session emits `session.idle` or `session.status=idle`. If no idle event is observed, it uses a fallback timer.

If OpenCode has just been reconfigured, tell the user to restart OpenCode Desktop/TUI before expecting new tools to appear.

## OpenCode oh-my-opencode-slim Skills

Use these rules only when the current environment is OpenCode and `oh-my-opencode-slim` skills or agents are available.

- Executors may use any available `oh-my-opencode-slim` skill, agent, or tool that fits the claimed task, including write-capable implementation helpers.
- Orchestrators may use only read-only `oh-my-opencode-slim` capabilities for discovery, analysis, review, documentation lookup, planning, decomposition, or design advice.
- Orchestrators must not use `Fixer`, Designer implementation/editing mode, refactoring helpers, formatting helpers, code generators that write files, `apply_patch`, or any capability whose purpose includes editing project files.
- Designer is allowed for orchestrators only when used for design planning, critique, specs, or task decomposition. It is not allowed for writing or modifying UI/source files.
- If it is unclear whether an `oh-my-opencode-slim` capability is read-only, treat it as not allowed for orchestrators.

Creating `tmp/shared_ctx` queue rows and Markdown mirrors is coordination work and remains allowed for orchestrators.

## SQLite State

The helper creates a `tasks` table with task metadata, Markdown body, ownership, timestamps, and status. It also creates one `project_state` row with:

- `is_gitignore_checked`: whether `.gitignore` has been checked for this project.
- `is_project_in_gitignore`: whether `tmp/shared_ctx/` is ignored.
- `user_asked`: whether the user has already been asked about adding `tmp/shared_ctx/` to `.gitignore`.

Keep `tmp/shared_ctx/` in `tmp/` and usually out of git. The SQLite database, WAL files, and Markdown mirrors are runtime coordination state, not source code.
Executor result reports are coordination artifacts, not source code.

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
5. If the OpenCode tool `shared_ctx_spawn_sessions` is available, call it once with the selected task ids/titles and `project_root`. Do not set `default_agent` unless the user requested a specific OpenCode agent; the tool defaults to the current agent, then `build`.
6. Expect the tool to create sessions now and send prompts after the dispatcher session becomes idle/status-idle, with fallback dispatch if the idle event is not observed. Do not manually resend prompts unless the tool reports a dispatch failure.
7. The spawned session prompt must identify the child agent as an `executor`, tell it to claim the exact task id first, then read and implement the body printed by the helper, then mark it done.
8. The spawned session prompt must require a Markdown result report and `done --result-file ... --summary ...`.
9. Report spawned task ids, titles, and session ids.

Preferred OpenCode tool call shape:

```typescript
shared_ctx_spawn_sessions({
  project_root: "/absolute/project/root",
  initial_delay_ms: 250,
  stagger_ms: 750,
  fallback_delay_ms: 5000,
  tasks: [
    { task_id: "price_api_doc", title: "Price API contract" }
  ]
})
```

Only pass `model_provider_id`, `model_id`, and `model_variant` when the user explicitly asks to force a model or reasoning preset. Otherwise let the tool inherit the parent session model and variant so spawned sessions use the same working API provider and reasoning preset as the dispatcher.

If only the `session` tool from `opencode-sessions` is available, use `session({ mode: "new", agent: "build", text: "<claim-first executor prompt>" })` once per selected task. Put `Chat title should be: <task title>` and `Role: executor` at the top of the prompt, but understand that `opencode-sessions` itself does not accept a title argument. If neither OpenCode spawn tool is available, do not claim the task; explain that session spawning is unavailable in the current environment and leave tasks pending.

When creating new handoff tasks and dispatching them immediately, create all pending tasks first, then dispatch those task ids through this workflow.

## Reader Workflow

Use this when the user tells the current agent to implement a contract or task from another agent.

1. List only pending task metadata with `list --status pending`.
2. If the request is to work on or implement a queue task, do not stop after listing.
3. If there is exactly one pending task, claim it immediately with `claim-next --agent {agent-name}` or `claim {task-id} --agent {agent-name}`.
4. If there are multiple pending tasks, do not choose automatically even when one appears to match the current role/session. Ask the user which task id to claim.
5. Read and implement the body only after `claim` succeeds.
6. Write a result report with what changed, changed files, validation, follow-ups, and blockers.
7. Mark the task done with `done {task-id} --agent {agent-name} --result-file <path> --summary <one-line summary>`.

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

- Role: normally `executor`.
- Objective: what the receiving agent must build or change.
- Contract: API routes, request/response schemas, events, state shape, generated types, or shared interfaces.
- Ownership: which side owns each file or module if backend and frontend work happen in parallel.
- Dependencies: task ids that must be done first, if any.
- Parallel safety: files or modules this task may touch and files it must avoid.
- Compatibility notes: migrations, feature flags, fallback behavior, auth, validation, error cases.
- Acceptance criteria: concrete checks that define done.
- Artifact paths: files already changed or files the receiving agent should modify.
- Risks or blockers: anything that can break integration.

Keep the document concise but executable. Do not include broad project background unless the receiving agent needs it to implement the task.

## Result Report Contents

Every executor result report should include:

- Summary: one or two sentences about the completed work.
- Changed files: exact paths touched, or `None` for chat-only/report-only tasks.
- Validation: commands or manual checks run and their results.
- Follow-ups: anything the orchestrator should schedule next.
- Blockers: unresolved issues, or `None`.

The executor final chat response can be short. The result report is the durable handoff artifact for orchestration.

## Cleanup Workflow

Use cleanup commands when the user asks to remove old, completed, stale, test, or all shared tasks.

- Delete one task with `delete {task-id} --root .`.
- Delete all queue tasks with `delete-all --root .`.
- Do not manually edit SQLite or remove individual files for normal cleanup.
- `delete` removes the task row plus its task mirror and result report files.
- `delete-all` removes all task rows plus all files under `tmp/shared_ctx/tasks/` and `tmp/shared_ctx/results/`.
- Cleanup preserves `tmp/shared_ctx/shared_ctx.sqlite` and `project_state` so gitignore/precommit metadata remains intact.

## Failure Handling

- If implementation is blocked after claiming, leave the task as `progress` and add a `## Blocked` section to the Markdown body in SQLite or the completion/final response.
- Do not move a blocked task back to `pending` unless the user asks or you are certain no implementation work started.
- If a `progress` task appears stale, report it instead of taking it silently.
- If Markdown and SQLite disagree, trust SQLite and refresh the mirror with `export-md`.
