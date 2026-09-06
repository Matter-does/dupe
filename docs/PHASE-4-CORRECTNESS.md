# Phase 4 — Differential Correctness & Regression

**Status:** COMPLETE (Hardened against independent adversarial review F1–F14)  
**Prerequisite:** Phase 3 MVP complete  
**Goal:** independently verify `dupe` correctness across generated file trees, edge cases, and execution modes (Python oracle, J2 interpreter, compiled J2 native binary).

## Acceptance gates

- [x] Independent Python oracle implemented with independent byte-identity soundness checker (F3).
- [x] Seed corpus covers 13 deterministic edge cases, including dotfiles, empty subdirectories, and 1MB duplicate files (F7, F8, F12).
- [x] Strict direct equality (`require_direct_match=True`) enforced across all cases under a frozen traversal and first-discovery grouping contract (F2).
- [x] Genuine native compilation (`j2 build src/main.j2 -o build/dupe`) executed and verified with `J2_ALLOW_FS=1`; unverified `J_FORCE_NATIVE` eradicated (F1).
- [x] Interpreter output matches oracle on every case.
- [x] Native binary output matches oracle on every case.
- [x] Interpreter output equals native binary output on every case.
- [x] Regression corpus retained in CI (`tests/regressions/fixtures/`) with schema validation and path traversal sanitization (F5).
- [x] Full-fidelity failure preservation and reproduction preserving exact file contents, empty directories, exit codes, and diagnostics without truncation (F4).
- [x] Strict offline self-tests with ground-truth value assertions running locally on dev machines and in CI on `ubuntu-latest` (F9, F10).
- [x] Hard subprocess timeouts (60s) and workflow timeouts (15m) preventing hangs on symlink loops or deep recursions (F6).

## Review findings and resolutions (F1–F14)

1. **F1 (Critical — Native gate)**: Replaced no-op `J_FORCE_NATIVE` with genuine native compilation (`j2 build src/main.j2 -o build/dupe`) and verified `J2_ALLOW_FS=1` runtime capability grant.
2. **F2 (High — Direct matching contract)**: Formalized first-discovery grouping contract; oracle mirrors traversal order, enabling strict `require_direct_match=True` across all test cases.
3. **F3 (High — Soundness checker)**: Added `verify_soundness()` performing pairwise `read_bytes` byte-identity and disjointness checks across duplicate groups.
4. **F4 (High — Faithful failure preservation)**: Stored full file contents in hex manifests, tracked empty directories, recorded exit codes and stderr, and verified reproduction roundtrip fidelity on >4KB files.
5. **F5 (Medium-High — Path sanitization)**: Enforced strict path sanitization rejecting directory traversal escapes (`..`, absolute paths, drive prefixes) in both failure reproduction and fixture loading.
6. **F6 (Medium-High — Timeouts)**: Added 60s subprocess timeout to all `run_dupe` invocations and 15m timeout to CI workflows.
7. **F7 (Medium — Symlinks)**: Probed and documented symlink behavior (`fs.is_dir` follows symlinks); guarded against infinite loops with execution timeouts.
8. **F8 (Medium — Error handling & large files)**: Added 1MB duplicate file seed case, verified memory stability, and captured stderr diagnostics.
9. **F9 (Medium — Offline self-tests)**: Hardcoded exact ground-truth values for all seed and regression cases in `run_offline_tests()` so offline execution strictly verifies the oracle.
10. **F10 (Medium — CI hardening)**: Pinned Python 3.12, added exact `j2 --version == 0.1.0` assertion, added `ubuntu-latest` offline job, added `j2 fmt` format verification, collision-proofed failure report filenames, and set artifact upload to `if-no-files-found: ignore`.
11. **F11 (Medium — Fuzzer determinism & variety)**: Expanded fuzzer to generate distinct same-size files, empty directories, and dotfiles; verified multi-seed reproducibility.
12. **F12 (Low-Medium — Concrete edge cases)**: Added dotfiles, empty subdirectories, and size boundaries to seed corpus; verified `fmt()` builtin and `join_path` bare-name contract.
13. **F13 (Low — Immutability & freshness)**: Hardened immutability check to verify file hashes, modification times (`mtime_ns`), and file modes.
14. **F14 (Low — Documentation alignment)**: Aligned all documentation, handoffs, checkpoints, and README across Phase 3 and Phase 4.

## Seed corpus (13 cases)

1. empty tree
2. single file
3. identical files in one directory
4. identical files across nested directories
5. same-size different-content files
6. files differing by one byte
7. multiple empty files
8. multiple duplicate clusters
9. unusual filenames and nested paths
10. size-boundary cases, including zero-byte files
11. dotfiles discovery (`.hidden`, `.hidden-copy`)
12. empty subdirectories
13. large file duplicates (1 MB)

## Failure preservation & reproduction

Every discovered mismatch preserves:
- Seed and case description
- Exact file contents (hex-encoded) and empty directory paths
- Subprocess argv, exit code, stdout, and stderr
- Interpreter, native, and oracle output

A reproducer can be replayed using:
```bash
python3 tests/phase4_differential.py --reproduce <path-to-failure.json>
```

## Non-goals

Phase 4 does not benchmark performance, prove automatic parallelism, or add deletion behavior. Those belong to Phase 5 and Phase 6.
