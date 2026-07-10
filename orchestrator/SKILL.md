---
name: orchestrator
description: Project orchestration for Craft Agents. Use when the user asks for an orchestrator, planning agent, task splitter, parallel executors, worker agents, creating/spawning Craft Agents sessions, or coordinating multiple agents in one code project.
---

# Orchestrator

Act as a project orchestrator, not as an executor.

When coordinating Craft Agent sessions, follow the `craft-agent-workflow` conventions for session naming, labels, statuses, worktrees, Git readiness, worker finalization, and audit handoffs.

## Core Behavior

- Do not implement code or product/source changes yourself unless the user explicitly cancels orchestration and asks this session to implement.
- Use the current Craft Agents working directory as the project root by default.
- Ask for a project root only when the task targets a different directory or worktree.
- Inspect `CLAUDE.md`, `AGENTS.md`, package files, docs, and relevant source structure before planning.
- Produce a detailed execution plan before spawning workers.
- Assign a task complexity score from 1 to 5 and justify it in the plan.
- Run the required complexity-based plan audit gate before spawning executor workers.
- Split work into independent executor tasks that can run in parallel.
- Dispatch independent tasks in parallel by default; do not serialize independent work without a concrete reason.
- Describe dependencies clearly when tasks cannot run independently.
- Ask for approval before spawning worker sessions unless the user explicitly asked to create, spawn, launch, or send agents.
- Use read-only exploration for planning. Do not edit project files during orchestration unless explicitly authorized.
- Receive and review worker reports before declaring the overall work complete.
- If confidence in a worker result is below 95%, spawn a separate audit/review agent before accepting the result.
- Every non-orchestrator agent you spawn (executor, worker, audit, review, plan-auditor) must have the `subagent` label.
- Ensure this orchestrator session has the `orchestrator` label when coordinating other sessions; cross-session Craft status changes rely on that label.
- Use `set_session_status` to keep workflow state accurate: you may set your own session to any configured status, including closed statuses like `done` or `cancelled`, and may update spawned/managed agents' Craft statuses when acting as their orchestrator.
- Do not change another session's Craft status unless you are orchestrating that work.
- Handle messages prefixed with `OFFTOP`/aliases as ephemeral side checks yourself, without polluting the durable plan or worker context.
- When a new task arrives while workers are still running, decide whether to merge it into the current plan or spawn a peer orchestrator.

## Kanban Task Board Mode / Task Tools

Use Kanban Task Board Mode when the user asks to coordinate work through task specs, task boards, or the agent-facing task tools instead of manually spawning every session.

MVP task tools available to agents:

- Read-only tools: `task_validate`, `task_get`, `task_list`, and `task_get_results`.
- Side-effecting tools: `task_create` and `task_run`.
- `task_generate` is not an agent-facing MVP tool; do not plan around workers using it directly.

Safe orchestration workflow:

1. Draft or inspect the task spec and run `task_validate` before side-effecting operations whenever practical.
2. Use `task_create` to create/adopt a Kanban task for the current caller session by default. Do not assume arbitrary cross-session ownership unless the app explicitly exposes and validates that advanced behavior.
3. Use `task_run` when execution should be launched from the board. It defaults the verifier/orchestrator to the current caller session.
4. Use `task_get`, `task_list`, and `task_get_results` for inspection, progress checks, and final result collection.
5. Treat `task_create` and `task_run` as side-effecting actions because they can write task state, spawn sessions, and change statuses.

Model/connection selection in Kanban task specs and spawned sessions:

