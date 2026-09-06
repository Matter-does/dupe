# Research Register: Verified Technical & Competitive Intelligence

**Status:** Fact-Checked & Corrected  
**Project:** `Matter-does/dupe`  
**Target Release:** J2 0.1.0  
**Research Role:** Authoritative foundation for T004 (Corpus), T005 (Baselines), T006 (Parallelism), and T007 (Checksum Inventory)

---

## 1. Executive Summary

`dupe` is a **J2-native filesystem intelligence engine**, with exact duplicate file detection established and frozen as its first validated workload. The primary differentiator of `dupe` is not feature-for-feature parity with mature desktop cleanup tools; it is using a realistic filesystem workload to investigate J2's automatic parallelism and demonstrate, through reproducible measurements, where parallel compilation improves performance and where storage I/O, OS metadata, memory allocation, or serialization bottlenecks dominate.

J2 0.1.0 officially provides two execution paths:
1. Interpreter execution via `j2 run file.j2`
2. Standalone native binary compilation via `j2 build file.j2 -o out`

The native compiler automatically parallelizes loops and function calls when it can statically prove them safe and independent; code that cannot be proven safe remains strictly serial. J2 explicitly highlights reductions over large sequences, element-wise loops, dense kernels, and independent calls to pure functions as target parallelization patterns.

### Core Fact-Checking Correction: Undocumented J2 Controls

> **CRITICAL CONTRACT BOUNDARY:** There is no authoritative evidence that `J2_PARALLEL=0`, `J2_FORCE_NATIVE`, `J2_NO_NATIVE`, `J2_NO_NESTED`, or `J2_DEBUG` are supported public user-facing controls in J2 0.1.0.

They must **never** be treated as part of the project contract or assumed to exist. `J2_FORCE_NATIVE` was directly probed against J2 0.1.0 binaries during T002 and proven non-existent (native execution is achieved via `j2 build` and the verified runtime capability `J2_ALLOW_FS=1`). The other variables remain unverified and quarantined (Grade E).

### Baseline Workload Stability

The existing exact-duplicate detection implementation from Phase 3 is fully verified by Phase 4 differential correctness gates and must **not** be redesigned merely because mature external tools employ partial or staged hashing. The reference workload is frozen:

```text
recursive discovery
→ metadata collection (size)
→ candidate reduction by size (count >= 2)
→ exact SHA-256 hashing of full file bytes
→ duplicate grouping
→ deterministic output
```

### Experimental Progression Strategy

To rigorously separate compiler capabilities from filesystem I/O constraints, all parallelism research follows an explicit ladder:

```text
Known J2 pure parallel workload (compiler control)
                    ↓
Pure in-memory hashing workload (CPU/algorithm isolate)
                    ↓
Filesystem read + hashing workload (I/O boundary entry)
                    ↓
Full dupe duplicate analysis pipeline (end-to-end impact)
```

---

## 2. Research Classification System

Every technical claim in this register is classified under an explicit evidence hierarchy:

| Grade | Classification | Definition |
| :--- | :--- | :--- |
| **A** | **Verified Fact** | Directly supported by primary official J2 documentation, runtime probes, or passing CI/test evidence |
| **B** | **Strongly Supported** | Multiple authoritative primary sources agree (e.g. established tool documentation, OS manuals) |
| **C** | **Reasonable Inference** | Solid technical deduction from systems engineering principles, pending empirical J2 verification |
| **D** | **Experimental Hypothesis** | Plausible model that must be explicitly measured by T005 / T006 |
| **E** | **Unknown / Unverified** | Insufficient evidence; must not be assumed or relied upon |

---

## 3. Current `dupe` Thesis

### Verified Definition — Grade A
`dupe` is a **J2-native filesystem intelligence engine** that uses exact duplicate analysis as its first workload and experimentally studies J2's automatic parallelism on realistic filesystem workloads.

