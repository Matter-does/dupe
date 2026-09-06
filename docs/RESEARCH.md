# Research Register: Verified Technical & Competitive Intelligence

**Status:** Fact-Checked & Remediated (Post-Independent Review)  
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

### Native Execution & Control Clarifications

- **`J2_FORCE_NATIVE` vs `J_FORCE_NATIVE`:** Official J2 documentation (`j2-lang.org/docs/parallelism.html` and `execution.html`) states that `J2_FORCE_NATIVE=1` causes the J2 runner to lower code to native instructions. However, its interaction with runtime capabilities (`J2_ALLOW_FS=1`) in J2 0.1.0 is unverified, and it is **not part of the verified `dupe` project contract**. `J_FORCE_NATIVE` (without the "2") was a historical typo in earlier CI configurations. For `dupe`, standalone native execution is achieved and verified exclusively via genuine `j2 build src/main.j2 -o build/dupe` with the verified runtime capability `J2_ALLOW_FS=1`.
- **Undocumented Controls:** `J2_PARALLEL=0`, `J2_NO_NATIVE`, `J2_NO_NESTED`, and `J2_DEBUG` are unverified (Grade E). They must **never** be treated as part of the project contract or assumed in benchmark harnesses.

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

## 4. J2 0.1.0: Verified Execution Modes & Platform Matrix

### 4.1 Interpreter Execution (`j2 run`) — Grade A
The official J2 documentation defines `j2 run file.j2` as interpreter execution. It provides rapid execution without compilation overhead. Official docs state: *"Interpreted runs with `j2 run` are always serial; the parallelism belongs to native builds."* Filesystem access requires explicit capability permission `--allow-fs`.

### 4.2 Native Compilation (`j2 build`) — Grade A
The official J2 documentation defines:
```bash
j2 build src/main.j2 -o build/dupe
```
as standalone native compilation. J2 compiles code into native machine instructions (Mach-O arm64 on macOS 15) and automatically applies loop/call parallelization where safety can be proven.

Probed and validated in T002:
- Standalone compiled binaries do not accept interpreter flags like `--allow-fs`.
- The native runtime sandbox grants filesystem access when the environment variable `J2_ALLOW_FS=1` is present.
- Running without `J2_ALLOW_FS=1` triggers an immediate runtime capability violation (negative control verified).

### 4.3 Supported Platform Boundary — Grade A
Official J2 0.1.0 installation documentation (`j2-lang.org/download.html`) confirms:
> *"J2 0.1.0 supports macOS on Apple Silicon (`aarch64-apple-darwin`). It is the only platform the release has been built and tested for. Intel macOS, Linux, and Windows builds are planned."*

- **macOS (Apple Silicon arm64):** The only validated execution environment for J2 0.1.0 binaries. All J2 benchmarks in T005/T006 must target `macos-15` (arm64).
- **Linux:** No J2 0.1.0 release artifact exists. Linux execution of J2 binaries is deferred until an official Linux release is published. `ubuntu-latest` is retained solely for non-J2 offline tooling (Python differential oracle, fuzzer, and corpus generation).

---

## 5. J2 Automatic Parallelism: What Is Verified

### 5.1 Independent Work Distribution — Grade A (Documentation)
J2 native compilation identifies loops and function calls it can prove independent and distributes execution across CPU cores. Code containing potential side effects or dependencies it cannot prove safe remains serial.

Documented parallel shapes:
- Reductions over large sequences
- Element-wise loops
- Dense numerical kernels
- Independent calls to pure functions

The compiler incorporates purity analysis, induction-variable rewriting, reduction lowering, variable privatization, and a runtime cost model.

### 5.2 No User-Facing Thread API — Grade A
J2 explicitly presents an automatic parallelism model rather than an explicit concurrency or threading API (e.g. no `thread.spawn`, thread pools, or mutex primitives).