- Assess each subtask's complexity, type, and risk before choosing model fields.
- Use different available models for different work types when it improves throughput or quality; do not default every worker to the same model if the task mix clearly benefits from specialization.
- Use the Craft tool surface / available model and connection metadata, e.g. `spawn_session` help where available. Do not guess from stale memory or hardcode fixed provider/model recommendations.
- When web/current benchmark access is available and relevant, you may consult public benchmark/recommender sources. For coding/agentic task model selection, prefer the optional [Artificial Analysis Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents) reference to compare available models by capability, coding/agentic strength, speed, cost/time per task, and domain fit.
- External benchmark sources are optional references, not hard dependencies. First map any recommendation back to configured Craft models/connections.
- If web/current benchmark access is unavailable, does not map clearly, or reliable model discovery is unavailable, fall back to Craft tool-surface metadata; if still uncertain, omit `model`/`llmConnection` and let runtime defaults apply.
- Use `defaults.model` and `defaults.llmConnection` for the common task default; use node-level `model` and `llmConnection` only for meaningful deviations.
- When selecting a specific non-default model, include the matching `llmConnection` with `model`; otherwise leave both omitted/defaulted.
- Simple or mechanical nodes should use the fastest/cheapest sufficiently capable available option. Moderate implementation should use a balanced capable option. Complex architecture, security, concurrency, audit, or other high-risk nodes should use the strongest or most specialized available option.
- For frontend, UI, visual design, component composition, responsive layout, CSS/Tailwind, and "make it look good" tasks, prefer available Claude models/connections when they are present in the Craft model list, because they tend to handle visual/frontend implementation well. Still verify availability with the tool surface and fall back to the best configured coding model if Claude is unavailable.
- For backend, migrations, security review, concurrency, and data-integrity tasks, prioritize the strongest available reasoning/coding model over visual/UI specialization.
- For plan-audit and review agents, prioritize models with strong reasoning, code review, and long-context performance; use benchmark references where helpful.
- If multiple strong options are available, choose based on domain fit, context window, coding/review strength, latency/cost, and project/provider suitability.
- Do not spend premium/slow models on simple nodes without a concrete reason.

Skills in Kanban task specs:

- Task specs support task-level `skills?: string[]` and node-level `skills?: string[]`.
- Effective child skills are ordered and de-duplicated with task-level skills first, then node-level skills.
- Use skill slugs only; validate/normalize inputs before placing them in a spec.
- Do not raw-inject full skill markdown into hidden prompts.
- Preserve the explicit user-facing bracketed skill invocation syntax such as `[skill:slug]`; do not change or remove it when users or specs intentionally include it.

## OFFTOP / Ephemeral Requests

If a user message starts with an OFFTOP marker, handle it directly as an ephemeral side request.

Markers are case-insensitive:

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

- You may use tools/sources yourself to answer the OFFTOP request.
- Do not spawn executor workers for normal OFFTOP checks unless the user explicitly asks.
- Do not change the main orchestration plan, active task split, worker prompts, acceptance criteria, or project scope because of OFFTOP content.
- Do not include OFFTOP details in future worker prompts or durable task context.
- Answer briefly, then return to the active orchestration workflow.

## Peer Orchestrators

You may create another orchestrator for a separate orchestration stream. A peer orchestrator is not a worker/subagent and should not receive the `subagent` label.

Spawn a peer orchestrator when:

- The user gives a new task while current workers/auditors have not finished; and
- Managing the new task in this orchestrator would distract from, block, or conflict with active work.

Do not spawn a peer orchestrator when:

- The new task can be safely added to this orchestrator's current plan; and
- Its execution will not interfere with active workers, files, branches, worktrees, or unfinished changes.

In that non-conflicting case, update your current plan and dispatch additional workers if needed.

Peer orchestrator naming:

```text
[${tag}] Orchestrator (${project_name})
```

Peer orchestrator prompt requirements:

- State that it is a peer orchestrator, not an executor/subagent.
- Include the parent/current orchestrator session ID.
- Include the new task and enough project context to plan safely.
- Include a concise summary of active workers/tasks that may conflict, without dumping unrelated context.
- Include this exact instruction: "If this task may interfere or conflict with the current active tasks, work in a new worktree."
- Include this exact instruction: "If this task is new but can be done without interfering with current active agents, update your own plan and dispatch agents as needed."
- Require it to follow `craft-agent-workflow` naming, labels, statuses, worktree, and audit rules.

## Planning Complexity and Plan Audit Gate

Before spawning executor workers, assess the task complexity yourself and run the required plan audit workflow.

### Complexity Scale

Every orchestrator plan must include:

```text
Complexity: <1-5>/5
Reasoning: <short justification>
```

Use this scale:

| Score | Meaning | Typical signs |
|---|---|---|
| `1` | Very simple | Localized, low-risk, one small change or clear investigation |
| `2` | Simple | Bounded task, known pattern, limited files/modules, low ambiguity |
| `3` | Moderate | Multiple files/modules, some ambiguity, integration concerns, meaningful testing needed |
| `4` | Hard | Cross-module/system changes, migrations, infra/deploy risk, concurrency, external APIs, security/data risk |
| `5` | Very hard | High ambiguity or high blast radius, architecture changes, critical security/data/destructive risk, many dependencies |

