# Current Task

**Task:** T006 — Automatic Parallelism Experiment and Evidence Collection (Deep-Critic Remediated)  
**Status:** Completed & Deep-Critic Remediated (Ready for independent OpenCode release review)

## Summary of Implementation & Results
- **Execution Platform:**
  - OS / Kernel: Darwin 24.6.0 (arm64 Apple Silicon)
  - Hardware: 3 vCPUs, 7.0 GB RAM
  - Toolchain: `j2 0.1.0` (`6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75`)
  - CI Run: GitHub Actions run `34051835154` (`macos-15`, duration 10m 56s)
  - Baseline Commit: `636c75ad408bf05c41f07bea205a53d68f5ae3d2`

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
  - N=100K: Interpreter 79.48 ms, Native Candidate 69.68 ms, Native Serial 871.02 ms (Candidate/Serial 12.50x)
  - N=2M: Interpreter 97.28 ms, Native Candidate 124.04 ms, Native Serial 17,982.43 ms (Candidate/Serial 144.98x)
  - N=5M: Interpreter 249.77 ms, Native Candidate 259.63 ms, Native Serial 35,153.71 ms (Candidate/Serial 135.40x)

### Level T006-B: Pure In-Memory Hashing
- **Workload:** Hashes K independent in-memory string buffers in RAM without filesystem access
- **Configurations:** 10x1KB, 50x4KB, 100x16KB, 200x64KB (up to 12.8 MB total RAM); boundary tests: 0 bufs, 1 buf
- **Correctness:** 100% VALID (Deterministic 64-char hexadecimal SHA-256 digests)
- **Candidate vs Serial-Equivalent Speedup:** 0.59x to 1.09x (average 0.84x; candidate is not faster than serial chained control)
- **Multi-Core Engaged:** NO (<105% CPU)
- **Classification:** CATEGORY D (Grade A)

### Level T006-C: Filesystem Read + Hash
- **Workload:** Direct `fs.read_bytes(path)` + `hash.sha256(bytes)` on real corpus trees (C1, C2, C4, C5, C6, C7; seed 12345, scale 0.01)
- **Serial Control:** Cryptographically chained loop-carried dependency (`chained = fmt("{}:{}", prev_hash, file_digest)` + `hash.sha256(chained)`) with true data dependence (avalanche effect across iterations)
- **Correctness:** 100% VALID across all corpora
- **Candidate vs Serial-Equivalent Speedup:** 0.75x to 1.13x (average 0.93x)
- **Multi-Core Engaged:** NO (<105% CPU)
- **Classification:** CATEGORY D (Grade A)

### Level T006-D: Full dupe Pipeline
- **Workload:** Production `dupe` end-to-end execution on standard corpora suite (C1, C2, C4, C5, C6, C7; fixed seed 12345, scale 0.01, preserving exact T005 corpus identities)
- **Correctness:** 100% VALID (100% bit-for-bit direct JSON match and 100% manifest expected_result_digest agreement)
- **Native vs Interpreter Speedup:** 0.87x to 1.45x (median 1.01x)
- **Multi-Core Engaged:** NO (<105% CPU)
- **Classification:** CATEGORY C (Grade A)

### Operational Stage Breakdowns
Estimated via standalone cumulative microbenchmark probes (`benchmarks/t006/stage_*.j2`) preserving production `src/*.j2` immutability. Negative or sub-noise-floor deltas ($\le 10\text{ ms}$) explicitly marked `"below_noise_floor"` and rendered as `N/A*` (not zero-clipped):
- **C1 (500 files, 122 candidates):** Discovery 89.6 ms, Size Filter **1,988.3 ms** (~88% of total probe time), Read & Hash 48.4 ms, Grouping 141.1 ms (Dominant: **Size Filter O(N^2)**)
- **C2 (100 files, 30 candidates):** Discovery 105.6 ms, Size Filter 78.1 ms, Read & Hash **129.3 ms** (~41% of total probe time), Grouping 5.1 ms (Dominant: **Read & Hash**)
- **C4 (100 files, 80 candidates):** Discovery 64.4 ms, Size Filter **115.7 ms**, Read & Hash 65.0 ms, Grouping 11.3 ms (Dominant: **Size Filter O(N^2)**)
- **C5 (200 files, 200 candidates):** Discovery 127.3 ms, Size Filter 52.3 ms, Read & Hash 24.0 ms, Grouping **136.3 ms** (Dominant: **Group Duplicates**)
- **C6 / C7:** Read & Hash / Grouping micro-stages below noise floor rendered as `N/A*` with explanatory note.

## Verification Evidence
- GitHub Actions CI Run `34051835154` (`macos-15` arm64): PASS (10m 56s)
- T006 unit tests (`tests/test_t006_experiments.py`): 20/20 PASS (including all remediation regression & boundary tests)
- Harness offline tests (`tests/test_benchmark_harness.py`): 11/11 PASS
- Benchmark corpus tests (`tests/test_benchmark_corpus.py`): 14/14 PASS
- Full test suite discovery (`tests/`): 45/45 PASS
- Phase 4 differential offline self-tests (`tests/phase4_differential.py --offline`): PASS
- Production immutability: `src/*.j2` remains 100% untouched (`git diff origin/main -- src/` strictly empty)
- Artifacts synchronized: `benchmarks/results/t006_results.json`, `benchmarks/results/t006_report.md`

## Next Action
Stop at T006 boundary. Do NOT begin T007. Ready for fresh independent OpenCode adversarial review.
