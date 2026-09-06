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
        ┌───────────────┼────────────────┐
        │               │                │
     discovery       metadata        analysis passes
                                        │
                              ┌─────────┼─────────┐
                              │         │         │
                           dupes     largest    statistics
                              │
                              ▼
                       deterministic results
                              │
                         JSON / human
```

## Engine stages

### 1. Discovery
Recursively enumerate regular files while retaining deterministic ordering where practical.

### 2. Metadata
Collect file metadata required by analysis passes. The existing Phase 3 scanner records path and size.

### 3. Candidate reduction
For duplicate analysis, group or filter by size before reading file contents.

### 4. Analysis
Run independent per-file or per-candidate computations where J2 can expose independence to its native execution system. Exact hashing is the first target workload.

### 5. Aggregation
Combine analysis records into deterministic result groups and totals.

### 6. Presentation
Keep analysis data independent from human-readable and JSON output. A future GUI should consume the same result model rather than reimplement the engine.

## Parallelism design principle
The application should express useful work as independent transformations over independent file records where possible. We must measure whether J2 actually parallelizes these operations effectively; source structure alone is not proof.

Do not add an explicit thread pool, thread API, or manual scheduler merely to force concurrency. The hackathon question is specifically how far J2's automatic parallelism can take the workload.

## Execution modes
Every important J2 workload should be testable through:

```text
source .j2
  ├── interpreter execution
  └── native execution
```

Correctness requires equivalent externally visible results. Performance comparisons must be made with controlled workload and environment.

## Safety boundary
The initial engine is read-only. Destructive file operations are outside the current scope. Filesystem capabilities must remain explicitly enabled in J2 execution environments.

## Extensibility rule
New analysis passes should consume the common discovered-file representation instead of creating a second filesystem traversal unless a measurement demonstrates a concrete reason to do so.