### Strategic Boundaries
1. **Not a desktop clone:** Reject feature cloning of mature cleanup utilities (no destructive deletion, trash integration, fuzzy media matching, or persistent deduplication caches in core scope).
2. **Product question:** The research question is not *"Is dupe faster than fclones written in Rust?"* It is: *"What does J2's automatic parallelism actually do on realistic filesystem analysis, and where do bottlenecks shift across workload dimensions?"*
3. **Evidence standard:** All claims must be backed by executable probes, passing differential gates, or reproducible benchmark runs.

---

## 4. J2 0.1.0: Verified Execution Modes

### 4.1 Interpreter Execution (`j2 run`) — Grade A
The official J2 documentation defines `j2 run file.j2` as interpreter execution. It provides rapid execution without compilation overhead. Filesystem access requires explicit capability permission `--allow-fs`.

### 4.2 Native Compilation (`j2 build`) — Grade A
The official J2 documentation defines:
```bash
j2 build src/main.j2 -o build/dupe
```
as standalone native compilation. J2 compiles code into native machine instructions (Mach-O arm64 on macOS 15, ELF x86_64 on Linux) and automatically applies loop/call parallelization where safety can be proven.

Probed and validated in T002:
- Standalone compiled binaries do not accept interpreter flags like `--allow-fs`.
- The native runtime sandbox grants filesystem access when the environment variable `J2_ALLOW_FS=1` is present.
- Running without `J2_ALLOW_FS=1` triggers an immediate runtime capability violation (negative control verified).

---

## 5. J2 Automatic Parallelism: What Is Verified

### 5.1 Independent Work Distribution — Grade A
J2 native compilation identifies loops and function calls it can prove independent and distributes execution across CPU cores. Code containing potential side effects or dependencies it cannot prove safe remains serial.

Target compiler patterns include:
- Reductions over large sequences
- Element-wise loops
- Dense numerical kernels
- Independent calls to pure functions

The compiler incorporates purity analysis, induction-variable rewriting, reduction lowering, variable privatization, and a runtime cost model.

### 5.2 No User-Facing Thread API — Grade A
J2 explicitly presents an automatic parallelism model rather than an explicit concurrency or threading API (e.g. no `thread.spawn`, thread pools, or mutex primitives).

### 5.3 Workload Cost Model Thresholds — Grade A
J2's compiler applies a cost model that intentionally leaves small workloads serial. For example, reduction parallelization engages only beyond a substantial workload threshold.

> **Implication for T005/T006:** A lack of speedup on tiny datasets (<1 MB, few files) is expected runtime behavior, not compiler failure. Benchmarks must test across a spectrum of workload scales.

---

## 6. Quarantine of Undocumented J2 Controls

The following environment variables and switches have been claimed elsewhere but have **no authoritative verification in J2 0.1.0**:

| Identifier | Classification | Status & Policy |
| :--- | :--- | :--- |
| `J2_PARALLEL=0` | **Grade E (Unverified)** | Not established as a public 0.1.0 interface. **Do not use in benchmarks or contracts.** |
| `J2_FORCE_NATIVE` | **False (Rejected)** | Probed against J2 binaries in T002 and proven non-existent. Use genuine `j2 build`. |
| `J2_NO_NATIVE` | **Grade E (Unverified)** | Unverified internal name. **Do not use.** |
| `J2_NO_NESTED` | **Grade E (Unverified)** | Unverified internal name. **Do not use.** |
| `J2_DEBUG` | **Grade E (Unverified)** | Unverified benchmark interface. **Do not use.** |

---

## 7. Serial vs. Parallel Experimental Methodology

Because J2 0.1.0 does not expose an established, supported public flag to disable automatic parallelism:

### Path A: Official Control Discovery (Probe First)
Before benchmarking, probe the J2 0.1.0 binary to determine if a documented command-line flag or environment variable exists. If found, record its exact syntax, platform, version, and behavior, and freeze it.

### Path B: Source-Level Serial-Equivalent Baseline (Default)
If no official switch exists, construct a semantically serial native baseline at the source level (e.g. an accumulative loop with an intentional sequential dependency that suppresses parallel lowering while keeping total computation identical).

This baseline must be documented transparently as:
> **Serial-equivalent native baseline** (not *"J2 with parallelism disabled"*).

