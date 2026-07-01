---
name: craft-agent-workflow
description: "Craft Agent workflow conventions for orchestrators and spawned agents: session naming, contextual tags, labels, statuses, worktrees, Git readiness, worker final reports, and audit handoffs."
---

# Craft Agent Workflow

Use this skill when coordinating Craft Agent sessions, naming orchestrators/workers, assigning session labels, tracking work status, spawning subagents, using worktrees, or handing work back to an orchestrator.

## Core Principles

- Keep orchestration and execution separate.
- The orchestrator plans, splits, dispatches, collects reports, and requests audits. It does not implement product/code changes itself.
- Spawned workers execute one bounded task and report back to the orchestrator.
- Peer orchestrators may be spawned for separate orchestration streams; they are not subagents.
- `OFFTOP` requests are ephemeral side checks handled by the orchestrator directly; do not add them to the durable plan/task context.
- Labels are combinable metadata. Use valued labels for stateful dimensions instead of many mutually exclusive boolean labels.
- Preserve existing labels when changing a single label dimension such as `status::...`, `git::...`, or `worktree::...`.

## Session Naming

### Orchestrator Sessions

Name orchestrator sessions as:

```text
[${tag}] Orchestrator (${project_name})
```

Examples:

```text
[FRT] Orchestrator (TEST frontend)
[SVB] Orchestrator (Servarium Backend)
[MAP] Orchestrator (Maps)
```

### Worker / Subagent Sessions

Name spawned worker, executor, and audit sessions as:

```text
${tag} ${title}
```

Examples:

```text
FRT Build login form
TEST-FE Fix dashboard filters
SVB Implement pricing API
```

### Tag Selection

- `tag` is a short context-specific prefix for one orchestrator-owned set of sessions.
- If the user provides a tag, use it exactly.
- If no tag is provided, infer a short meaningful tag from the project and scope, then keep it consistent for the orchestrator and every spawned session.
- `SVB` is only an example tag derived from `Servarium Backend`; it is not a fixed default.

## Labels

Labels are additive and can be combined.

Typical orchestrator labels:

```text
project::TEST
status::in-progress
```

Typical worker labels:

```text
subagent
project::TEST
status::in-progress
worktree::test-fe-auth
```

Typical completed worker labels with Git readiness:

```text
subagent
project::TEST
status::done
git::ready
worktree::test-fe-auth
```

### Label ID Casing

Craft Agent label IDs are lowercase slugs. Use `git::ready`, not `GIT::ready`. The label display name may be `GIT` in the UI.

### Project Label

Use:

```text
project::<name>
```

Apply it to every session related to a specific project, product area, or workstream.

Examples:

```text
project::Servarium Backend
project::TEST frontend
```

### Subagent Label

Use:

```text
subagent
```

Apply only to spawned worker, executor, and audit sessions. Do not apply it to the parent orchestrator session.

### Priority Label

Use:

```text
priority::<number>
```

Only set priority when the user explicitly provides it or the task context already makes it clear. Do not invent priority values.

### Operational Status Label

Use exactly one operational status label at a time:

```text
status::<name>
```

Recommended values:

- `status::ready` — the session is ready or waiting to start.
- `status::in-progress` — the agent is actively working.
- `status::wait` — the agent is waiting for an external event or another task.
- `status::wait-answer` — the agent is waiting for a user answer.
- `status::blocked` — the agent cannot continue without help or missing input.
- `status::review` — the result is under review or audit.
- `status::failed` — the agent failed the task.
- `status::cancelled` — the task was cancelled.
- `status::done` — the agent completed its assigned task.

When changing operational status, remove any previous `status::...` label and preserve all other labels.

### Git Status Label

Use exactly one Git status label at a time when Git readiness matters:

```text
git::<status>
```

Recommended values:

- `git::progress` — not ready to push; task still needs work or has unfinished changes.
- `git::ready` — ready to push but not pushed yet.
- `git::pushed` — changes have been pushed to Git.

Do not encode Git readiness in `status::...`.

### Worktree Label

Use:

```text
worktree::<name>
```

Apply when the orchestrator or workers are operating in a linked Git worktree or other isolated checkout.

Rules:

- `name` should be the worktree name, not necessarily the full path.
- Apply the same `worktree::<name>` label to every session working in that worktree.
- Preserve the label until the session is done or moves to another worktree.

Example:

```text
worktree::servarium-backend-auth-fix
```

### Legacy Agent Status Labels

Older configs may contain a boolean `agent-status` label tree with children like `ready`, `in-progress`, `ready-for-push`, and `pushed`.

For new sessions:

- Use `status::<name>` instead of legacy boolean operational labels.
- Use `git::ready` instead of `ready-for-push`.
- Use `git::pushed` instead of `pushed`.
- Do not delete legacy labels from old sessions unless the user explicitly asks for migration/cleanup.

## Updating Labels Safely

When using `set_session_labels`, remember that it replaces all labels.

Safe procedure:

1. Read current session labels first with `get_session_info`.
2. Remove only the old value for the dimension you are changing:
   - old `status::...` when setting a new `status::...`;
   - old `git::...` when setting a new `git::...`;
   - old `worktree::...` when moving worktrees.
