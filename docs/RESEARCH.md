# Research Register

## Purpose
This document records competitive and technical research that affects product direction. It exists so agents do not repeatedly rediscover the same category facts from chat history.

## Competitive finding: duplicate detection is a mature category
The project was initially framed as a generic duplicate-file finder. Repository/search research showed that `dupeGuru` is a prominent existing project with a mature desktop workflow, including application modes, reference/excluded folders, duplicate groups, filtering, result review, and file-management actions.

Other established and newer duplicate-finder projects also cover common optimizations such as size filtering, hashing, caching, and explicit parallel execution.

## Strategic conclusion
Do not compete with established duplicate managers by accumulating their features.

The useful distinction for this hackathon is:

> `dupe` is a J2-native filesystem intelligence workload, with duplicate detection as the first application, used to measure and demonstrate J2 automatic parallelism on a real workload.

## Research questions
1. Which stages of filesystem analysis does J2 actually parallelize?
2. What workload size is required before parallelism is measurable?
3. What is the interpreter/native baseline?
4. Does J2 native automatic parallelism improve wall time, throughput, or CPU utilization for hashing-heavy workloads?
5. Which filesystem operations become bottlenecks outside the CPU-bound hashing stage?
6. Does the same engine structure support additional analysis passes without sacrificing determinism or correctness?

## Evidence rules
- Competitive feature claims should cite primary project documentation or repository evidence.
- J2 language/compiler claims must be verified against the pinned J2 release or authoritative J2 documentation.
- Performance claims require reproducible benchmark evidence.
- Do not describe an implementation as parallel merely because a loop looks independent.

## Current product implication
Phase 3 remains useful as a stable exact-duplicate baseline. Phase 4 establishes correctness. Phase 5 should be designed as an experiment, not as a marketing benchmark.

## Open research
- Compare the exact duplicate algorithm against representative mature tools at the level needed for benchmark methodology, not feature cloning.
- Define fair benchmark corpora and controls.
- Determine whether filesystem discovery, hashing, or aggregation dominates each workload.
