# J2 0.1.0 API & Execution Contract

**Project:** `dupe`  
**J2 version:** `0.1.0`  
**Contract status:** **FROZEN MVP BOUNDARY — RUNTIME-VERIFIED CORE**  
**Research date:** 2026-09-05  
**Validated target:** `aarch64-apple-darwin` on GitHub Actions `macos-15` / observed `arm64`

> This document freezes only behavior supported by runtime/compiler experiments or the official J2 0.1.0 documentation. A name that merely parses or compiles is **not** a verified API.

## Evidence source

Primary experimental source: GitHub Actions run `33958991636`, job `101287390940`, using the exact J2 0.1.0 Apple Silicon release archive.

Validated machine/runtime facts from that run:

```text
macOS 15.7.9
architecture: arm64
j2: 0.1.0
archive SHA-256: 6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75
```

The research run completed successfully. Its native equivalence probe built and executed a native binary and matched interpreter output (`15` / diff status `0`).

## Evidence policy

Every proposed J2 API follows this ladder:

1. **Compile-valid** — source is accepted.
2. **Runtime symbol verified** — referenced name resolves.
3. **Runtime semantics verified** — result/type/side effect matches intended use.
4. **Native equivalence verified** — interpreter and native agree where relevant.
5. **Frozen** — safe to use in `dupe`.

---

# 2.1 Language primitives

## Strings — **VERIFIED**

Double-quoted string literals and printing are runtime verified.

```j2
a = "hello"
print(a)
```

Do not assume unprobed string methods.

## Integers — **VERIFIED**

Integer literals, arithmetic, and typed `int` parameters work. Integer overflow is reported as a runtime `OverflowError`; the probe of `9223372036854775807 + 1` exited with status `1`.

Do not encode a broader integer-width claim beyond the observed behavior.

## Booleans — **VERIFIED**

`true` is a valid boolean literal and printed successfully in the Phase 2 language probe.

## Functions — **VERIFIED**

Ordinary functions and `give` return syntax are runtime verified.

```j2
func add(x: int, y: int) -> int = {
    give x + y
}
```

Functions are the preferred unit for structuring `dupe` analysis stages.

## Classes — **PARTIALLY VERIFIED**

Class syntax exists in J2, but constructor/method/field semantics were not sufficiently exercised for the `dupe` MVP. Do not make core correctness depend on classes.

---

# 2.2 Collections

## Arrays — **VERIFIED**

Array literals, `len(...)`, indexed access, indexed assignment, and iteration were successfully exercised.

```j2
xs = [3, 1, 2]
print(len(xs))
xs[0] = 9
for x in xs { print(x) }
```

Arrays are the primary MVP representation for ordered file records and result lists.

## Maps / objects — **VERIFIED FOR JSON OBJECT USE**

J2's runtime namespace display exposes map-like values. More importantly, `json.parse` produces object values that can be indexed by string key, and `json.stringify` emits deterministic compact JSON for the tested object:

```j2
x = json.parse("{\"b\":2,\"a\":1}")
print(x["a"])
print(json.stringify(x))
```

The tested parsed object printed as `{a: 1, b: 2}` and stringified as `{"a":1,"b":2}`. Use JSON object values through the verified JSON API rather than inventing a separate map constructor syntax.

## Iteration — **VERIFIED**

`for x in xs { ... }` works over arrays. J2 documentation identifies loops and independent work as candidates for automatic parallelism.

## Sorting — **VERIFIED**

`sort([3, 1, 2])` executed successfully and returned `[1,2,3]` in the Phase 2 runtime probe.

Signature frozen for MVP use:

```j2
ordered = sort(values)
```

---

# 2.3 Filesystem

Filesystem APIs are now runtime-verified through the `fs` namespace.

## Namespace — **VERIFIED**

`print(fs)` exposed:

```text
list_dir
metadata
read_bytes
mkdir_p
rename
is_dir
write_bytes
copy
remove
write_file
remove_dir
append_file
mkdir
read_file
exists
is_file
read_lines
```

Do not use unqualified names such as `read_file(...)`; the verified API is namespaced as `fs.read_file(...)`.

## Directory enumeration — **VERIFIED**

```j2
entries = fs.list_dir(path)
```

The symbol resolves at runtime. A missing directory raises a runtime error.

**MVP adapter:** use `fs.list_dir` recursively, filtering child names with `fs.is_file` / `fs.is_dir` as needed.

## Metadata and file size — **VERIFIED**

