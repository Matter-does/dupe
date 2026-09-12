# Current Task

**Task:** T007 — Reusable Filesystem Analysis Pass for Checksum Inventory  
**Status:** Implementation Complete & Locally Verified (Ready for Antigravity Deep-Critic & OpenCode Release Gate)

## Summary of Implementation & Results

### 1. Workload Architecture & Discovery Reuse
- **Module:** `src/checksum.j2` (additive module).
- **Core Functionality:** Implements the second read-only filesystem intelligence workload: **File Checksum Inventory**.
- **Discovery Reuse:** Directly calls `discover(root)` from `src/scan.j2`. Reuses the recursive, depth-first directory traversal and safe metadata inspection without duplicating filesystem traversal or metadata collection code.
- **Processing Kernel:** Iterates over discovered regular file records `[path, size]`, reads raw file bytes with `fs.read_bytes(path)`, computes exact cryptographic hashes with `hash.sha256(bytes)`, and records inventory entries `[path, size, digest]`.
- **Determinism:** Discovery order is guaranteed deterministic by `scan.j2` sorting child names at every directory level via `sort(fs.list_dir(path))`. Checksum inventory strictly preserves this order.

### 2. CLI Contract & Subcommand Dispatch
- **CLI Surface:**
  - `dupe <path> [--json]`: Reference exact-duplicate scan (100% frozen Phase 3 behavior preserved).
  - `dupe checksum <path>`: Checksum inventory human-readable text output.
  - `dupe checksum <path> --json`: Checksum inventory compact deterministic JSON.
  - `dupe checksum --json <path>`: Checksum inventory compact deterministic JSON (positional independence for `--json`).
  - `dupe checksum` / `dupe checksum --json`: Missing path prints usage message.
- **Dispatch Implementation in `src/main.j2`:**
  - Added `import "checksum.j2"`.
  - Added helper `is_checksum_command(args)` which checks `args[1] == "checksum"`.
  - When `args[1] == "checksum"`, delegates to `run_checksum(args)`.
  - In all other cases, executes the unchanged reference duplicate-detection pass.

### 3. Output Formats
- **Human-Readable Text Format:**
  ```text
  <digest>  <file_path>
  ...
  Total files: N, Total bytes: B
  ```
- **Machine-Readable JSON Format (Schema Version 1):**
  ```json
  {
    "schema_version": 1,
    "workload": "checksum_inventory",
    "root": "...",
    "summary": {
      "total_files": N,
      "total_bytes": B
    },
    "entries": [
      {
        "path": "...",
        "size": S,
        "sha256": "64-char lowercase hex"
      }
    ]
  }
  ```

### 4. Benchmark Harness Integration
- Extended `benchmarks/harness.py`:
  - Added `BaselineChecksumWorkloadMetrics` dataclass (`total_files`, `total_bytes`, `entries_count`).
  - Added `extract_checksum_workload_metrics(parsed_json)`.
  - Added `measure_checksum_corpus_baselines(corpus_path, warmup_runs, measured_runs)` to `BenchmarkHarness` to measure interpreter vs native binary on standard corpora with manifest isolation and direct bit-for-bit JSON equivalence checks.
  - Added `ChecksumCorpusComparisonResult` dataclass.

### 5. Verification & Testing Evidence
- **Dedicated T007 Test Suite (`tests/test_t007_checksum_inventory.py`):**
  - 10 focused tests covering empty directory, single file, multiple files, nested directories, deterministic ordering, exact SHA-256 correctness against `hashlib.sha256`, byte totals, file counts, JSON schema conformance, argv parsing combinations, CLI dispatch separation, harness metrics extraction, and 0-byte file hashing.
  - Result: **10/10 PASS** in 0.12s.
- **Full Repository Test Suite (`python -m unittest discover -s tests`):**
  - Result: **58/58 PASS** in 13.39s (48 existing + 10 T007 tests).
- **Phase 4 Differential Offline Self-Tests (`python tests/phase4_differential.py --offline`):**
  - Result: **PASS** (100% backward compatibility with frozen Phase 4 oracle and regression gates).
- **Boundary Audit:**
  - `src/scan.j2`, `src/hash.j2`, `src/group.j2`, `src/output.j2` remain strictly untouched.
  - `benchmarks/results/t005_*` and `benchmarks/results/t006_*` remain strictly untouched.
  - No parallelism claims made; independent read-and-hash workload established.

## Next Action
1. Conduct Antigravity deep-critic self-review.
2. Await independent OpenCode release review.
