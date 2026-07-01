# Orchestrator Planning Audit Protocol

This reference documents the required planning quality gate for Craft Agent orchestrators.

## Goal

Improve task formulation and reduce bugs, weak plans, missed risks, security issues, and bad implementation splits before executor agents start work.

## Complexity score

Every orchestrator must score the task from 1 to 5 and include the score in the plan:

```text
Complexity: <1-5>/5
Reasoning: <short justification>
```

| Score | Meaning | Typical signs |
|---|---|---|
| `1` | Very simple | Localized, low-risk, one small change or clear investigation |
| `2` | Simple | Bounded task, known pattern, limited files/modules, low ambiguity |
| `3` | Moderate | Multiple files/modules, some ambiguity, integration concerns, meaningful testing needed |
| `4` | Hard | Cross-module/system changes, migrations, infra/deploy risk, concurrency, external APIs, security/data risk |
| `5` | Very hard | High ambiguity or high blast radius, architecture changes, critical security/data/destructive risk, many dependencies |

## Required audit flow

### Complexity 1-2

1. Draft the plan.
2. Spawn `1` plan-auditor agent.
3. Incorporate accepted findings.
4. Produce the final plan.
5. Only then dispatch executor workers if execution is requested/approved.

### Complexity 3+

Use two audit rounds.

| Complexity | Auditors per round |
|---|---:|
| `3` | `1` |
| `4` | `2` |
| `5` | `3` |

Workflow:

1. Draft the plan.
2. Spawn round-1 plan auditors.
3. Collect round-1 reports.
4. Rewrite the plan using accepted findings.
5. Spawn round-2 plan auditors with the revised plan.
6. Collect round-2 reports.
7. Produce the final plan using the last audit findings.
8. Only then dispatch executor workers if execution is requested/approved.

If audits reveal blocking uncertainty, ask the user or create discovery tasks before implementation.

## Plan auditor role

Plan auditors are audit agents, not implementation workers.

They must not write product/source code.

Recommended session name:

```text
${tag} Plan Audit R<round>-<n>
```

## Plan auditor prompt checklist

Include:

- Orchestrator session ID.
- Shared tag and project name.
- Complexity score and reasoning.
- Original user task.
- Relevant project context.
- Draft/revised plan to audit.
- Explicit instruction not to implement.
- Review criteria:
  - inaccuracies;
  - vulnerabilities;
  - weak points;
  - bad decisions;
  - missing dependencies;
  - unclear requirements;
  - file/worktree conflicts;
  - test gaps;
  - rollout/deploy risks;
  - security/data risks;
  - over/under-scoping.

## Required auditor response

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

## Distinction from result audits

This protocol audits the plan before executor workers start.

It is separate from the existing rule that requires a result audit when the orchestrator has less than 95% confidence in a completed worker result.
