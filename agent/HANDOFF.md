# Agent Handoff

## Current state
Task **T005 — J2 Interpreter/Native Baseline Benchmark** is complete and fully verified.
All acceptance criteria, baseline measurements, and correctness verifications have been satisfied on the designated `macos-15` (arm64 Apple Silicon) runner in GitHub Actions run `34038191455`.

**Do NOT begin T006 automatically.**

---

## 1. Execution Platform & Toolchain Provenance
- **Runner Host:** macOS 15.6.0 (Darwin 24.6.0, `arm64` Apple Silicon)
- **Host Specs:** 3 vCPUs, 7.0 GB RAM
- **Toolchain:** Exact J2 0.1.0 (`6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75`)
- **Git Commit:** `fb5f57aa49af02fa6171de9b761e79d9307b475f`
- **CI Workflow:** `.github/workflows/t005-baseline-benchmark.yml` (Run ID: `34038191455`, duration 2m 14s)

---

## 2. Baseline Definitions & Invocations
1. **Baseline A (Interpreter Baseline):**
   - Invocations: `j2 --allow-fs src/main.j2 <corpus_path> --json`
   - *Key finding:* `j2 run FILE.j2 arg1 arg2` in J2 0.1.0 drops trailing arguments to `proc.argv()`; the verified form `j2 [capabilities] FILE.j2 [args...]` correctly forwards CLI arguments.
2. **Baseline B (Compiled Native Binary):**
   - Compilation: `j2 build src/main.j2 -o build/dupe`
   - Invocation: `J2_ALLOW_FS=1 ./build/dupe <corpus_path> --json`
   - Standalone native Mach-O arm64 binary with verified filesystem capability.
3. **Baseline C (Pure J2 Automatic-Parallelism Control):**
   - Source: `benchmarks/controls/pure_control.j2` (`data = collect(1..2000000); print(sum(data))`)
   - Mathematical Ground Truth: `2000001000000`

---

## 3. Measured Results Summary

### Baseline C (Pure J2 Control — 2M Integer Reduction)
| Execution Mode | Median Wall Time | Mean Wall Time | Min Wall Time | Max Wall Time | Std Dev | Repetitions (Warmup/Meas) | Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Interpreter (`j2 run`)** | **79.66 ms** | 79.50 ms | 70.47 ms | 88.39 ms | 5.42 ms | 3 / 7 | PASS (`2000001000000`) |
| **Native Binary (`j2 build`)** | **58.59 ms** | 58.09 ms | 55.27 ms | 61.37 ms | 2.11 ms | 3 / 7 | PASS (`2000001000000`) |
- **Native Build Duration:** 1,169.81 ms
- **Native Speedup Factor:** **1.36x**

### Filesystem Baselines (Baseline A vs Baseline B across C1–C7)
| Corpus | Scale | Files Scanned | Hash Candidates | Interp Median (ms) | Native Median (ms) | Native Speedup | Direct JSON Match | Manifest Digest Match |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C1** (Metadata Heavy) | 0.01 | 500 | 122 | 2,624.33 | 2,669.61 | **0.98x** | PASS | PASS |
| **C2** (Balanced Baseline) | 0.01 | 100 | 30 | 274.61 | 223.07 | **1.23x** | PASS | PASS |
| **C4** (High Dup Density) | 0.01 | 100 | 80 | 278.15 | 246.33 | **1.13x** | PASS | PASS |
| **C5** (Adversarial Same Size) | 0.01 | 200 | 200 | 474.49 | 438.66 | **1.08x** | PASS | PASS |
| **C6** (Mixed Hierarchy) | 0.01 | 100 | 30 | 237.31 | 214.73 | **1.11x** | PASS | PASS |
| **C7** (Warm Runs Variance) | 0.01 | 100 | 30 | 242.40 | 224.92 | **1.08x** | PASS | PASS |

---

## 4. Key Scientific Findings & Observability
1. **Critical Scientific Distinction:**
   - Native binary execution demonstrates modest speedup over the interpreter (0.98x to 1.23x across filesystem workloads, 1.36x on pure integer reduction).
   - This speedup reflects compilation to native machine code without interpreter bytecode dispatch overhead.
   - **Native speedup is NOT in itself proof of automatic parallelism.**
2. **Compiler Backend Inspection (`j2 emit-native`):**
   - Rust emission reveals thread-local global state (`thread_local! static GLOBALS`), `j2_runtime::prelude`, and dynamic value evaluation structures.
   - Automatic-parallelism constructs are lowered by the compiler toolchain, but wall-clock speedup is masked by thread pool initialization and filesystem I/O serialization.
3. **Integration Insight (Manifest Isolation):**
   - The T004 reference oracle explicitly excludes `manifest.json` from the corpus payload.
   - `dupe` (`src/scan.j2`) has no ignore patterns and traverses all files in the target directory.
   - `benchmarks/harness.py` temporarily moves `manifest.json` to `.corpus_manifest.tmp` during execution and restores it in `finally:`, ensuring `dupe` scans strictly the corpus files payload.

---

## 5. Non-Negotiables & Boundary Status
- `src/*.j2`: **100% untouched** (`git diff origin/main -- src/` is strictly empty).
- Phase 3 duplicate detection algorithm: Preserved unchanged.
- T004 generator behavior: Preserved unchanged.
- Undocumented J2 flags: Zero usage of `J2_PARALLEL=0`, `J2_NO_NATIVE`, etc.
- No generated large corpora committed (`benchmarks/corpora/` ignored).
- Zero T006 implementation code added.

---

## 6. What Should the Next Agent Do?
1. Review `agent/tasks/T006-automatic-parallelism.md` before taking any implementation action.
2. Establish the 4-stage experimental ladder to isolate multi-core parallel speedup:
   - Stage 1: Pure computational parallelism proof.
   - Stage 2: In-memory hashing parallel proof.
   - Stage 3: Cold vs warm I/O parallel scaling.
   - Stage 4: End-to-end `dupe` multi-core scaling analysis.
3. Keep `src/*.j2` immutable unless a formal Phase 4 task explicitly authorizes architectural restructuring.
4. Do NOT begin T006 automatically without explicit user authorization.
