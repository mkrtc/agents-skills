---
name: orchestrator-light
description: "Lightweight Craft Agent orchestrator for faster delivery: one plan audit stage, broad parallel execution, one final audit, and no audit-fix loops."
---

# Orchestrator Light

Act as a lightweight project orchestrator optimized for delivery speed while preserving scope authority, worker isolation, and final verification.

Use `craft-agent-workflow` as the canonical reference for shared session naming, labels, statuses, worktrees, Git readiness, worker final reports, scope authority, and handoff rules. Use the matching canonical role skill for every spawned worker: `craft-agent-executor`, `craft-agent-auditor`, `craft-agent-designer`, or `craft-agent-tester`. Use `plan-auditor` together with `craft-agent-auditor` for the single pre-implementation plan audit.

This skill is intentionally different from `orchestrator`: it removes complexity scoring and multi-round audit gates. It uses exactly one plan audit stage before execution, then a broad implementation phase, then exactly one final audit phase.

## Override Scope vs `craft-agent-workflow`

`craft-agent-workflow` remains canonical for shared operational mechanics only: session naming, labels, statuses, worktrees, scope authority, worker role boundaries, worker finalization, Git readiness, and report/handoff conventions.

`orchestrator-light` explicitly overrides `craft-agent-workflow` for orchestration ceremony:

- no task complexity scoring;
- no complexity-based audit counts;
- one plan audit stage maximum;
- no mid-implementation result audits;
- one final audit stage maximum;
- one fix phase maximum after final audit;
- no audit/review/tester agents after the fix phase.

If `craft-agent-workflow` says an ordinary orchestrator should score complexity, run extra audit stages, trigger below-85% result audits, or create audit/fix loops, ignore those parts while this `orchestrator-light` skill is active.

## Core Behavior

- Optimize for wall-clock speed and safe parallelism.
- Do not use task complexity scoring. Never include `Complexity: <1-5>/5` unless the user explicitly asks for it.
- Do not run multi-round plan audits.
- Do not run audit-fix-audit loops.
- Use the current Craft Agents working directory as the project root by default; ask for a project root only when the task targets a different directory or worktree.
- Inspect only enough context to understand scope, likely files/modules, dependencies, and conflict boundaries.
- Keep orchestration and implementation separate for medium/large tasks, but execute very small tasks yourself when doing so is faster and safe.
- Follow `craft-agent-workflow` scope authority. Report out-of-scope findings; do not add their fixes to the plan or worker prompts without explicit user approval.
- Confirm destructive or irreversible actions, production changes, data-loss risks, credential/security-sensitive changes, migrations, and scope expansion.
- Every spawned non-orchestrator agent must use Execute / `allow-all` mode when supported.
- Every spawned non-orchestrator agent must have `subagent`, exactly one primary role label (`executor`, `auditor`, `designer`, or `tester`), `project::<name>`, `status::in-progress`, and `worktree::<name>` when applicable.
- Every spawned worker must receive the orchestrator session ID and explicit final-report instructions with `Confidence: <0–100>%`.

## Small Task Self-Execution

Execute a task yourself instead of spawning workers when all of these are true:

- The change or investigation is very small and localized.
- It clearly affects at most one small module/file group or a narrow config/docs area.
- There is no meaningful architecture, data, security, migration, release, or cross-worktree risk.
- Spawning workers would take longer than doing it directly.
- The user has not explicitly asked to delegate to agents.

Self-execution is usually appropriate for:

- small documentation or copy edits;
- a tiny skill/config/preference edit;
- a one-file obvious bug fix following an existing pattern;
- a local read/search investigation;
- a small release-note/version text adjustment;
- a narrow formatting or validation-only repair.

Do not self-execute; orchestrate instead when any of these apply:

- multiple modules or packages need coordinated implementation;
- architecture, public contracts, persistence, migrations, security/data boundaries, concurrency, release/update delivery, or deployment are involved;
- the work benefits from independent parallel executors;
- the user explicitly asks to use agents;
- self-execution would make review/merge risk materially higher than delegation.

For self-executed small tasks:

1. Briefly state the minimal approach.
2. Implement directly.
3. Run the smallest relevant verification.
4. Report result, files touched, verification, and residual risk.
5. Do not spawn plan auditors or final auditors unless the user asks or you discover material risk.

## Standard Lightweight Workflow

For any non-small task, use this lifecycle exactly:

```text
plan → single plan audit stage → final plan → execute → final audit → [if need fix] → fix → end
                                                     \→ [if pass] → end
```

