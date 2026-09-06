# T005 — J2 Interpreter/Native Baseline

## Goal
Measure the exact duplicate workload in a controlled environment before making any automatic-parallelism claim.

## Prerequisites
- T002 correctness complete.
- T003 research consolidated.
- T004 deterministic corpus available.

## Measurements
At minimum record:
- wall-clock runtime
- files processed
- total bytes
- hash candidates
- result count
- J2 version
- runner architecture/OS
- repository commit
- corpus seed/configuration

Measure interpreter and native execution separately using the same corpus and command semantics.

## Constraints
- No cherry-picked favorable runs.
- Keep warm/cold-cache policy explicit.
- Do not compare incomparable environments.
- No conclusion about automatic parallelism yet.

## Definition of done
A reproducible benchmark result exists for interpreter and native execution, with enough metadata to rerun it and explain the methodology.
