# T004 — Benchmark Corpus Specification and Generator

## Goal
Create a deterministic, reproducible benchmark corpus generator and JSON manifest specification for evaluating J2 filesystem-intelligence workloads across controlled data dimensions.

## CI Runner Constraints & Sizing Policy
- **Standard GitHub Actions Public Runner:** 4 vCPUs, 16 GB RAM, ~14 GB available SSD storage.
- **CI Storage Ceiling:** Automated CI corpora must not exceed **1 GB** total bytes to ensure safe execution without runner disk exhaustion.
- **Developer-Only Corpora:** Large-scale corpora (5 GB+) are reserved for developer hardware profiling and offline analysis.

## Orthogonal Workload Dimensions
The generator must allow independent control over 8 orthogonal parameters:

1. **Dimension A — File Count:** `1K`, `10K`, `50K`, `100K`
2. **Dimension B — Total Data Size:** `100 MB`, `500 MB`, `1 GB` (Standard CI), `5 GB` (Developer-only)
3. **Dimension C — Size Distribution:**
   - `tiny-heavy`: <4 KB (metadata/traversal bound)
   - `small-heavy`: 4 KB – 64 KB
   - `large-heavy`: 1 MB – 10 MB (I/O & hash bound)
   - `mixed`: Pareto/power-law distribution
4. **Dimension D — Duplicate Ratio:** `0%` (all unique), `10%`, `50%`, `90%`
5. **Dimension E — Same-Size Collision Density:**
   - `low`: unique sizes per file
   - `medium`: small size clusters
   - `high` (Adversarial): many distinct files sharing identical byte sizes to stress candidate filtering
6. **Dimension F — Tree Hierarchy:**
   - `flat`: single directory
   - `shallow-wide`: 1–2 levels, 500+ files per folder
   - `deep`: 8–15 nested subdirectories
   - `mixed`: balanced branching factor
7. **Dimension G — Content Similarity Structure:**
   - distinct prefixes and suffixes
   - shared prefix, distinct suffix
   - distinct prefix, shared suffix
   - exact byte identity
8. **Dimension H — Cache State:**
   - `fresh-job`: newly spun runner/job instance
   - `warm-state`: repeated executions against the generated tree

## Named Standard Corpora (C1–C7)

| Corpus ID | Name | Files | Target Size | Characteristics & Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | Metadata Heavy | ~50,000 | ~500 MB | Tiny files, deep/wide tree, low duplicate ratio (5%). Isolates discovery and metadata overhead. |
| **C2** | Balanced Baseline | ~10,000 | ~1 GB | Mixed sizes, balanced tree, 30% duplicate ratio. Primary reference workload. |
| **C3** | Large-File Throughput | 200–500 | ~1–2 GB | Large files (1–10 MB), shallow tree, 10% duplicate ratio. Tests sequential read and hash throughput. |
| **C4** | High Duplicate Density | ~10,000 | ~1 GB | 80% duplicates in large clusters. Stresses grouping, aggregation, and reclaimable-byte math. |
| **C5** | Same-Size Adversarial | ~20,000 | ~1 GB | High size collision, but distinct content. Forces 100% candidate survival into full SHA-256 hashing. |
| **C6** | Mixed Realistic | ~10,000 | ~1 GB | Long-tailed distribution, realistic structure. Primary live demo and cross-pass benchmark. |
| **C7** | Cache Transition | ~10,000 | ~1 GB | Multi-iteration runs of C2/C6 (run 1 cold-ish, runs 2–3 warm) to quantify OS page cache impact. |

## Manifest Specification (`manifest.json`)
Every generated corpus must output a machine-readable JSON manifest alongside the file tree:

```json
{
  "schema_version": 1,
  "corpus_id": "C5",
  "seed": 12345,
  "generator_version": "git-sha",
  "file_count": 20000,
  "total_bytes": 1073741824,
  "duplicate_groups": 1500,
  "duplicate_files": 6000,
  "same_size_candidate_files": 20000,
  "size_profile": "same_size_adversarial",
  "directory_shape": "shallow-wide",
  "expected_reclaimable_bytes": 241172480,
  "expected_result_digest": "sha256-hex"
}
```

## Acceptance Criteria
1. Deterministic, seed-based generator implemented in independent, verifiable script (`benchmarks/generator/`).
2. Exact reproducibility: identical seed and config produce byte-identical file trees and identical manifests.
3. Strict verification of file counts, byte totals, duplicate groups, and reclaimable bytes.
4. Generates C1 through C7 configurations reliably.
5. Standard CI configurations (C1, C2, C4, C5, C6) fit within <= 1 GB storage.
6. Generator validates disk space before generating files to prevent disk exhaustion.
