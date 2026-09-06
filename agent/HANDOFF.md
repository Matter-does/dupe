# Agent Handoff

## Current state
T002 is COMPLETE and fully hardened against independent adversarial review findings (F1–F14). Phase 4 differential correctness, fuzzer reproducibility, failure preservation, and retained regression gates are verified locally via strict offline assertions and automated via GitHub Actions on both `ubuntu-latest` (offline tests) and `macos-15` (J2 interpreter + compiled native binary).

## What changed?
1. `tests/phase4_differential.py`:
   - **F1**: Replaced unverified `J_FORCE_NATIVE` with true native compilation (`j2 build src/main.j2 -o build/dupe`), `--native-bin` support, execution with runtime capability `J2_ALLOW_FS=1`, and negative-control verification (fails when `J2_ALLOW_FS` is omitted).
   - **F2**: Formalized discovery-order grouping contract across J2 and the Python oracle; all test cases are strictly evaluated with `require_direct_match=True`. Added repeat-run byte-identity test.
   - **F3**: Added `verify_soundness()` independently asserting pairwise `read_bytes` byte identity across all group files and disjointness across groups.
   - **F4**: Upgraded failure preservation to capture full file contents as hex strings (no lossy 4KB truncation), empty directories, exit codes, and stderr diagnostics; verified roundtrip reproduction fidelity on >4KB files.
   - **F5**: Sanitized all file paths in `reproduce_from_failure` and `load_regression_fixtures` against directory traversal attacks (`..`, absolute paths, drive prefixes) and added fixture schema validation.
   - **F6**: Added `timeout=60` to all J2 subprocess invocations.
   - **F7, F8, F12**: Expanded seed corpus from 10 to 13 cases (added `.hidden` dotfiles, empty subdirectories, 1MB duplicate file pair, and trailing slash test). Captured stderr and return codes on error conditions. Added POSIX unreadable-file permission test.
   - **F9**: Added ground-truth hardcoded value assertions in `run_offline_tests()` for all 13 seed cases and 4 regression fixtures.
   - **F10**: Added collision-proof failure filenames using sanitized name, timestamp, PID, and counter.
   - **F11**: Expanded fuzzer to generate distinct same-size files, empty directories, and dotfiles; verified multi-seed reproducibility.
   - **F13**: Strengthened tree immutability check to verify byte content hash, `mtime_ns`, and `mode`.
2. `.github/workflows/phase4-correctness.yml`:
   - Added concurrency group with `cancel-in-progress: true`.
   - Added `timeout-minutes: 15` to prevent hanging CI runs.
   - Added `ubuntu-latest` offline job running `python3 tests/phase4_differential.py --offline`.
   - Pinned `python-version: '3.12'` across jobs.
   - Added exact J2 version assertion `test "$(j2 --version)" = "j2 0.1.0"`.
   - Added format verification with `j2 fmt -w src/*.j2` and `git diff --exit-code src/`.
   - Pre-compiled native binary with `j2 build src/main.j2 -o build/dupe`.
   - Ran differential matrix against the pre-compiled binary with `--native-bin build/dupe`.
   - Configured failure artifact preservation with `if-no-files-found: ignore`.
3. `.github/workflows/phase3-mvp.yml`:
   - Replaced unverified `J_FORCE_NATIVE=1` step with genuine native build `j2 build src/main.j2 -o build/dupe` and executed with `J2_ALLOW_FS=1`.
4. Documentation:
   - `docs/J2-API-0.1.0.md`: Documented verified native capabilities (`J2_ALLOW_FS=1`), symlink behavior (`fs.is_dir` follows links), sort limitations on nested arrays, and traversal ordering contract. Removed `J_FORCE_NATIVE`.
   - `docs/PHASE-4-CORRECTNESS.md`: Documented all 14 review finding resolutions and expanded acceptance criteria.

## What was discovered?
- `j2 build src/main.j2 -o build/dupe` produces an arm64 Mach-O native executable.
- Compiled J2 native binaries enforce capability restrictions via environment variables (`J2_ALLOW_FS=1`). `J_FORCE_NATIVE` was a non-existent env var.
- J2's `fs.is_dir` and `fs.is_file` follow symlinks.
- J2's `sort()` sorts primitive arrays only.
- Strict discovery-order matching between J2 and the oracle produces byte-identical dictionary JSON for all cases.

## What should the next agent avoid repeating?
- Do NOT alter Phase 3 J2 source files (`src/*.j2`) unless a real defect is discovered.
- Do NOT invoke J2 compiled binaries without `J2_ALLOW_FS=1` if filesystem access is needed.
- Do NOT assume J2 `sort()` can sort complex objects or tuples.
- Do NOT start performance benchmarking before reviewing T003/T004 specifications.

## Next task
T003 — Competitive/technical research consolidation into `docs/RESEARCH.md`.
Following T003: T004 (benchmark corpus specification and generator) -> T005 (interpreter/native baseline) -> T006 (automatic parallelism experiment).