```j2
meta = fs.metadata(path)
size = meta["size"]
is_file = meta["is_file"]
is_dir = meta["is_dir"]
modified = meta["modified_epoch"]
```

Observed metadata shape:

```text
{is_file: true, modified_epoch: <integer>, size: 6, is_dir: false}
```

The `size` field is the authoritative MVP file-size source.

## Raw byte reads — **VERIFIED**

```j2
bytes = fs.read_bytes(path)
```

A six-byte file containing `abc123` returned:

```text
[97,98,99,49,50,51]
```

with `len(bytes) == 6`.

This is the exact-byte representation required for duplicate detection.

## Text reads — **VERIFIED**

`fs.read_file(path)` resolves through the `fs` namespace. For duplicate detection, prefer `fs.read_bytes` so no text decoding can change the compared content.

## Existence/type tests — **VERIFIED**

```j2
fs.exists(path)
fs.is_file(path)
fs.is_dir(path)
```

All were runtime exercised successfully on existing/non-existing paths.

## Mutating filesystem calls — **VERIFIED SYMBOLS; NOT MVP**

`write_file`, `append_file`, `mkdir`, `mkdir_p`, `rename`, `copy`, `remove`, and `remove_dir` are present and some were executed successfully during the probe. They are deliberately excluded from the duplicate-scanning MVP to keep the initial product non-destructive.

## Path operations — **UNRESOLVED**

No dedicated `path.join` / basename API was frozen. For the MVP, let the CLI supply the root path and retain the path strings returned by directory enumeration rather than inventing a path namespace.

## Errors — **VERIFIED**

Invalid filesystem paths produced runtime errors and non-zero process status. Example:

```text
RuntimeError: fs.metadata: No such file or directory (os error 2)
STATUS=1
```

---

# 2.4 Hashing

## Hash namespace — **VERIFIED**

`print(hash)` exposed:

```text
md5
sha256
sha512
xxhash
```

## SHA-256 — **VERIFIED FOR EXACT FILE BYTES**

```j2
bytes = fs.read_bytes(path)
digest = hash.sha256(bytes)
```

For the bytes of `abc123`, J2 returned:

```text
6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090
```

The same digest was returned for `hash.sha256("abc123")`, establishing that `fs.read_bytes` can feed the hash API directly.

**MVP decision:** use `hash.sha256(fs.read_bytes(path))` unless later benchmarking proves another verified hash gives a materially better trade-off.

## Other hashes — **VERIFIED SYMBOLS / SEMANTICS**

`hash.md5`, `hash.sha512`, and `hash.xxhash` all accepted the tested byte input and returned values. SHA-256 is the frozen correctness-first default because its output is a stable hexadecimal digest and is independently easy to verify.

## Incremental hashing — **UNRESOLVED**

No streaming/update/finalize API was established. The MVP therefore hashes the byte array returned by `fs.read_bytes`.

## Encoding — **VERIFIED FOR SHA-256 OUTPUT**

SHA-256, SHA-512, and MD5 return hexadecimal strings. Do not assume a separate encoding helper is needed for these digest outputs.

---

# 2.5 CLI

## Program invocation — **VERIFIED**

J2 0.1.0 exposes:

```text
j2 FILE.j2 [args...]
j2 run FILE.j2
j2 build FILE.j2 -o OUT
j2 emit-native FILE.j2
j2 fmt [-w] FILE.j2
j2 repl
j2 test [DIR]
j2 --version
j2 --help
```

## `proc.argv()` — **VERIFIED**

The runtime exposes `proc.argv` as a builtin function. Calling it returns an array of argument strings.

Probe:

```j2
print(proc.argv())
```

When invoked as `j2 run probe.j2 one two`, the returned value contained the program path in the observed probe environment. Therefore the MVP CLI adapter must explicitly account for the actual argv layout rather than assuming index `0` is the user-supplied root.

## Options / capability flags — **VERIFIED**

The J2 CLI exposes:

```text
--allow-fs
--allow-proc
--allow-net
--allow-all
--allow-unsafe
```

`dupe` requires filesystem capability for its scanner.

## Exit status — **VERIFIED**

Successful programs returned status `0`; runtime failures such as overflow and invalid filesystem paths returned non-zero status.

---

# 2.6 Serialization

## JSON namespace — **VERIFIED**

`print(json)` exposed:

```text
parse
stringify
stringify_pretty
```

## JSON primitives — **VERIFIED**

The runtime successfully serialized and parsed:

