# T009 — Lightweight GUI Shell Over the Existing dupe Engine

## 1. Objective
Provide a clean, lightweight, responsive desktop graphical interface (GUI shell) over the existing `dupe` filesystem intelligence engine. The GUI acts strictly as a presentation and interaction wrapper, enabling users to select target directories, choose between the two established workloads (Duplicate Detection and Checksum Inventory), trigger execution asynchronously without blocking the UI, and inspect structured results or errors—all while delegating 100% of discovery, hashing, analysis, and formatting logic to the authoritative underlying J2 engine.

---

## 2. Supported Platforms
- **Primary Supported & CI-Verified Target:** macOS 15 Apple Silicon (`arm64`, `aarch64-apple-darwin`), matching the pinned J2 0.1.0 native binary compilation and execution environment.
- **Cross-Platform Compatibility:** The Python GUI shell and engine adapter are implemented with standard Python 3 (`>=3.10`) and standard library `tkinter`/`ttk`, allowing the application to launch and run on macOS, Windows, and Linux. When J2 native or interpreter binaries are configured (or simulated), the shell behaves consistently across platforms.

---

## 3. Technology Selection & Justification
- **Chosen Technology:** Python 3 Standard Library `tkinter` with themed widgets (`ttk`).
- **Rationale & Trade-Offs:**
  1. **Zero External Dependencies:** `tkinter` is bundled with standard Python distributions on macOS, Windows, and Linux. It requires zero package installations (`pip`, `wheel`, or native bindings), eliminating dependency drift and heavyweight build pipelines.
  2. **Lightweight Footprint:** Instant startup time (<100ms) with minimal memory overhead (<30MB RAM), staying true to the "lightweight shell" mandate.
  3. **Native Desktop Controls:** Utilizes native OS directory dialogs (`filedialog.askdirectory`) and native window decorations.
  4. **Strict Architectural Decoupling:** Facilitates a clean separation between GUI widgets, view-model data representations, and an asynchronous `EngineAdapter`.
  5. **Headless & Offline Testability:** The engine adapter and view models are 100% testable in headless CI environments without requiring an active X11/Aqua display server.

---

## 4. Architecture & Boundaries

```text
+---------------------------------------------------------------+
|                    GUI Shell (gui/app.py)                     |
|  - Directory Picker (Entry + Native FileDialog)               |
|  - Workload Selector (Duplicate Scan vs Checksum Inventory)   |
|  - Action Controls ("Analyze" Button, Progress Indicator)     |
|  - Results Views (Summary Cards + Treeview / Ledger)          |
|  - Error Presentation (Error Banner + Diagnostics Dialog)     |
+---------------------------------------------------------------+
                               │
                               ▼ (Event callbacks / ViewModels)
+---------------------------------------------------------------+
|                 View Models (gui/view_models.py)              |
|  - DuplicateViewModel (files, candidates, groups, reclaimable)|
|  - ChecksumViewModel (files, bytes, entry items)              |
|  - Human-friendly byte and number formatters                  |
+---------------------------------------------------------------+
                               │
                               ▼ (Structured DTOs)
+---------------------------------------------------------------+
|                Engine Adapter (gui/adapter.py)                |
|  - Binary Resolution (native ./build/dupe or j2 interpreter)  |
|  - Command Construction (dupe PATH --json / dupe checksum...) |
|  - Non-blocking Execution (threading.Thread + Queue / lambda) |
|  - Process Exit-Code, Stdout, and Stderr Capture              |
|  - Engine JSON Schema Validation & Error Propagation          |
+---------------------------------------------------------------+
                               │
                               ▼ (Subprocess Invocation)
+---------------------------------------------------------------+
|                 Existing dupe CLI / J2 Engine                 |
|  - Native: J2_ALLOW_FS=1 ./build/dupe PATH [--json]           |
|    or:     J2_ALLOW_FS=1 ./build/dupe checksum PATH [--json]  |
|  - Interpreter: j2 --allow-fs src/main.j2 ...                 |
|  (Frozen Phase 3 duplicate detection + T007 checksum modules) |
+---------------------------------------------------------------+
```

### Strict Non-Duplication Contract
The GUI shell and adapter must NOT:
- Implement directory traversal or file walking.
- Filter files by size.
- Compute SHA-256 digests or checksums.
- Form duplicate clusters or calculate reclaimable space.
- Alter the established JSON schemas from Phase 3 or T007.

The existing J2 engine remains the sole source of analysis truth.

---

