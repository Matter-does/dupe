# Current Task

**Task:** T010 — Demonstration / Integration Polish  
**Status:** Implementation Complete — Ready for Adversarial Review  

## Summary of Implementation

T010 turns the already-working `dupe` system into a clean, deterministic, hackathon-demonstration-ready product surface without changing the underlying engine algorithms or reopening previously frozen milestones:

### 1. Representative Demonstration Corpus (`tests/demo_corpus.py`)
- Compact, multi-topology, deterministic test corpus (8 regular files, 1 empty directory, nested subdirectories, total size: 5,258 bytes).
- Ground truth:
  - Exact Duplicate Scan: 8 files scanned, 5 candidates (100B and 256B), 2 duplicate groups, 456 reclaimable bytes.
  - Checksum Inventory: 8 files, 5,258 bytes, 100% verified SHA-256 digests.
- Callable via CLI (`python tests/demo_corpus.py --output demo_corpus`) and as a library (`create_demo_corpus`).

### 2. GUI Demonstration Polish (`gui/app.py`)
- Engine Resolution Badge: Displays `Engine: J2 Native (build/dupe)` vs `Engine: J2 Interpreter (j2)` in the window header to visually prove that the GUI is a presentation shell delegating to J2.
- Interactive Demo Loading: `Load Demo Corpus` button automatically loads or generates `demo_corpus` with one click.
- Workload Guidance: Dynamic description label explaining what each workload does when selected.
- Zero Analysis Logic Added: 100% pure presentation wrapper delegating to `EngineAdapter`.

### 3. Demonstration Verification Harness (`tests/verify_t010_demo.py`)
- Authoritative end-to-end verification script executing:
  1. Deterministic demo corpus generation
  2. Native CLI duplicate scan
  3. Native CLI checksum inventory
  4. Native vs Interpreter parity (byte-for-byte exact JSON equality)
  5. Independent Python `hashlib.sha256` oracle verification across all entries
  6. GUI `EngineAdapter` live invocations and ViewModel parsing
  7. Structured portable artifact generation (`summary.md`, `provenance.json`, `demo_verification_result.json`) in `artifacts/t010/`.

### 4. Tests & CI
- `tests/test_t010_demo.py`: 10 tests (corpus determinism, tamper detection, view model ground truth parsing, GUI demo integration, live J2 execution).
- Full local test suite: **124 tests** (96 PASS, 28 cleanly SKIPPED locally with explicit markers).
- Phase 4 offline self-tests: **PASS** (`tests/phase4_differential.py --offline`).
- Dedicated CI workflow: `.github/workflows/t010-demo.yml` on macOS 15 Apple Silicon arm64 with pinned J2 0.1.0.

### 5. Documentation (`README.md`)
- Added comprehensive "Hackathon Demo (T010)" section detailing corpus generation, canonical duplicate and checksum commands, GUI usage, and verification reproduction.

## Non-Negotiable Boundaries Audit
- `src/scan.j2`: UNTOUCHED (0 diff lines).
- `src/hash.j2`: UNTOUCHED (0 diff lines).
- `src/group.j2`: UNTOUCHED (0 diff lines).
- `src/output.j2`: UNTOUCHED (0 diff lines).
- `benchmarks/`: UNTOUCHED (0 diff lines).
- `benchmarks/results/t005_*`: UNTOUCHED (0 diff lines).
- `benchmarks/results/t006_*`: UNTOUCHED (0 diff lines).
- T007, T008, T009 contracts & tests: UNTOUCHED & FULLY PRESERVED.
