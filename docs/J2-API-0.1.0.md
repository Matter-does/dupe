# J2 0.1.0 API & Execution Contract

**Project:** `dupe`  
**J2 version:** `0.1.0`  
**Contract status:** **FROZEN FOR IMPLEMENTATION**  
**Research date:** 2026-09-05  
**Validated target:** `aarch64-apple-darwin` on GitHub Actions `macos-15-arm64`

> This document freezes only behavior supported by runtime/compiler experiments or the official J2 0.1.0 documentation. A name that merely parses or compiles is **not** considered a verified API.

## Evidence policy

Every proposed J2 API follows this evidence ladder:

1. **Compile-valid** — the source is accepted by the compiler.
2. **Runtime symbol verified** — the referenced name resolves when executed.
3. **Runtime semantics verified** — the result/type/side effect matches the intended use.
4. **Native equivalence verified** — interpreter and native execution agree where relevant.
5. **Frozen** — the verified behavior is safe to use in `dupe` implementation.

The previous filesystem probe demonstrated why step 1 is insufficient: candidate globals such as `read_file(...)` returned build status 0, but executing `read_file(...)` produced `NameError: "read_file" is not defined`.

---

# 2.1 Language primitives

## Strings — **VERIFIED**

**Verified behavior**

- String literals use double quotes, e.g. `"hello"`.
- String values can be printed.
- String interpolation/formatting is available through the documented `fmt(...)` example, but `fmt` is not frozen as a required `dupe` dependency until separately runtime-probed.

**Exact evidence**

```sh
echo 'print("hello, world")' > hello.j2
j hello.j2
```

Official J2 0.1.0 documentation also provides a runnable `fmt("longest: {}", longest(words))` example.

**Implementation rule:** ordinary strings are safe to use; do not assume additional string methods without a runtime probe.

## Integers — **VERIFIED**

**Verified behavior**

- Integer literals and arithmetic are supported.
- Typed integer parameters use `int`, e.g. `func f(x: int) = ...`.
- J2 treats integer overflow as an error rather than silently wrapping, according to the official documentation.

**Exact commands used**

```sh
j2 run "$ROOT/overflow.j2" 2>&1
```

Probe source:

```j2
print(9223372036854775807 + 1)
```

**Important:** the overflow probe establishes error behavior, not a promise that all integers are exactly signed 64-bit in every context. Do not encode an implementation-width assumption in `dupe` until the type model is probed further.

## Booleans — **PARTIALLY VERIFIED**

The research source contains a boolean literal probe (`true`) and the official language documentation treats boolean conditions as part of ordinary control flow. The Phase 2 workflow does not yet provide an isolated successful runtime assertion for boolean value/type printing.

**Current status:** safe for ordinary conditional use as documented, but exact representation/printing is not frozen.

## Functions — **VERIFIED**

Official J2 syntax:

```j2
func add(x: int, y: int) -> int = {
    give x + y
}
```

J2 functions return with `give`. The official documentation also uses ordinary function calls as a target for automatic parallelism analysis.

**Exact evidence command**

```sh
j2 run "$ROOT/language.j2" 2>&1
```

The frozen syntax above is also present in the official J2 examples.

**Implementation rule:** ordinary functions are the primary unit for structuring `dupe` analysis stages.

## Classes — **PARTIALLY VERIFIED**

The official language documentation states that classes are part of the language. The Phase 2 probe includes:

```j2
class Box {
    value: int
}
```

but the current successful probe set does not yet provide enough runtime evidence to freeze constructor, method, field-access, or mutation semantics.

**Implementation rule:** do not make core `dupe` correctness depend on class construction/method semantics until separately verified.

---

# 2.2 Collections

## Arrays — **VERIFIED**

Array literal syntax is documented and used by the official examples:

```j2
words = ["apple", "banana", "fig", "grapefruit"]
```

The Phase 2 probe also constructs integer arrays such as `[3, 1, 2]`.

**Exact research command**

```sh
j2 run "$ROOT/language.j2" 2>&1
```

**Implementation rule:** arrays are the current candidate representation for ordered file records/results.

## Maps — **PARTIALLY VERIFIED**

