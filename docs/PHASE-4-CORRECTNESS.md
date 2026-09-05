# Phase 4 — Differential Correctness & Regression

**Status:** IN PROGRESS  
**Prerequisite:** Phase 3 MVP complete  
**Goal:** independently verify `dupe` correctness across generated file trees and execution modes.

## Acceptance gates

- [ ] Independent Python oracle implemented.
- [ ] Seed corpus covers required edge cases.
- [ ] Interpreter output matches oracle on every seeded case.
- [ ] Native output matches oracle on every seeded case.
- [ ] Interpreter output equals native output on every seeded case.
- [ ] Regression corpus is retained in CI.
- [ ] Fuzzer can reproduce a failure from its seed.

## Oracle contract

The oracle must be independent of J2 implementation logic. It should recursively enumerate regular files, group by byte length, compare exact bytes, and calculate duplicate groups/reclaimable bytes.

The oracle must not call `dupe`, J2, or reuse the J2 source implementation.

## Seed corpus

Required deterministic cases:

1. empty tree
2. single file
3. identical files in one directory
4. identical files across nested directories
5. same-size different-content files
6. files differing by one byte
7. multiple empty files
8. multiple duplicate clusters
9. unusual filenames and nested paths
10. size-boundary cases, including zero-byte files

## Failure preservation

Every discovered mismatch must preserve:

```text
seed
case description
filesystem manifest
interpreter output
native output
oracle output

```

A minimized reproducer belongs under `tests/regressions/` before the bug is considered closed.

## Non-goals

Phase 4 does not benchmark performance, prove automatic parallelism, or add deletion behavior. Those belong to later phases.