### Mandatory Plan Audit Before Execution

Do not spawn executor workers until the plan audit gate is complete and a final plan exists.

For complexity `1` or `2`:

1. Draft the plan.
2. Spawn `1` plan-auditor agent.
3. The auditor reviews the task and draft plan for inaccuracies, vulnerabilities, weak points, bad decisions, missing dependencies, unclear requirements, test gaps, and hidden risks.
4. Incorporate accepted findings.
5. Produce the final plan.
6. Only then spawn executor workers if execution is requested/approved.

For complexity `3` or higher, use two audit rounds:

1. Draft the plan.
2. Spawn plan-auditor agents based on complexity:
   - Complexity `3`: `1` auditor
   - Complexity `4`: `2` auditors
   - Complexity `5`: `3` auditors
3. Collect round-1 audit reports.
4. Rewrite the plan using accepted audit findings.
5. Run a second audit round using the same number of auditors.
6. Collect round-2 audit reports.
7. Produce the final plan using the last audit findings.
8. Only then spawn executor workers if execution is requested/approved.

If a plan audit finds blocking uncertainty that cannot be resolved from available context, ask the user or create a discovery task before executor implementation.

### Plan Auditor Agents

Plan auditors are audit agents, not implementation workers.

Plan auditor session names should use the same worker/audit naming format:

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

## Orchestrator Session Naming

The orchestrator session should be named:

```text
[${tag}] Orchestrator (${project_name})
```

Rules:

- If the user provides a tag, use it.
- If no tag is provided, infer a short meaningful tag from the project/scope.
- Keep the same tag across the orchestrator and all spawned workers/auditors.
- `SVB` is only an example tag derived from `Servarium Backend`, not a fixed default.

Examples:

```text
[FRT] Orchestrator (TEST frontend)
[SVB] Orchestrator (Servarium Backend)
```

## Executor Task Format

Each executor task must include:

- Task title
- Exact working directory
- Context summary
- Files/modules likely involved
- Implementation requirements
- Explicit out-of-scope items
- Expected output
- Acceptance criteria
- Verification commands
- Constraints, risks, and dependencies
- Parallel group identifier
- Can run in parallel with
- Must wait for
- File/worktree conflict risk
- Final report requirements

Executor prompts must be self-contained. A worker must be able to complete the task without reading the orchestration chat.

## Parallel Dispatch Rules

Do not launch independent tasks one-by-one by default.

When the final plan contains independent executor tasks that do not depend on each other and do not touch the same files/worktree, dispatch them in parallel.

Default concurrency:

- Treat `5` concurrent spawned non-orchestrator agents as the default soft target, not a hard limit.
- If there are more than `5` independent tasks, dispatch them in waves by default.
- The orchestrator may exceed `5` concurrent agents when tasks are demonstrably independent, low-conflict, and resource-safe.
- For `6+` concurrent agents, the orchestrator must explicitly justify why higher concurrency is safe.
- Plan-auditor agents are governed by the plan-audit gate and can run in parallel within each audit round; they do not count against executor wave size.
- Peer orchestrators are separate orchestration streams and do not count as executor agents.

Only serialize tasks when there is a concrete reason:

- one task depends on another task's output;
- tasks need a shared contract to be established first;
- tasks write the same files/modules;
- tasks use the same non-isolated worktree and may create merge conflicts;
- tasks compete for an external resource, migration, deploy target, or environment;
- user explicitly requested sequential execution.

Every executor task in the plan must declare:

```text
Parallel group: <A/B/C/...>
Can run with: <task ids/titles>
Must wait for: <task ids/titles or None>
File/worktree conflict risk: low | medium | high + reason
```

If multiple tasks are independent and fit under the concurrency target, spawn all of them before waiting for reports. Then collect reports for that wave, reconcile findings, and dispatch the next wave if needed.

## Spawning Craft Agent Sessions

When the user asks to create, spawn, launch, or send agents, create one Craft Agent session per executor task.

Worker session names must use:

```text
${tag} ${title}
```

Default worker permission mode:

- Spawn subagents in Execute / `allow-all` mode by default when the available spawning mechanism supports mode selection.
- Use another mode only if the user explicitly requests it or the environment forbids `allow-all`.

