# Agent Handoff

## Current state
T003 targeted remediation is COMPLETE and prepared for targeted OpenCode re-check. All 18 findings from OpenCode's independent review (P1-1 to P1-10, P2-1 to P2-8) have been systematically resolved with primary evidence from official J2 documentation (`j2-lang.org`), official GitHub runner specifications, and repository differential testing. Non-negotiable boundaries were strictly respected: `src/*.j2` is 100% untouched, the Phase 3 duplicate detection algorithm is unmodified, and T004 implementation has NOT been started.

## What changed?
1. **`docs/RESEARCH.md`**:
   - Reclassified `J2_FORCE_NATIVE` as documented in official J2 docs (`j2-lang.org/docs/parallelism.html`, `execution.html`) but unverified in `dupe`'s capability contract; clarified `J_FORCE_NATIVE` as a historical typo (P1-1).
   - Removed Linux J2 execution legs and ELF claims; confirmed J2 0.1.0 is Apple Silicon macOS only; gated Linux benchmarks on future releases (P1-2).
   - Corrected runner hardware specifications (`macos-15` = 3 vCPU / 7 GB RAM / 14 GB SSD; `ubuntu-latest` = 4 vCPU / 16 GB RAM / 14 GB SSD); re-calibrated scaling to 3 cores (P1-3).
   - Corrected C1 corpus arithmetic (50,000 files, ~200 MB, tiny-heavy <4 KB) (P1-4).
   - Reframed C7 as warm-state transition and run-to-run variance, dropping cold-cache claims (P1-5).
   - Split H2 into Grade B principle (with official citation) and Grade D control speedup hypothesis (P1-7).
   - Replaced "<1 MB" threshold with official 32,768-element reduction threshold (P1-10).
   - Added comprehensive Sources section with URLs, versions, dates, and access timestamps; added `dupeGuru` to competitive matrix (P1-8).
   - Harmonized C3 definition (200–500 large files, 10% duplicates, ~1–2 GB, labeled Developer-Hardware Only) (P2-1).
   - Added explicit Evidence Grades (B, C, D) to each row of the §10 stage table (P2-4).
2. **`docs/ARCHITECTURE.md`**:
   - Made `FileRecord` representation-agnostic (`[path, size]`), avoiding unverified object-literal assumptions (P2-7).
   - Clarified that output determinism strictly follows the established first-discovery order contract, not synthetic sorting (P2-7).
   - Confirmed that Pass B (Checksum Inventory) is additive and preserves frozen baseline code (P2-6).
3. **`agent/tasks/T004-benchmark-corpus.md`**:
   - Reconciled C1 (50K, ~200 MB, <4 KB) and C3 (200–500 files, 10% dupes, ~1–2 GB, Dev Only) (P1-4, P2-1).
   - Updated runner specifications to 3 vCPU / 7 GB RAM on `macos-15` (P1-3).
   - Reframed C7 as warm-state transition (P1-5).
   - Defined `duplicate_ratio = duplicate_files / total_files`; defined `expected_result_digest` as SHA-256 of deterministic output JSON; closed all profile enums (P2-2).
   - Renamed dimensions to "Controlled Workload Dimensions" and documented interactions (P2-3).
   - Scoped byte-identity criterion to content, relative paths, and manifest (excluding volatile OS mtime) (P3).
4. **`agent/tasks/T005-j2-baseline-benchmark.md`**:
   - Restricted J2 benchmark target to `macos-15` (arm64, 3 vCPUs) (P1-2, P1-3).
   - Made total process wall-clock time mandatory; deferred internal stage timings pending verified runtime timing API (P1-6).
   - Named concrete Baseline C control program: `data = collect(1..2000000); print(sum(data))` from `j2-lang.org/docs/parallelism.html` (P2-5).
   - Mandated explicit `j2 run --allow-fs` for Baseline A (P2-8).
5. **`agent/tasks/T006-automatic-parallelism.md`**:
   - Named concrete T006-A control program (P2-5).
   - Calibrated scaling expectations to 3 cores on `macos-15` (P1-3).
   - Hedged Level 1 `emit-native` interpretability (P2-4).
6. **`agent/tasks/T007-checksum-inventory.md`**:
   - Made internal elapsed timing output deferred pending verified J2 timing API (P2-6).
   - Specified sub-command argv handling (`dupe checksum <path>`) (P2-6).
   - Mandated additive implementation in new modules without refactoring or modifying `src/*.j2` (P2-6).
7. **`agent/CURRENT_TASK.md`, `agent/CHECKPOINT.md`, `agent/TODO.md`**:
   - Updated tracking state to reflect remediation completion and hold for OpenCode re-check.

## Unresolved J2 Questions
1. **Official Parallelism Disable Switch:** Does J2 0.1.0 expose an officially supported public command-line option or environment variable for disabling automatic parallelism?
2. **`fs.read_bytes` Allocation Mechanics:** What is the actual allocation/copy behavior of `fs.read_bytes` in the J2 0.1.0 runtime, particularly for large files and repeated hashing workloads?
3. **Incremental/Streaming Hashing:** Is there a verified incremental/streaming hashing API in J2 0.1.0?

## What should the next agent avoid repeating?
- Do NOT start T004 implementation until the targeted OpenCode re-check approves T003.
- Do NOT modify `src/*.j2`.
- Do NOT re-introduce unsupported Linux J2 execution legs or ELF claims.
- Do NOT treat `J2_FORCE_NATIVE` as an established capability contract in `dupe`; native execution requires genuine `j2 build`.

## Next Action
Submit T003 for targeted OpenCode re-check.
