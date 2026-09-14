# T012 — Security Hardening Specification

**Project:** `Matter-does/dupe`  
**Milestone:** T012 — Post-Release Security Hardening  
**Baseline Commit:** `bd2f8c9c27822dbde1133a6ab93256c09e7be677`  
**Previous Security Assessment:** `SECURITY PASS WITH HARDENING`  
**Authoritative Engine:** J2 0.1.0  
**Classification:** Post-Release Security Hardening  

---

## 1. Purpose

The purpose of T012 is to execute a rigorous, defensive security hardening milestone for `dupe`. It remediates five actionable findings identified in the baseline security assessment while strictly preserving the frozen J2 computation core, existing CLI/GUI contracts, native/interpreter parity, benchmark evidence, and historical frozen milestones.

---

## 2. Findings Scope

Remediation is strictly bounded to the following five findings:

| Identifier | Severity | Title | Affected Subsystems | Target Remediation State |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-001** | Medium | Type-invalid engine JSON crashes GUI | `gui/adapter.py`, `gui/view_models.py`, `gui/app.py` | FIXED |
| **SEC-002** | Low | Misleading "J2 Native" badge when engine missing | `gui/adapter.py`, `gui/app.py` | FIXED |
| **SEC-003** | Low | $O(N^2)$ duplicate candidate/grouping cost | `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, tests | MITIGATED & DOCUMENTED LIMITATION |
| **SEC-004** | Low | `--clean` symlinked target deletion risk | `tests/demo_corpus.py` | FIXED |
| **SEC-005** | Low | Unbounded engine stdout buffering | `gui/adapter.py` | FIXED |

---

## 3. Explicit Non-Goals & Hard Boundaries

1. **No Engine Redesign:** Core Phase 3 J2 analysis engines (`src/scan.j2`, `src/hash.j2`, `src/group.j2`, `src/output.j2`) remain 100% frozen.
2. **No Reopening Historical Milestones:** T001 through T011 remain frozen and completed.
3. **No Unrelated Features:** No new CLI commands, no network services, telemetry, authentication, external databases, cloud infrastructure, or third-party Python dependencies.
4. **No Speculative Rewrites:** SEC-003 is mitigated through bounded testing and explicit architectural documentation without altering frozen J2 algorithms.
5. **No Destructive Operations in GUI:** The GUI remains strictly read-only.
6. **Immutable T011 Baseline:** The original T011 release commit (`bd2f8c9c27822dbde1133a6ab93256c09e7be677`) remains immutable.

---

## 4. Remediation Specifications

### SEC-001: Type-Invalid Engine JSON Crashes GUI (Medium)
- **Problem:** Schema validation in `gui/adapter.py` validated dictionary keys and list types, but failed to validate scalar types (e.g. `files_scanned`, `size`, `reclaimable_bytes`, `sha256`). When `gui/view_models.py` applied conversions (`int()`, `str()`), shape-valid but type-invalid engine output raised uncaught `ValueError` on the Tkinter main thread.
- **Remediation:**
  1. Strengthen `_validate_schema()` in `gui/adapter.py`:
     - Verify counts and byte sizes are non-negative strict integers (`isinstance(x, int) and not isinstance(x, bool) and x >= 0`).
     - Verify duplicate group file lists are non-empty lists of strings.
     - Verify `hash` in duplicate groups and `sha256` in checksum entries are exactly 64 lowercase hexadecimal characters.
     - Verify checksum `schema_version` is a positive integer.
  2. Ensure malformed engine payloads produce `EngineResult(success=False, error_message="Invalid schema: ...")` without raising uncaught exceptions.
  3. Wrap ViewModel construction in `gui/app.py` with defensive exception handling, displaying the error banner, resetting metrics, clearing the treeview, and ensuring `is_running = False` with interactive controls re-enabled.

### SEC-002: Misleading "J2 Native" Badge When Engine Is Missing (Low)
- **Problem:** `resolve_engine_mode()` in `gui/adapter.py` fell back to returning `"native"` if `self.native_bin` was configured, even when the executable did not exist or was not executable.
- **Remediation:**
  1. If native binary exists and is executable (`has_native_binary()`): return `"native"`.
  2. Else if J2 interpreter exists and is executable (`has_j2_interpreter()` and `main_j2.is_file()`): return `"interpreter"`.
  3. Else: return `"unavailable", []`.
  4. In `gui/app.py`, render `Engine: Unavailable` when the mode is `"unavailable"`.
  5. If `run_analysis()` is invoked when mode is unavailable, fail closed with a clean `EngineResult(success=False)`.

### SEC-003: $O(N^2)$ Duplicate Candidate/Grouping Cost (Low)
- **Problem:** Pairwise size candidate reduction and duplicate group clustering in J2 exhibit $O(N^2)$ worst-case complexity on metadata-heavy corpora with many files of identical sizes.
- **Remediation:**
  1. Preserve frozen Phase 3 J2 code without speculative rewriting.
  2. Document the algorithmic limitation, profile boundaries, and memory characteristics in `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, and `README.md`.
  3. Implement bounded scalability tests against controlled corpora verifying deterministic completion within safe resource limits.

### SEC-004: `--clean` Symlinked Target Deletion Risk (Low)
- **Problem:** `tests/demo_corpus.py` called `Path(target_dir).resolve()` before `shutil.rmtree()`, which could follow symlinks or directory junctions and delete files outside the intended path.
- **Remediation:**
  1. Inspect the raw user-specified path *before* resolution.
  2. Detect symlinks or reparse points (using `os.path.islink`, `Path.is_symlink`, and Windows reparse attributes).
  3. If the target itself is a symlink or reparse point, abort cleanup immediately with a clear refusal message.
  4. Never follow links for recursive deletion.

### SEC-005: Unbounded Engine Stdout Buffering (Low)
- **Problem:** `subprocess.run(..., capture_output=True)` buffered engine stdout entirely into memory before schema validation, allowing a runaway or hostile process to cause memory exhaustion.
- **Remediation:**
  1. Replace unbounded collection with chunked streaming via `subprocess.Popen`.
  2. Enforce a configurable default security limit of 16 MiB (`16 * 1024 * 1024` bytes), overridable via `DUPE_MAX_OUTPUT_BYTES`.
  3. If stdout exceeds the limit, terminate/kill the child process, discard buffers, and fail closed with `EngineResult(success=False, error_message="Engine stdout exceeded maximum allowed limit...")`.

---

## 5. Acceptance Criteria

Every remediation must satisfy:
1. **Deterministic Reproduction Test:** Explicit test case demonstrating the vulnerability or failure condition.
2. **Implementation Fix:** Targeted, minimal code change addressing the root cause.
3. **Regression Test:** Test ensuring the fix permanently prevents recurrence.
4. **Zero Unrelated Behavior Change:** 100% pass on existing test suite (132 tests) and Phase 4 differential correctness fuzzer.
5. **Security Verification Evidence:** Machine-readable artifacts generated in `artifacts/security/` and logged in the evidence register.

---

## 6. Release Model

- The T011 final release (`bd2f8c9c27822dbde1133a6ab93256c09e7be677`) remains immutable.
- T012 is a subsequent security-hardening engineering milestone.
- All evidence artifacts are generated into `artifacts/security/` and validated by automated CI (`.github/workflows/t012-security.yml`).
