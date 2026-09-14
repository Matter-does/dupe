# dupe

**J2-native filesystem intelligence engine**

`dupe` is a read-only filesystem analysis project written primarily in J2. It implements exact duplicate file detection and cryptographic checksum inventory workloads to study how a real-world, I/O- and compute-bound filesystem analysis pipeline behaves under J2's native compilation and execution model.

---

## Why this exists

Duplicate-file detection is a mature software domain with established utilities (e.g., dupeGuru, fclones). Rather than attempting to clone features such as deletion rules, media similarity, or custom cache daemons, `dupe` treats filesystem duplicate analysis as a disciplined, real-world benchmark workload.

Filesystem analysis presents a unique systems challenge: it combines OS directory traversal, metadata inspection, candidate reduction, sequential file reading, and cryptographic SHA-256 hashing. `dupe` investigates how cleanly these operations can be expressed as independent transformations in J2, and empirically evaluates what J2's native compilation and execution achieve on reproducible corpora.

---

## Why J2

Based on direct, reproducible evidence from this repository:

1. **Native Filesystem Access:** J2 provides built-in capability-gated filesystem primitives (`fs.list_dir`, `fs.read_bytes`, `fs.read_file`, `fs.metadata`, `fs.is_file`, `fs.is_dir`) that allow expressing traversal and inspection directly without C bindings or foreign function interfaces.
2. **Native Compilation:** J2 compiles pure source code (`src/main.j2`) directly into standalone Mach-O arm64 machine code (`j2 build`), eliminating bytecode interpreter dispatch overhead and accelerating compute-intensive hashing loops by up to 1.18x.
3. **Deterministic Behavior:** J2's standard data structures and deterministic iteration enable byte-for-byte identical output between interpreter execution and native machine code across all workloads.
4. **Engineering Value:** Developing `dupe` in J2 demonstrated how a declarative, functional-inspired language with capability sandboxing (`--allow-fs` / `J2_ALLOW_FS=1`) can structure a multi-stage data processing pipeline while preserving a 100% frozen core engine across CLI and desktop GUI interfaces.

---

## Architecture

The project maintains a strict, one-way dependency architecture:

```text
User
 │
 ├── CLI
 │    └── src/main.j2
 │
 └── GUI
      └── Python/Tk
           │
           ▼
      EngineAdapter
           │
           ▼
      J2 CLI / Engine
           │
           ▼
   scan → hash → group → output
```

For the checksum inventory workload:

```text
src/main.j2
    ↓
src/checksum.j2
    ↓
deterministic checksum ledger
```

### Architectural Responsibilities
- **Authoritative Engine (J2):** 100% of filesystem traversal, candidate filtering, SHA-256 hashing, duplicate grouping, and ledger calculation resides in J2 (`src/main.j2`, `src/checksum.j2`, `src/scan.j2`, `src/hash.j2`, `src/group.j2`, `src/output.j2`).
- **Presentation Layer (CLI & GUI):** The CLI (`dupe`) and lightweight desktop GUI (`python -m gui`) act strictly as presentation shells. The GUI invokes the engine via `EngineAdapter` and parses its standard JSON output, duplicating zero engine logic.
- **Verification Authority:** Correctness is established through automated differential fuzzing (`tests/phase4_differential.py`), an independent Python standard library `hashlib.sha256` oracle (`tests/test_t007_checksum_inventory.py`), native vs. interpreter parity checks, and GitHub Actions CI.

---

## Features

- **Exact Duplicate Detection:** Discovers regular files, prefilters candidates by file size (skipping unique sizes before reading bytes), computes SHA-256 digests for candidates, groups matching digests, and calculates reclaimable space.
- **Cryptographic Checksum Inventory:** Recursively enumerates all regular files and produces a sorted, deterministic SHA-256 inventory ledger with file sizes and total bytes.
- **Unified Command Router:** Dispatches workloads (`dupe PATH` vs. `dupe checksum PATH`), supports `--json` symmetrically before or after paths, provides context-aware `--help`, and fails cleanly with non-zero exit codes on invalid input.
- **Lightweight Desktop GUI:** Built with Python standard library `tkinter`/`ttk` (zero external pip dependencies). Features non-blocking asynchronous execution, metric summary cards, and scrollable results treeviews.
- **Dual Execution Modes:** Runs seamlessly via J2 interpreter (`j2 --allow-fs`) or standalone native binary (`build/dupe`).

---

## Demo

The canonical evaluator demonstration flow takes under 2 minutes:

