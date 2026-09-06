# T007 — Reusable Filesystem Analysis Pass for Checksum Inventory

## Goal
Implement a second read-only filesystem intelligence workload — **File Checksum Inventory** — that reuses the unified `FileRecord[]` discovery pipeline, eliminates duplicate grouping logic, and directly exercises parallel file reading and SHA-256 hashing.

## Motivation & Value
1. **Pipeline Decoupling:** Proves that the filesystem discovery engine (`FileRecord[]`) is modular and reusable across distinct analysis passes.
2. **Maximum Independent Parallelism:** Every single discovered file represents an independent read-and-hash computation, maximizing the volume of work submitted to J2's automatic parallelism engine without size-filtering reductions.
3. **No Grouping Overhead:** Eliminates the grouping, dictionary aggregation, and reclaimable-byte arithmetic present in duplicate detection, isolating the performance of I/O and cryptographic hashing.
4. **Practical Utility:** Produces a deterministic checksum ledger (e.g. SHA-256 manifest) suitable for file integrity verification.

## Architecture

```text
               Filesystem Discovery (fs.list_dir & metadata)
                                  │
                                  ▼
                     FileRecord[] (path, size)
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
Pass 1: Duplicate Analysis                        Pass 2: Checksum Inventory
 - Size filter (count >= 2)                        - Every discovered file
 - Candidate read & SHA-256                        - Read bytes & compute SHA-256
 - Digest grouping                                 - Emit checksum manifest / ledger
```

## CLI Surface
```bash
# Human-readable output:
dupe checksum <path>

# Machine-readable JSON output:
dupe checksum <path> --json
```

## Output Format Specification

### Text Format
```text
<digest>  <file_path>
...
Total files: N, Total bytes: B, Elapsed: T ms
```

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

## Implementation Strategy
1. Refactor `src/` to separate file discovery into a shared module returning `FileRecord[]`.
2. Implement `checksum_inventory()` kernel iterating over `FileRecord[]`, reading bytes, and computing `hash.sha256`.
3. Verify deterministic sorting of inventory entries by path string.
4. Ensure native binary execution with `J2_ALLOW_FS=1`.
5. Check cross-mode determinism (`interpreter == native`).

## Acceptance Criteria
1. Checksum inventory pass implemented natively in J2.
2. Discovered files shared between duplicate analysis and checksum inventory without redundant traversal.
3. Deterministic output ordering enforced.
4. Interpreter and native compiled executions produce byte-identical JSON.
5. Integrated into the benchmark harness for parallel scaling comparison against duplicate detection.
