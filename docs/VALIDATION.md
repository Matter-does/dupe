# Validation Matrix

This document provides the authoritative mapping between technical claims made by `dupe` and the objective verification evidence present in the repository and CI runs.

---

## 1. Core Technical Claims & Evidence Mapping

| Claim | Technical Statement | Verification Evidence | Evidence Location |
|---|---|---|---|
| **J2 Pinned Version** | Official J2 0.1.0 release tarball is cryptographically pinned and verified before execution. | CI checks SHA-256 hash `6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75` prior to extraction. | `.github/workflows/t011-final-release.yml`, `docs/J2-API-0.1.0.md` |
| **Duplicate Workload Correctness** | J2 duplicate detection correctly discovers files, prefilters by size, hashes candidates, groups duplicates, and calculates reclaimable bytes. | Differential fuzzer passes 13 seeds + 4 regressions. Deterministic demo corpus confirms 8 files, 5 candidates, 2 groups, 456 reclaimable bytes. | `tests/phase4_differential.py`, `tests/test_t010_demo.py`, `.github/workflows/phase4-correctness.yml` |
| **Checksum Workload Correctness** | J2 checksum inventory enumerates all regular files and computes exact SHA-256 digests matching standard cryptographic standards. | 100% match against independent Python `hashlib.sha256` oracle across all discovered regular files in CI. | `tests/test_t007_checksum_inventory.py`, `.github/workflows/t007-checksum-inventory.yml` |
| **Native Compilation** | `src/main.j2` compiles to a standalone Mach-O arm64 native executable via `j2 build`. | `j2 build src/main.j2 -o build/dupe` builds cleanly; executes with `J2_ALLOW_FS=1`. | `.github/workflows/t011-final-release.yml`, `tests/test_t008_cli_polish.py` |
| **Interpreter Execution** | `src/main.j2` runs directly via J2 interpreter with `--allow-fs`. | `j2 --allow-fs src/main.j2 [workload] [path]` executes and produces identical results. | `tests/test_t008_cli_polish.py`, `tests/test_t010_demo.py` |
| **Native/Interpreter Parity** | Standalone native binary and J2 interpreter produce byte-for-byte identical output. | Direct `cmp` verification in CI and automated parity assertions in test suite across both duplicate and checksum modes. | `tests/test_t010_demo.py`, `tests/test_t007_checksum_inventory.py`, `.github/workflows/t010-demo.yml` |
| **Unified CLI Surface** | Unified CLI router dispatches `duplicate` and `checksum` workloads, handles `--json` symmetrically, provides `--help`, and fails cleanly on errors. | Automated CLI test suite verifies option permutations, subcommand dispatch, usage messages, invalid path error codes, and stderr diagnostics. | `tests/test_t008_cli_polish.py`, `.github/workflows/t008-cli-polish.yml` |
| **Decoupled GUI Shell** | Desktop GUI wraps CLI engine without duplicating scanning, hashing, or grouping logic. | Unit and adapter tests mock process execution, verify JSON parsing, view-model projection, asynchronous threading, and UI states. | `tests/test_t009_gui_shell.py`, `gui/adapter.py`, `gui/view_models.py` |
| **Deterministic Demo** | Canonical demo corpus is generated deterministically and produces identical results on every run. | Deterministic corpus generator produces 8 files and 5,258 bytes; verification harness validates results against exact ground truth. | `tests/demo_corpus.py`, `tests/verify_t010_demo.py`, `tests/test_t010_demo.py` |
| **Frozen Phase 3 Core** | Frozen Phase 3 engine files (`scan.j2`, `hash.j2`, `group.j2`, `output.j2`) and benchmarks remain untouched. | CI and release scripts assert `git diff <baseline> -- src/scan.j2 src/hash.j2 src/group.j2 src/output.j2 benchmarks/` has 0 lines. | `.github/workflows/t011-final-release.yml`, `tests/test_t011_final_package.py` |
| **Zero Milestone Regressions** | All preceding milestones (T001–T010) remain fully green and operational. | CI workflows for Phase 4, T007, T008, T009, T010, and J2 probes pass cleanly. | `.github/workflows/` |

---

## 2. Evidence Verification Hierarchy

Every claim in the project adheres to the evidence hierarchy defined in `docs/RESEARCH.md`:

```text
Grade A: Verified Fact (primary official J2 docs, runtime probes, passing CI tests)
Grade B: Strongly Supported (multiple authoritative external sources agree)
Grade C: Reasonable Inference (solid deduction from systems principles)
Grade D: Experimental Hypothesis (must be tested and measured)
Grade E: Unknown / Unverified (never relied upon or claimed)
```

All 11 claims in the table above are **Grade A: Verified Facts**, backed by automated tests, machine-readable verification harnesses, and passing GitHub Actions CI runs on macOS 15 Apple Silicon.