The research probe contains map syntax:

```j2
m = {"b": 2, "a": 1}
```

but deterministic iteration/serialization and complete map mutation semantics are not yet frozen.

**Implementation rule:** maps may be used only after their required operations are runtime-confirmed for the exact use case.

## Iteration — **VERIFIED**

Official examples use:

```j2
for w in ws {
    ...
}
```

The Phase 2 probe uses the same form over an array.

J2's compiler documentation explicitly identifies ordinary loops as candidates for automatic parallelism.

**Exact research command**

```sh
j2 run "$ROOT/language.j2" 2>&1
```

## Mutation — **PARTIALLY VERIFIED**

The language documentation states that `=` creates a constant binding and `:=` creates a mutable binding. The probe attempts array element assignment:

```j2
d[0] = 9
```

The exact semantics of element mutation are not yet frozen as a library contract.

**Implementation rule:** use `:=` for mutable local accumulators; do not assume arbitrary collection element mutation until confirmed.

## Sorting — **UNRESOLVED**

`sort(d)` was included as a candidate API, but no successful runtime evidence has yet established a standard `sort` function or its signature.

**Implementation rule:** do not call `sort(...)` in production J2 code yet.

---

# 2.3 Filesystem

This section is deliberately conservative because filesystem API naming is the largest current uncertainty.

## Directory enumeration — **UNRESOLVED**

Candidates tested at compile time included:

```text
list_dir(path)
read_dir(path)
dir_entries(path)
fs.list_dir(path)
```

All candidate builds returned status 0 in the earlier compile-only probe, but that result is insufficient to establish that any symbol exists at runtime. The current runtime-qualified probe was added to the Phase 2 workflow, but its successful runtime log is not yet available in the current evidence snapshot.

**Production rule:** no directory API name is frozen yet.

## Metadata — **UNRESOLVED**

Candidates included:

```text
stat(path)
file_stat(path)
fs.stat(path)
```

No candidate is frozen until runtime behavior is observed.

## Size — **UNRESOLVED**

Candidates included:

```text
file_size(path)
get_file_size(path)
```

No candidate is frozen.

## Byte reads — **UNRESOLVED**

The candidate `read_file(path)` is explicitly **not verified**.

Observed runtime result from the previous probe:

```text
NameError: "read_file" is not defined (at line 1)
STATUS=1
```

This is the canonical example of why compile-only probing cannot freeze an API.

## Path operations — **UNRESOLVED**

Candidates included:

```text
path_join(a, b)
join_path(a, b)
path.join(a, b)
path.basename(path)
path.exists(path)
```

No candidate is frozen.

## Errors — **VERIFIED**

The J2 runtime is capability based. Filesystem access is denied by default and must be granted explicitly.

Official command forms:

```sh
j2 run report.j2
j2 run --allow-fs report.j2
```

The documentation gives the expected denied/allowed model:

```text
RuntimeError: read_file: capability denied
```

followed by successful execution with `--allow-fs`.

**Implementation rule:** `dupe` filesystem execution must explicitly run with filesystem capability enabled; the program must not assume ambient filesystem authority.

---

# 2.4 Hashing

## Byte representation — **UNRESOLVED**

No stable runtime API has yet been established for raw file bytes or a byte-array type appropriate for hashing.

Candidate expression tested:

```text
bytes("abc")
```

It is not frozen merely because it parses/compiles.

## Digest API — **UNRESOLVED**

Candidates tested:

```text
hash("abc")
sha256("abc")
sha256_hash("abc")
hash_sha256("abc")
digest("abc")
```

No digest API is frozen yet.

## Incremental hashing — **UNRESOLVED**

No verified streaming/incremental hash state type or update/finalize API has been established.

**Implementation rule:** `dupe` must not commit to a specific hash algorithm API until a runtime probe demonstrates it.

## Encoding — **UNRESOLVED**

String/byte encoding behavior relevant to hashes (UTF-8 conversion, hex encoding, etc.) is not frozen.

**Important:** duplicate detection must hash the file's exact bytes, not an implicitly decoded text representation.

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

The command surface is directly recorded from `j2 --help` in the successful Phase 2 research environment.