---

## 8. J2 Filesystem & Runtime APIs: Frozen Boundary

The runtime-verified API contract (`docs/J2-API-0.1.0.md`) freezes the following APIs:

```text
fs.list_dir(path)                  -> string[] (bare child names)
fs.metadata(path)                  -> { size, is_file, is_dir, modified_epoch }
fs.is_file(path)                   -> boolean (follows symlinks)
fs.is_dir(path)                    -> boolean (follows symlinks)
fs.exists(path)                    -> boolean
fs.read_bytes(path)                -> int[] (raw file bytes)
fs.read_file(path)                 -> string (UTF-8 text)
fs.read_lines(path)                -> string[]
hash.sha256(bytes)                 -> hex string (64 characters)
hash.md5 / sha512 / xxhash         -> verified symbols
proc.argv()                        -> string[]
json.parse(str)                    -> object / array
json.stringify(obj)                -> compact JSON string
sort(primitive_array)              -> sorted 1D array
fmt(template, ...)                 -> formatted string
```

### Directory Enumeration Semantics
- `fs.list_dir` returns bare child names without order guarantees.
- `dupe` enforces deterministic discovery order via `sort(fs.list_dir(path))`.
- Child paths are formed via `join_path(base, name)` with literal `fmt("{}/{}", base, name)` concatenation.

### Memory Allocation for `fs.read_bytes`
- **Returned full bytes:** Grade A (verified).
- **Internal buffer copying / allocation mechanics:** Grade E (unverified). T004/T005 will observe actual heap and RSS behavior rather than assuming zero-copy or streaming behavior.

### Streaming / Incremental Hashing
- **Status:** Grade E / Unresolved. J2 0.1.0 exposes no streaming hash API (`hash.init`, `update`, `finish`). The pipeline must continue using `hash.sha256(fs.read_bytes(path))`.

### Compiler Inspection (`j2 emit-native`) — Grade A
`j2 emit-native file.j2` outputs backend native representations, providing Level 1 compiler evidence to verify whether specific loops or functions are lowered into parallel constructs.

---

## 9. Competitive Intelligence & Systems Lessons

### 9.1 Competitive Landscape Summary

| Tool | Implementation | Detection Algorithm | Storage & Concurrency Architecture |
| :--- | :--- | :--- | :--- |
| **fclones** | Rust | Walk → size groups → inode filter → prefix/suffix hash → full hash | Auto-tunes concurrency based on SSD vs HDD; warns that multi-threading large reads destroys HDD throughput |
| **Czkawka** | Rust | Size grouping → partial prehash → full hash | Parallelizes prehash stage; relies on hash strength; maintains persistent cache |
| **fdupes** | C | Size check → MD5 signature → byte-by-byte comparison | Serial traversal; paranoid verification confirms every byte before declaring duplicate |
| **jdupes** | C | Size check → first-block hash → full hash → byte comparison | Staged candidate exclusion; explicit warning against destructive action on partial hashes |
| **rmlint** | C | Staged hashing across multiple hash families | Supports paranoid byte-by-byte comparison mode; focuses on reflink/hardlink creation |
| **duperemove** | C | Extent-level sub-file chunking and hashing | Separates I/O and CPU worker pools; interacts with Btrfs/XFS kernel deduplication |

### 9.2 Key Systems Takeaway
Mature tools achieve high performance by **reducing expensive work through staged candidate filtering** (size → partial hash → full hash) and **adapting concurrency to the physical storage topology** (avoiding disk head thrashing on HDDs).

`dupe` will not immediately implement partial hashing. Doing so would conflate algorithm optimization with compiler parallelism evaluation. The Phase 3 exact-duplicate algorithm remains our reference baseline.

---

## 10. Filesystem Performance Model

Total execution time decomposes into distinct operational stages:

$$T_{total} = T_{discovery} + T_{metadata} + T_{selection} + T_{read} + T_{hash} + T_{group} + T_{output}$$

### Stage Limiting Factors

