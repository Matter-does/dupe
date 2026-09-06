# Architecture

## Core idea
Build one reusable filesystem-analysis pipeline in J2 and place analysis passes on top of it.

```text
                 CLI / future GUI
                        │
                  command layer
                        │
             filesystem analysis engine
                        │
                  fs.list_dir & metadata
                        │
                  FileRecord[] [path, size]
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
    Duplicate        Checksum         Future
    Analysis        Inventory        Analyses
 (size filter +   (read & SHA-256  (largest, stats)
  SHA-256 groups)  per-file ledger)
        │               │                │
        └───────────────┼────────────────┘
                        │
                        ▼
              deterministic results
                        │
                   JSON / human
```

## Engine stages

### 1. Discovery & Metadata
Recursively enumerate regular files and collect file metadata required by analysis passes. The engine produces an array of `FileRecord` entries represented using verified J2 primitives (e.g. `[path, size]`, matching the verified Phase 3 scanner). Directory traversals sort child entry names via `sort(fs.list_dir(path))` to maintain deterministic discovery order.

### 2. Analysis Passes
Analysis passes consume the shared discovered file records without repeating discovery:

- **Pass A — Exact Duplicate Detection (Frozen Reference Workload):**
  Groups files by size, excludes unique sizes (count < 2), reads exact bytes for remaining candidates, computes SHA-256 digests, and groups matching digests into duplicate clusters. This workload is frozen as the baseline reference.
- **Pass B — File Checksum Inventory (Additive Second Workload — T007):**
  Processes discovered files, reads file bytes, computes SHA-256 digests, and emits a structured checksum inventory ledger. Implemented additively as an independent pass/module without refactoring or modifying frozen Phase 3 code.
- **Future Passes:**
  Largest files, extension distributions, or directory storage statistics.

### 3. Candidate Reduction (Duplicate Analysis)
For duplicate analysis, group or filter by size before reading file contents. Files with unique sizes are discarded before content read operations, significantly reducing unnecessary I/O.

### 4. Independent Analysis Kernels
Run per-file or per-candidate computations where J2 can expose independence to its native execution system. Exact hashing is the first target workload.

### 5. Aggregation
Combine analysis records into deterministic result groups, calculate reclaimable space (`reclaimable_bytes = Σ(count - 1) × size`), and format outputs strictly preserving the established first-discovery order determinism contract.

### 6. Presentation
Keep analysis data independent from human-readable and JSON output. Output adapters emit human-readable formatted text or compact deterministic JSON (`--json`).

## Parallelism design principle
The application expresses useful work as independent transformations over independent file records where possible. We must measure whether J2 actually parallelizes these operations effectively; source structure alone is not proof.

Do not add an explicit thread pool, thread API, or manual scheduler merely to force concurrency. The hackathon question is specifically how far J2's automatic parallelism can take the workload.

## Execution modes
Every important J2 workload should be testable through:

```text
source .j2
  ├── interpreter execution (j2 run --allow-fs ...)
  └── native execution (j2 build ... && J2_ALLOW_FS=1 ./build/dupe ...)
```

Correctness requires equivalent externally visible results. Performance comparisons must be made with controlled workload and environment on verified platforms (`macos-15` Apple Silicon).

## Safety boundary
The initial engine is read-only. Destructive file operations are outside the current scope. Filesystem capabilities must remain explicitly enabled in J2 execution environments (`--allow-fs` for interpreter, `J2_ALLOW_FS=1` for native binary).

## Extensibility rule
New analysis passes should consume the common discovered-file representation without creating a second filesystem traversal unless a measurement demonstrates a concrete reason to do so. All secondary passes must be additive and must not destabilize frozen baseline workloads.