## `argv` / positional arguments — **UNRESOLVED**

Candidates `argv` and `args` were included in runtime probes with:

```sh
j2 run "$probe" one two 2>&1
```

but no successful result is frozen yet.

## Options / capability flags — **VERIFIED**

The J2 0.1.0 help surface exposes:

```text
--allow-fs
--allow-proc
--allow-net
--allow-all
--allow-unsafe
```

## Exit status — **VERIFIED**

The research workflow captures the process status with shell `$?` after J2 execution. Runtime failures such as the unresolved `read_file` probe returned `STATUS=1`.

**Implementation rule:** `dupe` should use non-zero process status for operational failure once its own CLI layer is implemented.

---

# 2.6 Serialization

## JSON serialization — **UNRESOLVED**

Candidates tested:

```text
json_encode(value)
to_json(value)
json(value)
```

No candidate is frozen.

## Deterministic JSON — **UNRESOLVED**

Even if a JSON encoder is later verified, deterministic key ordering and byte-for-byte serialization have not yet been established.

**Required acceptance condition before freezing:** the same logical result must serialize identically across repeated runs and across interpreter/native execution modes.

**Implementation rule:** `dupe --json` should not depend on an unverified J2 JSON serializer. A deterministic, explicitly tested representation is required first.

---

# 2.7 Runtime

## Capabilities — **VERIFIED**

J2 uses deny-by-default capabilities. Filesystem, process, and network access are separately grantable.

Verified command forms:

```sh
j2 run report.j2
j2 run --allow-fs report.j2
```

See §2.3 Errors.

## Error handling — **VERIFIED / PARTIALLY VERIFIED**

Verified:

- runtime failures produce a non-zero process status;
- diagnostics include an error class/name and source line;
- capability violations are surfaced as runtime errors;
- integer overflow is treated as an error according to the official documentation.

Not yet frozen:

- complete typed-error construction syntax;
- catch/propagation syntax required for production filesystem error handling;
- exact error object fields/types.

## Timing — **UNRESOLVED**

Candidates:

```text
now()
time_now()
clock()
```

No timing API has been runtime-verified.

**Implementation rule:** benchmark timing for the hackathon should initially be performed by the surrounding shell/Python harness unless a J2 timing primitive is separately verified.

---

# 2.8 Compiler

## Native output — **VERIFIED**

Exact command:

```sh
j2 build file.j2 -o out
```

The official J2 0.1.0 README defines this as compiling the source to a native, auto-parallelized binary.

The Phase 2 equivalence probe also executes the produced binary directly.

## `emit-native` — **VERIFIED**

Exact command:

```sh
j2 emit-native file.j2
```

This command appears on the J2 0.1.0 CLI help surface and is included in the Phase 2 compiler probe.

**Purpose in `dupe`:** inspect lowered output when explaining how J2 transformed a candidate workload. It is diagnostic evidence, not part of the application's runtime dependency.

## Automatic parallelism — **VERIFIED**

Official J2 documentation states that, during native compilation, the compiler looks for loops and calls it can prove independent and spreads the work across cores. Work that cannot be proven safe remains serial.

The official README gives the same model: ordinary independent function calls can be automatically distributed without thread APIs, annotations, locks, or explicit scheduling.

**Critical project rule:** do not claim that a particular `dupe` loop/hash stage is actually parallel until `emit-native` and/or benchmark evidence demonstrates it.

## Native/interpreter equivalence — **VERIFIED AS A REQUIRED J2 PROPERTY; DUPE RESULT STILL TO BE MEASURED**

The official documentation states that the interpreter and native engine are held to identical output across the test suite.

`dupe` must still test this property for its own deterministic JSON/result model.

---

# 2.9 Reproducibility

## Exact J2 version — **VERIFIED**

```text
j2 0.1.0
```

Exact command:

```sh
j2 --version
```

## Exact macOS target — **VERIFIED**

```text
Target archive: j2-0.1.0-aarch64-apple-darwin.tar.gz
Runner image:   macos-15-arm64
Observed OS:    macOS 15.7.9
Architecture:   arm64
```

