# Agent Handoff

## Current state
T004 remediation complete, awaiting targeted OpenCode re-check.

All blocking findings from OpenCode's independent review (P1-A, P1-B) and accompanying enhancements (P2-C, P2-D, P2-E, C7 text fix) have been thoroughly investigated, implemented, and verified with 14 passing automated tests. Non-negotiables were strictly adhered to: `src/*.j2` remains 100% untouched, Phase 4 differential offline tests pass, no T005 code has been added, and no large benchmark corpora were committed.

The task boundary has been reached. **Do NOT begin T005 automatically.**

## Summary of Remediations
1. **P1-A (Safe Output Directory Handling)**:
   - Replaced unconditional directory wiping in `generate.py` with `prepare_output_directory()`.
   - Non-empty unrelated directories refuse overwrite with `FileExistsError` leaving all user files completely untouched.
   - Non-existent directories are created; empty directories are allowed.
   - Target directories containing a valid prior `manifest.json` for the same corpus allow controlled replacement.
   - Tested in `test_safe_output_directory_handling`.
2. **P1-B (Projected Actual Size Planning & Preflight)**:
   - Added in-memory sizing planner `plan_corpus_workload()` calculating exact file count, duplicate clusters, unique files, and individual payload byte sizes *before* touching filesystem.
   - Pre-flight disk space check strictly uses `projected_bytes`.
   - CI storage ceiling (<= 1 GB) enforced against projected bytes before writes.
   - Profile-specific target size tolerance enforced (`size_tolerance_ratio`).
   - Tested in `test_projected_size_preflight_and_planning`.
3. **P2-C (Manifest Scale & Tamper Detection)**:
   - Added `scale`, `target_bytes`, and `size_tolerance_ratio` to `Manifest` and `manifest.json`.
   - Validation cross-checks scale, target bytes, tolerance, and re-derives expected file counts and bytes to detect tampering.
   - Tested in `test_manifest_scale_and_tamper_detection`.
4. **P2-D (CI Coverage)**:
   - Added `python3 tests/test_benchmark_corpus.py -v` step to GitHub Actions CI (`.github/workflows/phase4-correctness.yml`) under the `offline` job on `ubuntu-latest`.
   - Added `benchmarks/**` to workflow path triggers.
5. **P2-E (Target vs Actual Size Testing)**:
   - Added `test_target_vs_actual_size_conformance` testing explicit tolerances across all C1–C7 profiles without false exact-byte assumptions.
6. **C7 Text Fix**:
   - Enumerated C7 in `agent/tasks/T005-j2-baseline-benchmark.md` and `agent/tasks/T006-automatic-parallelism.md` standard corpora lists.
   - Zero cold-cache terminology.

## Verification Run
```powershell
python tests/test_benchmark_corpus.py -v
# -> Ran 14 tests in ~13s: OK

python tests/phase4_differential.py --offline
# -> All offline self-tests PASS

git diff origin/main -- src/
# -> Completely empty (immutability preserved)
```

## What should the next agent do?
- Await the targeted OpenCode re-check of T004 remediation.
- Do NOT begin T005 automatically.
