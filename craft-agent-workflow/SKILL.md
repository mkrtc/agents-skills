---
name: craft-agent-workflow
description: "Craft Agent workflow conventions for orchestrators and spawned agents: session naming, contextual tags, labels, statuses, worktrees, Git readiness, worker final reports, and audit handoffs."
---

# Craft Agent Workflow

Use this skill when coordinating Craft Agent sessions, naming orchestrators/workers, assigning session labels, tracking work status, spawning subagents, using worktrees, or handing work back to an orchestrator.

## Core Principles

- Keep orchestration and execution separate.
- The orchestrator plans, scores task complexity from 1 to 5, runs the required plan audit gate, splits, dispatches, collects reports, and requests audits. It does not implement product/code changes itself.
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

Every non-orchestrator agent spawned by an orchestrator must have the `subagent` label.

This includes:

- executor agents;
- worker agents;
- audit/review agents;
- plan-auditor agents;
- any other bounded task agent created by the orchestrator.

Do not apply `subagent` to the parent orchestrator session.

Peer orchestrators are separate orchestrator streams and are not subagents.

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
- `status::error` — the agent hit an execution/tool/runtime error and could not complete normally.
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

### Removed Legacy Agent Status Labels

The old boolean `agent-status` label tree was removed from the current labels config.

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

- `status::<name>` for operational status.
- `git::ready` instead of `ready-for-push`.
- `git::pushed` instead of `pushed`.

If older sessions still contain these labels, treat them as historical metadata and do not re-add them to the config without an explicit user request.

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

Worker status transition rules:

| Worker condition | Required label transition | Required Craft session status |
|---|---|---|
| Work starts / is actively running | replace old `status::...` with `status::in-progress` | keep/open as `todo` unless already set by orchestrator |
| Work completed successfully | replace `status::in-progress` with `status::done` | `done` |
| Worker is blocked by missing info/dependency/access | replace `status::in-progress` with `status::blocked` | `needs-review` |
| Worker hit an execution/tool/runtime error | replace `status::in-progress` with `status::error` | `needs-review` |
| Work was cancelled | replace `status::in-progress` with `status::cancelled` | `cancelled` |

Additional rules:

- Any non-orchestrator agent spawned by an orchestrator must have the `subagent` label.
- The worker agent is responsible for updating its own labels and Craft session status at the end of its task.
- The worker must preserve unrelated labels such as `project::...`, `subagent`, `git::...`, and `worktree::...`.
- The worker must not leave itself in `status::in-progress` after it has finished, blocked, errored, or cancelled.
- Orchestrators awaiting review can use label `status::review` and Craft session status `needs-review`.

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

## Planning Complexity and Plan Audit Gate

Before spawning executor workers, the orchestrator must assess task complexity and run the required plan audit workflow.

Every orchestrator plan must include:

```text
Complexity: <1-5>/5
Reasoning: <short justification>
```

Complexity scale:

| Score | Meaning | Typical signs |
|---|---|---|
| `1` | Very simple | Localized, low-risk, one small change or clear investigation |
| `2` | Simple | Bounded task, known pattern, limited files/modules, low ambiguity |
| `3` | Moderate | Multiple files/modules, some ambiguity, integration concerns, meaningful testing needed |
| `4` | Hard | Cross-module/system changes, migrations, infra/deploy risk, concurrency, external APIs, security/data risk |
| `5` | Very hard | High ambiguity or high blast radius, architecture changes, critical security/data/destructive risk, many dependencies |

### Audit Counts

For complexity `1` or `2`:

- Draft the plan.
- Spawn `1` plan-auditor agent.
- Incorporate accepted findings.
- Produce the final plan.
- Only then spawn executor workers if execution is requested/approved.

For complexity `3` or higher, use two audit rounds:

| Complexity | Plan auditors per round |
|---|---:|
| `3` | `1` |
| `4` | `2` |
| `5` | `3` |

Workflow for complexity `3+`:

1. Draft the plan.
2. Spawn the required number of round-1 plan auditors.
3. Collect round-1 audit reports.
4. Rewrite the plan using accepted audit findings.
5. Spawn the same number of round-2 plan auditors.
6. Collect round-2 audit reports.
7. Produce the final plan using the last audit findings.
8. Only then spawn executor workers if execution is requested/approved.

