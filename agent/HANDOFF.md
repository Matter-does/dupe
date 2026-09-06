# Agent Handoff

## Current state
T003 is COMPLETE. The fact-checked T003 research report has been reconciled against the repository's verified J2 0.1.0 runtime contract (`docs/J2-API-0.1.0.md`, `docs/PHASE-4-CORRECTNESS.md`). Durable documentation has been updated with explicit Evidence Grades (A through E). Downstream specifications for T004, T005, T006, and T007 are established, and undocumented J2 environment flags have been strictly quarantined.

## What changed?
1. **`docs/RESEARCH.md`**:
   - Expanded into an authoritative technical and competitive register with an explicit Evidence Classification System (Grades A through E).
   - Documented verified execution modes (`j2 run`, `j2 build`), native capability mechanism (`J2_ALLOW_FS=1`), and backend inspection (`j2 emit-native`).
   - Quarantined unsupported/unverified controls (`J2_PARALLEL=0`, `J2_FORCE_NATIVE`, `J2_NO_NATIVE`, `J2_NO_NESTED`, `J2_DEBUG`).
   - Formulated hypotheses H1–H9 and established the 4-stage experimental ladder.
   - Synthesized competitive intelligence from `fclones`, `Czkawka`, `fdupes`, `jdupes`, `rmlint`, and `duperemove` (storage-adaptive concurrency and staged candidate reduction).
   - Decomposed the filesystem performance equation and corrected 256-bit collision probability ($4.31 \times 10^{-48}$ at $10^{15}$ files).
   - Established standard CI runner storage budget (<= 1 GB) and recommended Checksum Inventory as the second workload.
2. **`docs/ARCHITECTURE.md`**:
   - Formalized the reusable `FileRecord[]` abstraction feeding both `Duplicate Analysis` and `Checksum Inventory` without redundant directory traversal.
   - Reaffirmed the frozen reference baseline and automatic parallelism principles.
3. **`agent/tasks/T004-benchmark-corpus.md`**:
   - Updated specification with 8 orthogonal workload dimensions (file count, total bytes, size distribution, duplicate ratio, collision density, tree shape, similarity structure, cache state).
   - Defined 7 named standard corpora (C1 through C7) and JSON manifest schema (`manifest.json`).
   - Enforced <= 1 GB size limit for automated CI corpora.
4. **`agent/tasks/T005-j2-baseline-benchmark.md`**:
   - Defined the 3 distinct baselines: Baseline A (interpreter), Baseline B (compiled native binary), and Baseline C (pure J2 parallelism control).
   - Established measurement protocol: stage timings ($T_{discovery}$, $T_{read+hash}$, $T_{group}$), throughput rates, metadata logging, and repetition counts (3 warmup + 7 measured for microbenchmarks; 1 warmup + 3–5 measured for filesystem workloads).
   - Enforced serial-equivalent native baseline requirement if no official parallelism-disable switch is discovered.
5. **`agent/tasks/T006-automatic-parallelism.md`**:
   - Specified the 4-stage experimental ladder (T006-A pure control, T006-B in-memory hashing, T006-C read + hash, T006-D full `dupe` pipeline).
   - Established the 5-level observability hierarchy (emit-native IR, runtime timing, OS profiling, CPU utilization, bit-for-bit output identity).
   - Formulated acceptance criteria addressing all 7 core research questions.
6. **`agent/tasks/T007-checksum-inventory.md`**:
   - Created full specification for the second read-only workload (Checksum Inventory) reusing `FileRecord[]`.
7. **`agent/TODO.md`, `agent/CURRENT_TASK.md`, `agent/CHECKPOINT.md`**:
   - Marked T003 complete, updated checkpoint, and transitioned current task to T004.

## Key Research Decisions Incorporated
- **Keep Phase 3 Reference Workload Stable**: The exact-duplicate pipeline (`discovery -> metadata -> size filter -> full SHA-256 -> group -> output`) is not altered. Partial hashing is reserved as a future experimental variant, not a replacement baseline.
- **Strict Quarantine of Undocumented Flags**: `J2_PARALLEL=0` is Grade E (unverified) and must not be used in benchmarks or contracts. Serial comparisons must use an explicit source-level serial-equivalent native baseline.
- **CI Storage Reality**: Public GitHub runners provide ~14 GB SSD. Standard CI corpora are capped at <= 1 GB; multi-gigabyte corpora are developer-only.
- **Checksum Inventory as Second Workload**: Reuses `FileRecord[]`, eliminates grouping overhead, and isolates raw I/O and cryptographic hashing for parallel scaling tests.

## Unresolved J2 Questions
1. **Public Parallelism Control**: Does J2 0.1.0 expose any official command-line option or environment variable to suppress automatic loop parallelization? (If not, T005 must rely strictly on source-level serial-equivalent baselines).
2. **Buffer Allocation in `fs.read_bytes`**: Does `fs.read_bytes` allocate a complete new buffer on every call, or does the runtime reuse internal buffers? (T004/T005 will observe memory behavior).
3. **Streaming Hashing**: J2 0.1.0 does not expose an incremental hashing API (`hash.init/update/finish`), remaining an unresolved symbol.

## What should the next agent avoid repeating?
- Do NOT introduce or assume `J2_PARALLEL=0` or `J2_FORCE_NATIVE`.
- Do NOT modify `src/*.j2` to add partial hashing.
- Do NOT generate benchmark corpora exceeding 1 GB in CI workflows.
- Do NOT skip Baseline C (known pure J2 parallel control) in T005 before testing `dupe`.

## Next task
**T004 — Benchmark corpus specification and generator.**
Implement the deterministic, seed-based generator in `benchmarks/generator/`, generating corpora C1 through C7 with verifiable `manifest.json` metadata.