## 5. Supported Workloads
1. **Duplicate Detection (Default Workload):**
   - Dispatches: `dupe <path> --json` (or `dupe --json <path>`).
   - Parses established Phase 3 schema: `files_scanned`, `hash_candidates`, `duplicate_groups`, `reclaimable_bytes`.
   - Visualizes: High-level metric summary cards, expandable group list showing file paths and sizes per duplicate hash.
2. **Checksum Inventory (Secondary Workload):**
   - Dispatches: `dupe checksum <path> --json` (or `dupe checksum --json <path>`).
   - Parses established T007 schema: `summary.total_files`, `summary.total_bytes`, `entries` (`path`, `size`, `sha256`).
   - Visualizes: Summary totals, tabular ledger of discovered regular files with SHA-256 hashes.

---

## 6. User Experience & States

| State | Visual Behavior | Interactive Controls |
|---|---|---|
| **Idle / Initial** | Path input empty or default, results area blank, status: "Ready". | Analyze button enabled when path selected. Browse button active. Workload radio buttons active. |
| **Running** | Status: "Analyzing `<path>`... Please wait.", progress bar indeterminate active. | Analyze button disabled to prevent duplicate concurrent runs. Browse and Workload selectors disabled. |
| **Success** | Status: "Analysis complete in `<X.XX>`s", summary metrics displayed, Treeview populated with results. | Controls re-enabled. User can inspect rows or choose another directory. |
| **Error** | Status: "Analysis failed (exit code `<N>`)", prominent error message with stderr diagnostics, results area cleared. | Controls re-enabled immediately. Shell remains fully responsive and recoverable. |

---

## 7. Error Handling & Edge Cases
1. **Nonexistent Target Path:** J2 engine raises `RuntimeError` (`fs.list_dir failed`) and exits with non-zero status. Adapter captures `returncode != 0` and `stderr`, presenting an error dialog without crashing.
2. **Empty Directory Input:** User attempts to click "Analyze" without specifying a path. GUI prevents process spawn and highlights path input.
3. **Engine Non-Zero Exit:** Any failure (permission denied, unreadable directory) preserves exit code and raw stderr.
4. **Malformed JSON / Crash:** If engine output cannot be parsed as JSON, the adapter catches `JSONDecodeError` and surfaces the raw stdout/stderr as an integration error.
5. **UI Responsiveness:** Background subprocess execution ensures the Tkinter event loop remains 100% responsive without OS spinning beachballs or "Not Responding" window states.

---

## 8. Testing Strategy
- **Adapter Unit Tests (Offline / Mocked):**
  - Command line construction for duplicate and checksum modes with `--json`.
  - Process execution with mock outputs.
  - JSON schema validation for both workloads.
  - Exit code and stderr capture on failure.
  - Malformed JSON handling.
- **View Model Tests (Offline):**
  - Formatting human-readable sizes (B, KB, MB, GB).
  - Transformation of duplicate groups into hierarchical tree records.
  - Transformation of checksum entries into tabular records.
- **GUI Headless / Component Tests:**
  - State machine verification (Idle $\rightarrow$ Running $\rightarrow$ Success / Error).
  - Path input validation.
  - Workload toggle verification.
- **Live J2 Integration Tests:**
  - Real invocation of `j2` or `build/dupe` via `EngineAdapter` against controlled test corpus.
  - Symmetrical argument testing.
  - Skip discipline when J2 binary is not present (`LIVE_J2_TESTS_SKIPPED`).

---

## 9. CI & Objective Verification
- Dedicated workflow: `.github/workflows/t009-gui-shell.yml`.
- Runner: macOS 15 Apple Silicon (`macos-15`, `arm64`).
- Pinned J2 0.1.0 installation.
- Verification steps:
  1. Frozen file immutability audit (`src/scan.j2`, `src/hash.j2`, `src/group.j2`, `src/output.j2`).
  2. Full test suite execution including T009 adapter and view-model tests.
  3. Compilation of genuine native binary (`j2 build src/main.j2 -o build/dupe`).
  4. Live execution of GUI engine adapter against the genuine native binary.
  5. Headless Tkinter initialization and smoke validation.

---

## 10. Explicit Exclusions
T009 strictly excludes:
- Third-party heavy GUI frameworks (Electron, Qt/PyQt, WebViews, React).
- Destructive file deletion or manipulation actions.
- T010 demo presentation workflows or slide decks.
- T011 packaging, installer generation, or code signing.
- Performance experiments or benchmarking.
- Any modifications to frozen Phase 3 core algorithms or T005/T006/T007 benchmark data.
