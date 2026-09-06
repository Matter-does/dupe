# Current Task

**Task:** T004 — Benchmark Corpus Specification and Generator  
**Status:** T004 remediation complete, awaiting targeted OpenCode re-check

## Summary of Completed Remediation
- **P1-A (Safe Output Directory Handling):**
  - Refuses destructive wipe of non-empty arbitrary directories with `FileExistsError`, preserving all user data untouched.
  - Allows generation if target directory does not exist (creates it) or is empty.
  - Allows controlled replacement only if target directory contains a valid prior `manifest.json` from this generator for the same corpus.
  - Verified with 4 dedicated safety tests in `tests/test_benchmark_corpus.py`.
- **P1-B (Projected Actual Size Planning & Preflight):**
  - Generator determines exact file count, duplicate clusters, unique files, and individual payload byte sizes in memory via `plan_corpus_workload()` *before* touching filesystem.
  - Pre-flight disk space safety check strictly uses `projected_bytes`.
  - CI storage ceiling (<= 1 GB) enforced against projected bytes before any file write.
  - Profile-specific target size tolerance enforced (`size_tolerance_ratio`).
- **P2-C (Manifest Scale & Tamper Detection):**
  - Added `scale`, `target_bytes`, and `size_tolerance_ratio` to `Manifest` and `manifest.json`.
  - Strict validation cross-checks scale, target bytes, tolerance, and re-derives expected file counts and bytes to detect tampering.
- **P2-D (CI Coverage):**
  - Added `python3 tests/test_benchmark_corpus.py -v` to the `offline` job in `.github/workflows/phase4-correctness.yml` (`ubuntu-latest`).
  - Added `benchmarks/**` to workflow path triggers.
- **P2-E (Target vs Actual Size Testing):**
  - Added explicit test verifying realized corpus size conforms to each profile's explicit tolerance (C1–C7) without false assumptions of exact byte identity where variance is permitted.
- **C7 Text Fix:**
  - Enumerated C7 alongside C1, C2, C4, C5, C6 across T005 and T006 acceptance/specification text.
  - Zero "cold cache" terminology throughout.

## Verification Evidence
- `tests/test_benchmark_corpus.py`: 14/14 PASS (5.3s)
- `tests/phase4_differential.py --offline`: PASS
- Phase 3 source code (`src/*.j2`): 100% untouched (`git diff origin/main -- src/` empty)
- Zero T005 code added

## Next Action
Submit T004 remediation for targeted OpenCode re-check. Do NOT begin T005 automatically.