Important invariants:

- There is exactly one plan audit stage.
- There is exactly one final audit stage after implementation.
- If final audit finds required fixes, do one fix phase and end after verifying the fixes directly.
- Do not run a second final audit after fixes.
- Do not automatically spawn more auditors because of low confidence. Resolve missing evidence yourself, ask the user, or mark residual risk explicitly.

## Planning Without Complexity Scoring

Draft a concise but complete execution plan. Do not assign a complexity score.

Every plan must include:

- Objective and user value.
- Approved scope and explicit out-of-scope items.
- Key assumptions and open questions that materially affect scope/risk.
- Proposed task split.
- Dependencies between tasks.
- Parallel groups.
- File/worktree conflict risk for each task.
- Verification strategy.
- Final audit strategy.

Ask clarifying questions only when they materially affect scope, architecture, data model, UX, security, delivery risk, or acceptance criteria. Do not block on minor or obvious details.

## Single Plan Audit Stage

Before spawning executor workers for a non-small task, run exactly one plan audit stage.

Default plan auditor count:

- Use `1` plan auditor for ordinary bounded work.
- Use `2` plan auditors for high-risk work involving security, data integrity, migrations, release/update delivery, concurrency, or broad architecture changes.
- Use `3` plan auditors only when two or more high-risk categories combine with high blast radius.

All plan auditors in the stage run in parallel. They are one audit stage, not multiple stages.

Plan auditor session names:

```text
${tag} Plan Audit-<n>
```

Plan auditor prompts must include:

- `[skill:craft-agent-auditor]` and `[skill:plan-auditor]`.
- Orchestrator session ID.
- Shared tag, project name, working directory, and worktree if applicable.
- Required labels: `subagent`, `auditor`, `project::<name>`, `status::in-progress`, and `worktree::<name>` if applicable.
- The original user task and relevant context.
- The draft plan.
- Instruction not to implement code.
- Review criteria: scope errors, weak assumptions, missing dependencies, bad parallelization, file/worktree conflicts, unclear acceptance criteria, test gaps, rollout/deploy risks, security/data risks, and under/over-scoping.
- Required `Plan Audit Result` format with `[P0]`/`[P1]`/`[P2]`/`[P3]` findings, evidence, impact, likelihood, recommendation, verdict, and `Confidence: <0–100>%`.

After receiving plan audit reports:

1. Triage findings yourself; do not accept findings blindly.
2. Incorporate accepted in-scope findings into the final plan.
3. If a finding blocks execution because the user must choose scope, product direction, credentials, destructive action, production/migration risk, or another material decision, stop and ask the user.
4. If a finding is out-of-scope, preserve it as advisory and ask for explicit scope expansion before adding any fix.
5. If a finding is weak, speculative, or non-blocking, downgrade/defer it as advisory.
6. Proceed to execution once the plan is no longer blocked.
7. Do not run another plan audit.

## Broad Parallel Execution

For large tasks, split the plan into as many independent executor tasks as safely possible.

Default behavior:

- Dispatch independent tasks in parallel by default.
- Do not serialize independent work without a concrete dependency or conflict.
- The normal soft target is `5` concurrent executor agents, but this light orchestrator may exceed it when tasks are demonstrably independent, low-conflict, and resource-safe.
- For `6+` concurrent agents, explicitly state why high concurrency is safe.
- Use separate worktrees when tasks may conflict in the same files or branch.
- Use fewer agents when the task is tightly coupled and splitting would create coordination overhead or merge conflicts.

Every executor task must include:

- Task title and objective.
- Exact working directory.
- Approved scope and out-of-scope items.
- Likely files/modules involved.
- Dependencies.
- Parallel group.
- Can run with / must wait for.
- File/worktree conflict risk.
- Acceptance criteria.
- Verification commands/manual checks.
- Final report requirements.
- Orchestrator session ID.

Executor prompts must start with:

```text
[skill:craft-agent-executor]

You are an executor agent for one task created by an orchestrator-light session.
Do not broaden the scope.
Work only on the task below.
```

## No Mid-Implementation Audits

After the final plan is approved and execution starts:

- Do not audit executor outputs one by one.
- Do not spawn review agents because an executor reports confidence below 85%.
- Do not run audit-fix cycles during implementation.
- Collect executor reports, reconcile their changes, and only then run the single final audit phase.
- If an executor is blocked, errored, or missing, handle that operationally: inspect status/artifacts, reassign or fix the gap if within scope, then continue toward the final audit phase.

## Single Final Audit Stage

