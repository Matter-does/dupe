# Current Task

**Task:** T009 — Lightweight GUI Shell Over the Existing dupe Engine  
**Status:** Implementation Complete — Ready for Adversarial Review  

## Summary of Implementation

T009 provides a clean, responsive, and lightweight desktop GUI shell over the existing `dupe` filesystem intelligence engine without duplicating analysis logic or disturbing frozen Phase 3 algorithms:

### 1. Architectural Separation
- **GUI View (`gui/app.py`):** Tkinter/ttk desktop interface with native directory picker, workload mode selection, action triggers, status feedback, summary metric cards, and hierarchical/tabular result treeviews.
- **Engine Adapter (`gui/adapter.py`):** Encapsulates command line construction conforming to the T008 contract (`dupe <path> --json`, `dupe checksum <path> --json`), non-blocking asynchronous execution (`threading.Thread`), exit-code, stdout, and stderr capture, and established JSON parsing.
- **View Models (`gui/view_models.py`):** Decoupled data representations (`DuplicateViewModel`, `ChecksumViewModel`) providing human-readable number and byte formatters.
- **Zero Analysis Reimplementation:** 100% of discovery, file filtering, hashing, duplicate grouping, checksum computing, and deterministic ordering remain inside the J2 engine.

### 2. Supported Workload Workflows
- **Exact Duplicate Scan:** Displays high-level summary cards (Files Scanned, Hash Candidates, Duplicate Groups, Reclaimable Space) and an expandable hierarchical tree showing duplicate file clusters and individual member paths.
- **Checksum Inventory:** Displays summary metrics (Total Files, Total Bytes, Ledger Status) and a structured table of files with SHA-256 digests.

### 3. UI Responsiveness & Error Handling
- **Non-blocking Execution:** The engine is invoked on a background daemon thread, with thread-safe UI updates dispatched via `root.after()`. The UI never freezes during scans.
- **Error Surfacing:** Nonexistent paths, permission errors, and malformed outputs display a prominent error banner with the exact process exit code and stderr diagnostics.

## Verification Evidence
- `tests/test_t009_gui_shell.py`: 22 tests (10 adapter unit tests, 3 view-model tests, 6 headless GUI component tests, 3 live integration tests cleanly skipped locally when J2 is unavailable).
- Full local test suite: **114 tests** (88 PASS, 26 cleanly SKIPPED locally with explicit markers).
- Phase 4 offline self-tests: **PASS** (`tests/phase4_differential.py --offline`).
- Native verification script: `tests/verify_t009_gui.py`.
- Dedicated CI workflow: `.github/workflows/t009-gui-shell.yml` on macOS 15 Apple Silicon arm64 with J2 0.1.0.

## Non-Negotiable Boundaries Audit
- `src/scan.j2`: UNTOUCHED (0 diff lines).
- `src/hash.j2`: UNTOUCHED (0 diff lines).
- `src/group.j2`: UNTOUCHED (0 diff lines).
- `src/output.j2`: UNTOUCHED (0 diff lines).
- `benchmarks/results/t005_*`: UNTOUCHED (0 diff lines).
- `benchmarks/results/t006_*`: UNTOUCHED (0 diff lines).
- `benchmarks/t006/*`: UNTOUCHED (0 diff lines).
- T007 & T008 CLI contracts: UNTOUCHED & FULLY PRESERVED.
