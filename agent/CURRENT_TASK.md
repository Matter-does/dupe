# Current Task

**Task:** T003 — Competitive and technical research consolidation  
**Status:** READY FOR TARGETED OPENCODE RE-CHECK (Remediated post-independent review)

## Completed Remediation
- **P1-1 (`J2_FORCE_NATIVE`):** Reclassified from "proven non-existent" to documented in official J2 docs (`j2-lang.org/docs/parallelism.html`) but unverified in `dupe`'s runtime capability contract. Clarified `J_FORCE_NATIVE` as a historical typo. Reaffirmed native execution via `j2 build`.
- **P1-2 (Linux J2):** Removed Linux J2 execution legs and ELF claims; cited `j2-lang.org/download.html` confirming J2 0.1.0 is macOS Apple Silicon only. Gated Linux benchmarking on future J2 releases.
- **P1-3 (Runner specs):** Corrected runner hardware specifications per official GitHub docs (`macos-15` = 3 vCPU / 7 GB RAM / 14 GB SSD; `ubuntu-latest` = 4 vCPU / 16 GB RAM / 14 GB SSD). Re-calibrated scaling expectations to 3 cores.
- **P1-4 (C1 arithmetic):** Reconciled C1 corpus arithmetic to 50,000 files, ~200 MB (tiny-heavy <4 KB, avg 4 KB) identically across `docs/RESEARCH.md` and T004.
- **P1-5 (C7 methodology):** Reframed C7 as warm-state transition and run-to-run variance, dropping cold-cache claims.
- **P1-6 (T005 stage timing):** Made total process wall-clock time mandatory; made internal stage timings optional/deferred pending verified runtime timing API.
- **P1-7 (H2 grade inflation):** Split H2: J2 compiler parallelism principle = Grade B (with doc citation); specific control speedup = Grade D hypothesis.
- **P1-8 (Sources & dupeGuru):** Added comprehensive Sources section with URLs, access dates, and evidence grades to `docs/RESEARCH.md`. Added `dupeGuru` row to the competitive table.
- **P1-9 (Git boundary):** Committed all remediated files and prepared push to `origin/main`.
- **P1-10 ("<1 MB" threshold):** Replaced "<1 MB" with the official 32,768-element reduction threshold and cited `j2-lang.org/docs/parallelism.html`.
- **P2-1 (C3 definition):** Harmonized C3 across files (200–500 large files, 10% duplicates, ~1–2 GB, labeled Developer-Hardware Only).
- **P2-2 (Manifest semantics):** Defined `duplicate_ratio = duplicate_files / total_files`, defined digest input as deterministic JSON output, and closed all profile string enums.
- **P2-3 (Controlled dimensions):** Renamed to "Controlled Workload Dimensions", documented interactions, and reconciled allowed values with named corpora.
- **P2-4 (Stage table grades):** Added explicit Evidence Grades (B, C, D) to each row of the §10 stage table.
- **P2-5 (Concrete control):** Named exact Baseline C control program: `data = collect(1..2000000); print(sum(data))`.
- **P2-6 (T007 implementability):** Deferred mandatory internal elapsed timing; specified sub-command argv layout; mandated additive implementation without altering `src/*.j2`.
- **P2-7 (Architecture contract drift):** Made `FileRecord` representation-agnostic (`[path, size]`); clarified output determinism contract preserves discovery order.
- **P2-8 (Interpreter invocation):** Mandated explicit `j2 run --allow-fs` for all interpreter benchmark executions.

## Acceptance Criteria
- [x] All 18 OpenCode review findings (P1-1 to P1-10, P2-1 to P2-8) addressed and classified.
- [x] Verified J2 facts separated from hypotheses with defensible Evidence Grades.
- [x] Sources section populated with URLs, versions, and access dates.
- [x] Zero changes to Phase 3 code (`src/*.j2`).
- [x] Offline tests pass (`python tests/phase4_differential.py --offline`).
- [x] Git boundary synchronized with remote.
- [ ] T004 implementation NOT started (strictly blocked pending OpenCode re-check).

## Next Action
Submit T003 remediation for targeted OpenCode re-check. Do NOT start T004 implementation.