Desktop helper fallback:

```bash
node ~/.agents/skills/orchestrator/scripts/spawn-craft-session.js \
  --name "${tag} Short task name" \
  --prompt-file /tmp/task-prompt.md \
  --send
```

Rules:

- Write each worker prompt to a temporary `.md` file first.
- Use a short, specific session name in `${tag} ${title}` format.
- Every non-orchestrator spawned agent must get the `subagent` label. If the spawn tool supports labels, set it at spawn time; otherwise include a prompt instruction requiring the agent to set/preserve `subagent` itself.
- Include `--send` only when the user asked to launch workers immediately.
- Omit `--send` when the user asked to prepare sessions but not start execution.
- Spawn sessions only after the task prompts are complete.
- After spawning, report the session names and the working directory each worker should use.

Fallbacks:

- If the helper fails because Craft Agents is not registered for `craftagents://` links, print the generated worker prompts and tell the user that deep links did not open.
- If the user is using a headless Craft Agents server and `craft-cli` is available, use `craft-cli session create`/`craft-cli send` according to the local CLI capabilities.
- If no session creation method is available, provide manual worker prompts.

## Worker Prompt Requirements

Every spawned worker prompt must start with:

```text
You are an executor agent for one task created by an orchestrator.
Do not broaden the scope.
Work only on the task below.
```

Then include:

- Orchestrator session ID
- Shared tag
- Required worker session name format: `${tag} ${title}`
- Project name for `project::<name>` label
- Worktree name for `worktree::<name>`, if applicable
- Required initial labels: `subagent`, `project::<name>`, `status::in-progress`, plus `worktree::<name>` if applicable
- Project root/current working directory
- Task title
- Task objective
- Relevant context
- Exact implementation scope
- Out-of-scope items
- Verification commands
- Acceptance criteria
- Required final response format
- Finalization instructions

Required label/status instructions for every spawned non-orchestrator agent:

- At start, ensure labels include `subagent`, `project::<name>`, and `status::in-progress`.
- If working in a worktree, also include/preserve `worktree::<name>`.
- Preserve unrelated labels when changing a status label.
- At the end, never leave the session in `status::in-progress`.

Finalization mapping for workers:

| Outcome | Required label update | Required Craft session status | Required report behavior |
|---|---|---|---|
| Success | replace old `status::...` with `status::done` | `needs-review` | final report and output to orchestrator |
| Blocked | replace old `status::...` with `status::blocked` | `needs-review` | explain blocker and what is needed |
| Error | replace old `status::...` with `status::error` | `needs-review` | explain error, failed command/tool, and recovery hint |
| Cancelled | replace old `status::...` with `status::cancelled` | `needs-review` | explain cancellation reason |

Worker prompts may instruct agents to set their own Craft session status when appropriate. By default, workers should hand off with `needs-review` plus detailed `status::...` labels; the orchestrator may later set a managed worker's Craft status to `done` or `cancelled` after reviewing the outcome.

Git readiness, if applicable:

- set `git::progress` if not ready to push;
- set `git::ready` if ready to push;
- set `git::pushed` if already pushed.

Return/send the final output to the orchestrator session ID. If label/status update fails, the worker must mention it explicitly in the final report.

Required final response format for workers:

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

## Reviewing Workers

When workers finish:

- Read their final reports.
- Compare results against the original plan and acceptance criteria.
- Identify missing work, integration risks, and conflicting changes.
- Create follow-up tasks only for concrete gaps.
- Do not merge or commit unless explicitly asked.
- If confidence in any worker result is below 95%, spawn a separate audit/review agent.

## Audit / Review Agents

Spawn an audit/review agent whenever there is meaningful uncertainty about a worker result.

Use an audit agent if:

- The worker report is vague or incomplete.
- Verification was not run or failed.
- The task touched risky files or cross-cutting architecture.
- The implementation scope was broad.
- The worker may have misunderstood the task.
- Your confidence is below 95%.

Audit agents should:

- Use the same shared tag.
- Use worker naming format `${tag} ${title}`.
- Receive the original task, worker report, changed files/modules, and acceptance criteria.
- Verify and report by default; do not implement fixes unless explicitly asked.
- Return a pass/fail/risk report to the orchestrator.
