# Phase 3 — MVP Engine

**Status:** IMPLEMENTED; CI validation in progress  
**Target:** J2 0.1.0 / macOS Apple Silicon

## Completed work

- [x] 3.1 CLI argument handling via `proc.argv()`
- [x] 3.2 Recursive directory traversal via `fs.list_dir`
- [x] 3.3 File filtering via `fs.is_file` / `fs.is_dir`
- [x] 3.4 Metadata collection via `fs.metadata`
- [x] 3.5 Size-based candidate filtering
- [x] 3.6 Exact-byte SHA-256 hashing via `fs.read_bytes` + `hash.sha256`
- [x] 3.7 Duplicate grouping by SHA-256
- [x] 3.8 Reclaimable-byte calculation
- [x] 3.9 Deterministic result construction
- [x] 3.10 Human-readable output
- [x] 3.11 JSON output

## Engine flow

```text
PATH
  |
  v
recursive discovery
  |
  v
metadata / file size
  |
  v
same-size candidate filtering
  |
  v
exact-byte SHA-256 hashing
  |
  v
hash grouping
  |
  v
duplicate groups
  |
  v
reclaimable bytes
  |
  +-------------------+
  |                   |
  v                   v
human output       deterministic JSON
```

## Implementation boundary

The Phase 3 engine is intentionally contained in `src/main.j2`. J2 module/import syntax is not part of the frozen API contract, so no import syntax is invented for the MVP. The file is divided into functional boundaries that can be split after module semantics are verified.

The grouping implementation currently reconstructs arrays rather than relying on unverified associative-map mutation. This favors correctness and API certainty over premature optimization.

## MVP correctness rules

1. Only regular files are analyzed.
2. A file is hashed only when another discovered file has the same size.
3. Duplicate identity is exact SHA-256 of `fs.read_bytes(path)`.
4. A duplicate group contains two or more files with the same digest.
5. Reclaimable bytes for a group are `(count - 1) * size`.
6. Discovery order is stabilized by sorting each directory's entries before recursion.
7. JSON is constructed with stable field order and escaped path strings from `json.stringify`.
8. The MVP performs no deletion or mutation of user files.

## CI acceptance test

`.github/workflows/phase3-mvp.yml` creates a five-file test tree containing two duplicate pairs and one unique file, then verifies:

```text
files_scanned       == 5
hash_candidates     == 4
duplicate_groups    == 2
reclaimable_bytes   == 28
```

It also requires interpreter and native outputs to parse as JSON and compare equal.

## Known follow-up

The current implementation deliberately uses a linear same-size scan and linear hash grouping. Phase 4 correctness testing comes before optimization. Phase 5 will measure whether the hashing workload actually benefits from J2 automatic parallelism and will only replace these structures when a runtime-verified J2 API provides a measurable advantage.
