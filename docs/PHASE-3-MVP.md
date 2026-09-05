# Phase 3 — MVP Engine

**Status:** IMPLEMENTED; corrected CI validation in progress  
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

## Module boundary

J2 0.1.0 user-module syntax is now experimentally verified:

```j2
import "helper.j2"
```

The form was shown to run under `j2 run`, compile with `j2 build`, and execute as native code. Imported functions are available directly in the importing program. Other tested forms such as bare `import helper`, `use helper`, `from helper import answer`, `include "helper.j2"`, and `module ...` declarations did not provide a valid user-module mechanism in the probe.

Phase 3 therefore uses these functional source boundaries:

```text
src/
    main.j2
    scan.j2
    hash.j2
    group.j2
    output.j2
```

No module is allowed to perform user-file mutation in the MVP.

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

`.github/workflows/phase3-mvp.yml` creates a five-file test tree containing two duplicate pairs and one unique file.

The actual test data contains files of 14 and 13 bytes, so the correct expected result is:

```text
files_scanned       == 5
hash_candidates     == 4
duplicate_groups    == 2
reclaimable_bytes   == 27
```

It also requires interpreter and native outputs to parse as JSON and compare equal.

The first integration attempt exposed two real issues: J2 mutable bindings require `:=`, and the native binary retains the deny-by-default filesystem sandbox. Both are now reflected in the implementation/CI design.

## Known follow-up

The current implementation deliberately uses a linear same-size scan and linear hash grouping. Phase 4 correctness testing comes before optimization. Phase 5 will measure whether the hashing workload actually benefits from J2 automatic parallelism and will only replace these structures when a runtime-verified J2 API provides a measurable advantage.