The GitHub Actions run used the Apple Silicon release archive and observed `uname -m` as `arm64` in the validated J2 CI environment.

## Exact artifact hash — **VERIFIED**

```text
6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75
```

Verification command:

```sh
printf '%s  %s\n' "$J2_SHA256" j2.tar.gz | shasum -a 256 -c -
```

Expected output:

```text
j2.tar.gz: OK
```

## Exact installation sequence — **VERIFIED**

```sh
tar -xzf j2-0.1.0-aarch64-apple-darwin.tar.gz
cd j2-0.1.0-aarch64-apple-darwin
./install.sh
j2 --version
```

The installer places J2 under `~/.j2`; the GitHub Actions workflow adds `$HOME/.j2/bin` to `PATH`.

## Native-toolchain requirement — **VERIFIED**

J2 native builds link with the system linker. The official README states that Xcode Command Line Tools are required if they are not already installed.

---

# Frozen implementation boundary for `dupe`

At this snapshot, the following are safe architectural commitments:

```text
J2 0.1.0
    -> recursive file intelligence workload
    -> ordinary J2 functions and loops
    -> arrays / ordinary iteration
    -> explicit --allow-fs execution
    -> j2 run for rapid development
    -> j2 build for native benchmark/validation
    -> j2 emit-native for compiler evidence
    -> external harness for benchmarking until J2 timing is verified
```

The following **must remain behind an unresolved adapter boundary**:

```text
filesystem enumeration API
filesystem metadata/stat API
file-size API
raw byte-read API
path API
hash/digest API
incremental hashing API
JSON serialization API
argv API
timing API
sorting API
```

No guessed function name from the unresolved list may be merged into production `dupe` code merely because it compiles.

---

# Research commands / provenance

## J2 CLI surface

```sh
j2 --version
j2 --help
j2 build --help
j2 run --help
j2 repl --help
```

Observed J2 version: `0.1.0`.

## Language + collections probe

```sh
j2 run "$ROOT/language.j2" 2>&1
```

Probe included strings, integers, booleans, arrays, maps, functions, class syntax, `len`, sorting candidate, array mutation candidate, and `for` iteration.

## Filesystem candidate probe

```sh
j2 run --allow-fs "$ROOT/probe.j2" 2>&1
```

The exact candidate set is maintained in `.github/workflows/j2-api-research.yml` / the Phase 2 research workflow.

## Semantic candidate probe

```sh
j2 run "$probe" one two 2>&1
```

Used for byte/hash/JSON/timing/argv candidates.

## Capability and error probe

```sh
j2 run "$ROOT/errors.j2" 2>&1
j2 run --allow-fs "$ROOT/errors.j2" 2>&1
j2 run "$ROOT/overflow.j2" 2>&1
```

## Native equivalence probe

```sh
j2 run "$ROOT/determinism.j2" > "$ROOT/interpreter.txt" 2>&1
j2 build "$ROOT/determinism.j2" -o "$ROOT/determinism-bin"
"$ROOT/determinism-bin" > "$ROOT/native.txt" 2>&1
diff -u "$ROOT/interpreter.txt" "$ROOT/native.txt"
```

## Lowered compiler output

```sh
j2 emit-native "$ROOT/determinism.j2"
```

## Reproducible installation

```sh
curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
  -o j2.tar.gz \
  "https://github.com/JasnamSinghArora/j2/releases/download/v0.1.0/j2-0.1.0-aarch64-apple-darwin.tar.gz"
printf '%s  %s\n' \
  6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75 \
  j2.tar.gz | shasum -a 256 -c -
tar -xzf j2.tar.gz
find . -type f -name install.sh -print
./install.sh
j2 --version
```

---

# Freeze rule

This document is frozen **for the current J2 0.1.0 evidence snapshot**. It is not a claim that every J2 0.1.0 standard-library API has been discovered. When a previously unresolved API is experimentally verified, update this document with:

- exact source snippet;
- exact invocation command;
- observed stdout/stderr;
- process exit status;
- interpreter/native comparison when applicable;
- capability flags used;
- target architecture/version.

Do not replace an unresolved entry with an invented signature.