If a plan audit finds blocking uncertainty that cannot be resolved from available context, ask the user or create a discovery task before implementation.

### Plan Auditor Role

Plan auditors are audit agents, not implementation workers.

Plan auditor session names should use:

```text
${tag} Plan Audit R<round>-<n>
```

Plan auditor prompts must include:

- Orchestrator session ID.
- Shared tag and project name.
- Required labels: `subagent`, `project::<name>`, `status::in-progress`, and `worktree::<name>` if applicable.
- Complexity score and justification.
- Original user task.
- Relevant project context.
- Draft or revised plan to audit.
- Explicit instruction not to implement code.
- Review criteria: inaccuracies, vulnerabilities, weak points, bad decisions, missing dependencies, unclear requirements, file/worktree conflicts, test gaps, rollout/deploy risks, security/data risks, and over/under-scoping.

Required plan auditor response format:

```text
Plan Audit Result:
- Verdict: pass | needs-changes | blocked
- Critical findings:
- Major findings:
- Minor findings:
- Missing context/questions:
- Recommended plan changes:
- Confidence in plan after changes:
```

## Orchestrator Responsibilities

The orchestrator must not implement product/source changes directly.

The orchestrator is responsible for:

1. Inspecting enough project context to plan safely.
2. Assessing task complexity from 1 to 5 and justifying it.
3. Producing a detailed draft plan.
4. Running the required complexity-based plan audit gate before executor dispatch.
5. Rewriting the plan based on audit findings when required.
6. Producing a final plan.
7. Splitting the final plan into independent tasks.
8. Dispatching tasks to spawned agents.
9. Giving each agent a complete self-contained prompt.
10. Receiving final reports from agents.
11. Checking reports for completeness, contradictions, and risk.
12. Spawning audit/review agents whenever confidence in a worker result is below 95%.
13. Deciding whether new incoming tasks should be merged into the current plan or delegated to a peer orchestrator.
14. Handling OFFTOP side requests ephemerally without polluting the durable task context.
15. Creating follow-up tasks when work is incomplete or risky.

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
- Explicit required starting labels: `subagent`, `project::<name>`, `status::in-progress`, and `worktree::<name>` if applicable.
- Explicit finalization instructions, including the worker's responsibility to switch itself from `status::in-progress` to `status::done`, `status::blocked`, or `status::error` and to update its Craft session status.

Every spawned worker prompt must start with:

```text
You are an executor agent for one task created by an orchestrator.
Do not broaden the scope.
Work only on the task below.
```

## Worker Finalization

The worker agent is responsible for its own final state. The orchestrator must include these instructions in every worker prompt.

At start or before meaningful work, every non-orchestrator spawned agent must ensure its labels include:

```text
subagent
project::<name>
status::in-progress
```

If working in a worktree, it must also preserve/add:

```text
worktree::<name>
```

When the worker is done with its assigned scope, it must not leave itself in `status::in-progress`.

Final state mapping:

| Outcome | Required label update | Required Craft session status | Required report behavior |
|---|---|---|---|
| Success | replace old `status::...` with `status::done` | `done` | provide final report and return/send output to orchestrator |
| Blocked | replace old `status::...` with `status::blocked` | `needs-review` | explain blocker and what is needed to continue |
| Error | replace old `status::...` with `status::error` | `needs-review` | explain error, failed command/tool, and recovery hint |
| Cancelled | replace old `status::...` with `status::cancelled` | `cancelled` | explain cancellation reason |

Implementation rules:

1. Read current labels first.
2. Ensure `subagent` is present for every non-orchestrator spawned agent.
3. Ensure `project::<name>` is present when project name is known.
4. Remove only old `status::...` labels.
5. Preserve unrelated labels such as `project::...`, `subagent`, `git::...`, and `worktree::...`.
6. Set exactly one final `status::...` label.
7. Set Craft session status according to the mapping above.
8. If Git readiness applies, set exactly one of:
   - `git::progress` if not ready to push;
   - `git::ready` if ready to push;
   - `git::pushed` if already pushed.
9. Return/send the final output to the orchestrator session.
10. If label/status update fails, mention that explicitly in the final report.

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