### 5.3 Workload Cost Model Thresholds — Grade A
J2's compiler applies a cost model that intentionally leaves small workloads serial. Official documentation (`j2-lang.org/docs/parallelism.html`) states:
> *"Small inputs are left alone; the reduction path engages at 32,768 elements, below which a serial loop is faster than any coordination."*

> **Implication for T005/T006:** A lack of speedup on small workloads (<32,768 items or tiny files) is expected runtime behavior, not compiler failure. Benchmarks must test across a spectrum of workload scales.

---

## 6. Status of J2 Runtime Controls

| Identifier | Classification | Status & Policy |
| :--- | :--- | :--- |
| `J2_FORCE_NATIVE` | **Documented / Non-Contract (Grade C)** | Documented in official J2 docs (`j2-lang.org/docs/parallelism.html`), but unverified in `dupe` capability contract. Native execution must use genuine `j2 build`. |
| `J_FORCE_NATIVE` | **Historical Typo (Rejected)** | Historical typo of `J2_FORCE_NATIVE` without the "2". Never supported. |
| `J2_PARALLEL=0` | **Grade E (Unverified)** | Not established as a public 0.1.0 interface. Do not use in benchmarks or contracts. |
| `J2_NO_NATIVE` | **Grade E (Unverified)** | Unverified internal name. Do not use. |
| `J2_NO_NESTED` | **Grade E (Unverified)** | Unverified internal name. Do not use. |
| `J2_DEBUG` | **Grade E (Unverified)** | Unverified benchmark interface. Do not use. |

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
- Child paths are formed via literal `fmt("{}/{}", base, name)` concatenation. Output JSON preserves discovery order.

### Memory Allocation for `fs.read_bytes`
- **Returned full bytes:** Grade A (verified).
- **Internal buffer copying / allocation mechanics:** Grade E (unverified). T004/T005 will observe actual heap and RSS behavior rather than assuming zero-copy or streaming behavior.

### Streaming / Incremental Hashing
- **Status:** Grade E / Unresolved. J2 0.1.0 exposes no streaming hash API (`hash.init`, `update`, `finish`). The pipeline must continue using `hash.sha256(fs.read_bytes(path))`.

### Compiler Inspection (`j2 emit-native`) — Grade A (Command) / Grade C (Interpretability)
`j2 emit-native file.j2` outputs backend native representations, providing Level 1 compiler evidence. However, whether specific emitted C/Rust constructs can be definitively interpreted as parallel runtime loops requires empirical correlation with Level 2 performance measurements.

---

## 9. Competitive Intelligence & Systems Lessons

### 9.1 Competitive Landscape Summary

| Tool | Language | Detection Algorithm | Storage & Concurrency Architecture |
| :--- | :--- | :--- | :--- |
| **dupeGuru** | Python / Qt | Filename/size prefilter → MD5/SHA-1/block hash → duplicate clusters | Serial Python engine with native helper; rich desktop GUI with delta, music/picture modes, deletion; focuses on user curation. |
| **fclones** | Rust | Walk → size groups → inode filter → prefix/suffix hash → full hash | Auto-tunes concurrency based on SSD vs HDD; warns that multi-threading large reads destroys HDD throughput. |
| **Czkawka** | Rust | Size grouping → partial prehash → full hash | Parallelizes prehash stage; relies on hash strength; maintains persistent cache. |
| **fdupes** | C | Size check → MD5 signature → byte-by-byte comparison | Serial traversal; paranoid verification confirms every byte before declaring duplicate. |
| **jdupes** | C | Size check → first-block hash → full hash → byte comparison | Staged candidate exclusion; explicit warning against destructive action on partial hashes. |
| **rmlint** | C | Staged hashing across multiple hash families | Supports paranoid byte-by-byte comparison mode; focuses on reflink/hardlink creation. |
| **duperemove** | C | Extent-level sub-file chunking and hashing | Separates I/O and CPU worker pools; interacts with Btrfs/XFS kernel deduplication. |

### 9.2 Key Systems Takeaway
Mature tools achieve high performance by **reducing expensive work through staged candidate filtering** (size → partial hash → full hash) and **adapting concurrency to the physical storage topology** (avoiding disk head thrashing on HDDs).

