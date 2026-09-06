# Agent Handoff

## Current state
T004 (Benchmark Corpus Generator) is COMPLETE, independently verified, and committed. The repository contains a fully deterministic, seed-based generator and manifest validation system in `benchmarks/generator/`, supporting named corpora C1–C7 and controlled workload dimensions. All non-negotiables were strictly adhered to: `src/*.j2` remains 100% untouched, Phase 4 differential offline tests pass, and C3 is gated as Developer-Hardware-Only.

The task boundary has been reached. **Do NOT begin T005 automatically.**

## What changed in T004?
1. **`benchmarks/generator/profiles.py`**:
   - Implemented `CorpusProfile` dataclass and closed enums: `SizeProfile`, `DirectoryShape`, `SimilarityProfile`, `CacheState`, `CollisionDensity`.
   - Defined C1–C7 standard profiles:
     - **C1 (Metadata Heavy)**: 50,000 files, ~200 MB ($50\text{K} \times 4\text{ KB}$), tiny-heavy, 5% duplicates, CI.
     - **C2 (Balanced Baseline)**: 10,000 files, ~1 GB (avg 100 KB), mixed, 30% duplicates, CI.
     - **C3 (Large-File Throughput)**: 300 files, ~1.5 GB (1–10 MB files), large-heavy, 10% duplicates, **Developer-Hardware Only**.
     - **C4 (High Duplicate Density)**: 10,000 files, ~1 GB, mixed, 80% duplicates in large clusters, CI.
     - **C5 (Same-Size Adversarial)**: 20,000 files, ~1 GB, 100% same-size candidate collision, distinct contents, CI.
     - **C6 (Mixed Realistic)**: 10,000 files, ~1 GB, power-law distribution, deep tree, 30% duplicates, CI.
     - **C7 (Cache Transition)**: 10,000 files, ~1 GB, repeated run structure from C2/C6 (`initial_run`, `warm_repeated`), CI.
2. **`benchmarks/generator/manifest.py`**:
   - Implemented `Manifest` dataclass for schema version 1 matching the exact T004 specification.
   - Built independent reference oracle evaluating deterministic JSON output and SHA-256 digest (`expected_result_digest`) normalized to relative posix paths from corpus root.
   - Built strict `validate_manifest()` verifying schema types, closed enums, mathematical consistency, file tree count and byte totals, duplicate group byte soundness, and digest match.
3. **`benchmarks/generator/generate.py`**:
   - Implemented deterministic seed-based file and tree generator.
   - Added pre-flight disk space safety check (`check_disk_space()`).
   - Added CLI supporting `--corpus`, `--out-dir`, `--seed`, `--scale`, `--allow-developer-hardware`, `--validate`, `--list`.
4. **`tests/test_benchmark_corpus.py`**:
   - Created 10 automated unit tests verifying seed reproducibility, manifest validation, C1 arithmetic, C3 gating, C7 terminology, CI storage ceilings, pre-flight safety, oracle digest soundness, and full C1–C7 matrix generation.
5. **`.gitignore`**:
   - Added `benchmarks/corpora/` and `corpora/` to avoid committing large benchmark datasets.
6. **`agent/`**:
   - Updated `TODO.md`, `CURRENT_TASK.md`, `CHECKPOINT.md`, and `HANDOFF.md`.

## CLI Usage Quick Reference
```bash
# List named standard profiles
python benchmarks/generator/generate.py --list

# Generate standard corpus (e.g. C1)
python benchmarks/generator/generate.py --corpus C1 --out-dir benchmarks/corpora/C1 --seed 12345

# Generate miniature test corpus for rapid testing
python benchmarks/generator/generate.py --corpus C2 --scale 0.005 --out-dir temp_c2 --seed 42

# Validate an existing corpus against its manifest.json
python benchmarks/generator/generate.py --validate benchmarks/corpora/C1

# Generate Developer-Hardware-Only corpus C3 (requires flag)
python benchmarks/generator/generate.py --corpus C3 --out-dir benchmarks/corpora/C3 --allow-developer-hardware
```

## Verification Run
```powershell
python tests/phase4_differential.py --offline
# -> All offline self-tests PASS

python tests/test_benchmark_corpus.py -v
# -> Ran 10 tests in ~5s: OK

git diff origin/main -- src/
# -> Completely empty (immutability preserved)
```

## What should the next agent do?
- The next task in the queue is **T005 — J2 interpreter/native baseline benchmark** on `macos-15` (arm64).
- Do NOT modify `src/*.j2`.
- Target `macos-15` runner environment for J2 benchmarking per research register.
- Use explicit `j2 run --allow-fs` for Baseline A and `./build/dupe` with `J2_ALLOW_FS=1` for Baseline B.
- Use concrete control program `data = collect(1..2000000); print(sum(data))` for Baseline C.
