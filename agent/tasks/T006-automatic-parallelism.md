# T006 — Automatic-Parallelism Experiment

## Goal
Determine, with reproducible evidence, whether J2 automatic parallelism improves the filesystem-analysis workload and under which workload conditions.

## Prerequisites
- T002 correctness complete.
- T004 corpus complete.
- T005 interpreter/native baseline complete.

## Experiment matrix
Measure the same corpus under the execution modes that can be validly isolated in the pinned J2 environment. The exact commands must be established from verified J2 behavior, not assumed.

Record:
- wall-clock runtime
- throughput in files/sec and bytes/sec
- CPU utilization where the environment permits reliable measurement
- J2 version
- runner architecture/OS
- corpus seed/configuration
- repository commit

## Questions
1. Does the compiler expose enough independent work for useful parallelism?
2. Does the speedup appear only at larger workloads?
3. Is hashing CPU-bound or is filesystem I/O the dominant bottleneck?
4. Which pipeline stage limits total performance?
5. Are results deterministic across execution modes?

## Constraints
- Do not force explicit threads simply to manufacture a speedup.
- Do not claim parallelism from source structure alone.
- Report negative or negligible results honestly.
- Keep methodology fixed before comparing runs.

## Definition of done
A reproducible experiment and written interpretation establish what J2 automatic parallelism actually does on this workload, including cases where it does not help.
