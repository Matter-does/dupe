# Checkpoint

task: T002
status: complete

completed:
  - Phase 4 differential correctness gates hardened against independent adversarial review (F1-F14)
  - True native binary compilation and execution verified via J2_ALLOW_FS=1 (F1)
  - Independent Python oracle validated with pairwise read_bytes byte-identity soundness check (F3)
  - 13 seed corpus cases passing with strict direct match across interpreter, native, and oracle (F2, F7, F8, F12)
  - Retained regression corpus validated in tests/regressions/fixtures/ with schema and path traversal sanitization (F5)
  - Seed-based fuzzer generator expanded with same-size distinct files, dotfiles, and empty directories (F11)
  - Full-fidelity failure preservation and reproduction verified on >4KB files (F4)
  - Strict offline self-tests with ground-truth assertions passing locally and in dedicated CI job (F9, F10)
  - Hard timeouts (60s subprocess, 15m CI workflow) enforced against symlink loops and recursion hangs (F6, F7)
  - Workflow update in .github/workflows/phase4-correctness.yml with version assertion, j2 fmt, and native build
  - Second independent review remediation applied:
    * F12: verified trailing-slash raw argv handling and frozen literal '//' concatenation contract
    * F5: sanitized fixture name escaping and enhanced hex decode error diagnostics
    * F6: added timeout-minutes: 10 to phase3-mvp.yml and wrapped TimeoutExpired in run_dupe_raw
    * F7: added symlink-cycle bounded termination test and moved oracle/manifest inside preservation try with cycle guards
    * F3: added within-group duplicate path entry assertion
    * F13: documented discover-vs-hash TOCTOU limitation and path concatenation in docs/J2-API-0.1.0.md
    * Removed dead canonicalize_groups helper
  - docs/PHASE-4-CORRECTNESS.md and docs/J2-API-0.1.0.md updated to document all verified behaviors

not_done:
  - T003 competitive/technical research consolidation
  - T004 benchmark corpus specification and generator
  - T005 J2 interpreter/native baseline benchmark
  - T006 automatic-parallelism experiment

verification:
  local_offline_selftests: pass (multi-seed reproducibility, faithful >4KB failure preservation, 13 seed cases strict assertions, 4 regression fixtures strict assertions, offline symlink cycle test)
  ci_phase4_correctness: pass (run 34019865197, macOS 15 Apple Silicon arm64 job 101450344313 [1m8s], Ubuntu offline job 101450325863 [7s])
  ci_phase3_mvp_native: pass (run 34019865207, macOS 15 arm64, 1m44s)
  ci_j2_toolchain: pass (run 34019865243, macOS 15 arm64, 1m21s)
  interpreter_oracle_match: pass (strict direct match require_direct_match=True across all 13 seed cases, 4 regression fixtures, 5 fuzzer seeds)
  native_oracle_match: pass
  interpreter_native_match: pass
  repeat_run_determinism: pass (verified on single-dir and nested-dir trees)
  trailing_slash_handling: pass (raw argv and literal // contract verified)
  symlink_cycle_bounded_termination: pass (bounded within 10s on POSIX)
  soundness_byte_identity: pass (pairwise read_bytes byte identity across all group files and within-group path uniqueness)
  filesystem_immutability: pass (hash, mtime_ns, mode)
  safety_invalid_roots: pass (missing root, file as root)
  safety_unreadable_permissions: pass (unreadable subdirectory, unreadable duplicate candidate)
  native_negative_control: pass (capability denied without J2_ALLOW_FS=1)

pending_verification:
  none_for_t002: all Phase 4 correctness gates fully verified

next_action:
  - execute T003 (consolidate competitive and technical research into docs/RESEARCH.md)
  - prepare corpus specification for T004

last_agent: Antigravity
