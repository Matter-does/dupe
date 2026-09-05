# Phase 3 — MVP Engine

**Status:** COMPLETE / FROZEN  
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
- [x] 3.12 Modular interpreter execution
- [x] 3.13 Modular native execution
- [x] 3.14 Interpreter/native JSON equivalence

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

## Module boundary

J2 0.1.0 user-module syntax was experimentally verified as:

```j2
import "helper.j2"
```

The form was shown to run under `j2 run`, compile with `j2 build`, and execute as native code. Phase 3 uses these source boundaries:

```text
src/
    main.j2
    scan.j2
    hash.j2
    group.j2
    output.j2
```

No module performs user-file mutation in the MVP.

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

`.github/workflows/phase3-mvp.yml` creates a deterministic five-file tree containing two duplicate pairs and one unique file.

The expected result is:

```text
files_scanned       == 5
hash_candidates     == 4
duplicate_groups    == 2
reclaimable_bytes   == 27
```

The final Phase 3 GitHub Actions run `33961153461` completed successfully, and its `mvp` job reported all three acceptance steps as successful:

```text
1. Modular interpreter execution       PASS
2. Modular native execution            PASS
3. Interpreter JSON == native JSON     PASS
```

The run's warning is an unrelated `actions/checkout@v4` Node.js 20 deprecation annotation; it did not affect the Phase 3 result.

## Handoff to Phase 4

Phase 3 is frozen. The implementation deliberately uses a linear same-size scan and linear hash grouping. Phase 4 adds an independent oracle, seeded edge cases, differential testing, failure preservation, and regression coverage before optimization or automatic-parallelism benchmarking.
