# Project Specification

## Working title
`dupe`

## Product definition
`dupe` is a J2-native filesystem intelligence engine. It turns real filesystem analysis into a deterministic workload suitable for studying J2's automatic parallelism.

Exact duplicate detection is the first production workload because it is useful, easy to validate independently, and contains many naturally independent file-analysis operations.

## Problem
Duplicate-file detection is a familiar, real-world problem, but the duplicate-finder category is already mature. Existing tools cover deletion workflows, filtering, media similarity, caching, and explicit parallel implementations. `dupe` therefore must not compete primarily on feature count.

The project differentiator is the use of J2's automatic parallelism and the evidence-driven study of its behavior on a real filesystem workload.

## Product goals
1. Provide a correct exact-duplicate analysis workload.
2. Keep the core implementation primarily in J2.
3. Make interpreter and native execution behavior agree.
4. Establish reproducible workloads and measurements.
5. Demonstrate where J2 automatic parallelism helps, does not help, or has trade-offs.
6. Reuse the same filesystem representation for additional analysis passes.
7. Expose deterministic human-readable and machine-readable results.

## Non-goals
- Feature-for-feature reproduction of dupeGuru.
- Building a general-purpose desktop cleanup suite.
- Destructive deletion in the initial product.
- Claiming performance improvements before controlled measurement.
- Building a generic autonomous-agent platform for the hackathon.

## First workload
Exact duplicates:

```text
filesystem discovery
→ safe metadata collection
→ candidate reduction by size
→ exact SHA-256 comparison
→ duplicate grouping
→ reclaimable-byte calculation
→ deterministic output
```

The existing Phase 3 implementation is the baseline/reference workload. It should remain stable while Phase 4 correctness is completed.

## Planned workload family
The architecture should support multiple read-only analysis passes over the same discovered file set, such as:

- exact duplicates
- largest files
- extension/type distribution
- directory statistics
- storage/reclaim analysis

These are planned workloads, not commitments to implement all of them.

## Interface direction
Initial CLI:

```text
dupe PATH
dupe PATH --json
```

Future commands may include an audit/report surface and benchmark tooling, but they must be specified and verified before implementation.

## Evidence standard
All claims about J2 behavior, API availability, correctness, or performance must be backed by one of:
- executable probe
- passing test
- CI result
- reproducible benchmark
- authoritative project documentation

Do not infer a performance or compiler claim from source appearance alone.
