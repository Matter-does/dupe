# dupe

**J2-native filesystem intelligence engine**

`dupe` is a read-only filesystem analysis project written primarily in J2. Exact duplicate detection is the first real workload. The broader goal is to study how a real filesystem-analysis pipeline behaves under J2's automatic parallelism.

This is deliberately **not** a feature-for-feature clone of established duplicate managers. The duplicate scanner is our correctness/reference workload; the hackathon contribution is the J2-native execution model, reproducible experiments, and evidence about what automatic parallelism actually does.

## Product model

```text
filesystem
    ↓
discovery + metadata
    ↓
reusable file records
    ↓
analysis passes
 ┌──┴───────────┬───────────────┐
 │              │               │
duplicates   largest files   statistics
    ↓
 deterministic result model
    ↓
 human / JSON output
```

The first analysis pass is exact duplicate detection:

1. recursively discover regular files
2. collect safe metadata
3. reduce candidates by file size
4. hash only files that can have duplicates
5. group equal SHA-256 digests
6. calculate reclaimable bytes
7. emit deterministic output

No destructive deletion is part of the current product.

## Why this project exists

Duplicate detection is already a mature software category. Projects such as dupeGuru and other modern duplicate finders provide substantial user-facing features and, in some cases, their own explicit parallel implementations.

`dupe` therefore uses the category as a useful workload rather than claiming that duplicate detection itself is novel.

The central question is:

> **Can J2 express a useful filesystem-analysis workload as independent operations, and what does its automatic parallelism actually achieve on reproducible real-world-shaped workloads?**

Performance claims are made only from controlled measurements.

## Development model

Development is performed on Windows. J2 native compilation and the reproducible execution/benchmark environment run in GitHub Actions on macOS Apple Silicon because the pinned public J2 0.1.0 release provides the required binary there.

The J2 version and checksum are pinned in CI. See the workflow files and `docs/J2-API-0.1.0.md`.

## Repository-first agent workflow

The repository is the durable project state. Agents must not depend on the full ChatGPT conversation to continue work.

Read first:

```text
AGENTS.md
docs/PROJECT.md
docs/ARCHITECTURE.md
docs/J2-API-0.1.0.md
agent/CURRENT_TASK.md
agent/CHECKPOINT.md
agent/HANDOFF.md
```

Agent roles:

- **Antigravity:** primary implementation.
- **OpenCode:** persistent terminal continuation/fallback.
- **Claude Code through OmniRouter:** adversarial architecture/correctness/J2/benchmark review.
- **GLM-5:** independent second opinion or implementation/review.
- **ChatGPT:** research, architecture, specification, task decomposition, and evidence synthesis.
- **GitHub Actions:** reproducible verification authority.

See `docs/HACKATHON.md` and `docs/AGENT-HARNESS.md`.

## Current phases

```text
Phase 3  MVP                              COMPLETE / FROZEN
Phase 4  Differential correctness        IN PROGRESS
Phase 5  Performance / J2 research       NEXT
Phase 6  Product surface                 LATER
Final    Demo + documentation            LATER
```

## Important rule

Do not invent J2 syntax or APIs. Verify uncertain behavior against the pinned compiler with an executable probe, and record important discoveries in the repository.

## Current CLI

```text
dupe PATH
dupe PATH --json
```

Future interfaces must be specified and verified before implementation.
