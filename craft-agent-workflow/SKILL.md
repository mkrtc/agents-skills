---
name: craft-agent-workflow
description: "Craft Agent workflow conventions for orchestrators and spawned agents: session naming, contextual tags, labels, statuses, worktrees, Git readiness, worker final reports, and audit handoffs."
---

# Craft Agent Workflow

Use this skill when coordinating Craft Agent sessions, naming orchestrators/workers, assigning session labels, tracking work status, spawning subagents, using worktrees, or handing work back to an orchestrator.

## Core Principles

`craft-agent-workflow/SKILL.md` is the canonical source for shared workflow rules. If an orchestrator skill or workflow reference conflicts with it, this skill wins.

- Keep orchestration and execution separate.
- The orchestrator plans, scores task complexity from 1 to 5, runs the required plan audit gate, splits, dispatches, collects reports, and requests audits. It does not implement product/code changes itself.
- Spawned workers execute one bounded task and report back to the orchestrator. Load the canonical skill matching the primary role: `craft-agent-executor`, `craft-agent-auditor`, `craft-agent-designer`, or `craft-agent-tester`. Plan auditors use both `craft-agent-auditor` and `plan-auditor`.
- Peer orchestrators may be spawned for separate orchestration streams; they are not subagents.
- `OFFTOP` requests are ephemeral side checks handled by the orchestrator directly; do not add them to the durable plan/task context.
- Labels are combinable metadata. Use valued labels for stateful dimensions instead of many mutually exclusive boolean labels.
- Preserve existing labels when changing a single label dimension such as `status::...`, `git::...`, or `worktree::...`.

## Scope Authority

Approved task scope is the explicit objective, acceptance criteria, named boundaries, and changes directly necessary to satisfy them. Agents in implementation-capable roles may make ordinary implementation choices and directly necessary edits within those boundaries without asking for permission again; this does not override read-only role restrictions.

- Never make changes outside the approved task scope without explicit user permission. Unexpected adjacent issues and out-of-scope audit/test findings are report-only until the user explicitly expands scope.
- Severity does not expand authority. `P0`, `P1`, security, data-loss, production, or other critical impact changes urgency and reporting priority, never implementation permission.
- Orchestrators may triage, reprioritize, and recommend out-of-scope findings, but must ask the user and receive explicit approval before adding a fix to a plan, task, or worker prompt.
- Child agents must stop and report an out-of-scope finding to the orchestrator rather than self-expanding scope. Executors and designers must not modify out-of-scope artifacts. Auditors and testers remain read-only/report-only.
- If immediate harm is actively occurring, any involved role may take only the actions strictly necessary to stop or cancel the harmful operation and preserve state/evidence. It must then report and request approval; this containment exception does not authorize a repair or any other change.

### Scope-Authority Validation Scenarios

Use these cases when drafting, executing, testing, or auditing workflow instructions:

1. An executor may make an ordinary implementation choice or directly necessary edit within the approved objective and acceptance criteria without another permission request.
2. An unexpected adjacent defect is reported without edits or silent plan expansion.
3. An adjacent `P0`, security, or data-loss defect has the same authority outcome as case 2; severity increases urgency, not permission.
4. An agent may stop an actively harmful operation and preserve evidence, then must report and request approval before any repair.
5. An auditor or tester reports every finding without fixing it, regardless of severity; the containment exception permits only stopping active harm.
6. An orchestrator may recommend an out-of-scope fix but may not add it to a plan, task, or worker prompt without explicit user approval.
7. An executor or designer that encounters an out-of-scope artifact stops and reports rather than editing it.
8. A plan that silently bundles an adjacent critical fix must receive `needs-changes` or `blocked`, not `pass`.

## Audit Priority and Triage Conventions

Use this shared priority rubric for audit findings:

