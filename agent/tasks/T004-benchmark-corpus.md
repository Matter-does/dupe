# T004 — Benchmark Corpus Specification and Generator

## Goal
Create a deterministic, reproducible benchmark corpus generator and JSON manifest specification for evaluating J2 filesystem-intelligence workloads across controlled data dimensions.

## Host Hardware Environment & Sizing Policy

| Runner Platform | Architecture | vCPUs | RAM | SSD Scratch Space | Purpose |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`macos-15`** | Apple Silicon (arm64) | 3 | 7 GB | 14 GB | **Primary J2 Execution & Benchmarking** |
| **`ubuntu-latest`** | x86_64 | 4 | 16 GB | 14 GB | Offline Differential, Oracle, Corpus Generation |

- **CI Storage Ceiling:** Automated CI corpora must not exceed **1 GB** total bytes to ensure safe execution without runner disk exhaustion.
- **Developer-Only Corpora:** Large-scale corpora (e.g. C3, 5 GB+) are reserved for developer hardware profiling and offline analysis.

## Controlled Workload Dimensions
The generator allows structured control over 8 workload parameters with documented interactions:

1. **Dimension A — File Count:** `1K`, `10K`, `50K`, `100K` *(interacts with total size to determine average file size)*
2. **Dimension B — Total Data Size:** `100 MB`, `200 MB`, `500 MB`, `1 GB` (Standard CI), `5 GB` (Developer-only)
3. **Dimension C — Size Distribution (`size_profile`):**
   - `tiny_heavy`: <4 KB (metadata/traversal bound)
   - `small_heavy`: 4 KB – 64 KB
   - `large_heavy`: 1 MB – 10 MB (I/O & hash bound)
   - `mixed`: Pareto/power-law distribution
   - `same_size_adversarial`: uniform size across distinct files
4. **Dimension D — Duplicate Ratio (`duplicate_ratio`):**
   - Formal definition: $\text{duplicate\_ratio} = \frac{\text{duplicate\_files}}{\text{total\_files}}$
   - Allowed values: `0.0` (0%), `0.05` (5%), `0.10` (10%), `0.30` (30%), `0.50` (50%), `0.80` (80%), `0.90` (90%)
5. **Dimension E — Same-Size Collision Density:**
   - `low`: unique sizes per file
   - `medium`: small size clusters
   - `high` (Adversarial): many distinct files sharing identical byte sizes to stress candidate filtering
6. **Dimension F — Tree Hierarchy (`directory_shape`):**
   - `flat`: single directory
   - `shallow_wide`: 1–2 levels, 500+ files per folder
   - `deep`: 8–15 nested subdirectories
   - `mixed`: balanced branching factor
7. **Dimension G — Content Similarity Structure (`similarity_profile`):**
   - `distinct`: distinct prefixes and suffixes
   - `shared_prefix`: shared prefix, distinct suffix
   - `shared_suffix`: distinct prefix, shared suffix
   - `exact`: exact byte identity
8. **Dimension H — Cache State (`cache_state`):**
   - `initial_run`: first execution after corpus generation in a fresh job
   - `warm_repeated`: successive executions within the same job measuring steady-state variance

## Named Standard Corpora (C1–C7)

| Corpus ID | Name | Files | Target Size | CI / Dev | Characteristics & Purpose |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **C1** | Metadata Heavy | 50,000 | ~200 MB | **CI** | Tiny files (<4 KB, avg 4 KB), wide tree, 5% duplicate ratio. Isolates discovery and metadata overhead. *(Mathematically consistent: $50\text{K} \times 4\text{ KB} \approx 200\text{ MB}$.)* |
| **C2** | Balanced Baseline | 10,000 | ~1 GB | **CI** | Mixed sizes (avg 100 KB), balanced tree, 30% duplicate ratio. Realistic everyday filesystem baseline. |
| **C3** | Large-File Throughput | 200–500 | ~1–2 GB | **Dev Only** | Large files (1–10 MB), shallow tree, 10% duplicate ratio. Exceeds 1 GB CI cap; tests sequential I/O and hash throughput. |
| **C4** | High Duplicate Density | 10,000 | ~1 GB | **CI** | 80% duplicate ratio in large clusters. Stresses grouping, aggregation, and reclaimable-byte math. |
| **C5** | Same-Size Adversarial | 20,000 | ~1 GB | **CI** | 100% same-size candidate collision, distinct byte content. Forces all candidates into full SHA-256 hashing. |
| **C6** | Mixed Realistic | 10,000 | ~1 GB | **CI** | Power-law distribution, realistic hierarchy, 30% duplicates. Primary live demo workload. |
| **C7** | Cache Transition | 10,000 | ~1 GB | **CI** | Repeated runs of C2/C6 (run 1 initial, runs 2–3 warm) to quantify warm-state transition and run-to-run variance. |

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
  "duplicate_ratio": 0.3,
  "duplicate_groups": 1500,
  "duplicate_files": 6000,
  "same_size_candidate_files": 20000,
  "size_profile": "same_size_adversarial",
  "directory_shape": "shallow_wide",
  "similarity_profile": "distinct",
  "expected_reclaimable_bytes": 241172480,
  "expected_result_digest": "sha256-of-deterministic-json-output"
}
```

- **`expected_result_digest` Specification:** The hexadecimal SHA-256 digest of the UTF-8 bytes of the deterministic JSON output emitted by the reference oracle when run against the corpus root.

## Acceptance Criteria
1. Deterministic, seed-based generator implemented in independent, verifiable script (`benchmarks/generator/`).
2. Exact reproducibility: identical seed and configuration reproduce identical file contents, relative directory structures, and identical `manifest.json` files (excluding volatile OS mtime/ownership metadata).
3. Strict verification of file counts, byte totals, duplicate groups, and reclaimable bytes.
4. Generates C1 through C7 configurations reliably without mathematical contradictions.
5. Standard CI configurations (C1, C2, C4, C5, C6, C7) fit within <= 1 GB storage.
6. Generator validates available disk space before writing files to prevent runner disk exhaustion.