```text
string -> JSON string
integer -> JSON number
boolean -> JSON boolean
array -> JSON array
object -> JSON object
```

Examples observed:

```text
json.stringify("abc") -> "abc"
json.stringify(123) -> 123
json.stringify(true) -> true
json.stringify([1,2,3]) -> [1,2,3]
```

## Object ordering / deterministic serialization — **VERIFIED FOR THE TESTED PARSED OBJECT**

Parsing `{"b":2,"a":1}` produced an object displayed as `{a: 1, b: 2}` and `json.stringify` produced `{"a":1,"b":2}`. `json.stringify_pretty` produced the corresponding stable pretty form in the same probe.

For `dupe --json`, still enforce deterministic construction/ordering at the application level: do not rely on unspecified iteration order of arbitrary in-memory structures.

---

# 2.7 Runtime

## Capabilities — **DOCUMENTED / CLI-VERIFIED**

J2 0.1.0 exposes deny-by-default capability flags. The research environment successfully accepted `--allow-fs`, and filesystem calls were exercised with that flag.

For production execution, `dupe` must explicitly grant filesystem access rather than relying on ambient authority.

## Error handling — **VERIFIED FOR OPERATIONAL FAILURE**

Observed runtime failures include an error class/message plus source line, with non-zero status. Exact typed-error construction and catch syntax remain out of scope for the MVP.

## Timing — **PARTIALLY VERIFIED / NOT FROZEN**

`time` exposes:

```text
now
elapsed_ms
```

`time.now()` returned integer values in the probe. The attempted zero-argument call to `time.elapsed_ms()` produced:

```text
TypeError: time.elapsed_ms(t) takes 1 argument
```

So `elapsed_ms` exists and requires one argument, but the exact argument semantics were not fully established by this run.

**MVP rule:** benchmark wall time using the surrounding shell/Python harness. Do not make application correctness depend on `time.elapsed_ms` yet.

---

# 2.8 Compiler

## Native output — **VERIFIED**

```sh
j2 build file.j2 -o out
```

The Phase 2 probe built a native binary successfully and executed it.

## `emit-native` — **VERIFIED**

```sh
j2 emit-native file.j2
```

The command completed successfully and emitted backend source.

## Automatic parallelism — **DOCUMENTED AND COMPILER-BACKED; DUPE-SPECIFIC PARALLELISM STILL TO MEASURE**

J2's native compiler is documented as automatically distributing independent work across cores, without a thread API. The project must not claim that a particular `dupe` loop is parallel until `emit-native` and benchmark evidence demonstrate it.

## Native/interpreter equivalence — **VERIFIED ON A CONTROL PROGRAM**

The Phase 2 control program produced `15` in both `j2 run` and the native binary; `diff` returned status `0`.

`dupe` must independently enforce byte-identical result/JSON output across the execution modes used in the benchmark and test harness.

---

# 2.9 Reproducibility

## Exact J2 version — **VERIFIED**

```text
j2 0.1.0
```

## Exact artifact — **VERIFIED**

```text
j2-0.1.0-aarch64-apple-darwin.tar.gz
SHA-256: 6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75
```

## Exact environment — **VERIFIED**

```text
GitHub Actions runner image: macos-15-arm64 (observed by run)
Observed architecture:       arm64
Observed OS:                 macOS 15.7.9
```

The workflow can select `macos-15`; the actual validated runner reported Apple Silicon `arm64` and used the `aarch64-apple-darwin` release artifact.

## Native toolchain — **VERIFIED**

The J2 native build completed on the Apple Silicon macOS runner. J2's official distribution requires the system toolchain/Xcode Command Line Tools for native linking when not already installed.

---

# Frozen implementation boundary for `dupe`

The MVP may now directly use:

```text
J2 0.1.0
  -> fs.list_dir(path)
  -> fs.metadata(path)["size"]
  -> fs.is_file(path)
  -> fs.is_dir(path)
  -> fs.exists(path)
  -> fs.read_bytes(path)
  -> hash.sha256(bytes)
  -> arrays + for iteration
  -> sort(values)
  -> json.parse / json.stringify
  -> proc.argv()
  -> explicit --allow-fs execution
  -> j2 run for development
  -> j2 build for native validation/benchmarking
  -> j2 emit-native for compiler evidence
  -> external harness for benchmark timing
```

Keep these behind adapter/deferred boundaries:

```text
incremental/streaming file hashing
path-join/basename helpers
J2-native benchmark timing
class-heavy domain models
error-catching abstractions beyond process-failure handling
```

