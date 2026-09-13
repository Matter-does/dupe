# T010 — Demonstration / Integration Polish Specification

## 1. Purpose
The purpose of T010 is to turn the already-working `dupe` filesystem intelligence engine into a clean, deterministic, hackathon-demonstration-ready product surface without altering the underlying engine algorithms or reopening previously frozen milestones.

T010 is **not** a new algorithm milestone. It builds on the existing capabilities:
- Frozen Phase 3 J2 duplicate detection engine
- Checksum inventory workload (T007)
- Unified CLI product surface (T008)
- Lightweight desktop Tk GUI shell (T009)
- Standalone native compilation (`j2 build`) & interpreter (`j2 run`) paths
- Differential correctness, parity checks, and benchmark evidence

T010 ensures that the system is effortless to demonstrate, reproduce, verify, and explain to judges and users.

---

## 2. Scope
The scope of T010 is strictly bounded to presentation, demonstration, integration verification, and documentation:

1. **Representative Demonstration Corpus (`tests/demo_corpus.py`):**
   - Provide a compact, deterministic, multi-topology demonstration corpus generator.
   - Visually obvious structure: duplicate clusters, files of differing sizes, nested directories, text/binary files, zero-byte file, and unique files.
   - Deterministic duplicate and checksum results with exact expected ground truth.

2. **GUI Demonstration Polish (`gui/app.py`):**
   - Display active J2 engine mode (`Native binary` vs `Interpreter`) in header/status to prove the GUI is a thin presentation shell calling J2.
   - Clarify workload descriptions and labels.
   - Enhance readability of summary cards and treeview/tabular results.
   - Improve initial state guidance and status feedback.

3. **Demonstration Verification Harness (`tests/verify_t010_demo.py`):**
   - End-to-end verification script executing the full demo contract.
   - Validates deterministic corpus generation, duplicate CLI, checksum CLI, native/interpreter parity, independent `hashlib.sha256` oracle agreement, and GUI adapter invocation.
   - Emits structured portable evidence to `artifacts/t010/`.

4. **Demonstration Test Coverage (`tests/test_t010_demo.py`):**
   - Unit and integration tests covering the demo corpus, expected duplicate/checksum demonstration outcomes, GUI presentation state, and adapter execution.

5. **CI Automation (`.github/workflows/t010-demo.yml`):**
   - Dedicated GitHub Actions workflow on macOS 15 Apple Silicon arm64 with pinned J2 0.1.0 verifying formatting, frozen-core boundaries, full test suite, native binary build, and T010 demo verification.

6. **Documentation & Agent State:**
   - Update `README.md` with a concise, prominent "Hackathon Demo" section.
   - Update agent tracking files (`agent/TODO.md`, `agent/CURRENT_TASK.md`, `agent/CHECKPOINT.md`, `agent/HANDOFF.md`).

---

## 3. Non-Goals & Hard Release Boundaries
The following release boundaries are absolute and non-negotiable:

- **Frozen Phase 3 Engine:** DO NOT modify `src/scan.j2`, `src/hash.j2`, `src/group.j2`, or `src/output.j2` (0 diff lines).
- **Historical Benchmark Evidence:** DO NOT modify `benchmarks/`, T005 results, or T006 results (0 diff lines).
- **No Algorithm Changes:** No new duplicate-detection algorithms, partial hashing, or custom hash algorithms.
- **No Parallelism/Concurrency Changes:** No manual thread pools, multiprocessing redesigns, or runtime concurrency tampering.
- **No New External Dependencies:** Zero third-party Python packages (`pip`). Standard library `tkinter`/`ttk` remains the sole GUI technology.
- **No Storage/Network Layers:** No databases, caching daemons, cloud services, or network calls.
- **No Cancellation Architecture:** Cancellation remains future work as recorded in T009 P3 findings.
- **Preserve Prior Milestones:** T005, T006, T007, T008, and T009 contracts, tests, and behaviors remain fully preserved.

---

## 4. Demonstration Contract

The demonstration experience communicates two distinct, compelling workload stories powered by the authoritative J2 engine:

### 4.1 Workload Story A — Exact Duplicate Detection
```text
Input Corpus (demo_corpus)
         ↓
Filesystem Discovery & Safe Metadata (8 files)
         ↓
Candidate Reduction by File Size (5 candidates; 3 unique sizes filtered out)
         ↓
Exact SHA-256 Hashing of Candidates
         ↓
Duplicate Group Clustering (2 duplicate groups)
         ↓
Reclaimable Bytes Calculation (456 bytes reclaimable)
         ↓
Deterministic Output (human-readable or JSON)
```

### 4.2 Workload Story B — Checksum Inventory
```text
Input Corpus (demo_corpus)
         ↓
Filesystem Discovery & Enumeration (8 regular files)
         ↓
Full Content Read & SHA-256 Digest Computation
         ↓
Deterministic Ledger Synthesis (5,258 total scanned bytes)
         ↓
Complete Verifiable Audit Trail (human-readable or JSON)
```

### 4.3 CLI Demonstration Surface
Conforms strictly to the established T008 CLI contract:
- Duplicate scan (human-readable):
  ```bash
  dupe demo_corpus
  ```
- Duplicate scan (compact JSON):
  ```bash
  dupe demo_corpus --json
  ```
- Checksum inventory (human-readable):
  ```bash
  dupe checksum demo_corpus
  ```