`dupe` will not immediately implement partial hashing. Doing so would conflate algorithm optimization with compiler parallelism evaluation. The Phase 3 exact-duplicate algorithm remains our reference baseline.

---

## 10. Filesystem Performance Model

Total execution time decomposes into distinct operational stages:

$$T_{total} = T_{discovery} + T_{metadata} + T_{selection} + T_{read} + T_{hash} + T_{group} + T_{output}$$

### Stage Limiting Factors

| Stage | Primary Bottleneck | Grade | J2 Parallelism Potential |
| :--- | :--- | :---: | :--- |
| **$T_{discovery}$** | Directory traversal latency, OS metadata calls | **B** | Low (sequential recursive traversal) |
| **$T_{metadata}$** | Per-file `stat` / `metadata` latency | **C** | Moderate (if metadata collection is decoupled) |
| **$T_{selection}$** | CPU sorting and size grouping | **B** | Low (fast in-memory filter) |
| **$T_{read}$** | Storage bus bandwidth, OS page cache, read latency | **B** | Mixed (SSD handles parallel reads; HDD degrades) |
| **$T_{hash}$** | CPU instruction throughput, memory bandwidth | **D** | High (independent pure computation over byte arrays) |
| **$T_{group}$** | In-memory hash indexing and aggregation | **C** | Low (dominated by memory allocation) |
| **$T_{output}$** | JSON string serialization, console I/O | **B** | Negligible |

### Storage Topology Dynamics: SSD vs HDD
- **SSDs / NVMes:** High random IOPS and parallel channels benefit from concurrent read operations.
- **HDDs:** Concurrency creates severe disk head contention and thrashing.
- **Project Scope:** Automated CI benchmarks target SSD-backed GitHub Actions virtual environments. Storage type must always be recorded in benchmark manifests.

### Corrected Hash Collision Mathematics
For a 256-bit cryptographic hash (SHA-256) and $n$ independently distributed files, the birthday-bound collision probability is approximated by:

$$P \approx \frac{n(n - 1)}{2 \cdot 2^{256}}$$

For an extreme corpus of $n = 10^{15}$ (one quadrillion) files:

$$P \approx \frac{10^{30}}{2 \cdot 1.1579 \times 10^{77}} \approx 4.31 \times 10^{-48}$$

*(Under the birthday-bound approximation; corrects previous external estimates of $10^{-27}$.)*  
For 128-bit hashes at the same scale, $P \approx 1.47 \times 10^{-9}$. In all cases, `dupe` differential correctness in T002 independently guarantees soundness via pairwise byte-identity checks rather than relying on theoretical collision resistance.

---

## 11. Research Hypotheses (H1–H9)

The following hypotheses guide T005 and T006 experimental designs:

- **H1 (Grade D):** Filesystem I/O loops (`fs.read_bytes`) will constrain J2 automatic parallelization compared to pure computation loops due to capability sandbox and system call boundaries.
- **H2 (Split):**
  * *Principle (Grade B):* J2 native compilation automatically parallelizes supported pure/independent numerical loops and reductions over 32,768 elements.
  * *Control Hypothesis (Grade D):* The selected T006-A pure control workload will be lowered into parallel machine code and exhibit measurable multi-core speedup on `macos-15`.
- **H3 (Grade D):** Pure in-memory hashing over pre-allocated byte buffers will exhibit measurable multi-core scaling under J2 native compilation.
- **H4 (Grade D):** Compute-heavy hashing workloads will show clearer speedup than end-to-end filesystem scanning, where storage and traversal overhead attenuate compiler gains.
- **H5 (Grade C):** End-to-end duplicate detection performance will be dominated by filesystem discovery and read I/O on small files, shifting to CPU hashing only on large candidate files.
- **H6 (Grade C):** Multi-core scaling on the 3-core `macos-15` runner will plateau early when storage bandwidth or coordination overhead matches hash computation time.
- **H7 (Grade B):** Many-small-file workloads will exhibit high metadata/traversal overhead and minimal speedup, whereas few-large-file workloads will be bounded by storage read throughput.
- **H8 (Grade B):** Same-size candidate collision density determines the number of full file hashes required ($N_{full} = N_{candidates}$), dictating the CPU load of the pipeline.
- **H9 (Grade D):** The synthetic workload that best demonstrates J2 automatic parallelism (dense in-memory pure hashing) is unrepresentative of real-world filesystem distributions.

