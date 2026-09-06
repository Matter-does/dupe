# Current Task

**Task:** T005 — J2 Interpreter/Native Baseline Benchmark  
**Status:** Completed (Verified on macOS 15 Apple Silicon `macos-15` arm64)

## Summary of Implementation & Results
- **Execution Platform:**
  - OS / Kernel: Darwin 24.6.0 (arm64 Apple Silicon)
  - Hardware: 3 vCPUs, 7.0 GB RAM
  - Toolchain: `j2 0.1.0` (`6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75`)
  - CI Run: GitHub Actions run `34037979685` (`macos-15`)

- **Baseline C — Pure J2 Automatic-Parallelism Control:**
  - Workload: `data = collect(1..2000000); print(sum(data))`
  - Mathematical Ground Truth: `2000001000000` (Verified PASS in both interpreter and native)
  - Build Duration: 1,674.63 ms
  - Interpreter Median: 94.19 ms (min: 86.32 ms, max: 116.99 ms, stddev: 10.94 ms)
  - Native Median: 88.97 ms (min: 58.44 ms, max: 149.37 ms, stddev: 31.99 ms)
  - Native Speedup: **1.06x**

- **Filesystem Workload Baselines (Baseline A vs Baseline B):**
  - **Baseline A (Interpreter):** `j2 --allow-fs src/main.j2 <corpus> --json`
  - **Baseline B (Compiled Native):** `J2_ALLOW_FS=1 ./build/dupe <corpus> --json`
  - **Corpora Evaluated:** Standard CI suite (C1, C2, C4, C5, C6, C7)
  - **Direct JSON Match:** PASS (100% bit-for-bit equivalence across all corpora)
  - **Manifest Digest Match:** PASS (100% match against T004 expected_result_digest across all corpora)
  - **Measured Wall-Clock Durations & Speedup Factors:**
    - **C1 (Metadata Heavy, 500 files, 122 candidates):** Interp 2,217.87 ms vs Native 2,204.48 ms (**1.01x**)
    - **C2 (Balanced Baseline, 100 files, 30 candidates):** Interp 229.14 ms vs Native 199.87 ms (**1.15x**)
    - **C4 (High Dup Density, 100 files, 80 candidates):** Interp 260.24 ms vs Native 240.57 ms (**1.08x**)
    - **C5 (Adversarial Same Size, 200 files, 200 candidates):** Interp 444.52 ms vs Native 459.60 ms (**0.97x**)
    - **C6 (Mixed Hierarchy, 100 files, 30 candidates):** Interp 216.91 ms vs Native 202.99 ms (**1.07x**)
    - **C7 (Cache Transition / Warm Runs, 100 files, 30 candidates):** Interp 201.81 ms vs Native 184.57 ms (**1.09x**)

- **Compiler Inspection (`j2 emit-native`):**
  - Inspected emitted Rust backend code for both pure control and `dupe` main.
  - Identifies thread-local global state, `j2_runtime::prelude`, and dynamic value evaluation structures.
  - Confirms automatic-parallelism constructs lowered by compiler, but runtime wall-clock speedup is constrained by filesystem I/O serialization and thread initialization overhead.

- **Critical Scientific Conclusion:**
  - Native binary speedup over the interpreter is modest (0.97x to 1.15x across filesystem workloads, 1.06x on pure control).
  - Native speedup represents compilation to native machine code without interpreter loop dispatch; it is **NOT** evidence of automatic parallel speedup.
  - Automatic parallelism multi-core scaling remains to be isolated and evaluated in T006.

## Verification Evidence
- GitHub Actions CI Run `34037979685` (`macos-15`): PASS (2m30s)
- Harness offline tests (`tests/test_benchmark_harness.py`): 8/8 PASS (1.1s)
- Benchmark corpus tests (`tests/test_benchmark_corpus.py`): 14/14 PASS (9.2s)
- Phase 4 differential offline self-tests (`tests/phase4_differential.py --offline`): PASS
- Source immutability: `src/*.j2` remains 100% untouched (`git diff origin/main -- src/` strictly empty)
- Zero T006 implementation code started

## Next Action
Complete handoff and checkpoint documentation. Do NOT begin T006 automatically.
