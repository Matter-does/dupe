# T002 — Complete Phase 4 Correctness

## Goal
Finish differential correctness and regression gates before performance work.

## Inputs
- `src/`
- `tests/phase4_differential.py`
- `docs/PHASE-4-CORRECTNESS.md`
- J2 0.1.0 CI workflow

## Requirements
- Confirm interpreter == oracle.
- Confirm native == oracle.
- Confirm interpreter == native.
- Preserve filesystem immutability for normal scans.
- Validate invalid-root behavior for interpreter and native execution.
- Add reproducible failure preservation/minimization infrastructure.
- Retain deterministic regression cases in CI.

## Constraints
- No performance benchmarking.
- No destructive file operations.
- Do not alter Phase 3 behavior unless a concrete defect is discovered.

## Verification
- Run the Phase 4 GitHub Actions workflow.
- Inspect the actual logs for every acceptance gate.
- Record the run identifier in the handoff/checkpoint.

## Definition of done
Every Phase 4 acceptance gate is evidenced by passing CI or a retained regression artifact, and `docs/PHASE-4-CORRECTNESS.md` is updated to COMPLETE only after all gates truly pass.