- Checksum inventory (JSON):
  ```bash
  dupe checksum demo_corpus --json
  ```
- Help guidance:
  ```bash
  dupe --help
  dupe checksum --help
  ```

### 4.4 GUI Demonstration Surface
Conforms strictly to the T009 GUI architecture:
```bash
python -m gui
python -m gui --target demo_corpus --workload duplicate
python -m gui --target demo_corpus --workload checksum
```
- Presentation shell strictly delegating to `EngineAdapter`.
- Indeterminate background progress indicator ensures non-blocking UI.
- Displays resolved engine execution mode (`Native binary` or `Interpreter`).
- Visually separates summary cards, duplicate clusters, and checksum ledger tables.

### 4.5 Native vs Interpreter Parity
Where standalone native compilation is available (macOS 15 Apple Silicon):
- Native execution: `J2_ALLOW_FS=1 ./build/dupe ...`
- Interpreter execution: `j2 --allow-fs src/main.j2 ...`
- Output requirement: Byte-for-byte exact equality between native and interpreter JSON output.

### 4.6 Representative Demonstration Corpus Ground Truth
The demo corpus generated by `tests/demo_corpus.py` defines fixed, deterministic expectations:
- **Files (8 regular files):**
  1. `documents/report_draft.txt` (100 B, text)
  2. `documents/report_final.txt` (100 B, duplicate of `report_draft.txt`)
  3. `archive/old_backup/report_backup.txt` (100 B, duplicate of `report_draft.txt`)
  4. `images/banner.raw` (256 B, binary)
  5. `images/banner_copy.raw` (256 B, duplicate of `banner.raw`)
  6. `archive/system.iso` (4096 B, unique binary)
  7. `notes/meeting_notes.md` (350 B, unique text)
  8. `zero_byte.dat` (0 B, zero-byte file)
- **Directories:** Includes empty directory `empty_dir/` and nested directories `archive/old_backup/`, `documents/`, `images/`, `notes/`.
- **Expected Duplicate Scan Metrics:**
  - Files scanned: `8`
  - Hash candidates: `5`
  - Duplicate groups: `2`
    - Group 1: 100 bytes, 3 files (`report_draft.txt`, `report_final.txt`, `report_backup.txt`), reclaimable: `200` bytes
    - Group 2: 256 bytes, 2 files (`banner.raw`, `banner_copy.raw`), reclaimable: `256` bytes
  - Total reclaimable bytes: `456` bytes
- **Expected Checksum Inventory Metrics:**
  - Total regular files: `8`
  - Total bytes: `5,258` bytes
  - All SHA-256 digests mathematically match Python `hashlib.sha256`.

---

## 5. Evidence Requirements
T010 completion requires objective, machine-verifiable evidence:

1. **Deterministic Corpus Evidence:**
   - Independent verification that repeated generation produces byte-identical files and directory trees.
2. **CLI Contract Evidence:**
   - Both `duplicate` and `checksum` commands execute cleanly against the demo corpus.
3. **Parity Evidence:**
   - Byte-for-byte JSON identity between native binary and interpreter execution on macOS Apple Silicon.
4. **Oracle Evidence:**
   - Python `hashlib.sha256` oracle verifies all file digests emitted by the engine.
5. **GUI Presentation Evidence:**
   - EngineAdapter executes both workloads and verifies schema conformance without UI lockup.
6. **Machine-Readable Artifacts:**
   - `artifacts/t010/summary.md`
   - `artifacts/t010/provenance.json`
   - `artifacts/t010/demo_verification_result.json`

---

## 6. Reproducibility Requirements
A fresh checkout of `Matter-does/dupe` on a supported environment must be able to reproduce the demonstration and verification in under 2 minutes:

```bash
# 1. Generate representative demonstration corpus
python tests/demo_corpus.py --output demo_corpus

# 2. Run duplicate detection demo (CLI)
# If native binary built:
./build/dupe demo_corpus
# Or via J2 interpreter:
j2 --allow-fs src/main.j2 demo_corpus

# 3. Run checksum inventory demo (CLI)
./build/dupe checksum demo_corpus
# Or via J2 interpreter:
j2 --allow-fs src/main.j2 checksum demo_corpus

# 4. Launch GUI shell demo
python -m gui --target demo_corpus

# 5. Run full automated verification
python tests/verify_t010_demo.py --output-dir artifacts/t010
```

---

## 7. Exit Criteria
T010 is complete when all of the following conditions are met:

1. `agent/tasks/T010-demo.md` authored and committed.
2. Deterministic demo corpus generator implemented in `tests/demo_corpus.py`.
3. Presentation-only GUI polish implemented in `gui/app.py` with zero analysis logic duplicated.
4. Verification harness `tests/verify_t010_demo.py` created and passing.
5. Test suite `tests/test_t010_demo.py` created and passing; full test suite passes with zero regressions.
6. CI workflow `.github/workflows/t010-demo.yml` created and running successfully on `macos-15` (arm64).
7. `README.md` updated with "Hackathon Demo" section.
8. Frozen-core boundary check is 100% clean (`git diff 03ba35f... -- src/scan.j2 src/hash.j2 src/group.j2 src/output.j2 benchmarks/` is empty).
9. Agent tracking documents updated (`TODO.md`, `CURRENT_TASK.md`, `CHECKPOINT.md`, `HANDOFF.md`).
10. Antigravity Red-Team adversarial self-critic review completed with verdict `PASS`.
