# T005 — J2 Interpreter/Native Baseline Benchmark

## Goal
Establish rigorous, reproducible execution baselines for `dupe` across J2 execution modes (interpreter and compiled native binary) and a concrete J2 automatic-parallelism control on `macos-15` (arm64) before conducting parallel scaling experiments.

## Prerequisites
- **T002:** Phase 4 differential correctness verified and frozen.
- **T003:** Technical research, sources, and evidence ledger consolidated.
- **T004:** Deterministic benchmark corpus generator and manifests operational.

## Execution Platform
- **Target OS / Architecture:** macOS 15 (Apple Silicon arm64, 3 vCPUs, 7 GB RAM).
- **Platform Scope:** All J2 benchmark legs execute on `macos-15` as the sole supported platform for J2 0.1.0. Linux execution is deferred until an official Linux release of J2 is available.

## Baseline Matrix

### Baseline A — J2 Interpreter Baseline
```bash
j2 run --allow-fs src/main.j2 <corpus_path> --json
```
- **Execution Engine:** Explicit `j2 run` invocation to guarantee serial interpreted execution without bare-form compiler fallback.
- **Capabilities:** Explicit `--allow-fs` capability flag.

### Baseline B — J2 Compiled Native Binary
```bash
j2 build src/main.j2 -o build/dupe
J2_ALLOW_FS=1 ./build/dupe <corpus_path> --json
```
- **Execution Engine:** Standalone native Mach-O arm64 binary compiled with `j2 build`.
- **Capabilities:** Standalone native sandbox granted via runtime environment variable `J2_ALLOW_FS=1`.

### Baseline C — Concrete J2 Parallelism Control
```j2
data = collect(1..2000000)
print(sum(data))
```
- **Source:** `https://j2-lang.org/docs/parallelism.html`
- **Purpose:** Execute an official J2 automatic-parallelism workload (reduction over 2,000,000 integers) exceeding the documented 32,768-element cost-model threshold.
- **Role:** Proves that the native compiler toolchain and host runner activate multi-core parallel execution before interpreting `dupe` results.

## Serial-vs-Parallel Baseline Policy
- **Native Execution Contract:** Native execution must use genuine `j2 build src/main.j2 -o build/dupe` with `J2_ALLOW_FS=1`. `J2_FORCE_NATIVE` is documented in J2 documentation but is not part of the verified `dupe` capability contract. `J_FORCE_NATIVE` was a historical typo.
- **Undocumented Flags:** `J2_PARALLEL=0`, `J2_NO_NATIVE`, `J2_NO_NESTED`, and `J2_DEBUG` are unverified (Grade E) and must NOT be used.
- **Serial Baseline:** If an official compiler disable flag is not verified, construct a source-level serial-equivalent native benchmark (introducing a sequential loop dependency). Document this transparently as **"serial-equivalent native baseline"**.

## Repetition & Statistical Protocol
- **Microbenchmarks:** 3 warmup runs, 7 measured iterations.
- **Filesystem Workloads:** 1 warmup run, 3–5 measured iterations.
- **Data Retention:** Retain all raw run timings. Report median, minimum, maximum, and standard deviation.

## Metrics & Captured Metadata

### Core Metrics
- `wall_time_ms` (**Mandatory** — total external process execution time)
- `stage_discovery_ms` (*Optional/Deferred* — internal stage timing pending verified runtime API or separate stage programs)
- `stage_hash_ms` (*Optional/Deferred*)
- `stage_group_ms` (*Optional/Deferred*)
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
- OS kernel and platform architecture (`macos-15` arm64)
- CPU model and core count (3 vCPUs on standard GitHub runner)
- System RAM (7 GB)
- Runner ID / machine identifier
- Git commit hash
- Corpus ID and manifest SHA-256

## Acceptance Criteria
1. Baseline A (interpreter) measured across standard corpora (C1, C2, C4, C5, C6, C7) using explicit `j2 run --allow-fs`.
2. Baseline B (compiled native) measured across identical corpora using `build/dupe` with `J2_ALLOW_FS=1`.
3. Baseline C (concrete pure J2 parallel control) executed to validate multi-core reduction lowering.
4. Identical corpus trees and manifests used across comparison runs.
5. Multiple repetitions performed with raw data preserved.
6. Total process wall-clock time recorded and reported; internal stage timings recorded where supported by explicit stage benchmarks.
7. Zero reliance on undocumented J2 environment flags.
8. Exact J2 version and environment provenance logged in benchmark output JSON.
9. Bit-for-bit output JSON equivalence verified between interpreter and native runs.
10. Benchmark results formatted into reproducible machine-readable summary.
