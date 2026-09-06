# Agent Harness Specification

## Purpose
Provide the smallest useful local harness for making the J2 project resumable, verifiable, and independent of any single agent or chat session.

## Commands
The implementation may be PowerShell on Windows and shell scripts in CI. The exact command names are not fixed until verified against the local environment.

```text
harness task T004
harness verify
harness checkpoint
harness continue
```

## `task`
1. Read `AGENTS.md`.
2. Read `docs/PROJECT.md` and the J2 reference.
3. Read `agent/CURRENT_TASK.md`, `agent/CHECKPOINT.md`, and `agent/HANDOFF.md`.
4. Show the task goal, constraints, acceptance criteria, and current checkpoint.
5. Ask/dispatch the selected implementation agent outside the harness as appropriate.

## `verify`
Run the verification appropriate to the current task. For J2 application tasks this normally includes formatting, relevant tests, interpreter execution, native build/execution, and differential checks where applicable.

The harness must report failures without converting them into a false success.

## `checkpoint`
Validate/update the structured task state. A checkpoint records completed atomic actions, remaining actions, verification status, last commit, and next action.

## `continue`
Inspect task/checkpoint/handoff/Git state and identify the first unfinished atomic action. It must not repeat completed actions merely because a previous agent stopped.

## Agent dispatch policy
- Default builder: Antigravity.
- Fallback/continuation: OpenCode.
- Review: Claude Code through OmniRouter.
- Independent second opinion: GLM-5.

The harness does not need to control every agent API. It only needs to maintain durable state and produce an unambiguous next action.

## Failure behavior
A failed verification leaves the task in a non-complete state. The failure, command, relevant output summary, and next diagnostic action belong in `HANDOFF.md` or the checkpoint.

## Scope limit
Do not build a generalized autonomous-agent framework. The harness exists only to make this J2 application development workflow reliable.
