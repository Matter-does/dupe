# Agent Handoff

## Current state
T001 is complete. The repository now contains durable project context and a resumable multi-agent workflow.

## Product position
The project is a J2-native filesystem intelligence engine. Exact duplicate detection is the first workload/reference implementation, not the full product ambition.

## Durable context
Read `AGENTS.md`, `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/J2-API-0.1.0.md`, `agent/CURRENT_TASK.md`, `agent/CHECKPOINT.md`, and this file before coding.

## Agent roles
- Antigravity: primary builder.
- OpenCode: persistent continuation/fallback.
- Claude Code via OmniRouter: adversarial review.
- GLM-5: independent second opinion.
- ChatGPT: research/architecture/specification/task decomposition.
- GitHub Actions: reproducible verification.

## Existing validated baseline
- Phase 3 modular J2 implementation is frozen.
- Phase 4 differential correctness infrastructure exists.
- J2 0.1.0 is pinned in CI.
- Interpreter/native equivalence has previously passed CI.

## Important strategic decision
Do not turn the project into a feature-for-feature duplicate-manager clone. Do not make automatic-parallelism claims without controlled evidence.

## Next task
T002 — complete Phase 4 correctness and regression gates.

## After T002
T003 research consolidation → T004 benchmark corpus → T005 interpreter/native baseline → T006 automatic-parallelism experiment.

## Failure/recovery rule
When an agent stops unexpectedly, the next agent reads checkpoint + handoff + Git state and resumes the first unfinished atomic action. It must not reconstruct the project from the ChatGPT transcript.

## Review concern
Before starting T002, inspect the latest Phase 4 GitHub Actions run and determine whether the newest safety/error validation passed. Do not mark Phase 4 complete without actual evidence.