---

## 12. Benchmark Corpus Specification (T004 Input)

### CI Hardware Budget

| Runner Platform | Architecture | vCPUs | RAM | SSD Scratch Space | Purpose |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`macos-15`** | Apple Silicon (arm64) | 3 | 7 GB | 14 GB | **Primary J2 Execution & Benchmarking** |
| **`ubuntu-latest`** | x86_64 | 4 | 16 GB | 14 GB | Offline Differential, Oracle, Corpus Generation |

> **Hard Storage Constraint:** Automated CI benchmark corpora must not exceed **1 GB** total size to ensure safe execution without runner disk exhaustion. Multi-gigabyte (5 GB+) corpora are designated developer-hardware only.

### 12.1 Controlled Workload Dimensions
The generator allows structured control over 8 workload parameters (with documented interactions):

1. **Dimension A — File Count:** `1K`, `10K`, `50K`, `100K` *(interacts with total size to fix average file size)*
2. **Dimension B — Total Data Size:** `100 MB`, `200 MB`, `1 GB` (Standard CI), `5 GB` (Developer-only)
3. **Dimension C — Size Distribution:**
   - `tiny-heavy`: <4 KB (metadata/traversal bound)
   - `small-heavy`: 4 KB – 64 KB
   - `large-heavy`: 1 MB – 10 MB (I/O & hash bound)
   - `mixed`: Pareto/power-law distribution
4. **Dimension D — Duplicate Ratio:** `0%` (unique), `5%`, `10%`, `30%`, `50%`, `80%`, `90%` *(defined as `duplicate_files / total_files`)*
5. **Dimension E — Same-Size Collision Density:**
   - `low`: unique sizes per file
   - `medium`: small size clusters
   - `high` (Adversarial): many distinct files sharing identical byte sizes to stress candidate filtering
6. **Dimension F — Tree Hierarchy:**
   - `flat`: single directory
   - `shallow-wide`: 1–2 levels, 500+ files per folder
   - `deep`: 8–15 nested subdirectories
   - `mixed`: balanced branching factor
7. **Dimension G — Content Similarity Structure:**
   - `distinct`: distinct prefixes and suffixes
   - `shared-prefix`: shared prefix, distinct suffix
   - `shared-suffix`: distinct prefix, shared suffix
   - `exact`: exact byte identity
8. **Dimension H — Cache State:**
   - `initial-run`: first execution after corpus generation in a fresh job
   - `warm-repeated`: successive executions within the same job measuring steady-state variance

### 12.2 Standard Named Corpora (C1–C7)

| Corpus ID | Name | Files | Target Size | CI / Dev | Characteristics & Purpose |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **C1** | Metadata Heavy | 50,000 | ~200 MB | **CI** | Tiny files (<4 KB, avg 4 KB), wide tree, 5% duplicate ratio. Isolates discovery and metadata overhead. *(Mathematically verified: $50\text{K} \times 4\text{ KB} \approx 200\text{ MB}$.)* |
| **C2** | Balanced Baseline | 10,000 | ~1 GB | **CI** | Mixed sizes (avg 100 KB), balanced tree, 30% duplicate ratio. Realistic everyday filesystem baseline. |
| **C3** | Large-File Throughput | 200–500 | ~1–2 GB | **Dev Only** | Large files (1–10 MB), shallow tree, 10% duplicate ratio. Exceeds 1 GB CI cap; tests sequential I/O and hash throughput. |
| **C4** | High Duplicate Density | 10,000 | ~1 GB | **CI** | 80% duplicate ratio in large clusters. Stresses grouping, aggregation, and reclaimable-byte math. |
| **C5** | Same-Size Adversarial | 20,000 | ~1 GB | **CI** | 100% same-size candidate collision, distinct byte content. Forces all candidates into full SHA-256 hashing. |
| **C6** | Mixed Realistic | 10,000 | ~1 GB | **CI** | Power-law distribution, realistic hierarchy, 30% duplicates. Primary live demo workload. |
| **C7** | Cache Transition | 10,000 | ~1 GB | **CI** | Repeated runs of C2/C6 (run 1 initial, runs 2–3 warm) to quantify warm-state transition and run-to-run variance. |