3. Preserve unrelated labels such as `project::...`, `subagent`, and `priority::...`.
4. Call `set_session_labels` with the full updated label list.

## Craft Session Status vs Labels

Craft session status is a lifecycle bucket such as `todo`, `needs-review`, `done`, or `cancelled`.

Labels are richer metadata.

Guidelines:

- Worker starts: session status usually `todo`; label `status::in-progress`.
- Worker blocked: keep session status open; label `status::blocked`.
- Worker completed: set label `status::done` and Craft session status `done`.
- Orchestrator awaiting review: set label `status::review` and, when useful, Craft session status `needs-review`.
- Cancelled work: set label `status::cancelled` and Craft session status `cancelled`.

## OFFTOP / Ephemeral Requests

If a user message starts with an OFFTOP marker, the orchestrator handles it directly as an ephemeral side request.

Markers are case-insensitive and include:

```text
OFFTOP
оффтоп
отп
ot
oft
```

A colon after the marker is optional.

Examples:

```text
OFFTOP: how many resources does container ID use?
ot check current pod CPU
оффтоп: покажи размер директории tmp
```

Rules:

- The orchestrator may use tools/sources itself to answer the OFFTOP request.
- Do not spawn executor workers for ordinary OFFTOP checks unless the user explicitly asks.
- Do not modify the main plan, task queue, worker prompts, acceptance criteria, or project scope because of OFFTOP content.
- Do not carry OFFTOP details into future worker context. Treat the information as disposable after answering.
- Answer briefly, then return to the active orchestration workflow.

## Peer Orchestrators

The orchestrator may spawn another orchestrator for a separate orchestration stream. A peer orchestrator is not a subagent and should not receive the `subagent` label.

Use a peer orchestrator when:

- The user gives a new task while current workers/auditors are still running; and
- The new task is separate enough that managing it in the current orchestrator would distract from or conflict with the active plan.

Do not spawn a peer orchestrator when:

- The new task can be safely added to the current plan; and
- It will not interfere with files, worktrees, branches, active workers, or unfinished changes.

In that case, update the current plan and dispatch additional workers if needed.

Peer orchestrator naming:

```text
[${tag}] Orchestrator (${project_name})
```

Peer orchestrator prompt requirements:

- State that it is a peer orchestrator, not an executor/subagent.
- Include the new task and relevant project context.
- Include the parent/current orchestrator session ID for coordination.
- Include a short summary of active workers/tasks that may conflict, without dumping unrelated context.
- Explicitly instruct: if the new task may interfere with current active work, use a new worktree.
- Explicitly instruct: if it discovers the task is actually safe and non-conflicting, it may proceed in the current workspace according to project rules.
- Require it to follow `craft-agent-workflow` naming, labels, statuses, worktree, and audit rules.

## Orchestrator Responsibilities

The orchestrator must not implement product/source changes directly.

The orchestrator is responsible for:

1. Inspecting enough project context to plan safely.
2. Producing a detailed plan.
3. Splitting the plan into independent tasks.
4. Dispatching tasks to spawned agents.
5. Giving each agent a complete self-contained prompt.
6. Receiving final reports from agents.
7. Checking reports for completeness, contradictions, and risk.
8. Spawning audit/review agents whenever confidence in a worker result is below 95%.
9. Deciding whether new incoming tasks should be merged into the current plan or delegated to a peer orchestrator.
10. Handling OFFTOP side requests ephemerally without polluting the durable task context.
11. Creating follow-up tasks when work is incomplete or risky.

## Worker Prompt Requirements

Every spawned worker prompt must include:

- The orchestrator session ID.
- The shared `tag`.
- The required worker session name format: `${tag} ${title}`.
- The project name for `project::<name>`.
- The worktree name for `worktree::<name>`, if applicable.
- The exact working directory.
- The task title and objective.
- The exact implementation scope.
- Explicit out-of-scope items.
- Acceptance criteria.
- Verification commands or manual checks.
- Required final report format.
- Finalization instructions.

Every spawned worker prompt must start with:

```text
You are an executor agent for one task created by an orchestrator.
Do not broaden the scope.
Work only on the task below.
```

## Worker Finalization

When a worker completes successfully, it must:

1. Produce the required final report.
2. Set its labels so it has `status::done`.
3. Set Git readiness if applicable:
   - `git::progress` if not ready to push;
   - `git::ready` if ready to push;
   - `git::pushed` if already pushed.
4. Set its Craft session status to `done`.
5. Return/send its output to the orchestrator session.

If blocked, the worker must:

1. Set `status::blocked`.
2. Keep Craft session status open.
3. Report the blocker clearly.
4. Avoid claiming completion.

## Worker Final Report Format

```text
Result:
- Summary:
- Files touched:
- Verification run and outcome:
- Labels/status set:
- Git status:
- Worktree:
- Blockers:
- Follow-up needed:
```

## Audit Rule

If the orchestrator has less than 95% confidence that a worker completed the task correctly, it must spawn a separate audit/review agent.

Audit agents should:

- Use the same `tag`.
- Use a title that makes the audit scope clear.
- Receive the original worker task, worker report, changed files/modules, and acceptance criteria.
- Avoid implementing changes unless explicitly asked; the default audit task is verification and reporting.
- Return a clear pass/fail/risk report to the orchestrator.
