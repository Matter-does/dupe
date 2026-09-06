# Checkpoint

task: T003
status: remediated_pending_recheck

completed:
  - Addressed all 18 independent OpenCode review findings (P1-1 to P1-10, P2-1 to P2-8)
  - Reclassified J2_FORCE_NATIVE as documented in official J2 docs (j2-lang.org/docs/parallelism.html) but unverified in dupe runtime capability contract; clarified J_FORCE_NATIVE as historical typo
  - Removed Linux J2 native execution and ELF claims, gating Linux benchmarks on future J2 releases; confirmed J2 0.1.0 is macOS Apple Silicon only
  - Corrected GitHub runner hardware specs: macos-15 = 3 vCPU / 7 GB RAM / 14 GB SSD; ubuntu-latest = 4 vCPU / 16 GB RAM / 14 GB SSD
  - Reconciled C1 corpus arithmetic (50,000 files, ~200 MB, tiny-heavy <4 KB) identically across all files
  - Reframed C7 as warm-state transition and run-to-run variance, dropping cold-cache claims
  - Made total process wall-clock time mandatory in T005, deferring internal stage timings pending verified runtime timing API
  - Split H2 into Grade B principle (with official citation) and Grade D control speedup hypothesis
  - Replaced "<1 MB" threshold with official 32,768-element reduction threshold from J2 documentation
  - Added full Sources section with URLs and access dates to docs/RESEARCH.md; added dupeGuru to competitive matrix
  - Harmonized C3 definition (200-500 large files, 10% duplicates, ~1-2 GB, Developer-Hardware Only)
  - Defined manifest duplicate_ratio formula and expected_result_digest input; closed all profile string enums
  - Renamed benchmark dimensions to "Controlled Workload Dimensions" and documented interactions
  - Graded all rows in §10 stage table with explicit Evidence Grades (B, C, D)
  - Specified concrete Baseline C control program: data = collect(1..2000000); print(sum(data))
  - Updated T007 to mandate additive implementation without modifying src/*.j2, documented argv parsing, and deferred elapsed timing
  - Updated docs/ARCHITECTURE.md with representation-agnostic FileRecord [path, size] and discovery-order determinism
  - Mandated explicit j2 run --allow-fs for interpreter baseline execution
  - Maintained 100% immutability of Phase 3 source code (src/*.j2 untouched)
  - Verified passing offline self-tests (python tests/phase4_differential.py --offline)

not_done:
  - T004 benchmark corpus generator implementation (strictly blocked pending OpenCode re-check)
  - T005 J2 interpreter/native baseline execution
  - T006 automatic-parallelism experiment execution
  - T007 second workload implementation

verification:
  local_offline_selftests: pass (multi-seed reproducibility, faithful >4KB failure preservation, 13 seed cases, 4 regression fixtures, symlink cycle handling)
  phase3_source_integrity: pass (git diff c4eb4c6..HEAD -- src/ is completely empty)
  sources_verified: pass (official J2 docs at j2-lang.org fetched live and verified)
  git_boundary: pending push to origin/main

pending_verification:
  targeted_opencode_recheck: awaiting independent re-check of T003 remediation

next_action:
  - commit T003 remediation changes
  - push to origin/main and verify remote SHA agreement
  - submit for targeted OpenCode re-check

last_agent: Antigravity
