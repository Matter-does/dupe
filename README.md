# dupe

**J2-native file intelligence CLI**

`dupe` is a small command-line utility for finding exact duplicate files, measuring reclaimable storage, and (later) detecting near-duplicates safely.

The project is intentionally small: the primary goal is to build a useful tool while using J2's automatic parallelism on the expensive, independent file-analysis workload.

## Development model

Development is performed on Windows. J2-native compilation and benchmarking is performed in GitHub Actions on a macOS Apple Silicon runner because the public J2 0.1.0 release currently ships a macOS Apple Silicon binary.

The workflow pins J2 0.1.0 and verifies its SHA-256 before use. See `.github/workflows/j2.yml`.

## MVP pipeline

1. Recursively discover files.
2. Collect safe metadata.
3. Group candidates by file size.
4. Hash only files that can actually have duplicates.
5. Group equal hashes into duplicate sets.
6. Report duplicate sets and reclaimable bytes.
7. Produce deterministic, machine-readable JSON output.

No destructive deletion is part of the MVP.

## Intended CLI

```text
dupe PATH
dupe PATH --json
dupe PATH --explain
dupe PATH --near
dupe PATH --trash
dupe --benchmark
```

These commands are the target interface; implementation should only be added after the corresponding J2 / standard-library capabilities have been verified against the real compiler.

## J2 rule

Do not invent J2 APIs. The first engineering milestone is to compile tiny programs on the macOS CI runner and record the exact syntax and standard-library interfaces that are actually available in J2 0.1.0.
