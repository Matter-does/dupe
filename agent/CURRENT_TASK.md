# Current Task

**Task:** T004 — Benchmark Corpus Specification and Generator  
**Status:** COMPLETE (Ready for T005)

## Summary of Accomplishments
- **Deterministic Corpus Generator:** Implemented seed-based generator in `benchmarks/generator/generate.py` with reproducible PRNG trees and file payloads.
- **Manifest Schema Version 1:** Implemented strict manifest schema and validation in `benchmarks/generator/manifest.py` adhering to T004 specification.
- **C1–C7 Standard Corpora:** Implemented all 7 named profiles in `benchmarks/generator/profiles.py` across controlled workload dimensions.
- **C1 Arithmetic Consistency:** Verified $50\text{K} \times 4\text{ KB} \approx 200\text{ MB}$, 5% duplicates (2,500 duplicate files in pairs), tiny-heavy (<4 KB), CI storage compliant.
- **C3 Developer-Hardware-Only Gating:** Verified C3 (~1.5 GB, >1 GB CI limit) is explicitly labeled `Developer-Hardware-Only` and guarded behind mandatory `--allow-developer-hardware` flag.
- **C7 Terminology:** Framed C7 as warm-state transition and repeated-run variance (`initial_run`, `warm_repeated`), completely eliminating "cold cache" terminology.
- **CI Storage Limits:** Enforced <= 1 GB ceiling across all CI corpora (C1, C2, C4, C5, C6, C7).
- **Pre-flight Disk Space Safety:** Enforced `check_disk_space()` before file generation to prevent runner disk exhaustion.
- **Deterministic Expected Result Digest:** Computed via independent reference oracle evaluated against the corpus root with normalized relative paths.
- **Comprehensive Validation Suite:** Created `tests/test_benchmark_corpus.py` (10 passing test cases covering reproducibility, schema checking, arithmetic consistency, C3 protection, and full C1–C7 matrix).
- **Immutability:** Zero modifications to `src/*.j2`.
- **Differential Gates:** Verified passing offline self-tests (`python tests/phase4_differential.py --offline`).

## Acceptance Criteria
- [x] Generator exists and is deterministic (`benchmarks/generator/`).
- [x] C1–C7 definitions implemented consistently with specification.
- [x] Manifest schema version 1 and validation operational.
- [x] Expected-result semantics are deterministic.
- [x] Corpus size/storage constraints respected (CI <= 1 GB, C3 labeled Dev-Only).
- [x] All 10 benchmark corpus tests pass (`python tests/test_benchmark_corpus.py`).
- [x] All Phase 4 offline self-tests pass (`python tests/phase4_differential.py --offline`).
- [x] `src/*.j2` remains completely untouched.
- [x] Working tree clean, committed, and pushed to `origin/main`.
- [x] Checkpoint and handoff identify next task as T005.

## Next Task
T005 — J2 interpreter/native baseline benchmark. (Do NOT start automatically).