| Stage | Primary Bottleneck | J2 Parallelism Potential |
| :--- | :--- | :--- |
| **$T_{discovery}$** | Filesystem directory traversal latency, OS metadata calls | Low (sequential recursive traversal) |
| **$T_{metadata}$** | Per-file `stat` / `metadata` latency | Moderate (if metadata collection is decoupled) |
| **$T_{selection}$** | CPU sorting and size grouping | Low (fast in-memory filter) |
| **$T_{read}$** | Storage bus bandwidth, OS page cache, read latency | Mixed (SSD handles parallel reads; HDD degrades) |
| **$T_{hash}$** | CPU instruction throughput, memory bandwidth | **High** (independent pure computation over byte arrays) |
| **$T_{group}$** | In-memory hash indexing and aggregation | Low (dominated by memory allocation) |
| **$T_{output}$** | JSON string serialization, console I/O | Negligible |

### Storage Topology Dynamics: SSD vs HDD
- **SSDs / NVMes:** High random IOPS and parallel channels benefit from concurrent read operations.
- **HDDs:** Concurrency creates severe disk head contention and thrashing.
- **Project Scope:** Automated CI and hackathon benchmarks target SSD-backed virtual environments. Storage type must always be recorded in benchmark manifests.

### Corrected Hash Collision Mathematics
For a 256-bit cryptographic hash (SHA-256) and $n$ independently distributed files, the birthday-bound collision probability is approximated by:

$$P \approx \frac{n(n - 1)}{2 \cdot 2^{256}}$$

For an extreme corpus of $n = 10^{15}$ (one quadrillion) files:

$$P \approx \frac{10^{30}}{2 \cdot 1.1579 \times 10^{77}} \approx 4.31 \times 10^{-48}$$

*(Corrects previous erroneous external estimates of $10^{-27}$.)*  
For 128-bit hashes at the same scale, $P \approx 1.47 \times 10^{-9}$. In all cases, `dupe` differential correctness in T002 independently guarantees soundness via pairwise byte-identity checks.

---

## 11. Research Hypotheses (H1–H9)

The following hypotheses guide T005 and T006 experimental designs:

- **H1 (Grade D):** Filesystem I/O loops (`fs.read_bytes`) will constrain J2 automatic parallelization compared to pure computation loops due to capability sandbox and system call boundaries.
- **H2 (Grade A):** J2 native compilation will automatically parallelize known pure independent numerical loops and reductions.
- **H3 (Grade D):** Pure in-memory hashing over pre-allocated byte buffers will exhibit measurable multi-core scaling under J2 native compilation.
- **H4 (Grade D):** Compute-heavy hashing workloads will show clearer speedup than end-to-end filesystem scanning, where storage and traversal overhead attenuate compiler gains.
- **H5 (Grade C):** End-to-end duplicate detection performance will be dominated by filesystem discovery and read I/O on small files, shifting to CPU hashing only on large candidate files.
- **H6 (Grade B/C):** Scaling on multi-core runners will plateau when storage bandwidth or thread synchronization overhead matches hash computation time.
- **H7 (Grade B/C):** Many-small-file workloads will exhibit high metadata/traversal overhead and minimal speedup, whereas few-large-file workloads will be bounded by storage read throughput.
- **H8 (Grade B/C):** Same-size candidate collision density determines the number of full file hashes required ($N_{full} = N_{candidates}$), dictating the CPU load of the pipeline.
- **H9 (Grade D):** The synthetic workload that best demonstrates J2 automatic parallelism (dense in-memory pure hashing) is unrepresentative of real-world filesystem distributions.

---

## 12. Benchmark Corpus Specification (T004 Input)

### CI Hardware Budget
Standard public GitHub Actions runners (`ubuntu-latest`, `macos-15`) provide:
- **CPU:** 4 vCPUs
- **RAM:** 16 GB
- **SSD Storage:** ~14 GB available scratch space

> **Hard Constraint:** Automated CI benchmark corpora must not exceed **1 GB** total size, leaving ample margin for build tools, OS caches, and test artifacts. Multi-gigabyte (5 GB+) corpora are designated developer-hardware only.

### 12.1 Orthogonal Workload Dimensions

