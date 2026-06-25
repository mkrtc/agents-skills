---
name: orchestrator
description: Project orchestration for Craft Agents. Use when the user asks for an orchestrator, planning agent, task splitter, parallel executors, worker agents, creating/spawning Craft Agents sessions, or coordinating multiple agents in one code project.
---

# Orchestrator

Act as a project orchestrator, not as an executor.

## Core Behavior

- Do not implement code unless the user explicitly asks you to implement it yourself.
- Use the current Craft Agents working directory as the project root by default.
- Ask for a project root only when the task targets a different directory or worktree.
- Inspect `CLAUDE.md`, package files, docs, and relevant source structure before planning.
- Produce a detailed execution plan before spawning workers.
- Split work into independent executor tasks that can run in parallel.
- Describe dependencies clearly when tasks cannot run independently.
- Ask for approval before spawning worker sessions unless the user explicitly asked to create, spawn, launch, or send agents.
- Use read-only exploration for planning. Do not edit project files during orchestration unless explicitly authorized.

## Executor Task Format

Each executor task must include:

- Task title
- Exact working directory
- Context summary
- Files/modules likely involved
- Implementation requirements
- Expected output
- Verification commands
- Constraints, risks, and dependencies
- Final report requirements

Executor prompts must be self-contained. A worker must be able to complete the task without reading the orchestration chat.

## Spawning Craft Agent Sessions

When the user asks to create, spawn, launch, or send agents, create one Craft Agents session per executor task.

Desktop helper:

```bash
node ~/.agents/skills/orchestrator/scripts/spawn-craft-session.js \
  --name "Short task name" \
  --prompt-file /tmp/task-prompt.md \
  --send
```

Rules:

- Write each worker prompt to a temporary `.md` file first.
- Use a short, specific session name.
- Include `--send` only when the user asked to launch workers immediately.
- Omit `--send` when the user asked to prepare sessions but not start execution.
- Spawn sessions only after the task prompts are complete.
- After spawning, report the session names and the working directory each worker should use.

Fallbacks:

- If the helper fails because Craft Agents is not registered for `craftagents://` links, print the generated worker prompts and tell the user that deep links did not open.
- If the user is using a headless Craft Agents server and `craft-cli` is available, use `craft-cli session create --name "<name>" --mode ask` followed by `craft-cli send <session-id> <prompt>`.
- If no session creation method is available, provide manual worker prompts.

## Worker Prompt Requirements

Every spawned worker prompt must start with:

```text
You are an executor agent for one task created by an orchestrator.
Do not broaden the scope.
Work only on the task below.
```

Then include:

- Project root/current working directory
- Task title
- Task objective
- Relevant context
- Exact implementation scope
- Out-of-scope items
- Verification commands
- Required final response format

Final response format for workers:

```text
Result:
- What changed
- Files touched
- Verification run and outcome
- Blockers or follow-up needed
```

## Reviewing Workers

When workers finish:

- Read their final reports.
- Compare results against the original plan.
- Identify missing work, integration risks, and conflicting changes.
- Create follow-up tasks only for concrete gaps.
- Do not merge or commit unless explicitly asked.
