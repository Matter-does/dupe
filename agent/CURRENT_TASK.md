# Current Task

**Task:** T006 — Automatic Parallelism Experiment and Evidence Collection (Deep-Critic Remediated)  
**Status:** Remediated & Verified (P2-STALE resolved; ready for independent OpenCode release review)

## Summary of Implementation & Results
- **Execution Platform:**
  - OS / Kernel: Darwin 24.6.0 (arm64 Apple Silicon)
  - Hardware: 3 vCPUs, 7.0 GB RAM
  - Toolchain: `j2 0.1.0` (`6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75`)
  - CI Run: GitHub Actions run `34246767819` (`macos-15`, duration 11m 30s)
  - Baseline Commit: `ce893b4cc8360df1f963d6d840c7f888ac075320`

- **Overall Scientific Classification:** **CATEGORY C** (Native compilation effect only; no multi-core automatic parallelism observed in J2 0.1.0)
- **Multi-Core Utilization:** Consistently **NO (<105% process CPU)** across all tested workloads where periodic sampling was statistically valid ($\ge 4$ samples).
- **Compiler Inspection (`j2 emit-native`):** Emitted backend Rust code utilizes single-threaded thread-local static globals (`thread_local! static GLOBALS`) and standard sequential loops; no multi-threaded runtime primitives (`rayon`, `par_iter`, `thread::spawn`) were detected.

## Experimental Ladder Summary

### Level T006-A: Pure J2 Computational Control
- **Workload:** Reduction `sum(collect(1..n))` (Candidate) vs Accumulator Loop with Loop-Carried Dependency (Serial-Equivalent Native Baseline)
- **Classification:** **CATEGORY E / Evidence Grade C\*** (Reconciled: Candidate-vs-serial comparison is confounded by J2's built-in `sum()` runtime iterator fold optimization and does not establish automatic parallelism)
- **Workload Sizes:** N = 100,000, 2,000,000, 5,000,000; boundary tests N = 0, 1, 32767, 32769
- **Correctness:** 100% VALID mathematical match ($N(N+1)/2$) across all modes
- **Measured Timings (Median):**
  - N=100K: Interpreter 87.95 ms, Native Candidate 92.31 ms, Native Serial 910.53 ms (Candidate/Serial 9.86x, Native/Interp 0.95x)
  - N=2M: Interpreter 103.20 ms, Native Candidate 102.84 ms, Native Serial 17,731.96 ms (Candidate/Serial 172.43x, Native/Interp 1.00x)
  - N=5M: Interpreter 205.41 ms, Native Candidate 174.26 ms, Native Serial 42,249.23 ms (Candidate/Serial 242.45x, Native/Interp 1.18x)

### Level T006-B: Pure In-Memory Hashing
- **Workload:** Hashes K independent in-memory string buffers in RAM without filesystem access
- **Configurations:** 10x1KB, 50x4KB, 100x16KB, 200x64KB (up to 12.8 MB total RAM); boundary tests: 0 bufs, 1 buf
- **Correctness:** 100% VALID (Deterministic 64-char hexadecimal SHA-256 digests)
- **Candidate vs Serial-Equivalent Speedup:** 0.39x to 1.07x (candidate generally slower or parity with serial chained control)
- **Multi-Core Engaged:** NO (<105% CPU / insufficient samples)
- **Classification:** CATEGORY D (Grade A: 3 configs) / CATEGORY E (Grade C: 1 config)

### Level T006-C: Filesystem Read + Hash
- **Workload:** Direct `fs.read_bytes(path)` + `hash.sha256(bytes)` on real corpus trees (C1, C2, C4, C5, C6, C7; seed 12345, scale 0.01)
- **Serial Control:** Cryptographically chained loop-carried dependency (`chained = fmt("{}:{}", prev_hash, file_digest)` + `hash.sha256(chained)`) with true data dependence (avalanche effect across iterations)
- **Correctness:** 100% VALID across all corpora
- **Candidate vs Serial-Equivalent Speedup:** 0.88x to 1.36x (average 1.10x)
- **Multi-Core Engaged:** NO (<105% CPU / insufficient samples)
- **Classification:** CATEGORY D (Grade A: C4, C6, C7) / CATEGORY E (Grade C: C1, C2, C5)

### Level T006-D: Full dupe Pipeline
- **Workload:** Production `dupe` end-to-end execution on standard corpora suite (C1, C2, C4, C5, C6, C7; fixed seed 12345, scale 0.01, preserving exact T005 corpus identities)
- **Correctness:** 100% VALID (100% bit-for-bit direct JSON match and 100% manifest expected_result_digest agreement)
- **Native vs Interpreter Speedup:** 0.70x to 1.18x (average 0.99x)
- **Multi-Core Engaged:** NO (<105% CPU)
- **Classification:** CATEGORY C (Grade A: C4, C7) / CATEGORY D (Grade A: C1, C2, C5, C6)

### Operational Stage Breakdowns
Estimated via standalone cumulative microbenchmark probes (`benchmarks/t006/stage_*.j2`) preserving production `src/*.j2` immutability. Negative or sub-noise-floor deltas ($\le 10\text{ ms}$) explicitly marked `"below_noise_floor"` and rendered as `N/A*` (not zero-clipped):
- **C1 (500 files, 122 candidates):** Discovery 75.9 ms, Size Filter **2,192.2 ms** (~86% of total probe time), Read & Hash 191.8 ms, Grouping 80.8 ms (Dominant: **Size Filter O(N^2)**)
- **C2 (100 files, 30 candidates):** Discovery 124.9 ms, Size Filter 181.2 ms, Read & Hash N/A*, Grouping N/A* (Dominant: **Size Filter O(N^2)**)
- **C4 (100 files, 80 candidates):** Discovery 44.2 ms, Size Filter **101.6 ms**, Read & Hash 89.7 ms, Grouping 4.9 ms (Dominant: **Size Filter O(N^2)**)
- **C5 (200 files, 200 candidates):** Discovery 35.9 ms, Size Filter 90.3 ms, Read & Hash 99.0 ms, Grouping **125.7 ms** (Dominant: **Group Duplicates**)
- **C6 (100 files, 30 candidates):** Discovery **176.0 ms**, Size Filter 159.3 ms, Read & Hash 45.1 ms, Grouping N/A* (Dominant: **Discovery**)
- **C7 (100 files, 30 candidates):** Discovery **128.0 ms**, Size Filter 116.7 ms, Read & Hash N/A*, Grouping 78.2 ms (Dominant: **Discovery**)

## Verification Evidence
- GitHub Actions CI Run `34246767819` (`macos-15` arm64): PASS (11m 30s)
- T006 unit tests (`tests/test_t006_experiments.py`): 23/23 PASS (including real unmocked timeout and generic error tests)
- Harness offline tests (`tests/test_benchmark_harness.py`): 11/11 PASS
- Benchmark corpus tests (`tests/test_benchmark_corpus.py`): 14/14 PASS
- Full test suite discovery (`tests/`): 48/48 PASS
- Phase 4 differential offline self-tests (`tests/phase4_differential.py --offline`): PASS
- Production immutability: `src/*.j2` remains 100% untouched (`git diff origin/main -- src/` strictly empty)
- Artifacts synchronized: `benchmarks/results/t006_results.json`, `benchmarks/results/t006_report.md`

## Next Action
Stop at T006 boundary. Do NOT begin T007. Ready for fresh independent OpenCode adversarial review.
