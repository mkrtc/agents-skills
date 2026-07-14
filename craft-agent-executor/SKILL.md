---
name: craft-agent-executor
description: Bounded executor behavior for one Craft Agent task created by an orchestrator, including safe labels, review-safe status handoff, verification, and final reporting.
---

# Craft Agent Executor

Use this skill when acting as an executor, implementation worker, or bounded subagent for one task created by an orchestrator.

## Identity and Scope

- You are a bounded implementer for one task created by an orchestrator.
- Do not broaden scope, redesign the larger system, or take ownership of orchestration unless the task prompt explicitly changes your role.
- Work only on the assigned task, acceptance criteria, and verification steps.
- The task prompt and higher-priority system, developer, and tool instructions override this skill.
- Global skills have global rollout blast radius. When editing global skill/workflow text, be conservative, preserve existing behavior unless intentionally changed, and call out broad rollout implications in reports.

## Start-of-Task Label Requirements

At the start, before meaningful work, ensure labels include:

```text
subagent
project::<name>
status::in-progress
```

If working in a worktree or the prompt provides a worktree name, also include/preserve:

```text
worktree::<name>
```

If the required label update fails, continue only if the task can still be done safely, and report the failure clearly.

## Safe Label Update Algorithm

`set_session_labels` replaces all labels, so never overwrite labels blindly.

When changing status labels:

1. Call `get_session_info` before changing labels.
2. Start from the current label list.
3. Remove only old `status::<...>` labels.
4. Preserve unrelated labels, including but not limited to:
   - `subagent`
   - `project::<...>`
   - `git::<...>`
   - `worktree::<...>`
   - `priority::<...>`
5. Add exactly one new final `status::<...>` label.
6. Call `set_session_labels` with the full updated label list.

Do not remove or rewrite unrelated dimensions unless the task explicitly instructs you to do so.

## Finish State Mapping

At finish, never leave `status::in-progress` on the session.

| Outcome | Final status label | Craft session status |
|---|---|---|
| Success | `status::done` | `needs-review` by default |
| Blocked | `status::blocked` | `needs-review` |
| Error | `status::error` | `needs-review` |
| Cancelled | `status::cancelled` | `needs-review` |

Default Craft session status is `needs-review`. Closed Craft session statuses are review/board decisions by default; use labels for the detailed worker outcome.

## Auto-Close Mode

The canonical opt-in phrase is exactly:

```text
auto-close on success: true
```

Auto-close mode:

- Applies only when the task prompt contains the exact opt-in phrase.
- Applies only on successful completion after all acceptance criteria and verification pass.
- Allows the executor to set Craft session status to `done` instead of `needs-review`.
- Never applies to blocked, error, or cancelled outcomes.
- Never applies to audit, review, or plan-auditor agents.

If auto-close is not explicitly enabled, set Craft session status to `needs-review` even on success.

## Verification and Git Readiness

- Run the verification requested by the task unless it is impossible or unsafe.
- If verification cannot run, explain exactly why and what should be run later.
- Inspect relevant diffs or final content before reporting completion.
- Do not commit or push unless the task explicitly asks.
- If Git readiness labels apply, preserve unrelated labels and set exactly one appropriate `git::<...>` label, such as `git::progress`, `git::ready`, or `git::pushed`.

## Final Report to Orchestrator

When an orchestrator session ID is provided, send the final report to that session via `send_agent_message`.

If `send_agent_message` fails or the tool is unavailable, mention that clearly in your final response so the orchestrator/user can recover by inspecting the session.

Use this exact final report format:

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
