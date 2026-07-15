# Craft Session Labeling Reference

This reference is subordinate to [`craft-agent-workflow/SKILL.md`](../SKILL.md), the canonical source for shared workflow rules.

## Naming

- Orchestrator: `[${tag}] Orchestrator (${project_name})`
- Worker/subagent/audit/plan-auditor: `${tag} ${title}`
- `SVB` is an example tag only, not a fixed default.

## Mandatory role labels

Every session coordinating other sessions must self-apply and preserve `orchestrator`, especially before changing another session's Craft status. Orchestrators are not `subagent`s.

Every non-orchestrator agent must have `subagent` and **exactly one mandatory primary role**:

- `executor` — implementation;
- `auditor` — audit/review and plan audit;
- `designer` — product/UX/UI design;
- `tester` — QA/testing/verification.

A role worker must read current labels, remove conflicting primary-role labels, preserve unrelated `project::...`, `worktree::...`, `git::...`, `priority::...`, and appropriate `status::...` labels, add its own primary role, and call `set_session_labels` with the complete result. `set_session_labels` replaces all labels.

At start, every worker has:

```text
subagent
<executor | auditor | designer | tester>
project::<name>
status::in-progress
```

Also preserve/add `worktree::<name>` when applicable. Do not use `orchestrator` on workers.

## Other label dimensions

- `project::<name>`: apply to every project/workstream session.
- `priority::<number>`: only when explicit or clear from context.
- Exactly one `status::<name>`: `ready`, `in-progress`, `wait`, `wait-answer`, `blocked`, `review`, `error`, `cancelled`, or `done`.
- Exactly one `git::<status>` when Git readiness matters: `progress`, `ready`, or `pushed`.
- `worktree::<name>`: use for linked worktrees or isolated checkouts.

## Worker finalization

Workers preserve unrelated labels, replace the status value with exactly one of `status::done`, `status::blocked`, `status::error`, or `status::cancelled`, and normally set Craft status to `needs-review`. Only a verified executor task containing the exact phrase `auto-close on success: true` may set Craft status to `done`.

Every final report must include these exact lines:

```text
- Confidence: <0–100>%
- Confidence rationale:
```

Role-specific report schemas are authoritative. The generic `Result:` report is executor-only; when both auditor skills load, `plan-auditor` supersedes the generic auditor schema.

## Removed legacy labels

Do not create or re-add the removed boolean labels `ready`, `in-progress`, `wait`, `wait-answer`, `blocked`, `review`, `ready-for-push`, `pushed`, `failed`, or `cancelled`. Use the valued `status::<name>` and `git::<status>` dimensions instead.
