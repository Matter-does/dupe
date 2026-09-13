# T008 — CLI / Product Surface Polish

## Goal
Polish the `dupe` command-line and product surface so the application functions as a coherent, predictable, and professional CLI rather than a research prototype, while strictly preserving frozen Phase 3 core algorithms and established T005/T006/T007 evidence.

## Motivation & Value
1. **Discoverability & Professional UX:** The CLI provides clear, concise top-level help (`--help`, `-h`, `help`) detailing all available workloads (duplicate scanning, checksum inventory) and options.
2. **Deterministic Argument Parsing:** Both workloads (`dupe` and `dupe checksum`) handle arguments symmetrically, supporting flag placement before or after the target directory (`dupe <path> --json` and `dupe --json <path>`).
3. **Explicit Validation & Clean Error Discipline:** Missing paths, multiple root arguments, and invalid options fail deterministically with informative diagnostics rather than attempting invalid filesystem operations.
4. **Frozen Boundary Preservation:** All improvements are confined strictly to the CLI routing layer (`src/main.j2`) and workload interface (`src/checksum.j2`). Frozen Phase 3 modules (`src/scan.j2`, `src/hash.j2`, `src/group.j2`, `src/output.j2`) remain 100% untouched.

## Supported CLI Surface

### 1. Help Commands
```bash
dupe --help
dupe -h
dupe help
dupe checksum --help
dupe checksum -h
dupe checksum help
```

### 2. Duplicate Detection (Default Workload)
```bash
dupe <path>
dupe <path> --json
dupe --json <path>
```

### 3. Checksum Inventory (Secondary Workload)
```bash
dupe checksum <path>
dupe checksum <path> --json
dupe checksum --json <path>
```

## Argument Handling Contract
- **Argument Symmetry:** Both duplicate mode and checksum mode accept `--json` either before or after the path.
- **Strict Validation:** Supplying multiple paths or unexpected trailing arguments outputs an explicit error message and usage instructions.
- **Missing Path:** Invocations lacking a target path output clear usage instructions.
- **Nonexistent Paths:** Target paths that do not exist trigger J2's runtime filesystem failure (`RuntimeError` from `fs.list_dir`) and exit with a non-zero exit status.
- **Determinism:** JSON outputs remain compact, machine-readable, schema-stable, and byte-for-byte identical across equivalent invocations.

## Verification Matrix
- `tests/test_t008_cli_polish.py`: 20 unit and live J2 execution tests covering help flags, argument symmetry, determinism, validation, and error handling.
- `tests/verify_t008_polish.py`: Authoritative parity and CLI verification script asserting byte-for-byte identity between native binary and interpreter outputs on macOS Apple Silicon.
- `.github/workflows/t008-cli-polish.yml`: Dedicated GitHub Actions workflow executing formatting checks, full unit test suite, native build, parity verification, and artifact upload.
