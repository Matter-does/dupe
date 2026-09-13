# Current Task

**Task:** T008 — CLI / Product Surface Polish  
**Status:** Implementation Complete — Ready for Adversarial Review  

## Summary of Implementation

T008 elevates the user-facing CLI contract of `dupe` into a professional, predictable, and script-friendly interface while preserving 100% of frozen Phase 3 core duplicate algorithms and established T005/T006/T007 benchmark and correctness evidence:

### 1. Help & Usage Experience
- **Top-Level Guidance:** `--help`, `-h`, and `help` display a clean, terminal-friendly guide showing available workloads (`duplicate` and `checksum`) and options (`--json`).
- **Checksum Guidance:** `dupe checksum --help`, `-h`, and `help` provide dedicated sub-command documentation while preserving backward-compatible signature keywords (`dupe checksum PATH`).

### 2. Argument Symmetry & Predictability
- **Symmetric Option Placement:** `--json` can be supplied before or after the target directory symmetrically for both workloads:
  - `dupe <path> --json` == `dupe --json <path>`
  - `dupe checksum <path> --json` == `dupe checksum --json <path>`
- Outputs are byte-for-byte identical across both arrangements.

### 3. Explicit Validation & Error Discipline
- **Missing Path:** Invocations lacking a target path output clear usage guidance (`dupe PATH [--json]`).
- **Multiple Roots / Unexpected Arguments:** Supplying multiple paths (e.g. `dupe /dir1 /dir2` or `dupe checksum /dir1 /dir2`) or invalid options outputs explicit error messages rather than silently ignoring extra arguments.
- **Failure Preservation:** Nonexistent or unreadable paths propagate J2 filesystem runtime errors (`RuntimeError` from `fs.list_dir`) resulting in a non-zero exit status.

### 4. Output Stability & Determinism
- JSON outputs for both duplicate analysis and checksum inventory remain compact, machine-readable, schema-stable, and byte-for-byte identical across repeated runs.
- Human-readable outputs maintain clear headings and formatting.

## Verification Evidence
- `tests/test_t008_cli_polish.py`: 20 tests (9 offline unit tests PASS, 11 live J2 tests cleanly SKIPPED locally with explicit `LIVE_J2_TESTS_SKIPPED`).
- Full local suite: **92 tests** (69 PASS, 23 SKIPPED locally).
- Phase 4 offline self-tests: **PASS** (`tests/phase4_differential.py --offline`).
- CI workflow added: `.github/workflows/t008-cli-polish.yml` targeting macOS 15 Apple Silicon arm64 with pinned J2 0.1.0.
- Parity script added: `tests/verify_t008_polish.py`.

## Non-Negotiable Boundaries Audit
- `src/scan.j2`: UNTOUCHED (0 diff lines).
- `src/hash.j2`: UNTOUCHED (0 diff lines).
- `src/group.j2`: UNTOUCHED (0 diff lines).
- `src/output.j2`: UNTOUCHED (0 diff lines).
- `benchmarks/results/t005_*`: UNTOUCHED (0 diff lines).
- `benchmarks/results/t006_*`: UNTOUCHED (0 diff lines).
- `benchmarks/t006/*`: UNTOUCHED (0 diff lines).
