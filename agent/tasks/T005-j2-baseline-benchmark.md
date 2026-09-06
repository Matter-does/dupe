# T005 — J2 Interpreter/Native Baseline Benchmark

## Goal
Establish rigorous, reproducible execution baselines for `dupe` across J2 execution modes (interpreter and compiled native binary) and a known J2 automatic-parallelism control before conducting parallel scaling experiments.

## Prerequisites
- **T002:** Phase 4 differential correctness verified and frozen.
- **T003:** Technical research and evidence ledger consolidated.
- **T004:** Deterministic benchmark corpus generator and manifests available.

## Baseline Matrix

### Baseline A — J2 Interpreter
```bash
j2 run --allow-fs src/main.j2 <corpus_path> --json
```
- **Purpose:** Establish the pure interpreter execution baseline.
- **Characteristics:** Deny-by-default capabilities unlocked via `--allow-fs`. Single-thread interpreter execution.

### Baseline B — J2 Compiled Native Binary
```bash
j2 build src/main.j2 -o build/dupe
J2_ALLOW_FS=1 ./build/dupe <corpus_path> --json
```
- **Purpose:** Measure standalone native compilation speedup over the interpreter.
- **Contract Boundary:** Runs with the verified runtime capability `J2_ALLOW_FS=1`. Makes no assumptions about parallelism flags.

### Baseline C — Known J2 Parallelism Control
- **Purpose:** Execute a known pure J2 parallel workload (e.g. dense numerical reduction / element-wise array kernel documented by J2) within the exact same benchmark harness.
- **Contract Boundary:** Proves the benchmarking environment and J2 compiler are capable of activating automatic parallelism before evaluating `dupe`.

## Serial-vs-Parallel Baseline Policy
- **NO Undocumented Flags:** `J2_PARALLEL=0`, `J2_FORCE_NATIVE`, `J2_NO_NATIVE`, `J2_NO_NESTED`, and `J2_DEBUG` are quarantined (Grade E / rejected) and must NOT be used.
- **Serial-Equivalent Baseline:** If an official compiler disable flag is not discovered via verified binary probes, construct an honest source-level serial-equivalent native benchmark (introducing an intentional loop carry dependency that suppresses parallelization while performing identical work). Report this honestly as **"serial-equivalent native baseline"**.

## Repetition & Statistical Protocol
- **Microbenchmarks:** 3 warmup runs, 7 measured iterations.
- **Filesystem Workloads:** 1 warmup run, 3–5 measured iterations.
- **Data Retention:** Retain all raw run timings. Report median, minimum, maximum, and standard deviation.

## Metrics & Captured Metadata

### Core Metrics
- `wall_time_ms` (total process time)
- `stage_discovery_ms` ($T_{discovery}$)
- `stage_hash_ms` ($T_{read+hash}$)
- `stage_group_ms` ($T_{group}$)
- `files_scanned`
- `candidate_files`
- `bytes_hashed`
- `duplicate_groups`
- `duplicate_files`
- `reclaimable_bytes`

### Derived Rates
- Files scanned / sec
- Candidate files / sec
- MB hashed / sec
- Native speedup factor ($T_{\text{interpreter}} / T_{\text{native}}$)

### Provenance Metadata
- Exact J2 version (`j2 0.1.0`)
- OS kernel and platform architecture
- CPU model and physical/logical core count
- System RAM
- CI runner ID / machine identifier
- Git commit hash
- Corpus ID and manifest SHA-256

## Acceptance Criteria
1. Baseline A (interpreter) measured across standard corpora (C1, C2, C5, C6).
2. Baseline B (compiled native) measured across identical corpora.
3. Baseline C (pure J2 parallel control) executed to validate multi-core activation.
4. Exactly identical corpus trees and manifests used across comparison runs.
5. Multiple repetitions performed with raw data preserved.
6. Stage timings recorded and reported.
7. Zero reliance on undocumented J2 environment flags.
8. Exact J2 version and environment provenance logged in benchmark output JSON.
9. Bit-for-bit output JSON equivalence verified between interpreter and native runs.
10. Benchmark results formatted into reproducible machine-readable summary.
