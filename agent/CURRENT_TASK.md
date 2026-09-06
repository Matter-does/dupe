# Current Task

**Task:** T002 — Complete Phase 4 correctness and regression gates
**Status:** COMPLETE

## Completed
- Verified independent Python oracle contract against J2 interpreter and native execution.
- Verified all 10 seed corpus cases (empty, single, same-dir, nested, same-size different-content, 1-byte diff, empty-dupes, clusters, filename-torture, size-boundaries).
- Implemented and retained deterministic regression corpus under `tests/regressions/fixtures/` with 4 fixtures.
- Implemented seed-based fuzzer generator with byte-for-byte tree and manifest reproducibility.
- Implemented failure preservation and minimization infrastructure capturing all 6 required fields (`seed`, `case_description`, `filesystem_manifest`, `interpreter_output`, `native_output`, `oracle_output`).
- Implemented failure reproduction harness via `--reproduce <path-to-failure.json>`.
- Verified safety and error validation (non-existent root, file as root) for both interpreter and native modes.
- Verified input filesystem tree immutability across all test executions.
- Validated end-to-end passing CI run on GitHub Actions (`macos-15` Apple Silicon with J2 0.1.0).

## Acceptance criteria
- [x] Independent Python oracle implemented.
- [x] Seed corpus covers required edge cases.
- [x] Interpreter output matches oracle on every seeded case.
- [x] Native output matches oracle on every seeded case.
- [x] Interpreter output equals native output on every seeded case.
- [x] Regression corpus is retained in CI.
- [x] Fuzzer can reproduce a failure from its seed.
- [x] Filesystem immutability verified across all test executions.
- [x] Safety/error behavior for invalid roots verified.

## Verification evidence
- CI run `34017174166` (job `101442888586`) on macOS 15 arm64 / J2 0.1.0: PASS
- CI run `34017174186` (job `101442888619`) on macOS 15 arm64 / J2 0.1.0: PASS
- Local Python offline self-tests: PASS

## Next task
T003 — Competitive and technical research consolidation (from `agent/tasks/T003-research.md`).
