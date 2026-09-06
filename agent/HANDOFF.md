# Agent Handoff

## Current state
The repository has been moved toward a repository-first, multi-agent workflow.

## Important product change
The project is no longer treated as a generic duplicate-manager clone. The stable exact-duplicate implementation is the first filesystem-intelligence workload used to investigate J2 automatic parallelism.

## Recent changes
- Added `AGENTS.md` with operating and verification rules.
- Added durable project, architecture, research, decision, and hackathon documents.
- Added explicit checkpoint/current-task state.

## Existing validated baseline
- Phase 3 modular J2 implementation exists and is frozen.
- Differential correctness infrastructure exists in `tests/phase4_differential.py`.
- Exact J2 0.1.0 is pinned in CI.
- Interpreter/native equivalence has previously been verified in CI.

## Do not redo
- Do not replace the Phase 3 scanner unless a concrete defect is found.
- Do not add duplicate-manager feature parity.
- Do not claim automatic parallelism benefits without benchmark evidence.

## Next work
1. Finish repository workflow files and task queue.
2. Confirm latest Phase 4 CI result.
3. Complete remaining Phase 4 correctness work.
4. Design and implement reproducible benchmark methodology.
5. Measure interpreter vs native vs automatic-parallelism behavior.

## Review concerns
The next reviewer should check that the README, architecture, and task queue consistently describe the revised product thesis and that no source implementation was altered by workflow changes.