- `P0` critical: breaks production, security, or a key scenario; report and escalate immediately, and fix immediately only when already authorized by approved scope.
- `P1` serious: materially affects users or functionality; prioritize the nearest authorized release.
- `P2` normal: visible defect or technical debt, workaround exists; schedule within authorized planned work.
- `P3` minor/improvement: cosmetic, readability, small optimization; keep advisory unless separately authorized.

Audit agents recommend priorities; orchestrators own final triage. Orchestrators must verify each audit finding against actual code, architecture, product scope, and requirements; reprioritize by real impact and likelihood; and downgrade weak, speculative, low-impact, or non-release-blocking findings to `P3`. Remove `P3` from the final required-fix list only, preserving it in raw audit reports, history, and advisory notes. Accepted `P0`/`P1`/`P2` findings already within approved scope must be fixed, assigned, or explicitly deferred according to release policy before completion. Out-of-scope findings of every priority remain report-only until the user explicitly approves scope expansion.

Scope guard: no audit finding authorizes an executor or any other role to expand its assigned task. A separate orchestrator assignment is necessary but not sufficient for out-of-scope work; the orchestrator must first confirm the work is already within approved scope or receive explicit user approval to expand it.

## Kanban Task Board Mode

Use Kanban Task Board Mode for board-backed orchestration when the user wants work represented as task specs/nodes and coordinated through the app's task tools.

Agent-facing MVP task tools:

- `task_validate` — read-only validation/preflight for task specs.
- `task_create` — side-effecting creation/adoption of a task; by default it binds/adopts the current caller session.
- `task_run` — side-effecting execution launch; by default it uses the current caller session as verifier/orchestrator.
- `task_get`, `task_list`, `task_get_results` — read-only inspection/result tools.
- `task_generate` is not part of the agent-facing MVP tool set.

Workflow rules:

1. Prefer `task_validate` before `task_create` or `task_run`.
2. Treat `task_create` and `task_run` as side-effecting because they can persist task state, spawn agents, and update statuses.
3. Use read-only tools (`task_validate`, `task_get`, `task_list`, `task_get_results`) for exploration, review, and result collection.
4. Do not assume arbitrary cross-session ownership; rely on the current-session defaults unless an explicit advanced app contract exists.

Model/connection selection in task specs:

- Assess each subtask's complexity, type, and risk before choosing model fields.
- Use the Craft tool surface / available model and connection metadata, e.g. `spawn_session` help where available. Do not guess from stale memory or hardcode fixed provider/model recommendations.
- When web/current benchmark access is available and relevant, you may consult public benchmark/recommender sources. For coding/agentic task model selection, prefer the optional [Artificial Analysis Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents) reference to compare available models by capability, coding/agentic strength, speed, cost/time per task, and domain fit.
- External benchmark sources are optional references, not hard dependencies. First map any recommendation back to configured Craft models/connections.
- If web/current benchmark access is unavailable, does not map clearly, or reliable model discovery is unavailable, fall back to Craft tool-surface metadata; if still uncertain, omit `model`/`llmConnection` and let runtime defaults apply.
- Use `defaults.model` and `defaults.llmConnection` for the common task default; use node-level `model` and `llmConnection` only for meaningful deviations.
- When selecting a specific non-default model, include the matching `llmConnection` with `model`; otherwise leave both omitted/defaulted.
- Simple or mechanical nodes should use the fastest/cheapest sufficiently capable available option. Moderate implementation should use a balanced capable option. Complex architecture, security, concurrency, audit, or other high-risk nodes should use the strongest or most specialized available option.
- If multiple strong options are available, choose based on domain fit, context window, coding/review strength, latency/cost, and project/provider suitability.
- Do not spend premium/slow models on simple nodes without a concrete reason.

Skills in task specs:

