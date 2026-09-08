# Checkpoint

task: T006
status: T006 automatic parallelism experiment complete, gates verified, verified CI results captured

completed:
  - Implemented T006 4-stage experimental ladder in `benchmarks/t006/` without modifying production `src/*.j2`:
    - Level T006-A: Pure J2 computational reduction candidate (`t006_a_candidate.j2`) vs serial-equivalent accumulator control (`t006_a_serial.j2`) across scaling sizes (100K, 2M, 5M)
    - Level T006-B: Pure in-memory hashing candidate (`t006_b_candidate.j2`) vs chained serial control (`t006_b_serial.j2`) across buffer counts and sizes (10x1KB to 200x64KB)
    - Level T006-C: Filesystem read + hash candidate (`t006_c_candidate.j2`) vs chained control (`t006_c_serial.j2`) across standard corpora
    - Level T006-D: Full dupe pipeline across standard corpora (C1, C2, C4, C5, C6, C7)
    - Standalone stage probes (`stage_discovery.j2`, `stage_filter.j2`, `stage_read_hash.j2`, `stage_group.j2`) for measured sub-stage decomposition
  - Implemented comprehensive T006 harness and data models (`benchmarks/t006_harness.py`) supporting:
    - Level 1: Compiler backend IR inspection (`j2 emit-native`) with regex pattern extraction and context excerpt retention
    - Level 2: Empirical wall-clock timing statistics (min, max, median, mean, stddev, variance)
    - Level 3: External OS profiling methodology and warm-run repeatability
    - Level 4: Concurrent background process CPU core load sampler (`ps -o %cpu`) detecting multi-core threshold (>110%)
    - Level 5: Bit-for-bit result determinism and manifest digest verification
    - Scientific classification into Categories A–E with Evidence Grades A–E
  - Implemented top-level CLI runner (`benchmarks/run_t006.py`) generating publication-quality Markdown report (`benchmarks/results/t006_report.md`) and machine-readable schema (`benchmarks/results/t006_results.json`)
  - Added dedicated unit test suite (`tests/test_t006_experiments.py`, 14/14 PASS)
  - Implemented and executed dedicated GitHub Actions workflow (`.github/workflows/t006-automatic-parallelism.yml`) on `macos-15` (arm64 Apple Silicon, 3 vCPUs, 7.0 GB RAM, Run ID `34051835154`)
  - Verified 100% test and correctness pass across all 4 levels and all 6 standard corpora
  - Answered all 7 authoritative research questions with explicit Evidence Grades (A–E)
  - Established scientific conclusion: Overall **CATEGORY C** (Native compilation effect only; no sustained multi-core automatic parallelism observed in J2 0.1.0 under tested workloads)
  - Synchronized verified CI results into repository artifacts

not_done:
  - T007 second workload implementation (Checksum Inventory) — halted per task discipline
  - T008 CLI polish
  - T009 GUI shell
  - T010 Demo presentation
  - T011 Final package

verification:
  ci_workflow_run: pass (run 34051835154 on macos-15 arm64 Apple Silicon, 10m 56s)
  overall_classification: CATEGORY C
  t006_a_classification: CATEGORY E / Evidence Grade C* (Reconciled: candidate vs serial comparison confounded by runtime sum() loop fold optimization)
  t006_a_correctness: pass (100% VALID mathematical reduction match across 100K, 2M, 5M, and boundary N=0, 1, 32767, 32769)
  t006_b_correctness: pass (100% VALID deterministic in-memory SHA-256 digests across all configs, and boundary 0, 1 buffer)
  t006_c_correctness: pass (100% VALID across C1, C2, C4, C5, C6, C7; cryptographic chaining loop-carried dependence)
  t006_d_correctness: pass (100% VALID direct JSON match and manifest expected_result_digest agreement across C1, C2, C4, C5, C6, C7; seed 12345, scale 0.01)
  cpu_monitoring: pass (verified no sustained multi-core utilization <105% CPU across all levels; explicit observability status cpu_measurement_valid=false for <4 samples)
  stage_breakdowns: pass (approximate standalone cumulative probes; sub-noise-floor deltas <=10 ms preserved as below_noise_floor and rendered N/A*)
  compiler_inspection: pass (single-threaded thread-local globals; zero concurrency primitives found in emitted backend)
  t006_unit_tests: pass (20/20 tests in tests/test_t006_experiments.py)
  harness_offline_tests: pass (11/11 tests in tests/test_benchmark_harness.py)
  corpus_generator_tests: pass (14/14 tests in tests/test_benchmark_corpus.py)
  full_test_suite: pass (45/45 tests in unittest discover -s tests)
  phase4_offline_tests: pass (tests/phase4_differential.py --offline)
  production_source_integrity: pass (git diff origin/main -- src/ is strictly empty)
  git_boundary: clean, all T006 artifacts committed and synchronized

next_action:
  - Stop at T006 boundary. Do NOT begin T007.
  - Await independent OpenCode adversarial review.

last_agent: Antigravity