## Recommended MVP scan pipeline

```text
root path
   |
   v
recursive fs.list_dir
   |
   v
file records { path, size }
   |
   v
filter size groups with count >= 2
   |
   v
hash.sha256(fs.read_bytes(path))
   |
   v
group by digest
   |
   v
DuplicateGroup { digest, size, files[], reclaimable_bytes }
   |
   +--> human output
   +--> deterministic --json output
   +--> GUI model
```

The expensive independent unit to benchmark is file analysis, while the size-group prefilter prevents unnecessary reads/hashes for unique sizes.

## Differential-testing requirements

The implementation test harness should enforce:

1. **Soundness:** every reported duplicate group is byte-identical under an independent checker.
2. **Completeness:** every seeded duplicate cluster appears exactly once.
3. **No false merges:** files differing by one byte never share a duplicate group.
4. **Cross-mode determinism:** interpreter/native outputs match byte-for-byte for the same tree.
5. **Arithmetic self-check:** reclaimable bytes equals `Σ(count - 1) × size` across duplicate groups.

Do not freeze unverified J2 environment variables such as `J2_PARALLEL` as part of the test matrix. Those names require direct J2 evidence before use. Note: `J_FORCE_NATIVE` and `J2_FORCE_NATIVE` were probed against J2 0.1.0 binary strings and found not to exist; native execution is achieved directly by compiling with `j2 build src/main.j2 -o build/dupe` and running with runtime capability `J2_ALLOW_FS=1`.

## Verified Native Capabilities and Execution Contract — **VERIFIED**

Probed in CI workflow `j2-native-capabilities.yml`:
1. **Compilation**: `j2 build src/main.j2 -o build/dupe` produces an arm64 Mach-O native executable.
2. **Capability Grant**: Standalone compiled binaries do not parse interpreter flags like `--allow-fs`. Instead, the J2 runtime sandbox grants filesystem access to compiled binaries when the environment variable `J2_ALLOW_FS=1` is set.
3. **Negative Control**: Running the compiled native binary without `J2_ALLOW_FS=1` fails with a runtime sandbox/capability violation.
4. **Symlink Semantics**: `fs.is_dir` and `fs.is_file` follow symbolic links (e.g., a symlink to a directory returns `fs.is_dir(...) == true`). Because J2 0.1.0 does not include a builtin cycle guard, recursive traversals must be protected against cycles; the test harness enforces a strict 60s subprocess timeout.
5. **Sort Contract**: `sort(array)` sorts 1D arrays of primitives (strings, numbers). It does not support nested array comparison (e.g. `[["b", 1], ["a", 2]]`).
6. **Builtin `fmt()`**: Positionally formats strings using `{}` placeholders (e.g. `fmt("{} ({} files, {} bytes each):", digest, count, size)`).
7. **Directory & Grouping Determinism**: `fs.list_dir(path)` returns bare child names. Traversals sort children via `sort(fs.list_dir(path))`. Duplicate groups are formed in first-discovery order, and paths within each group preserve first-discovery order.
8. **Trailing Slash Path Concatenation**: `join_path(base, name)` performs literal string concatenation `fmt("{}/{}", base, name)`. When the root argument ends with a trailing slash (e.g. `/tmp/dir/`), child paths preserve the literal concatenation prefix `//` (e.g. `/tmp/dir//file.txt`). POSIX path resolution handles adjacent slashes transparently, while the emitted JSON faithfully reflects the verbatim path strings without synthetic normalization.
9. **Symlink Cycles & Bounded Recursion**: J2 0.1.0 provides no builtin cycle detection or inode tracking. Directory symlink cycles cause recursive descent that continues until OS/process recursion limits or execution timeouts; external test harnesses and CI jobs must enforce strict timeouts (60s subprocess, 15m CI).
10. **TOCTOU Limitation (Discover vs Hash)**: In accordance with the single-pass pipeline design, file sizes are recorded in `discover()` and preserved into candidate records. Hashing occurs subsequently in `hash_candidates()`. If a file is mutated concurrently between discovery and hashing, the reported size will reflect the initial discovery state while the SHA-256 digest reflects the bytes read at hash time. Concurrent tree modification during scanning is outside the static analysis contract.

## Next implementation gate

The Phase 2 and Phase 4 research runs have verified the full compiler and native runtime matrix. Phase 4 differential correctness enforces soundness, completeness, byte-identity verification, failure preservation, and cross-mode (interpreter vs native binary) equivalence.