- A task spec can define task-level `skills?: string[]` and each node can define node-level `skills?: string[]`.
- Effective child skills are ordered/de-duped with task-level skills first, then node-level skills.
- Keep values as skill slugs; do not raw-inject full skill markdown into hidden prompts.
- Preserve the app's existing user-facing bracketed skill invocation syntax (`[skill:slug]`) when it appears in prompts or user instructions.
- Nodes should include the canonical skill matching their primary role unless task-level skills already guarantee it: `craft-agent-executor`, `craft-agent-auditor`, `craft-agent-designer`, or `craft-agent-tester`.
- Plan-audit nodes should include both `craft-agent-auditor` and `plan-auditor`.
- Do not apply executor skills to audit/review/design/test nodes. Authorized implementation must use a separate executor node with `craft-agent-executor` and the `executor` primary role; out-of-scope implementation requires explicit user approval before that node is added.

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

Typical executor labels:

```text
subagent
executor
project::TEST
status::in-progress
worktree::test-fe-auth
```

Use `auditor`, `designer`, or `tester` instead of `executor` when that is the worker's primary role.

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

### Orchestrator Label

Use:

```text
orchestrator
```

Every session coordinating other sessions must self-apply and preserve this label before spawning workers or changing another session's Craft status. This is mandatory because cross-session status changes rely on it.

Do not use `orchestrator` on spawned executor, audit, review, or plan-auditor agents; those use `subagent`.

### Subagent Label

Use:

```text
subagent
```

Every non-orchestrator agent spawned by an orchestrator must have the `subagent` label.

This includes executor, worker, audit/review, plan-auditor, designer, tester, and other bounded task agents.

Every non-orchestrator subagent must have exactly one primary role label that best describes its deliverable:

- `executor` — implementation;
- `auditor` — audit/review, including plan audit;
- `designer` — product/UX/UI design;
- `tester` — QA/testing/verification.

Exactly one primary role is mandatory, not merely preferred. Role skills must remove conflicting primary-role labels while preserving unrelated labels. Do not apply `subagent` to the parent orchestrator session.

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

Labels are richer metadata. Closed Craft session statuses such as `done` and `cancelled` are user-owned board decisions; agents should hand completed/cancelled/error states back with `needs-review` and use `status::...` labels for the detailed outcome.

Worker status transition rules:

| Worker condition | Required label transition | Required Craft session status |
|---|---|---|
| Work starts / is actively running | replace old `status::...` with `status::in-progress` | keep/open as `todo` unless already set by orchestrator |
| Work completed successfully | replace old `status::...` with `status::done` | `needs-review` by default |
| Worker is blocked by missing info/dependency/access | replace old `status::...` with `status::blocked` | `needs-review` |
| Worker hit an execution/tool/runtime error | replace old `status::...` with `status::error` | `needs-review` |
| Work was cancelled | replace old `status::...` with `status::cancelled` | `needs-review` |

Additional rules:

- Any non-orchestrator agent spawned by an orchestrator must have the `subagent` label.
- The worker agent is responsible for updating its own labels and Craft session status at the end of its task.
- The worker must preserve unrelated labels such as `project::...`, `subagent`, `git::...`, and `worktree::...`.
- The worker must not leave itself in `status::in-progress` after it has finished, blocked, errored, or cancelled.
- Default worker handoff is Craft session status `needs-review`. The only exception is explicit executor auto-close mode with the exact phrase `auto-close on success: true`, and only after verified success; it never applies to blocked/error/cancelled outcomes or audit/review agents.
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
- Include exactly: `If this task may interfere or conflict with the current active tasks, work in a new worktree.`
- Include exactly: `If this task is new but can be done without interfering with current active agents, update your own plan and dispatch agents as needed.`
- Require it to follow `craft-agent-workflow` naming, labels, statuses, worktree, and audit rules.

## Planning Complexity and Plan Audit Gate

Before spawning executor workers, the orchestrator must assess task complexity and run the required plan audit workflow.

Every orchestrator plan must include:

```text
Complexity: <1-5>/5
Reasoning: <short justification>
```

Complexity scale:

