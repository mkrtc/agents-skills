# Orchestrator Planning Audit Protocol

This reference is subordinate to [`craft-agent-workflow/SKILL.md`](../SKILL.md), the canonical source for shared workflow rules.

## Goal

Improve task formulation and reduce missed risks before executor agents start work.

## Complexity score

Every plan includes:

```text
Complexity: <1-5>/5
Reasoning: <short justification>
```

| Score | Meaning |
|---|---|
| `1` | Very simple, localized, low-risk |
| `2` | Simple, bounded, known pattern |
| `3` | Moderate, multi-file/module or integration risk |
| `4` | Hard, cross-system, migration, infra, security, or data risk |
| `5` | Very hard, high ambiguity or blast radius |

## Required audit flow

For complexity `1` or `2`: draft the plan, run one plan auditor, incorporate accepted findings, produce the final plan, then dispatch executors if approved.

For complexity `3+`, use two rounds:

| Complexity | Auditors per round |
|---|---:|
| `3` | `1` |
| `4` | `2` |
| `5` | `3` |

Draft, audit round 1, revise, audit round 2, then produce the final plan before executor dispatch. If a plan audit finds blocking uncertainty, ask the user or create a bounded discovery task before implementation.

## Plan-auditor role

Plan auditors are audit-only workers. They load `craft-agent-auditor` and `plan-auditor`, carry `subagent`, `auditor`, `project::<name>`, `status::in-progress`, and any worktree label, and must not implement, commit, or push. They report implementation needs to the orchestrator. A separate `executor` session loading `craft-agent-executor` and labeled `executor` may be created only when the work is already within approved scope or after the user explicitly approves scope expansion.

Recommended name: `${tag} Plan Audit R<round>-<n>`.

Prompts include the orchestrator ID, tag/project/worktree, complexity and reasoning, original task/context, plan, no-implementation instruction, and review criteria spanning assumptions, security, dependencies, conflicts, parallelism, verification, rollout, and scope. Plan auditors apply the canonical `craft-agent-workflow` scope-authority scenarios and reject silent out-of-scope fixes or severity-based authority expansion.

## Required plan-auditor response

When both auditor skills load, this specialized schema supersedes the generic auditor schema:

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

Each actionable finding includes `[P0]`–`[P3]`, evidence, impact, likelihood, and recommendation.

## Result audits and terminal handling

The automatic below-85% result-audit trigger applies only to executor, designer, and tester results. It does not trigger from auditor or plan-auditor confidence. For a low-confidence audit result, the orchestrator must resolve missing evidence, create one bounded discovery/retest task, explicitly accept or defer the documented risk, or mark it blocked. Do not create an unbounded audit chain.
