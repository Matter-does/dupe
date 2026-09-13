# T011 — Final Submission Package Specification

## 1. Purpose
The purpose of T011 is to prepare `dupe` for final submission to the J2 Hackathon. It converts an already-proven, multi-milestone engineering project into a self-explaining, rigorously defensible, reproducible, and verifiable submission package.

T011 is **not** a new algorithm milestone. It answers the natural questions of an evaluator or judge:
- **"What is this?"** — A J2-native filesystem intelligence engine providing exact duplicate file detection and cryptographic checksum inventory workloads.
- **"Why J2?"** — To study how a real-world, I/O- and compute-bound filesystem analysis pipeline behaves under J2's native compilation and automatic parallelism model without requiring manual threading primitives.
- **"Show me."** — Canonical, deterministic CLI and GUI demonstrations against a small, multi-topology demonstration corpus.
- **"Can I reproduce it?"** — Under 2 minutes from a clean checkout on supported platforms with zero external dependencies.
- **"How do you know it is correct?"** — Phase 4 differential fuzzer gates, mathematical candidate ground truth, independent Python `hashlib.sha256` oracles, native/interpreter byte-for-byte parity checks, and GitHub Actions CI on macOS 15 Apple Silicon.

---

## 2. Scope
The scope of T011 is strictly bounded to documentation, validation registers, submission metadata, packaging, and CI automation:

1. **Evaluator-Facing Documentation:**
   - Primary entry point in `README.md` explaining the problem, J2 value, clean architectural separation, canonical demo commands, and honest platform limitations.
   - Comprehensive Claim → Evidence mapping in `docs/VALIDATION.md`.
   - Comprehensive evidence register in `docs/FINAL_EVIDENCE.md`.
   - Submission release audit checklist in `docs/SUBMISSION_CHECKLIST.md`.
2. **Authoritative CI Release Workflow:**
   - Dedicated workflow `.github/workflows/t011-final-release.yml` executing the full release gate on macOS 15 Apple Silicon arm64 with pinned J2 0.1.0.
   - Automated emission and upload of release evidence artifacts (`final_release_evidence.json`, `final_release_summary.md`).
3. **Packaging & Integrity Testing:**
   - Automated submission package validation test in `tests/test_t011_final_package.py`.
   - Release evidence synthesis script in `tests/verify_t011_final_release.py`.
4. **Durable Agent Metadata:**
   - Synchronize `agent/TODO.md`, `agent/CURRENT_TASK.md`, `agent/CHECKPOINT.md`, and `agent/HANDOFF.md`.

---

## 3. Non-Goals & Absolute Boundaries
The following boundaries are frozen and non-negotiable:

- **Frozen Phase 3 Engine:** DO NOT modify `src/scan.j2`, `src/hash.j2`, `src/group.j2`, or `src/output.j2` (0 diff lines).
- **Historical Benchmark Evidence:** DO NOT modify `benchmarks/`, T005 evidence, or T006 evidence (0 diff lines).
- **No Algorithm Redesigns:** Do not change duplicate grouping, candidate prefiltering, filesystem traversal, or SHA-256 computation.
- **No New Dependencies:** Zero external Python dependencies (`pip`); Python standard library `tkinter`/`ttk` remains the sole GUI technology.
- **No Heavyweight Systems:** No databases, cloud integrations, network servers, telemetry, authentication, or caching daemons.
- **No Unrelated Features:** No cancellation architecture (remains future work), no complex GUI re-architectures.
- **No Milestone Reopening:** T001 through T010 contracts, tests, and evidence remain frozen.

---

## 4. Submission Requirements
The final repository must contain:
1. Complete, executable, and formatted J2 source code (`src/*.j2`).
2. Lightweight, decoupled desktop GUI shell (`gui/`).
3. Deterministic demonstration corpus generator (`tests/demo_corpus.py`).
4. Full regression and differential correctness test suite (`tests/`).
5. Comprehensive documentation suite (`README.md`, `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/RESEARCH.md`, `docs/VALIDATION.md`, `docs/FINAL_EVIDENCE.md`, `docs/SUBMISSION_CHECKLIST.md`).
6. Authoritative GitHub Actions CI release workflows (`.github/workflows/t011-final-release.yml`).
7. Clean git working tree with zero untracked, transient, or machine-specific files.

---

## 5. Demonstration Requirements
The evaluator demonstration flow must be canonical, concise, and reproducible in under 2 minutes:

```bash
# 1. Generate deterministic demonstration corpus
python tests/demo_corpus.py --output demo_corpus

# 2. Run duplicate detection demo (CLI)
# Standalone native binary (macOS Apple Silicon):
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
```

---

## 6. Evidence Requirements
Objective correctness and performance evidence must be documented and verifiable:
- **J2 Version & Integrity:** Pinned J2 0.1.0 (`6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75`).
- **Differential Correctness:** 13 seed cases, 4 regression fixtures, 100% agreement with reference model (`tests/phase4_differential.py`).
- **Parity Guarantee:** 100% byte-for-byte identical JSON output between native compiled binary and J2 interpreter.
- **Cryptographic Ground Truth:** 100% agreement between J2 SHA-256 output and Python `hashlib.sha256` oracle across all discovered regular files.
- **Architectural Separation:** GUI shell uses `EngineAdapter` with zero duplicated scanning, hashing, or grouping logic.
- **Empirical Parallelism Evidence:** Documented in `docs/ARCHITECTURE.md` and `docs/RESEARCH.md` from controlled T005/T006 benchmarks on macOS Apple Silicon.

---

## 7. Reproducibility Requirements
A fresh evaluator cloning the repository on a supported runner (macOS 15 Apple Silicon arm64) must be able to:
1. Install pinned J2 0.1.0 in under 30 seconds via official distribution tarball.
2. Compile standalone native binary via `j2 build src/main.j2 -o build/dupe`.
3. Run the full test suite (`python3 -m unittest discover -s tests -v`) with 100% passing tests.
4. Run the end-to-end verification harness and receive `VERDICT: PASS`.

---

## 8. Exit Criteria
T011 is complete when:
1. `agent/tasks/T011-final-package.md` authored and committed.
2. `README.md` audited and finalized as the primary evaluator portal.
3. `docs/VALIDATION.md` created with complete Claim → Evidence mapping.
4. `docs/FINAL_EVIDENCE.md` created with all empirical and cryptographic metrics.
5. `docs/SUBMISSION_CHECKLIST.md` created and 100% verified.
6. `tests/test_t011_final_package.py` created and passing.
7. `tests/verify_t011_final_release.py` created and operational.
8. `.github/workflows/t011-final-release.yml` created and passing green on macOS 15 Apple Silicon arm64.
9. Frozen-core boundary verified clean (`git diff 630eb1f... -- src/scan.j2 src/hash.j2 src/group.j2 src/output.j2 benchmarks/` is empty).
10. Agent state files synchronized (`TODO.md`, `CURRENT_TASK.md`, `CHECKPOINT.md`, `HANDOFF.md`).
11. Antigravity final adversarial self-critic review passed with verdict `PASS`.