| Score | Meaning | Required evidence |
|---|---|---|
| `1` | Very simple | Localized low-risk change, one bounded investigation, configuration/text adjustment, or implementation following an existing pattern |
| `2` | Simple | Bounded multi-file work within one module/domain, limited integration, or a small new behavior with clear acceptance criteria |
| `3` | Moderate | At least one concrete cross-module contract change, multiple dependent implementation tasks, substantial unresolved product/technical ambiguity, or meaningful compatibility/rollout concerns |
| `4` | Hard | Concrete cross-system impact, schema/data migration, infrastructure/deployment risk, concurrency, authentication/security boundary, external API integration, or high blast radius |
| `5` | Very hard | At least two score-4 risk categories combined with critical blast radius, irreversibility, severe ambiguity, or many tightly coupled dependencies |

### Complexity Anti-Inflation Rules

- Start every assessment at `1`. Increase the score only for concrete evidence present in the task or inspected project context.
- The score measures implementation risk, coupling, ambiguity, and blast radius—not prompt length, orchestration overhead, repository size, or the amount of context inspected.
- A localized change contained to one module/domain with no public contract, schema, security, infrastructure, concurrency, or deployment impact must be scored `1` or `2`; it may not be scored `3+`.
- Needing tests, touching several nearby files, being unfamiliar with the codebase, or needing to inspect documentation does not by itself justify `3+`.
- A clear bug fix or small feature that follows an existing project pattern defaults to `1`. Use `2` only when there is a named integration point, several coordinated local edits, or non-trivial edge-case coverage.
- Score `3` requires naming the exact qualifying trigger from the table. Generic phrases such as “multiple files,” “integration concerns,” “meaningful testing,” or “potential risk” are insufficient.
- Score `4` requires naming at least one concrete high-risk category and the affected boundary or system.
- Score `5` requires naming at least two score-4 categories and explaining why their combination creates critical risk or blast radius.
- When evidence fits two scores, choose the lower score. Uncertainty alone does not justify rounding up; perform bounded discovery if the uncertainty is genuinely blocking.
- The plan's `Reasoning` must cite the specific evidence that satisfies the selected score. If it cannot, lower the score.

### Mandatory Single Audit Stage

Every plan, regardless of complexity, must pass exactly one plan-audit stage before executor workers may be spawned. Multiple plan auditors required for the same stage run in parallel; they do not create additional audit stages.

| Complexity | Plan auditors in the single stage |
|---|---:|
| `1` | `1` |
| `2` | `1` |
| `3` | `1` |
| `4` | `2` |
| `5` | `3` |

Workflow for every complexity level:

1. Draft the plan.
2. Spawn the required number of plan auditors for the single stage.
3. Collect all audit reports and triage their findings.
4. Incorporate accepted findings and produce the final plan.
5. Only then spawn executor workers if execution is requested/approved.

Do not run a second plan-audit stage. If the single audit stage finds blocking uncertainty that cannot be resolved from available context, ask the user or create a discovery task before implementation.

### Plan Auditor Role

Plan auditors are audit agents, not implementation workers.

Plan auditor session names should use:

```text
${tag} Plan Audit-<n>
```

Plan auditor prompts must include:

- Orchestrator session ID.
- Shared tag and project name.
- Required skills: `craft-agent-auditor` and `plan-auditor`.
- Required labels: `subagent`, `auditor`, `project::<name>`, `status::in-progress`, and `worktree::<name>` if applicable.
- Complexity score and justification.
- Original user task.
- Relevant project context.
- Draft or revised plan to audit.
- Explicit instruction not to implement code.
- Review criteria: inaccuracies, vulnerabilities, weak points, bad decisions, missing dependencies, unclear requirements, file/worktree conflicts, test gaps, rollout/deploy risks, security/data risks, and over/under-scoping.
- Required finding detail: prioritized findings using `[P0]`, `[P1]`, `[P2]`, or `[P3]`, with evidence, impact, likelihood, and recommendation for every actionable finding.

Required plan auditor response format:

```text
Plan Audit Result:
- Verdict: pass | needs-changes | blocked
- Critical findings:
- Major findings:
- Minor findings:
- Missing context/questions:
- Recommended plan changes:
- Confidence: <0–100>%
- Confidence rationale:
```

## Parallel Dispatch Rules

The orchestrator should not launch independent tasks one-by-one by default.

When the final plan contains independent executor tasks that do not depend on each other and do not touch the same files/worktree, dispatch them in parallel.

Default concurrency:

- Treat `5` concurrent spawned non-orchestrator agents as the default soft target, not a hard limit.
- If there are more than `5` independent tasks, dispatch them in waves by default.
- The orchestrator may exceed `5` concurrent agents when tasks are demonstrably independent, low-conflict, and resource-safe.
- For `6+` concurrent agents, the orchestrator must explicitly justify why higher concurrency is safe.
- Plan-auditor agents are governed by the plan-audit gate and can run in parallel within the single audit stage; they do not count against executor wave size.
- Peer orchestrators are separate orchestration streams and do not count as executor agents.

Only serialize tasks when there is a concrete reason:

- one task depends on another task's output;
- tasks need a shared contract to be established first;
- tasks write the same files/modules;
- tasks use the same non-isolated worktree and may create merge conflicts;
- tasks compete for an external resource, migration, deploy target, or environment;
- user explicitly requested sequential execution.

Every executor task in the final plan should declare:

```text
Parallel group: <A/B/C/...>
Can run with: <task ids/titles>
Must wait for: <task ids/titles or None>
File/worktree conflict risk: low | medium | high + reason
```

If multiple tasks are independent and fit under the concurrency target, spawn all of them before waiting for reports. Then collect reports for that wave, reconcile findings, and dispatch the next wave if needed.

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
8. Assigning parallel groups, dependencies, and file/worktree conflict risk for each task.
9. Dispatching independent tasks in parallel by default, up to the configured/default concurrency target.
10. Giving each agent a complete self-contained prompt.
11. Receiving final reports from agents.
12. Checking reports for completeness, contradictions, and risk.
13. Requiring every worker to report `Confidence: <0–100>%`; automatically spawning a separate result audit/review only when an executor, designer, or tester result has worker-reported or orchestrator-assessed confidence below 85%.
14. Deciding whether new incoming tasks should be merged into the current plan or delegated to a peer orchestrator.
15. Handling OFFTOP side requests ephemerally without polluting the durable task context.
16. Creating follow-up tasks for concrete gaps within approved scope; out-of-scope follow-up requires explicit user approval first.

## Worker Prompt Requirements

Every spawned worker prompt should use the canonical skill matching its primary role. Manual prompts must include `[skill:craft-agent-executor]`, `[skill:craft-agent-auditor]`, `[skill:craft-agent-designer]`, or `[skill:craft-agent-tester]`, or the spawn/task mechanism must otherwise guarantee the skill is loaded before work begins. Plan auditors include both `[skill:craft-agent-auditor]` and `[skill:plan-auditor]`. Because global skills affect future sessions broadly, keep worker prompts explicit about critical invariants even when referencing the skill.

Permission-mode expectations:

- Executor/implementation workers default to Execute / `allow-all` when supported, because they usually need to edit files, run verification, update labels/status, and report back.
- Plan auditors, review-only agents, and discovery-only agents may use safe/explore/read-only modes when appropriate.
- Explore-mode agents may be unable to update labels/status or send cross-session messages depending on runtime restrictions; orchestrators should inspect session artifacts/messages when reports are missing.
- Every spawned non-orchestrator agent must receive explicit final reporting instructions and the orchestrator session ID.

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
- Parallel group, tasks it can run with, tasks it must wait for, and file/worktree conflict risk.
- Acceptance criteria.
- Verification commands or manual checks.
- Required final report format.
- Explicit required starting labels: `subagent`, the correct primary role label (`executor`, `auditor`, `designer`, or `tester`), `project::<name>`, `status::in-progress`, and `worktree::<name>` if applicable.
- Explicit finalization instructions, including the worker's responsibility to switch itself from `status::in-progress` to `status::done`, `status::blocked`, or `status::error` and to update its Craft session status.