```bash
# 1. Generate the deterministic demonstration corpus (8 files, 5,258 bytes)
python tests/demo_corpus.py --output demo_corpus

# 2. Run duplicate detection demo (CLI)
# Standalone native binary (macOS 15 Apple Silicon):
./build/dupe demo_corpus
# Or J2 interpreter:
j2 --allow-fs src/main.j2 demo_corpus

# 3. Run checksum inventory demo (CLI)
# Standalone native binary:
./build/dupe checksum demo_corpus
# Or J2 interpreter:
j2 --allow-fs src/main.j2 checksum demo_corpus

# 4. Launch Desktop GUI demonstration
python -m gui --target demo_corpus

# 5. Run automated demonstration verification
python tests/verify_t010_demo.py --native-bin build/dupe --output-dir artifacts/t010

# 6. Run full test suite (132 tests)
python -m unittest discover -s tests -v
```

---

## Verification

The repository enforces objective correctness across multiple independent gates:

- **Phase 4 Correctness:** 13 seed corpora and 4 regression fixtures tested against an independent Python reference model with 100% agreement.
- **T007 Checksum Inventory:** Comprehensive cryptographic validation against Python's `hashlib.sha256` oracle across all discovered regular files (22 tests in `tests/test_t007_checksum_inventory.py`).
- **T008 CLI Contract:** 20 automated tests in `tests/test_t008_cli_polish.py` verifying subcommand routing, argument handling, usage diagnostics, and error codes.
- **T009 GUI Shell:** 22 automated unit and adapter tests in `tests/test_t009_gui_shell.py` verifying background thread isolation, model transformation, and zero engine logic duplication.
- **T010 Deterministic Demo:** Fixed 8-file corpus ground truth (5 candidates, 2 duplicate groups, 456 reclaimable bytes, 5,258 total bytes) verified end-to-end (10 tests in `tests/test_t010_demo.py`).
- **T011 Package Integrity:** 8 automated packaging and boundary tests in `tests/test_t011_final_package.py`.
- **Native / Interpreter Parity:** Automated `cmp` assertions verify byte-for-byte identical stdout between native machine code and interpreter.
- **Independent SHA-256 Oracle:** J2 cryptographic output is validated against non-circular standard library hash calculations.

See [`docs/VALIDATION.md`](docs/VALIDATION.md) for the complete Claim-to-Evidence matrix and [`docs/FINAL_EVIDENCE.md`](docs/FINAL_EVIDENCE.md) for detailed test metrics.

---

## Platform Matrix

```text
AUTHORITATIVE J2 VALIDATION:
    macOS 15 Apple Silicon (aarch64-apple-darwin / arm64)
    Official J2 0.1.0 release compiler and native runtime

GENERAL GUI SHELL CODE:
    Standard Python 3.10+ / Tkinter compatibility
    Runs across macOS, Linux, and Windows where Python/Tk is installed
```

*Note:* Official J2 0.1.0 compiler binaries are distributed exclusively for macOS Apple Silicon. On other operating systems, the test suite cleanly detects the missing J2 binary and skips live J2 compiler tests while running 100% of Python, adapter, GUI, and reference model tests.

---

## Limitations

In the interest of rigorous scientific and engineering honesty:

1. **J2 0.1.0 Platform Availability:** J2 0.1.0 has only been compiled and released for Apple Silicon macOS. Linux, Windows, and Intel macOS compiler builds are not yet provided upstream.
2. **Single-Threaded Runtime in 0.1.0:** While J2 language specifications anticipate automatic loop parallelization, empirical measurements in T006 demonstrated that J2 0.1.0 emitted single-threaded native instructions (bounded <105% CPU). Standalone native compilation yields up to 1.18x speedup over the interpreter via machine code generation, but multi-core scaling was not observed in this release.
3. **Read-Only Safety Boundary:** `dupe` deliberately does not implement file deletion, symlinking, or filesystem modification. Destructive actions are outside the project charter.
4. **In-Memory Candidate Model & $O(N^2)$ Pairwise Filter (SEC-003):** Candidate grouping and size prefiltering are performed in-memory with pairwise candidate reduction in J2 exhibiting $O(N^2)$ worst-case characteristics on corpora with many identical file sizes. The engine is optimized for typical filesystem structures, not petabyte-scale out-of-core streaming deduplication; tested bounds demonstrate stable, bounded execution under practical workloads.
5. **GUI Display Server:** The Python/Tk GUI requires an active desktop window environment (Cocoa on macOS, X11/Wayland on Linux, DWM on Windows) for interactive usage, though all GUI logic and adapter models are 100% testable in headless CI.

---

## Final Status

- **Frozen Releases:** T001 through T010 completed, validated, and frozen.
- **Frozen Core Boundary:** `src/scan.j2`, `src/hash.j2`, `src/group.j2`, and `src/output.j2` preserved with zero modifications.
- **Historical Benchmarks:** `benchmarks/` and T005/T006 evidence preserved with zero modifications.
- **Milestone T011:** Final submission packaging, comprehensive documentation, and automated release verification complete.
- **Milestone T012:** Post-release defensive security hardening complete (SEC-001 through SEC-005 remediated and verified with zero frozen core diffs).
- **Release Verdict:** Engineering state is frozen at the final verified commit upon passing the authoritative CI release gate.
