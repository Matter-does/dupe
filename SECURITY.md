# Security Policy: dupe

## Security Boundary & Project Purpose

`dupe` is a read-only filesystem intelligence engine implemented in the J2 programming language with a Python/Tk presentation layer. The tool analyzes directory hierarchies to detect exact duplicate files and generate cryptographic SHA-256 ledgers.

The security model strictly decouples:
1. **Authoritative Engine (`src/*.j2`):** Processes filesystem structures and produces structured JSON output.
2. **Presentation Shell (`gui/` & CLI):** Decodes and renders engine results with fail-closed validation.

`dupe` is **strictly read-only** with respect to analyzed target directories. It does not modify, move, quarantine, or delete user files during duplicate detection or checksum inventory workloads.

## Threat Model

The threat model evaluates the defense of `dupe` and the host system against:
- **Hostile Target Directories:** Directories containing crafted filenames, deeply nested paths, cyclic structures, or symbolic links.
- **Engine Output Corruption:** Malformed or type-divergent JSON emitted by child processes or adversarial engine mocks.
- **Resource Exhaustion:** Unbounded subprocess stdout generation leading to memory denial-of-service.
- **Argument Injection:** Malicious metacharacters passed via directory paths.

## Filesystem Safety

- **Read-Only Invariant:** Scanning and hashing routines read files without altering metadata or data.
- **Hostile Path Handling:** Directory and file paths are passed as discrete arguments via `subprocess.run(..., shell=False)`. Shell metacharacters (`;`, `&`, `|`, `$`, `` ` ``, `"`) are never interpreted or expanded by a command shell.

## Symlink / Junction / Reparse Point Handling

- **Evaluation Invariant:** The J2 engine operates on regular files.
- **Demonstration / Test Cleanup Guard (SEC-004):** Test harnesses and corpus generation scripts inspect paths using `is_symlink_or_reparse()` prior to any cleanup operation (`--clean`). Destructive operations strictly refuse to operate on or traverse directory symlinks, junction points, or reparse targets.

## Output Bounding & Denial-of-Service Defense

- **Process Output Limit (SEC-005):** The presentation adapter enforces a strict 16 MiB (`DEFAULT_MAX_OUTPUT_BYTES = 16,777,216`) cap on subprocess stdout and stderr streams.
- **Fail-Closed Truncation:** If an engine process emits output exceeding this threshold, execution immediately fails closed before full decoding or JSON deserialization, preventing out-of-memory crashes.

## Malformed Engine Output Handling

- **Strict Scalar Validation (SEC-001):** The Python GUI `EngineAdapter` applies comprehensive schema checks (`_validate_schema`) before accepting engine output.
- **Type Invariants:** Metrics such as `files_scanned`, `hash_candidates`, `reclaimable_bytes`, `size`, and `total_bytes` must be non-negative integers; digests must conform to valid 64-character hexadecimal SHA-256 strings.
- **GUI Crash Prevention:** Type-invalid or structurally corrupt payloads trigger a visible error banner, clear the result view, and re-enable user controls without throwing unhandled Tkinter exceptions.

## Engine Availability & Introspection (SEC-002)

- The GUI inspects the host environment for genuine executable binaries (`build/dupe` or `j2`).
- When no valid engine binary is located, the header badge explicitly displays `Engine: Unavailable`. The UI never claims native or interpreter execution unless genuinely present.

## Scalability Boundary (SEC-003)

- The candidate grouping algorithm operates with an $O(N^2)$ comparison loop over candidate files sharing identical file sizes.
- The engine is verified for corpora up to 250,000 files. Datasets exceeding this scale are a documented boundary limitation.

## Dependency & Supply-Chain Invariants

- **Runtime Zero-Dependency Invariant:** `dupe` has **zero** third-party Python runtime dependencies. The GUI and CLI adapters rely exclusively on Python standard library modules (`tkinter`, `json`, `subprocess`, `hashlib`, `pathlib`).
- **Visual Evidence Tooling:** Image generation scripts (`tests/build_visual_evidence.py`) use Pillow (`PIL`) strictly as an offline development tool for rendering verification cards; Pillow is never loaded or required during production operation.

## Reporting Guidance

If you discover a security defect, invariant violation, or unexpected behavior in `dupe`, please report it by opening an issue on the GitHub repository:
https://github.com/Matter-does/dupe/issues

Please include:
1. Operating system and platform architecture (e.g., macOS 15 arm64, Ubuntu 24.04).
2. Exact command line or GUI action that triggered the issue.
3. Observed behavior versus expected invariant.
