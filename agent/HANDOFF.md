# Agent Handoff

## Current state
T002 is COMPLETE. Phase 4 differential correctness, fuzzer reproducibility, failure preservation, and retained regression gates are fully implemented and verified in CI.

## What changed?
1. `tests/phase4_differential.py`:
   - Added failure preservation infrastructure (`preserve_failure`) capturing all 6 required fields (`seed`, `case_description`, `filesystem_manifest`, `interpreter_output`, `native_output`, `oracle_output`) to JSON.
   - Added failure reproduction capability (`reproduce_from_failure` and `--reproduce <path-to-json>`).
   - Added deterministic seed-based fuzzer (`generate_fuzz_case`) generating arbitrary recursive directories with duplicate clusters, same-size distinct-content files, and unique files from a reproducible seed.
   - Added retained regression corpus loader (`load_regression_fixtures`) executing all fixtures in `tests/regressions/fixtures/`.
   - Added `--offline` self-testing flag to enable verification in non-J2 environments (e.g. Windows dev machines).
2. `tests/regressions/`:
   - Created `README.md` documenting regression corpus structure.
   - Created `fixtures/` with 4 deterministic fixtures:
     - `case01_nested_clusters.json`: multi-directory nested clusters.
     - `case02_size_boundary_zero.json`: 0-byte and 1-byte file boundary duplicates.
     - `case03_same_size_distinct_content.json`: four 10-byte files with two duplicates and two distinct unique files.
     - `case04_one_byte_diff_clusters.json`: clusters differing by one byte.
3. `.github/workflows/phase4-correctness.yml`:
   - Added upload of preserved failure artifacts (`if: failure()`).
4. `docs/PHASE-4-CORRECTNESS.md`:
   - Marked status as COMPLETE and all 7 acceptance gates as checked with CI run evidence.
5. `.gitignore`:
   - Ignored python `__pycache__`, `*.pyc`, and local `tests/regressions/failures/`.

## Why?
T002 required independent differential testing across oracle, interpreter, and native modes, reproducible failure preservation/minimization infrastructure, seed reproducibility, and retained regression cases before any performance/parallelism work begins.

## What was discovered?
- The 10 seed corpus cases already produce exact direct dictionary matches (`interpreter == native == oracle`).
- In complex arbitrary file trees, directory recursion in J2 preserves first-discovery order for duplicate groups and paths within groups. Canonical group equivalence (`canonicalize_groups`) ensures independent oracle group set correctness regardless of internal dictionary key iteration order, while `interpreter == native` enforces byte-and-list-level determinism across J2 execution modes.
- Python `Random(seed)` with fixed generator choices provides 100% byte-for-byte tree and manifest reproducibility across different runs on both Windows and macOS runners.
- J2 0.1.0 on `macos-15` passes all seed cases, regression cases, fuzzer cases, and invalid root safety tests.

## What failed?
- In initial fuzzer reproducibility checking, comparing raw absolute path strings between two test directory trees failed because absolute root paths differed. Comparing relative paths resolved the check cleanly.

## What should the next agent avoid repeating?
- Do NOT alter Phase 3 J2 source files (`src/*.j2`) unless a real defect is discovered. They have been proven correct and verified by differential testing.
- Do NOT start performance benchmarking before reviewing T003/T004 specifications.
- Do NOT commit generated benchmark or test failure artifacts unless explicitly intended as a minimized regression fixture.

## Next task
T003 — Competitive/technical research consolidation into `docs/RESEARCH.md`.
Following T003: T004 (benchmark corpus specification and generator) -> T005 (interpreter/native baseline) -> T006 (automatic parallelism experiment).
