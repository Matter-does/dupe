# Current Task

**Task:** T002 — Complete Phase 4 correctness and regression gates
**Status:** COMPLETE (Hardened against independent review F1–F14)

## Completed
- Verified genuine compiled native binary (`j2 build src/main.j2 -o build/dupe`) with runtime capability `J2_ALLOW_FS=1` and negative control test (F1).
- Enforced frozen discovery-order grouping contract with strict direct equality (`require_direct_match=True`) across all cases (F2).
- Implemented independent `verify_soundness()` asserting pairwise byte identity and group disjointness (F3).
- Implemented faithful failure preservation retaining full file contents, empty dirs, exit codes, and stderr without truncation (F4).
- Added path sanitization and fixture schema validation preventing directory traversal attacks (F5).
- Added hard 60s subprocess timeouts and 15m CI workflow timeouts to guard against symlink loops (F6, F7).
- Expanded seed corpus to 13 cases (dotfiles, empty dirs, 1MB duplicates, size boundaries) (F7, F8, F12).
- Added strict ground-truth value assertions to offline self-tests and added dedicated offline CI job on `ubuntu-latest` (F9, F10).
- Pinned Python 3.12, asserted exact J2 0.1.0 version, and added `j2 fmt` verification to CI workflow (F10).
- Expanded fuzzer to generate distinct same-size files, empty directories, and dotfiles with multi-seed reproducibility (F11).
- Strengthened tree immutability check to verify byte content hash, `mtime_ns`, and `mode` (F13).
- Documented verified runtime capabilities, symlink semantics, and sort constraints in `docs/J2-API-0.1.0.md` and `docs/PHASE-4-CORRECTNESS.md` (F14).

## Acceptance criteria
- [x] Independent Python oracle implemented with byte-identity soundness checker.
- [x] Seed corpus covers 13 required edge cases.
- [x] Interpreter output matches oracle on every seeded case.
- [x] Native compiled binary output matches oracle on every seeded case.
- [x] Interpreter output equals native output on every seeded case.
- [x] Regression corpus retained in CI with path sanitization and schema checks.
- [x] Failure preservation and reproduction infrastructure verified on synthetic records (>4KB) and seed replay.
- [x] Filesystem immutability verified across all test executions.
- [x] Safety/error behavior for invalid roots and unreadable files verified.

## Verification evidence
- CI run `34018671137` (job `101447099395` macOS 15 arm64 / J2 0.1.0 [1m48s], job `101447082243` Ubuntu offline [6s]): PASS
- CI run `34018559525` (Phase 3 MVP genuine native build / `J2_ALLOW_FS=1`): PASS
- CI run `34018559466` (J2 CI toolchain smoke tests): PASS
- Local Python offline self-tests: PASS

## Next task
T003 — Competitive and technical research consolidation (from `agent/tasks/T003-research.md`).