### 12.3 Corpus Manifest Schema (`manifest.json`)
Every generated corpus must output a machine-readable JSON manifest alongside the file tree:

```json
{
  "schema_version": 1,
  "corpus_id": "C5",
  "seed": 12345,
  "generator_version": "git-sha",
  "file_count": 20000,
  "total_bytes": 1073741824,
  "duplicate_ratio": 0.3,
  "duplicate_groups": 1500,
  "duplicate_files": 6000,
  "same_size_candidate_files": 20000,
  "size_profile": "same_size_adversarial",
  "directory_shape": "shallow_wide",
  "similarity_profile": "distinct",
  "expected_reclaimable_bytes": 241172480,
  "expected_result_digest": "sha256-of-deterministic-json-output"
}
```

---

## 13. Baseline Benchmark Methodology (T005 Input)

T005 establishes three distinct baselines on `macos-15` (arm64):
1. **Baseline A — J2 Interpreter Baseline:**
   ```bash
   j2 run --allow-fs src/main.j2 <corpus_path> --json
   ```
   *Note:* Uses explicit `j2 run` to guarantee interpreted serial execution.
2. **Baseline B — Compiled Native Baseline:**
   ```bash
   j2 build src/main.j2 -o build/dupe
   J2_ALLOW_FS=1 ./build/dupe <corpus_path> --json
   ```
3. **Baseline C — Concrete J2 Parallelism Control:**
   ```j2
   data = collect(1..2000000)
   print(sum(data))
   ```
   *Source:* `j2-lang.org/docs/parallelism.html`. Proves compiler multi-core lowering on `macos-15` before interpreting `dupe` results.

### Measurement Protocols
- **Timing Metric:** Mandatory total process wall-clock time (`wall_time_ms`). Internal stage timings ($T_{discovery}$, $T_{read+hash}$, $T_{group}$) are optional/deferred pending a verified runtime timing API.
- **Repetitions:** 3 warmup runs + 7 measured iterations for microbenchmarks; 1 warmup + 3–5 measured iterations for filesystem workloads.
- **Metadata Captured:** J2 version (`j2 0.1.0`), OS kernel, 3-vCPU Apple Silicon hardware, RAM, Git commit, corpus manifest hash.

---

## 14. Automatic Parallelism Experiment (T006 Input)

T006 executes an incremental 4-stage experimental ladder:

```text
[T006-A] Known Pure Parallel Workload (Control: sum(collect(1..2000000)))
   ↓
[T006-B] Pure In-Memory Hashing (Isolates CPU/hashing parallel lowering)
   ↓
[T006-C] Filesystem Read + Hash (Evaluates capability/syscall interaction)
   ↓
[T006-D] Full dupe Pipeline (Evaluates total real-world application performance)
```

### Observability Hierarchy
- **Level 1 — Compiler IR / Backend Source:** Inspect `j2 emit-native` for parallel loop lowering (hedged with Level 2 correlation).
- **Level 2 — Empirical Runtime Speedup:** Compare wall-clock time against serial-equivalent native baseline.
- **Level 3 — External OS Counters:** Profile syscalls and context switches where available.
- **Level 4 — CPU Core Utilization:** Measure aggregate multi-core CPU load across the 3 cores.
- **Level 5 — Result Validation:** Ensure bit-for-bit output JSON identity across all execution modes.

---