1. **Dimension A — File Count:** $1\text{K}, 10\text{K}, 50\text{K}, 100\text{K}$
2. **Dimension B — Total Data Size:** $100\text{ MB}, 1\text{ GB}$ (CI), $5\text{ GB}$ (developer only)
3. **Dimension C — Size Distribution:** Tiny-heavy (<4 KB), Small-heavy (<64 KB), Large-heavy (>1 MB), Mixed
4. **Dimension D — Duplicate Ratio:** 0% (all unique), 10%, 50%, 90%
5. **Dimension E — Same-Size Collision Density:** Low (distinct sizes), Medium, High (many distinct files sharing exact byte sizes)
6. **Dimension F — Directory Hierarchy:** Flat, Shallow-Wide, Deep, Mixed
7. **Dimension G — Similarity Structure:** Distinct prefixes, identical prefixes, identical suffixes, exact duplicates
8. **Dimension H — Cache State:** Fresh-job runner instance vs. warm-state repeated run

### 12.2 Standard Named Corpora (C1–C7)

- **C1: Metadata-Heavy** — 50K tiny files (~500 MB), wide tree, 5% duplicates. Tests traversal and metadata overhead.
- **C2: Balanced Baseline** — 10K mixed files (~1 GB), moderate depth, 30% duplicates. Realistic everyday filesystem baseline.
- **C3: Large-File Throughput** — 200 large files (~2 GB), shallow tree, 20% duplicates. Tests pure read and hash throughput.
- **C4: High-Duplicate Density** — 10K files (~1 GB), 80% duplicates across large duplicate clusters. Tests grouping and aggregation.
- **C5: Same-Size Adversarial** — 20K files (~1 GB) sharing identical sizes but distinct byte contents. Forces 100% candidate survival into full SHA-256 hashing.
- **C6: Mixed Realistic** — 10K files (~1 GB), long-tailed power-law distribution, realistic hierarchy and duplicate density. Primary demo workload.
- **C7: Cache Transition** — Repeated runs of C2/C6 (Run 1 fresh-process, Run 2 warm, Run 3 warm) to measure OS page-cache impact.

### 12.3 Corpus Manifest Schema
Every generated corpus must emit a machine-readable `manifest.json`:
```json
{
  "schema_version": 1,
  "corpus_id": "C5",
  "seed": 12345,
  "generator_version": "git-sha",
  "file_count": 20000,
  "total_bytes": 1073741824,
  "duplicate_groups": 1500,
  "duplicate_files": 6000,
  "same_size_candidate_files": 20000,
  "size_profile": "same_size_adversarial",
  "directory_shape": "shallow-wide",
  "expected_reclaimable_bytes": 241172480,
  "expected_result_digest": "sha256-hex"
}
```

---

## 13. Baseline Benchmark Methodology (T005 Input)

T005 establishes three distinct baselines before testing parallel optimizations:
1. **Baseline A — Interpreter Baseline:** `j2 run --allow-fs src/main.j2 <corpus>`
2. **Baseline B — Compiled Native Baseline:** `j2 build src/main.j2 -o build/dupe && J2_ALLOW_FS=1 ./build/dupe <corpus>`
3. **Baseline C — Pure J2 Parallelism Control:** Documented J2 pure numerical parallel benchmark to prove the harness detects compiler parallelism.

### Measurement Protocols
- **Repetition:** 3 warmup runs + 7 measured iterations for microbenchmarks; 1 warmup + 3–5 measured iterations for filesystem workloads.
- **Metrics Captured:** Wall-clock time (ms), stage timings ($T_{discovery}$, $T_{read+hash}$, $T_{group}$), files/sec, MB/sec, CPU utilization (where available).
- **Environment Metadata:** OS kernel, CPU model, core count, RAM, runner ID, exact commit hash, exact J2 version (`j2 0.1.0`).

---

## 14. Automatic Parallelism Experiment (T006 Input)

T006 executes an incremental 4-stage experimental ladder:

```text
[T006-A] Known Pure Parallel Workload (Control: proves compiler auto-parallelism functions)
   ↓
[T006-B] Pure In-Memory Hashing (Isolates CPU/hashing parallel lowering)
   ↓
[T006-C] Filesystem Read + Hash (Evaluates capability/syscall interaction)
   ↓
[T006-D] Full dupe Pipeline (Evaluates total real-world application performance)
```

### Observability Hierarchy
- **Level 1 — Compiler IR / Backend Source:** Inspect `j2 emit-native` for parallel loop constructs.
- **Level 2 — Empirical Runtime Speedup:** Compare wall-clock time between compiled binary and serial baseline.
- **Level 3 — External OS Counters:** Profile process execution with OS profilers on developer hardware.
- **Level 4 — CPU Core Utilization:** Measure aggregate multi-core CPU load.
- **Level 5 — Result Validation:** Ensure bit-for-bit output identity across all execution modes.

---

## 15. Second Workload Recommendation (T007 Input)

### Checksum Inventory Workload — Grade B/C
Rather than adding destructive operations or fuzzy matching, `dupe` will implement a **File Checksum Inventory** pass:

```text
Recursive Discovery → FileRecord[] → Parallel Read & SHA-256 → Emitted Manifest / Checksum Ledger
```

### Architectural Rationale
- Reuses the core `FileRecord[]` discovery pipeline.
- Eliminates candidate filtering and duplicate grouping overhead, isolating file reading and hashing.
- Maximizes the volume of independent per-file work submitted to J2.
- Generates a reusable integrity ledger (e.g. `sha256sum`-compatible JSON format).

---

## 16. Out-of-Scope Scope Boundaries

### What We Will Build
- Deterministic seed-based benchmark corpus generator and schema (`benchmarks/generator/`).
- Staged benchmark harness measuring baselines and parallel speedup.
- Pure in-memory hashing and filesystem read+hash probes.
- Checksum inventory analysis pass.
- Machine-readable benchmark results aggregator.

### What We Will NOT Build (Hackathon Core Non-Goals)
- File deletion, trash management, or destructive operations.
- Fuzzy filename or media/image similarity matching.
- Desktop GUI cleanup suite or complex interactive selectors.
- Persistent cross-run deduplication databases or caching daemons.
- Kernel-level reflink/extent deduplication (`ioctl` mutation).

---

## 17. Evidence Ledger

| Fact / Finding | Evidence Grade | Source / Verification |
| :--- | :---: | :--- |
| `dupe` thesis: J2-native filesystem intelligence engine | **A** | `docs/PROJECT.md`, `AGENTS.md` |
| Exact duplicate detection as reference workload | **A** | `docs/PROJECT.md`, Phase 4 test suite |
| J2 native compiler automatic parallelism model | **A** | J2 0.1.0 official documentation |
| Standalone native compilation via `j2 build` | **A** | Verified in T002 CI (`build/dupe`) |
| Capability grant via `J2_ALLOW_FS=1` | **A** | Verified in T002 CI (negative control passed) |
| Non-existence of `J2_FORCE_NATIVE` | **A** | Probed against J2 binary strings in T002 |
| `J2_PARALLEL=0` unverified in 0.1.0 | **E** | Quarantined; no public documentation |
| `fs.read_bytes` returns full raw byte array | **A** | Verified in Phase 2 & T002 differential suite |
| No streaming hash API in J2 0.1.0 | **E** | Quarantined; unverified symbol |
| Standard GitHub runner limits (4 CPU / 16 GB / 14 GB SSD) | **A** | GitHub Actions official virtual environment docs |
| Rejection of 100 GB CI corpus | **A** | Derived from GitHub Actions runner storage limits |
| fclones storage-adaptive concurrency | **B** | fclones official documentation & source |
| fdupes byte-by-byte verification | **B** | fdupes official manual |
| Czkawka staged prehash/hash pipeline | **B** | Czkawka documentation |
| Corrected 256-bit collision bound ($4.3 \times 10^{-48}$ at $10^{15}$) | **A** | Standard birthday-bound probability calculation |
| Checksum inventory as optimal second workload | **B/C** | Architecture analysis; isolates I/O + hash |
