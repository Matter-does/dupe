# Current Task

**Task:** T005 — J2 Interpreter/Native Baseline Benchmark  
**Status:** In Progress (Harness implemented, verified offline, executing CI baselines on macOS 15 Apple Silicon)

## Summary of Implementation
- **Pure J2 Parallelism Control (Baseline C):**
  - Created `benchmarks/controls/pure_control.j2` implementing official pure computation workload (`data = collect(1..2000000); print(sum(data))`).
  - Verified mathematical ground truth: `sum(1..2000000) = 2000001000000`.
- **Benchmark Harness (`benchmarks/harness.py`):**
  - Platform and toolchain provenance capture (OS, kernel, arm64, CPU count, RAM, runner ID, J2 version, git commit).
  - External process wall-clock timing using `time.perf_counter_ns()`.
  - Full execution engines for Baseline A (`j2 run --allow-fs`), Baseline B (`J2_ALLOW_FS=1 ./build/dupe`), and Baseline C (interpreter & native with build time).
  - Pre-flight manifest validation before every run via `validate_manifest()`.
  - Bit-for-bit output JSON equivalence and digest match against manifest `expected_result_digest`.
  - Strict statistical protocol: median, mean, min, max, stddev, variance, and derived throughput rates.
  - Failure preservation (non-zero returncodes, stdout, stderr).
  - Compiler inspection helper via `j2 emit-native`.
- **Benchmark Runner (`benchmarks/run_baselines.py`):**
  - Configurable CLI orchestrator managing pure control, standard corpora (C1, C2, C4, C5, C6, C7), and compiler inspection.
  - Outputs machine-readable results JSON (`benchmarks/results/baseline_results.json`) and Markdown report.
- **Offline Test Suite (`tests/test_benchmark_harness.py`):**
  - 7 offline unit tests covering statistics, throughput rates, provenance schema, ground-truth math, equivalence checking, failure preservation, and pre-flight validation.
  - All 7 tests PASS locally.
  - Integrated into `.github/workflows/phase4-correctness.yml` offline job.
- **Dedicated CI Workflow (`.github/workflows/t005-baseline-benchmark.yml`):**
  - Runs on `macos-15` (arm64 Apple Silicon, 3 vCPUs, 7 GB RAM).
  - Installs exact J2 0.1.0, verifies formatting, runs harness offline tests, executes Baseline A, B, C matrix, and uploads results artifacts.

## Verification Evidence
- `tests/test_benchmark_harness.py`: 7/7 PASS (1.5s)
- `tests/test_benchmark_corpus.py`: 14/14 PASS (10.6s)
- `tests/phase4_differential.py --offline`: PASS
- Phase 3 source code (`src/*.j2`): 100% untouched (`git diff origin/main -- src/` empty)
- Zero T006 implementation code added

## Next Action
Push to `origin/main` to trigger `t005-baseline-benchmark.yml` on `macos-15`, retrieve measured baseline timings and compiler inspection, update checkpoints, and record final results.
