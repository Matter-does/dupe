# Phase 4 — Differential Correctness & Regression

**Status:** COMPLETE  
**Prerequisite:** Phase 3 MVP complete  
**Goal:** independently verify `dupe` correctness across generated file trees and execution modes.

## Acceptance gates

- [x] Independent Python oracle implemented.
- [x] Seed corpus covers required edge cases.
- [x] Interpreter output matches oracle on every seeded case.
- [x] Native output matches oracle on every seeded case.
- [x] Interpreter output equals native output on every seeded case.
- [x] Regression corpus is retained in CI (`tests/regressions/fixtures/`).
- [x] Fuzzer can reproduce a failure from its seed (verified by self-test and seed CLI).

## Evidence

GitHub Actions run `34017174166` (job `101442888586`) on macOS 15 Apple Silicon arm64 with J2 0.1.0:
- Seed corpus (10 cases): PASS (exact match interpreter == native == oracle)
- Regression corpus (4 fixtures): PASS
- Fuzzer batch (seeds 42001..42005): PASS
- Fuzzer seed reproducibility check: PASS
- Failure preservation infrastructure check: PASS
- Interpreter missing-root failure: PASS
- Native missing-root failure: PASS
- Interpreter file-root failure: PASS
- Native file-root failure: PASS
- Filesystem tree immutability: PASS across all runs

## Oracle contract

The oracle is independent of J2 implementation logic. It recursively enumerates regular files, groups by byte length, compares exact bytes with SHA-256, and calculates duplicate groups and reclaimable bytes.

The oracle does not call `dupe`, J2, or reuse the J2 source implementation.

## Seed corpus

Required deterministic cases:

1. empty tree
2. single file
3. identical files in one directory
4. identical files across nested directories
5. same-size different-content files
6. files differing by one byte
7. multiple empty files
8. multiple duplicate clusters
9. unusual filenames and nested paths
10. size-boundary cases, including zero-byte files

## Failure preservation

Every discovered mismatch preserves:

```text
seed
case description
filesystem manifest
interpreter output
native output
oracle output
```

Preserved reports are saved to `tests/regressions/failures/` and uploaded in CI if a step fails. A minimized reproducer can be replayed using:
```bash
python3 tests/phase4_differential.py --reproduce <path-to-failure.json>
```

## Non-goals

Phase 4 does not benchmark performance, prove automatic parallelism, or add deletion behavior. Those belong to later phases.