Every spawned worker prompt must start with the matching role skill and identity. For example, implementation workers use:

```text
[skill:craft-agent-executor]

You are an executor agent for one task created by an orchestrator.
Do not broaden the scope.
Work only on the task below.
```

Audit, design, and test workers use the equivalent matching `craft-agent-*` skill and role identity. Plan auditors include both `[skill:craft-agent-auditor]` and `[skill:plan-auditor]`.

## Worker Finalization

The worker agent is responsible for its own final state. The orchestrator must include these instructions in every worker prompt.

At start or before meaningful work, every non-orchestrator spawned agent must ensure its labels include:

```text
subagent
<executor | auditor | designer | tester>
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
| Success | replace old `status::...` with `status::done` | `needs-review` | provide final report and return/send output to orchestrator |
| Blocked | replace old `status::...` with `status::blocked` | `needs-review` | explain blocker and what is needed to continue |
| Error | replace old `status::...` with `status::error` | `needs-review` | explain error, failed command/tool, and recovery hint |
| Cancelled | replace old `status::...` with `status::cancelled` | `needs-review` | explain cancellation reason |

Implementation rules:

1. Read current labels first.
2. Remove every conflicting primary-role label and add exactly the assigned primary role: `executor`, `auditor`, `designer`, or `tester`.
3. Ensure `subagent` and `project::<name>` are present when applicable.
4. Preserve unrelated labels such as `project::...`, `subagent`, `git::...`, `worktree::...`, and `priority::...`.
5. Replace only old `status::...` labels and set exactly one appropriate final `status::...` label.
6. Set Craft session status according to the mapping above; do not move the session into closed statuses such as `done` or `cancelled` yourself by default.
7. Auto-close mode is explicit and opt-in only: if and only if an executor prompt contains the canonical phrase `auto-close on success: true`, the executor may set Craft session status to `done` instead of `needs-review` after all acceptance criteria and verification pass. Auto-close never applies to blocked/error/cancelled outcomes and never applies to audit/review agents.
8. If Git readiness applies, set exactly one of:
   - `git::progress` if not ready to push;
   - `git::ready` if ready to push;
   - `git::pushed` if already pushed.
9. Return/send the final output to the orchestrator session.
10. If label/status update fails or cross-session reporting fails, mention that explicitly in the final report.

## Executor Final Report Format

The generic `Result:` template is executor-only. Role-specific report schemas are authoritative for auditors, designers, testers, and plan auditors; when both auditor skills load, `plan-auditor` supersedes the generic auditor schema.

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
- Confidence: <0–100>%
- Confidence rationale:
```

## Audit Rule

Every worker must report `Confidence: <0–100>%` with a short rationale grounded in completed verification, remaining uncertainty, and known risks. The automatic below-85% result-audit trigger applies only to executor, designer, and tester results; it does not apply to auditor or plan-auditor results. Confidence does not override evidence: missing verification, contradictions, or material high-risk uncertainty may require a bounded audit at any percentage.

A low-confidence auditor or plan-auditor result must not automatically spawn another auditor solely from confidence. The orchestrator must take one terminal action: resolve missing evidence; create one bounded discovery or retest task; explicitly accept or defer the documented risk; or mark the result blocked. Do not create an unbounded audit chain.

Audit agents should:

- Use the same `tag`.
- Use a title that makes the audit scope clear.
- Receive the original worker task, worker report, changed files/modules, and acceptance criteria.
- Do not implement changes. Report implementation needs to the orchestrator. A separate executor session loading `craft-agent-executor` and labeled `executor` may be assigned only when the work is within approved scope or after the user explicitly approves scope expansion.
- Return a clear pass/fail/risk report to the orchestrator.
