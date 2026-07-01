# Craft Session Labeling Reference

This reference mirrors the conventions from `craft-agent-workflow/SKILL.md` and the recommended labels in `labels.config.json`.

## Naming

### Orchestrator

```text
[${tag}] Orchestrator (${project_name})
```

### Worker / subagent / audit session

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

### Worker in progress

```text
subagent
project::TEST
status::in-progress
worktree::test-fe-auth
```

### Worker done and ready to push

```text
subagent
project::TEST
status::done
git::ready
worktree::test-fe-auth
```

## Label dimensions

### `project::<name>`

Use on every session that belongs to a project/workstream.

### `subagent`

Use only on spawned worker/audit sessions, not on the orchestrator.

Peer orchestrators are not subagents; do not label them with `subagent`.

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
- `status::failed`
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

- changing `status::...` should not remove `project::...`, `subagent`, `git::...`, or `worktree::...`;
- changing `git::...` should not remove `status::...`;
- changing `worktree::...` should not remove task/project status labels.

Always read current labels first, then replace only the relevant valued-label dimension.

## Legacy labels

Legacy boolean `agent-status` children may still exist in older sessions/configs. New sessions should prefer:

- `status::<name>` for operational status;
- `git::ready` instead of `ready-for-push`;
- `git::pushed` instead of `pushed`.
