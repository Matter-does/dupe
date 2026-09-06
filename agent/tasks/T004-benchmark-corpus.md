# T004 — Benchmark Corpus

## Goal
Create a deterministic benchmark corpus specification and generator for filesystem-intelligence workloads.

## Requirements
- Multiple workload sizes.
- Controlled duplicate ratios.
- Unique files and same-size different-content files.
- Nested directory structure.
- Small and large files.
- Stable seed and manifest.
- Corpus generation must be independent of the J2 implementation.

## Measurement contract
Every benchmark run must identify:
- corpus seed
- corpus configuration
- file count
- total bytes
- duplicate groups
- execution environment
- J2 version
- commit

## Constraints
Do not optimize the benchmark generator until the corpus itself is deterministic and auditable.

## Definition of done
A clean machine can regenerate the same corpus manifest from the same seed/configuration, and the manifest is sufficient to reproduce a performance result.
