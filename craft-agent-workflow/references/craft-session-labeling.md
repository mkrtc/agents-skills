# Craft Session Labeling Reference

This reference mirrors the conventions from `craft-agent-workflow/SKILL.md` and the recommended labels in `labels.config.json`.

## Naming

### Orchestrator

```text
[${tag}] Orchestrator (${project_name})
```

### Worker / subagent / audit / plan-auditor session

```text
${tag} ${title}
```

`SVB` is an example tag only, not a fixed default.

## Common label combinations

### Orchestrator

```text
project::TEST
status::in-progress
```

### Executor in progress

```text
subagent
executor
project::TEST
status::in-progress
worktree::test-fe-auth
```

Use `auditor`, `designer`, or `tester` instead of `executor` for those primary roles.

### Executor done and ready to push

```text
subagent
executor
project::TEST
status::done
git::ready
worktree::test-fe-auth
```

## Label dimensions

### `project::<name>`

Use on every session that belongs to a project/workstream.

### `orchestrator`

Optional user-managed label for orchestrator sessions.

Use when you want to visually mark a session as an orchestrator. Agents do not need to set this automatically unless explicitly instructed.

Do not use `orchestrator` on spawned executor/audit/plan-auditor/designer/tester agents; those use `subagent` plus their primary role label.

### `subagent`

Every non-orchestrator agent spawned by an orchestrator must have this label.

This includes executor, worker, audit/review, plan-auditor, designer, tester, and other bounded task agents.

Also apply exactly one primary role label whenever possible:

- `executor` — implementation;
- `auditor` — audit/review and plan audit;
- `designer` — product/UX/UI design;
- `tester` — QA/testing/verification.

Do not apply `subagent` or a worker role label to the parent orchestrator session.

Peer orchestrators are not subagents; do not label peer orchestrators with `subagent`.

### `priority::<number>`

Use only when priority is explicit or obvious from context.

### `status::<name>`

Operational state. Keep exactly one current `status::...` value.

Recommended values:

- `status::ready`
- `status::in-progress`
- `status::wait`
- `status::wait-answer`
- `status::blocked`
- `status::review`
- `status::error`
- `status::cancelled`
- `status::done`

### `git::<status>`

Git readiness/push state. Keep exactly one current `git::...` value when applicable.

Recommended values:

- `git::progress` — not ready to push.
- `git::ready` — ready to push, not pushed yet.
- `git::pushed` — pushed to Git.

### `worktree::<name>`

Use when work happens in a linked worktree or isolated checkout. `name` is the worktree name.

## Safe update rule

When changing one dimension with `set_session_labels`, preserve all unrelated labels:

- changing `status::...` should not remove `project::...`, `subagent`, the primary role label, `git::...`, or `worktree::...`;
- changing `git::...` should not remove `status::...`;
- changing `worktree::...` should not remove task/project status labels.

Always read current labels first, then replace only the relevant valued-label dimension.

## Worker finalization mapping

Every non-orchestrator spawned agent starts or works with:

```text
subagent
<executor | auditor | designer | tester>
project::<name>
status::in-progress
```

If it works in a worktree, also preserve/add:

```text
worktree::<name>
```

When the worker finishes, it must not leave itself as `status::in-progress`.

| Outcome | Required label update | Required Craft session status |
|---|---|---|
| Success | replace old `status::...` with `status::done` | `needs-review` by default |
| Blocked | replace old `status::...` with `status::blocked` | `needs-review` |
| Error | replace old `status::...` with `status::error` | `needs-review` |
| Cancelled | replace old `status::...` with `status::cancelled` | `needs-review` |

The spawned agent updates its own labels and Craft session status at the end of its task, preserving unrelated labels. Every final worker report must include `Confidence: <0–100>%` and a short evidence-based rationale covering verification, remaining uncertainty, and known risks.

## Removed legacy labels

The old boolean `agent-status` tree has been removed from the current labels config.

Do not use these removed labels for new sessions:

- `ready`
- `in-progress`
- `wait`
- `wait-answer`
- `blocked`
- `review`
- `ready-for-push`
- `pushed`
- `failed`
- `cancelled`

Use instead:

- `status::<name>` for operational status;
- `git::ready` instead of `ready-for-push`;
- `git::pushed` instead of `pushed`.