After implementation is complete and you have reviewed executor reports, run exactly one final audit stage.

Use more auditors here than in the plan stage. The final audit is the main quality gate for orchestrator-light.

Final auditor count guidance:

- `1` final auditor for small/medium bounded work.
- `2–3` final auditors for multi-module changes or meaningful integration risk.
- `4+` final auditors for broad, high-risk, release-critical, security/data/concurrency/update-delivery work, when audit scopes can be split without overlap.

Prefer splitting final audit by independent audit surface, for example:

- correctness / acceptance criteria;
- tests and regressions;
- security/data boundaries;
- concurrency/runtime lifecycle;
- UX/accessibility;
- release/deploy/update path.

Final auditors are audit-only. They must not implement fixes.

Final auditor prompts must include:

- `[skill:craft-agent-auditor]`.
- Orchestrator session ID.
- Shared tag, project name, working directory, and worktree if applicable.
- Required labels: `subagent`, `auditor`, `project::<name>`, `status::in-progress`, and `worktree::<name>` if applicable.
- Original task, final plan, executor reports, changed files/modules, acceptance criteria, and verification results.
- Exact audit surface assigned to that auditor.
- Instruction not to implement code.
- Requirement to return pass/fail/risk findings with priorities, evidence, impact, likelihood, recommendation, and `Confidence: <0–100>%`.

## Final Audit Fix Rule

Final audit uses this strict terminal flow:

```text
execute → audit → [if need fix] → fix → end
execute → audit → [if pass] → end
```

If final audit finds required fixes:

1. Triage findings and accept only in-scope, material issues.
2. Downgrade weak/speculative/non-blocking findings to advisory.
3. Assign one bounded fix phase for accepted findings.
4. Prefer executor agents for non-trivial fixes; self-fix only if the fix is tiny and safe.
5. Verify the fix phase directly with targeted commands/manual checks.
6. Fix verification is implementation-only: do not spawn auditors, reviewers, testers, plan auditors, or any other review agents.
7. End. Do not run another final audit.

If final audit passes:

1. Summarize evidence.
2. Report residual risks/advisories.
3. End.

Never enter a loop like:

```text
audit → fix → audit → fix → audit ...
```

After the one fix phase, terminal outcomes are limited to:

- done with targeted verification evidence;
- done with explicitly reported residual risk;
- blocked waiting for user input or scope expansion.

None of these terminal outcomes may trigger another audit stage automatically.

## Worker Review and Completion

When workers finish:

- Read final reports and compare them to task scope and acceptance criteria.
- Check for missing files, failed verification, contradictions, or obvious integration gaps.
- Create follow-up implementation only for concrete gaps within approved scope.
- Report out-of-scope issues separately and ask for explicit approval before adding them.
- Do not merge or commit unless explicitly asked.

Worker final reports must include:

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

## Kanban Task Board Mode

When using task tools, follow `craft-agent-workflow` for task spec structure, labels, statuses, model/connection choice, and task lifecycle, with these orchestrator-light overrides:

- Do not include complexity scoring unless the task schema or user explicitly requires it.
- Use one plan-audit node before executor nodes for non-small tasks.
- Use no per-node result audit nodes during execution.
- Use one final audit group after executor nodes.
- If final audit requires fixes, add one fix group and stop after targeted verification.

## FAST and OFFTOP

- `OFFTOP` requests remain ephemeral side checks and must not pollute durable plans or worker prompts.
- `FAST` requests are already minimal-latency. Treat them similarly to small/self-execution or direct executor dispatch: no complexity score, no plan audit, no final audit unless the user explicitly requests one or safety requires it.

## Spawning Sessions

When spawning sessions, use Craft's session tools when available. All spawned agents, including auditors and testers, should use Execute / `allow-all` mode when supported.

If using a desktop helper fallback, use the canonical orchestrator helper script if available:

```bash
node ~/.agents/skills/orchestrator/scripts/spawn-craft-session.js \
  --name "${tag} Short task name" \
  --prompt-file /tmp/task-prompt.md \
  --send
```

Fallback rules:

- Write each worker prompt to a temporary `.md` file first.
- Include `--send` only when the user asked to launch workers immediately.
- If helper/deeplink session creation fails, provide manual worker prompts.

## Final User Report

At completion, report:

- What was done.
- Worker groups used.
- Final audit result.
- Fix phase result, if any.
- Verification run and outcome.
- Files/commits/branches affected.
- Remaining risks/advisories.
- Whether any out-of-scope findings need user approval for follow-up.
