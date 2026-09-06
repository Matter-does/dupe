# Current Task

**Task:** T003 — Competitive and technical research consolidation  
**Status:** COMPLETE (Fact-checked and reconciled against J2 0.1.0 runtime contract)

## Completed
- Reconciled the fact-checked T003 research report with `docs/J2-API-0.1.0.md` and `docs/PHASE-4-CORRECTNESS.md`.
- Comprehensive rewrite and expansion of `docs/RESEARCH.md`:
  * Applied explicit Evidence Classification System (Grades A through E).
  * Formalized `dupe` product thesis as a J2-native filesystem intelligence engine studying automatic parallelism.
  * Verified execution modes (`j2 run` interpreter, `j2 build` native binary with `J2_ALLOW_FS=1`).
  * Quarantined unsupported/unverified controls (`J2_PARALLEL=0`, `J2_FORCE_NATIVE`, `J2_NO_NATIVE`, `J2_NO_NESTED`, `J2_DEBUG`).
  * Established serial-vs-parallel experimental design (Path A official probe, Path B serial-equivalent baseline).
  * Documented competitive analysis (`fclones`, `Czkawka`, `fdupes`, `jdupes`, `rmlint`, `duperemove`) and storage-adaptive concurrency lessons.
  * Formalized filesystem performance model and corrected 256-bit collision mathematics ($4.31 \times 10^{-48}$ at $n=10^{15}$).
  * Formulated hypotheses H1–H9 and established standard CI runner budget (<= 1 GB storage constraint).
- Updated `docs/ARCHITECTURE.md` to establish the reusable `FileRecord[]` abstraction feeding multiple analysis passes.
- Established actionable specifications for downstream tasks:
  * `agent/tasks/T004-benchmark-corpus.md`: 8 orthogonal dimensions, 7 named corpora (C1–C7), JSON manifest schema, and runner storage budget (<=1 GB).
  * `agent/tasks/T005-j2-baseline-benchmark.md`: 3 baselines (interpreter, native, pure J2 control), repetition protocol, stage timings, and serial-equivalent native baseline requirement.
  * `agent/tasks/T006-automatic-parallelism.md`: 4-stage experimental ladder (T006-A through T006-D) and 5-level observability hierarchy.
  * `agent/tasks/T007-checksum-inventory.md`: Complete specification for Checksum Inventory pass over `FileRecord[]`.
- Preserved the frozen Phase 3 exact-duplicate algorithm as the reference baseline workload.

## Acceptance Criteria
- [x] Verified J2 facts clearly separated from hypotheses via explicit Evidence Grades (A through E).
- [x] Unsupported/undocumented claims (`J2_PARALLEL=0`, `J2_FORCE_NATIVE`, etc.) quarantined and prohibited.
- [x] Frozen Phase 3 duplicate detection algorithm preserved as reference baseline without unverified partial-hash changes.
- [x] T004 benchmark corpus specification and generator requirements made explicit (8 dimensions, 7 named corpora, <=1 GB CI ceiling).
- [x] T005 interpreter/native baseline specification made explicit (3 baselines, repetition rules, stage timings).
- [x] T006 automatic-parallelism experiment specification made explicit (4-stage ladder, 5-level observability).
- [x] T007 second read-only workload (Checksum Inventory) specified over common `FileRecord[]` pipeline.
- [x] CI runner storage constraints (14 GB SSD ceiling) documented and respected.
- [x] Tracking state (`agent/TODO.md`, `agent/CHECKPOINT.md`, `agent/HANDOFF.md`, `agent/CURRENT_TASK.md`) updated.

## Verification Evidence
- Offline differential and regression suite: PASS (`python tests/phase4_differential.py --offline`).
- Git diff reviewed; no modifications to Phase 3 J2 sources (`src/*.j2`).
- Specifications cross-checked against J2 0.1.0 runtime-verified APIs in `docs/J2-API-0.1.0.md`.

## Next Task
T004 — Benchmark corpus specification and generator (`agent/tasks/T004-benchmark-corpus.md`).