## 15. Second Workload Recommendation (T007 Input)

### Checksum Inventory Workload — Grade B/C
Rather than adding destructive operations or fuzzy matching, `dupe` will implement a **File Checksum Inventory** pass:

```text
Recursive Discovery → FileRecord[] → Parallel Read & SHA-256 → Emitted Manifest / Checksum Ledger
```

### Architectural & Scope Rules
- **Additive Implementation:** T007 must be implemented as an additive module or CLI sub-command. It must **NOT** refactor or modify frozen Phase 3 `src/*.j2` code.
- **Timing:** Omit mandatory internal elapsed time formatting pending verified J2 timing API resolution.
- **CLI Argv:** Explicitly account for sub-command argv shift (`dupe checksum <path>`).

---

## 16. Out-of-Scope Scope Boundaries

### What We Will Build
- Deterministic seed-based benchmark corpus generator and schema (`benchmarks/generator/`).
- Staged benchmark harness measuring baselines and parallel speedup.
- Pure in-memory hashing and filesystem read+hash probes.
- Additive checksum inventory analysis pass.
- Machine-readable benchmark results aggregator.

### What We Will NOT Build (Hackathon Core Non-Goals)
- File deletion, trash management, or destructive operations.
- Fuzzy filename or media/image similarity matching.
- Desktop GUI cleanup suite or complex interactive selectors.
- Persistent cross-run deduplication databases or caching daemons.
- Kernel-level reflink/extent deduplication (`ioctl` mutation).

---

## 17. Sources & Primary Documentation Ledger

| Source Title | Organization / Publisher | URL | Publication / Access Date | Supported Finding / Claim | Grade |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Automatic Parallelism** | J2 Language Project | `https://j2-lang.org/docs/parallelism.html` | 2026-07-07 / 2026-09-06 | Auto-parallel shapes, 32,768-element reduction threshold, `J2_FORCE_NATIVE=1`, serial interpreter, control program | **A** |
| **How J2 Runs** | J2 Language Project | `https://j2-lang.org/docs/execution.html` | 2026-07-07 / 2026-09-06 | Two engines, native compilation lowering, `time.elapsed_ms` reference | **A** |
| **Download J2** | J2 Language Project | `https://j2-lang.org/download.html` | 2026-07-07 / 2026-09-06 | Apple Silicon macOS sole platform for 0.1.0; absence of Linux release | **A** |
| **GitHub-Hosted Runners** | GitHub Documentation | `https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners` | 2026-09-06 | `macos-15` (3 vCPU / 7 GB RAM / 14 GB SSD), `ubuntu-latest` (4 vCPU / 16 GB RAM / 14 GB SSD) | **A** |
| **fclones Documentation** | fclones Project | `https://github.com/pkolaczk/fclones` | 2026-09-06 | Staged hashing, SSD/HDD storage-adaptive concurrency | **B** |
| **Czkawka Repository** | Czkawka Project | `https://github.com/qarmin/czkawka` | 2026-09-06 | Size grouping, prehash, full hash stages, cache integration | **B** |
| **fdupes Manual** | Adrian Lopez | `https://github.com/adrianlopezroche/fdupes` | 2026-09-06 | Size comparison, MD5 signature, byte-by-byte verification | **B** |
| **jdupes Documentation** | Jody Bruchon | `https://github.com/jbruchon/jdupes` | 2026-09-06 | First-block hash candidate exclusion, safety warnings | **B** |
| **rmlint Documentation** | rmlint Project | `https://rmlint.readthedocs.io/` | 2026-09-06 | Multi-stage hashing, paranoid byte-for-byte check | **B** |
| **duperemove Manual** | Mark Fasheh | `https://github.com/markfasheh/duperemove` | 2026-09-06 | Extent-level deduplication, I/O and CPU pool separation | **B** |
| **dupeGuru Project** | Hardcoded Software | `https://github.com/arsenetar/dupeguru` | 2026-09-06 | Desktop cleanup workflow, UI curation, serial Python execution | **B** |
