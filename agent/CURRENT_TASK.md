# Current Task

**Task:** T005 — J2 Interpreter/Native Baseline Benchmark  
**Status:** Completed (Verified on macOS 15 Apple Silicon `macos-15` arm64)

## Summary of Implementation & Results
- **Execution Platform:**
  - OS / Kernel: Darwin 24.6.0 (arm64 Apple Silicon)
  - Hardware: 3 vCPUs, 7.0 GB RAM
  - Toolchain: `j2 0.1.0` (`6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75`)
  - CI Run: GitHub Actions run `34038191455` (`macos-15`)

- **Baseline C — Pure J2 Automatic-Parallelism Control:**
  - Workload: `data = collect(1..2000000); print(sum(data))`
  - Mathematical Ground Truth: `2000001000000` (Verified PASS in both interpreter and native)
  - Build Duration: 1,169.81 ms
  - Interpreter Median: 79.66 ms (min: 70.47 ms, max: 88.39 ms, stddev: 5.42 ms)
  - Native Median: 58.59 ms (min: 55.27 ms, max: 61.37 ms, stddev: 2.11 ms)
  - Native Speedup: **1.36x**

- **Filesystem Workload Baselines (Baseline A vs Baseline B):**
  - **Baseline A (Interpreter):** `j2 --allow-fs src/main.j2 <corpus> --json`
  - **Baseline B (Compiled Native):** `J2_ALLOW_FS=1 ./build/dupe <corpus> --json`
  - **Corpora Evaluated:** Standard CI suite (C1, C2, C4, C5, C6, C7)
  - **Direct JSON Match:** PASS (100% bit-for-bit equivalence across all corpora)
  - **Manifest Digest Match:** PASS (100% match against T004 expected_result_digest across all corpora)
  - **Measured Wall-Clock Durations & Speedup Factors:**
    - **C1 (Metadata Heavy, 500 files, 122 candidates):** Interp 2,624.33 ms vs Native 2,669.61 ms (**0.98x**)
    - **C2 (Balanced Baseline, 100 files, 30 candidates):** Interp 274.61 ms vs Native 223.07 ms (**1.23x**)
    - **C4 (High Dup Density, 100 files, 80 candidates):** Interp 278.15 ms vs Native 246.33 ms (**1.13x**)
    - **C5 (Adversarial Same Size, 200 files, 200 candidates):** Interp 474.49 ms vs Native 438.66 ms (**1.08x**)
    - **C6 (Mixed Hierarchy, 100 files, 30 candidates):** Interp 237.31 ms vs Native 214.73 ms (**1.11x**)
    - **C7 (Cache Transition / Warm Runs, 100 files, 30 candidates):** Interp 242.40 ms vs Native 224.92 ms (**1.08x**)
    - *Topology Note on C7:* Generated with parameters identical to C2; produces byte-identical files for identical seeds. Designed to measure warm-state repeated-run variance over the baseline topology.

- **Compiler Inspection (`j2 emit-native`):**
  - Inspected emitted Rust backend code for both pure control and `dupe` main.
  - Identifies single-threaded runtime structures: thread-local global state (`thread_local! static GLOBALS`), `j2_runtime::prelude`, and dynamic value evaluation structures (`Rc<RefCell<Env>>`).
  - No multi-core concurrency primitives (such as `rayon`, `par_iter`, or `thread::spawn`) were detected in the backend emission.

- **Critical Scientific Conclusion:**
  - Native binary speedup over the interpreter is modest (0.98x to 1.23x across filesystem workloads, 1.36x on pure control).
  - Native speedup represents compilation to native machine code without interpreter loop dispatch; it is **NOT** evidence of automatic parallel speedup.
  - Automatic parallelism multi-core scaling remains to be isolated and evaluated in T006.

## Verification Evidence
- GitHub Actions CI Run `34038191455` (`macos-15`): PASS (2m14s)
- Harness offline tests (`tests/test_benchmark_harness.py`): 8/8 PASS (1.1s)
- Benchmark corpus tests (`tests/test_benchmark_corpus.py`): 14/14 PASS (9.2s)
- Phase 4 differential offline self-tests (`tests/phase4_differential.py --offline`): PASS
- Source immutability: `src/*.j2` remains 100% untouched (`git diff origin/main -- src/` strictly empty)
- Zero T006 implementation code started

## Next Action
Complete handoff and checkpoint documentation. Do NOT begin T006 automatically.
