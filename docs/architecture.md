# Architecture

## Exact duplicate MVP

```text
filesystem scan
      |
      v
metadata collection
      |
      v
size grouping
      |
      v
candidate files
      |
      v
independent hashing  <--- primary J2 parallelism target
      |
      v
equal-hash grouping
      |
      v
reclaimable-storage report
```

The key design decision is to avoid hashing every file blindly. Files whose sizes are unique cannot be exact duplicates of another file, so the expensive hashing stage should operate only on same-size candidate groups.

## Parallelism hypothesis

For many candidate files, hashing each file is naturally independent. The intended experiment is to express that ordinary work in J2 and compare real native execution with J2's documented parallel execution behavior.

Benchmark results are not part of the repository until measured on the actual CI runner.
