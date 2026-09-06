# T005 — J2 Interpreter/Native Baseline Benchmark Report

**Task ID:** T005  
**Timestamp:** 2026-09-06T14:09:17Z  
**Platform:** Darwin 24.6.0 (arm64)  
**CPU:** 3 vCPUs  
**Memory:** 7.0 GB RAM  
**Runner:** `34038191455`  
**Git Commit:** `fb5f57aa49af02fa6171de9b761e79d9307b475f`  
**J2 Version:** `j2 0.1.0`  

---

## Baseline C — Pure J2 Parallelism Control

```j2
data = collect(1..2000000)
print(sum(data))
```

- **Ground Truth Result:** `2000001000000`
- **Correctness Verified:** `PASS`
- **Native Build Time:** `1169.81 ms`
- **Native Speedup Factor:** `1.36x`

| Metric | Interpreter (`j2 run`) | Native Binary (`j2 build`) | Speedup |
| :--- | :---: | :---: | :---: |
| **Median Wall Time** | **79.66 ms** | **58.59 ms** | **1.36x** |
| Mean Wall Time | 79.50 ms | 58.09 ms | — |
| Min Wall Time | 70.47 ms | 55.27 ms | — |
| Max Wall Time | 88.39 ms | 61.37 ms | — |
| Std Dev | 5.42 ms | 2.11 ms | — |
| Iterations (Warmup / Measured) | 3 / 7 | 3 / 7 | — |

## Filesystem Workload Baselines (Baseline A vs Baseline B)

| Corpus | Scale | Seed | Files | Candidates | Interp Median (ms) | Native Median (ms) | Native Speedup | Direct JSON Match | Digest Match |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C1** | 0.01 | 12345 | 500 | 122 | 2624.33 | 2669.61 | **0.98x** | PASS | PASS |
| **C2** | 0.01 | 12345 | 100 | 30 | 274.61 | 223.07 | **1.23x** | PASS | PASS |
| **C4** | 0.01 | 12345 | 100 | 80 | 278.15 | 246.33 | **1.13x** | PASS | PASS |
| **C5** | 0.01 | 12345 | 200 | 200 | 474.49 | 438.66 | **1.08x** | PASS | PASS |
| **C6** | 0.01 | 12345 | 100 | 30 | 237.31 | 214.73 | **1.11x** | PASS | PASS |
| **C7** | 0.01 | 12345 | 100 | 30 | 242.40 | 224.92 | **1.08x** | PASS | PASS |

> **Workload Topology Note on C7:** Corpus C7 is generated using parameters identical to C2 (10,000 files, ~1 GB target, 30% duplicate ratio, mixed directory hierarchy). For a given seed, C7 and C2 contain byte-identical files. C7 is designed specifically to measure warm-cache repeated-run variance over the standard baseline topology rather than to serve as an independent workload.

### Detailed Throughput Rates

| Corpus | Files/sec (Interp) | Files/sec (Native) | Cand/sec (Interp) | Cand/sec (Native) | MB/sec (Interp) | MB/sec (Native) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **C1** | 190.5 | 187.3 | 46.5 | 45.7 | 0.19 | 0.18 |
| **C2** | 364.1 | 448.3 | 109.2 | 134.5 | 8.31 | 10.23 |
| **C4** | 359.5 | 406.0 | 287.6 | 324.8 | 27.88 | 31.48 |
| **C5** | 421.5 | 455.9 | 421.5 | 455.9 | 21.08 | 22.80 |
| **C6** | 421.4 | 465.7 | 126.4 | 139.7 | 9.62 | 10.63 |
| **C7** | 412.5 | 444.6 | 123.8 | 133.4 | 9.41 | 10.15 |

## Compiler Inspection (`j2 emit-native`)

### dupe_main
- **Has Parallel Constructs:** `False`
- **Matched Constructs:** `[]`
- **Evidence Excerpts:** None (no multi-core or parallel primitives detected)

```rust
use j2_runtime::prelude::*;
use j2_runtime::value::{J2Value, J2Func, J2FuncClause};
use j2_runtime::error::{J2Err, J2ErrKind, J2Result};
use j2_runtime::flow::J2Flow;
#[allow(unused_imports)]
use j2_runtime::convert::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

#[derive(Clone)]
struct Env {
    table: HashMap<String, (J2Value, bool)>,
    locals: std::collections::HashSet<String>,
}

type EnvRef = Rc<RefCell<Env>>;

thread_local! {
    static GLOBALS: RefCell<HashMap<String, (J2Value, bool)>> = RefCell::new(HashMap::new());
```

### pure_control
- **Has Parallel Constructs:** `False`
- **Matched Constructs:** `[]`
- **Evidence Excerpts:** None (no multi-core or parallel primitives detected)

```rust
use j2_runtime::prelude::*;
use j2_runtime::value::{J2Value, J2Func, J2FuncClause};
use j2_runtime::error::{J2Err, J2ErrKind, J2Result};
use j2_runtime::flow::J2Flow;
#[allow(unused_imports)]
use j2_runtime::convert::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

#[derive(Clone)]
struct Env {
    table: HashMap<String, (J2Value, bool)>,
    locals: std::collections::HashSet<String>,
}

type EnvRef = Rc<RefCell<Env>>;

thread_local! {
    static GLOBALS: RefCell<HashMap<String, (J2Value, bool)>> = RefCell::new(HashMap::new());
```

## Scientific Findings & Baseline Conclusions

- Interpreter baseline (Baseline A) and native binary baseline (Baseline B) successfully established on macOS Apple Silicon.
- Bit-for-bit JSON equivalence between interpreter and native execution holds across all measured standard corpora.
- Computed JSON digests strictly match T004 manifest expected_result_digest, verifying algorithm soundness and determinism.
- Baseline C pure J2 control (2,000,000 element integer reduction) successfully executes with verified ground-truth output (2000001000000).
- CRITICAL SCIENTIFIC DISTINCTION: Native binary speedup over interpreter reflects unboxed native CPU execution and absence of interpreter dispatch overhead. Native-vs-interpreter speed difference is NOT in itself proof of automatic parallelism.
- Compiler backend inspection of `j2 emit-native` shows sequential lowering with thread-local storage (`thread_local! static GLOBALS`); no multi-core primitives (such as rayon, par_iter, or thread::spawn) were detected.

## Limitations & Deferred Questions

- Internal stage timing (T_discovery, T_hash, T_group) remains deferred pending verified J2 timing runtime API.
- Automatic parallelism multi-core isolation requires the dedicated 4-stage experimental ladder defined in T006.
- Compiler emission from `j2 emit-native` provides structural backend source but requires runtime correlation to confirm multi-core concurrency.
