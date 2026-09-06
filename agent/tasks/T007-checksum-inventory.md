# T007 — Reusable Filesystem Analysis Pass for Checksum Inventory

## Goal
Implement a second read-only filesystem intelligence workload — **File Checksum Inventory** — as an additive pass reusing the common `FileRecord` discovery pipeline, eliminating duplicate grouping logic, and directly exercising parallel file reading and SHA-256 hashing without modifying frozen Phase 3 code.

## Motivation & Value
1. **Pipeline Decoupling:** Proves that the filesystem discovery engine is modular and reusable across distinct analysis passes.
2. **Maximum Independent Parallelism:** Every single discovered file represents an independent read-and-hash computation, maximizing the volume of work submitted to J2's automatic parallelism engine without size-filtering candidate reduction.
3. **No Grouping Overhead:** Eliminates the grouping, dictionary aggregation, and reclaimable-byte arithmetic present in duplicate detection, isolating the performance of I/O and cryptographic hashing.
4. **Practical Utility:** Produces a deterministic checksum ledger (SHA-256 manifest) suitable for file integrity verification.

## Architecture

```text
               Filesystem Discovery (fs.list_dir & metadata)
                                  │
                                  ▼
                   Discovered Files [path, size]
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
Pass 1: Duplicate Analysis                        Pass 2: Checksum Inventory
 - Frozen Phase 3 implementation                   - Additive independent pass
 - Size filter (count >= 2)                        - Every discovered file
 - Candidate read & SHA-256                        - Read bytes & compute SHA-256
 - Digest grouping                                 - Emit checksum manifest / ledger
```

## CLI Surface & Argv Parsing
```bash
# Duplicate scan (default, existing CLI):
dupe <path> [--json]

# Checksum inventory (sub-command):
dupe checksum <path> [--json]
```

### Argv Handling Contract
- When `argv[1] == "checksum"`, the root path argument shifts to `argv[2]`.
- Optional `--json` flag is parsed regardless of positional placement.
- When `argv[1]` is a directory path (not `"checksum"`), execution defaults to the reference duplicate-analysis pass.

## Output Format Specification

### Text Format
```text
<digest>  <file_path>
...
Total files: N, Total bytes: B
```
*(Internal elapsed timing output is deferred pending resolution of a verified J2 runtime timing API).*

### JSON Format
```json
{
  "schema_version": 1,
  "workload": "checksum_inventory",
  "root": "/path/to/scan",
  "summary": {
    "total_files": 1000,
    "total_bytes": 104857600
  },
  "entries": [
    {
      "path": "/path/to/scan/file1.txt",
      "size": 1024,
      "sha256": "6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090"
    }
  ]
}
```

## Implementation Strategy & Freezing Rules
1. **Additive Implementation:** T007 must be added in new additive files (e.g. `src/checksum.j2` or as a secondary entrypoint). It must **NOT** modify or refactor the frozen Phase 3 code in `src/main.j2`, `src/scan.j2`, etc.
2. **Deterministic Output:** Entries in the inventory ledger must preserve deterministic discovery order (or explicit path sorting).
3. **Capability Contract:** Standalone compiled native execution requires runtime capability `J2_ALLOW_FS=1`.
4. **Cross-Mode Equivalence:** Interpreter (`j2 run`) and compiled native binary must produce bit-for-bit identical JSON output.

## Acceptance Criteria
1. Checksum inventory pass implemented additively in J2 without modifying frozen Phase 3 sources.
2. File discovery logic reused without redundant directory traversal.
3. Sub-command argv shift (`dupe checksum <path>`) correctly handled.
4. Deterministic output ordering strictly enforced.
5. Interpreter and native compiled executions produce byte-identical JSON.
6. Integrated into benchmark harness on `macos-15` for parallel scaling comparison against duplicate detection.
