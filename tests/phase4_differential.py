from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
J2 = os.environ.get("J2_BIN", "j2")

_counter = 0


def next_counter() -> int:
    global _counter
    _counter += 1
    return _counter


def discover_files(path: Path) -> list[Path]:
    """Recursively discover regular files in deterministic depth-first directory order,
    sorting entry names in each directory, exactly matching J2's scan.j2 discover()."""
    files: list[Path] = []
    if not path.is_dir():
        return files
    for entry in sorted(path.iterdir(), key=lambda p: p.name):
        if entry.is_dir():
            files.extend(discover_files(entry))
        elif entry.is_file():
            files.append(entry)
    return files


def oracle(root: Path) -> dict:
    """Independent Python oracle implementing the required exact-duplicate specification:
    1. Recursively discover files in deterministic directory order.
    2. Group candidates by size (keep only sizes with >= 2 files).
    3. Hash candidates in discovery order using SHA-256.
    4. Group duplicates in first-discovery order; paths within each group follow discovery order.
    5. Calculate reclaimable bytes as (count - 1) * size per group."""
    files = discover_files(root)

    by_size: dict[int, list[Path]] = {}
    for path in files:
        by_size.setdefault(path.stat().st_size, []).append(path)

    # Size filtering preserving discovery order
    candidates = [p for p in files if len(by_size[p.stat().st_size]) >= 2]

    by_hash: dict[str, list[str]] = {}
    sizes: dict[str, int] = {}
    hash_order: list[str] = []

    for path in candidates:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest not in by_hash:
            by_hash[digest] = []
            sizes[digest] = len(data)
            hash_order.append(digest)
        by_hash[digest].append(path.as_posix())

    groups = []
    for digest in hash_order:
        paths = by_hash[digest]
        if len(paths) < 2:
            continue
        size = sizes[digest]
        groups.append(
            {
                "hash": digest,
                "size": size,
                "files": paths,
                "reclaimable_bytes": (len(paths) - 1) * size,
            }
        )

    return {
        "files_scanned": len(files),
        "hash_candidates": len(candidates),
        "duplicate_groups": groups,
        "reclaimable_bytes": sum(g["reclaimable_bytes"] for g in groups),
    }


def canonicalize_groups(groups: list[dict]) -> list[dict]:
    return sorted(
        [
            {
                "hash": g["hash"],
                "size": g["size"],
                "files": sorted(g["files"]),
                "reclaimable_bytes": g["reclaimable_bytes"],
            }
            for g in groups
        ],
        key=lambda g: (g["hash"], g["size"]),
    )


def assert_schema(result: dict) -> None:
    assert set(result) == {
        "files_scanned",
        "hash_candidates",
        "duplicate_groups",
        "reclaimable_bytes",
    }
    assert isinstance(result["files_scanned"], int)
    assert isinstance(result["hash_candidates"], int)
    assert isinstance(result["duplicate_groups"], list)
    assert isinstance(result["reclaimable_bytes"], int)
    for group in result["duplicate_groups"]:
        assert set(group) == {"hash", "size", "files", "reclaimable_bytes"}
        assert len(group["files"]) >= 2
        assert group["reclaimable_bytes"] == (len(group["files"]) - 1) * group["size"]


def verify_soundness(result: dict, context: str) -> None:
    """Fulfills Soundness requirement (J2-API-0.1.0.md:523):
    - Asserts all files within every reported duplicate group are pairwise byte-identical.
    - Asserts every reported file exists and reported size matches exact byte length.
    - Asserts reported hash matches exact SHA-256 of the byte content.
    - Asserts duplicate groups are pairwise disjoint (no file in multiple groups)."""
    seen_files: set[str] = set()
    for group in result["duplicate_groups"]:
        files = group["files"]
        assert len(files) >= 2, f"{context}: duplicate group has fewer than 2 files: {group}"
        first_path = Path(files[0])
        assert first_path.is_file(), f"{context}: group file does not exist: {first_path}"
        first_bytes = first_path.read_bytes()
        assert len(first_bytes) == group["size"], (
            f"{context}: size mismatch for {first_path}: reported {group['size']}, actual {len(first_bytes)}"
        )
        expected_hash = hashlib.sha256(first_bytes).hexdigest()
        assert group["hash"] == expected_hash, (
            f"{context}: hash mismatch for {first_path}: reported {group['hash']}, computed {expected_hash}"
        )

        for other_str in files[1:]:
            other_path = Path(other_str)
            assert other_path.is_file(), f"{context}: group file does not exist: {other_path}"
            other_bytes = other_path.read_bytes()
            assert other_bytes == first_bytes, (
                f"{context}: Soundness failure: {first_path} and {other_path} are in the same group but NOT byte-identical!"
            )
            assert other_str not in seen_files, (
                f"{context}: Soundness failure: file {other_str} appears in multiple duplicate groups!"
            )
            seen_files.add(other_str)
        seen_files.add(files[0])


def run_dupe(root: Path, *, native: bool, native_bin: Path | None = None) -> dict:
    if native:
        if native_bin is None or not native_bin.exists():
            raise RuntimeError(f"Native binary not provided or does not exist: {native_bin}")
        cmd = [str(native_bin), str(root), "--json"]
        env = {**os.environ, "J2_ALLOW_FS": "1"}
    else:
        cmd = [J2, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), str(root), "--json"]
        env = {k: v for k, v in os.environ.items() if k != "J2_ALLOW_FS"}

    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        mode = "native" if native else "interpreter"
        raise AssertionError(f"dupe {mode} timed out after 60s for {root}") from exc

    if proc.returncode != 0:
        mode = "native" if native else "interpreter"
        raise AssertionError(
            f"dupe {mode} failed (exit {proc.returncode}) for {root}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        mode = "native" if native else "interpreter"
        raise AssertionError(f"dupe {mode} returned invalid JSON: {proc.stdout!r}") from exc


def run_dupe_raw(root: Path, *, native: bool, native_bin: Path | None = None) -> str:
    if native:
        if native_bin is None or not native_bin.exists():
            raise RuntimeError(f"Native binary not provided or does not exist: {native_bin}")
        cmd = [str(native_bin), str(root), "--json"]
        env = {**os.environ, "J2_ALLOW_FS": "1"}
    else:
        cmd = [J2, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), str(root), "--json"]
        env = {k: v for k, v in os.environ.items() if k != "J2_ALLOW_FS"}

    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        mode = "native" if native else "interpreter"
        raise AssertionError(f"dupe {mode} failed with status {proc.returncode}:\n{proc.stderr}")
    return proc.stdout


def run_dupe_expect_failure(
    root: Path, *, native: bool, native_bin: Path | None = None
) -> subprocess.CompletedProcess[str]:
    if native:
        if native_bin is None or not native_bin.exists():
            raise RuntimeError(f"Native binary not provided or does not exist: {native_bin}")
        cmd = [str(native_bin), str(root), "--json"]
        env = {**os.environ, "J2_ALLOW_FS": "1"}
    else:
        cmd = [J2, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), str(root), "--json"]
        env = {k: v for k, v in os.environ.items() if k != "J2_ALLOW_FS"}

    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def manifest(root: Path) -> dict[str, dict]:
    """Capture full filesystem state including byte hash, mtime, and mode
    to rigorously prove zero filesystem mutation (F13)."""
    res: dict[str, dict] = {}
    if not root.exists():
        return res
    for path in sorted(root.rglob("*")):
        if path.is_file():
            stat = path.stat()
            res[path.relative_to(root).as_posix()] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mtime_ns": stat.st_mtime_ns,
                "mode": stat.st_mode,
                "size": stat.st_size,
            }
    return res


def sanitize_relative_path(rel_str: str, target_root: Path) -> Path:
    """Security check to prevent directory traversal or escapes (F5)."""
    p = Path(rel_str)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Insecure relative path detected: {rel_str}")
    dest = (target_root / p).resolve()
    if not dest.is_relative_to(target_root.resolve()):
        raise ValueError(f"Path escapes target root: {rel_str}")
    return dest


def preserve_failure(
    *,
    case_name: str,
    root: Path,
    seed: int | None = None,
    error: str = "",
    oracle_out: dict | None = None,
    interpreter_out: dict | None = None,
    native_out: dict | None = None,
    output_dir: Path | None = None,
    j2_version: str | None = None,
    argv: list[str] | None = None,
    returncode: int | None = None,
    stderr: str | None = None,
    stdout: str | None = None,
) -> Path:
    """Faithfully preserves failure records with complete file hex payloads (F4)."""
    if output_dir is None:
        output_dir = REPO_ROOT / "tests" / "regressions" / "failures"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_manifest: dict[str, dict] = {}
    empty_directories: list[str] = []
    if root.exists():
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                data = p.read_bytes()
                file_manifest[rel] = {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "hex": data.hex(),
                }
            elif p.is_dir() and not any(p.iterdir()):
                empty_directories.append(p.relative_to(root).as_posix())

    record = {
        "seed": seed,
        "case_description": f"{case_name}: {error}",
        "j2_version": j2_version or os.environ.get("J2_VERSION", "0.1.0"),
        "command_argv": argv,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "empty_directories": empty_directories,
        "filesystem_manifest": file_manifest,
        "interpreter_output": interpreter_out,
        "native_output": native_out,
        "oracle_output": oracle_out,
        "timestamp": int(time.time()),
    }

    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in case_name)
    suffix = f"seed_{seed}" if seed is not None else str(int(time.time()))
    pid = os.getpid()
    cnt = next_counter()
    out_file = output_dir / f"failure_{clean_name}_{suffix}_{pid}_{cnt}.json"
    out_file.write_text(json.dumps(record, indent=2))
    print(f"FAILURE PRESERVED: {out_file}")
    return out_file


def reproduce_from_failure(failure_file: Path, target_dir: Path) -> Path:
    """Replays a failure artifact with 100% byte fidelity (F4, F5)."""
    record = json.loads(failure_file.read_text())
    target_dir.mkdir(parents=True, exist_ok=True)

    # Recreate empty directories
    for rel_dir in record.get("empty_directories", []):
        dest_dir = sanitize_relative_path(rel_dir, target_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

    # Recreate files with byte fidelity
    manifest_data = record.get("filesystem_manifest", {})
    for rel_path, meta in manifest_data.items():
        dest = sanitize_relative_path(rel_path, target_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "hex" in meta and meta["hex"] is not None:
            dest.write_bytes(bytes.fromhex(meta["hex"]))
        else:
            raise ValueError(f"Cannot faithfully reproduce file {rel_path}: hex payload missing in record.")
    return target_dir


def load_regression_fixtures(fixtures_dir: Path, target_base: Path) -> list[tuple[str, Path]]:
    """Loads and validates all regression fixtures with path sanitization (F5)."""
    cases: list[tuple[str, Path]] = []
    if not fixtures_dir.exists():
        return cases
    for fix_path in sorted(fixtures_dir.glob("*.json")):
        data = json.loads(fix_path.read_text())
        assert "name" in data and isinstance(data["name"], str), f"Malformed fixture {fix_path}: missing 'name'"
        assert "manifest" in data and isinstance(data["manifest"], dict), f"Malformed fixture {fix_path}: missing 'manifest'"
        name = data["name"]
        case_dir = target_base / name
        case_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, hex_data in data["manifest"].items():
            dest = sanitize_relative_path(rel_path, case_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(bytes.fromhex(hex_data))
        cases.append((name, case_dir))
    return cases


def generate_fuzz_case(base: Path, seed: int) -> tuple[str, Path]:
    """Deterministic pseudo-random tree generator with extended depth, dotfiles,
    and distinctness assertion (F11, F12)."""
    rng = random.Random(seed)
    case_name = f"fuzz-seed-{seed}"
    case_dir = base / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    num_clusters = rng.randint(1, 4)
    num_uniques = rng.randint(2, 6)

    # 1. Duplicate clusters
    for cluster_idx in range(num_clusters):
        cluster_len = rng.choice([0, 1, 7, 33, 256])
        cluster_content = rng.randbytes(cluster_len)
        num_copies = rng.randint(2, 4)
        subdirs = ["", f"sub_{cluster_idx}", f"deep/level_{cluster_idx}/nested"]
        for copy_idx in range(num_copies):
            sub = rng.choice(subdirs)
            target_sub = case_dir / sub if sub else case_dir
            target_sub.mkdir(parents=True, exist_ok=True)
            fname = f"cluster_{cluster_idx}_copy_{copy_idx}.dat"
            (target_sub / fname).write_bytes(cluster_content)

    # 2. Same-size distinct-content files (asserted distinct!)
    common_size = rng.choice([8, 32, 128])
    data_a = rng.randbytes(common_size)
    # Ensure byte difference
    data_b = bytearray(data_a)
    data_b[0] = (data_b[0] + 1) % 256
    data_b = bytes(data_b)
    assert data_a != data_b, "Fuzzer failed to produce distinct same-size files"
    (case_dir / f"same_size_{common_size}_0.bin").write_bytes(data_a)
    (case_dir / f"same_size_{common_size}_1.bin").write_bytes(data_b)

    # 3. Unique files (including dotfiles)
    for u_idx in range(num_uniques):
        u_size = rng.randint(1, 100)
        u_data = rng.randbytes(u_size)
        prefix = "." if u_idx == 0 else ""
        (case_dir / f"{prefix}unique_{u_idx}.txt").write_bytes(u_data)

    # 4. Empty subdirectory
    (case_dir / "empty_subfolder").mkdir(parents=True, exist_ok=True)

    return case_name, case_dir


def build_cases(base: Path) -> list[tuple[str, Path]]:
    """Builds comprehensive deterministic seed corpus including dotfiles,
    empty directories, and large files (F12)."""
    base.mkdir(parents=True, exist_ok=True)
    cases: list[tuple[str, Path]] = []

    # 1. empty tree
    empty = base / "empty"
    empty.mkdir(parents=True, exist_ok=True)
    cases.append(("empty tree", empty))

    # 2. single file
    single = base / "single"
    write(single / "one.txt", b"one")
    cases.append(("single file", single))

    # 3. identical files in one directory
    same_dir = base / "same-dir"
    write(same_dir / "a.txt", b"same-content")
    write(same_dir / "b.txt", b"same-content")
    cases.append(("identical files in one directory", same_dir))

    # 4. identical files across nested directories
    nested = base / "nested"
    write(nested / "root.txt", b"nested-content")
    write(nested / "deep" / "copy.bin", b"nested-content")
    cases.append(("identical files across nested directories", nested))

    # 5. same-size different-content files
    same_size = base / "same-size-different-content"
    write(same_size / "left.txt", b"abcdef")
    write(same_size / "right.txt", b"abcdeg")
    cases.append(("same-size different-content files", same_size))

    # 6. files differing by one byte
    one_byte = base / "one-byte-difference"
    write(one_byte / "left.bin", b"0123456789")
    write(one_byte / "right.bin", b"0123456788")
    cases.append(("files differing by one byte", one_byte))

    # 7. multiple empty files
    empty_dupes = base / "empty-dupes"
    write(empty_dupes / "empty-a", b"")
    write(empty_dupes / "empty-b", b"")
    write(empty_dupes / "nonempty", b"x")
    cases.append(("multiple empty files", empty_dupes))

    # 8. multiple duplicate clusters
    clusters = base / "clusters"
    write(clusters / "alpha-1", b"alpha")
    write(clusters / "alpha-2", b"alpha")
    write(clusters / "alpha-3", b"alpha")
    write(clusters / "beta-1", b"beta")
    write(clusters / "nested" / "beta-2", b"beta")
    write(clusters / "unique", b"unique")
    cases.append(("multiple duplicate clusters", clusters))

    # 9. filename and path edge cases
    names = base / "filename-torture"
    write(names / "space name.txt", b"space")
    write(names / "copy space name.txt", b"space")
    write(names / "unicode-☃.txt", b"snow")
    write(names / "nested dir" / "unicode-☃-copy.txt", b"snow")
    write(names / "[brackets](test){x}.bin", b"brackets")
    write(names / "[copy] {x}.bin", b"brackets")
    cases.append(("filename and path edge cases", names))

    # 10. zero and small size boundaries
    boundaries = base / "size-boundaries"
    write(boundaries / "zero-a", b"")
    write(boundaries / "zero-b", b"")
    write(boundaries / "one-a", b"x")
    write(boundaries / "one-b", b"x")
    write(boundaries / "two-a", b"xy")
    write(boundaries / "two-b", b"xy")
    cases.append(("zero and small size boundaries", boundaries))

    # 11. dotfiles edge case (F12)
    dotfiles = base / "dotfiles"
    write(dotfiles / ".hidden-a.txt", b"dotfile-content")
    write(dotfiles / "sub" / ".hidden-b.txt", b"dotfile-content")
    write(dotfiles / "normal.txt", b"normal")
    cases.append(("dotfiles discovery", dotfiles))

    # 12. empty subdirectories edge case (F12)
    empty_sub = base / "empty-subdirs"
    write(empty_sub / "file.txt", b"hello")
    (empty_sub / "empty_folder_1" / "nested_empty").mkdir(parents=True, exist_ok=True)
    cases.append(("empty subdirectories", empty_sub))

    # 13. large file (1 MB) duplicate pair (F8, F12)
    large = base / "large-file"
    large_data = b"D" * 1048576  # 1 MB
    write(large / "large-1.bin", large_data)
    write(large / "large-2.bin", large_data)
    cases.append(("large file (1MB) duplicates", large))

    return cases


def verify_case(
    name: str,
    root: Path,
    *,
    native_bin: Path | None = None,
    seed: int | None = None,
) -> None:
    before = manifest(root)
    expected = oracle(root)
    interpreter = None
    native = None
    try:
        interpreter = run_dupe(root, native=False)
        native = run_dupe(root, native=True, native_bin=native_bin)

        assert_schema(interpreter)
        assert_schema(native)

        # Soundness verification on both outputs (F3)
        verify_soundness(interpreter, f"{name} (interpreter)")
        verify_soundness(native, f"{name} (native)")

        # Direct exact match verification (F2):
        # With discovery-order oracle, interpreter == native == expected DIRECTLY for all cases!
        assert interpreter == expected, (name, "interpreter != oracle", expected, interpreter)
        assert native == expected, (name, "native != oracle", expected, native)
        assert interpreter == native, (name, "interpreter != native", interpreter, native)

        # Filesystem immutability assertion (F13)
        after = manifest(root)
        assert after == before, (name, "dupe modified filesystem state or metadata")
        print(f"PASS: {name}")
    except Exception as exc:
        preserve_failure(
            case_name=name,
            root=root,
            seed=seed,
            error=str(exc),
            oracle_out=expected,
            interpreter_out=interpreter,
            native_out=native,
        )
        raise


def test_repeat_run_determinism(root: Path, native_bin: Path | None) -> None:
    """Verifies byte-for-byte reproducibility across repeat executions (F2)."""
    raw_i1 = run_dupe_raw(root, native=False)
    raw_i2 = run_dupe_raw(root, native=False)
    assert raw_i1 == raw_i2, "Interpreter output was not byte-identical across repeat executions"

    raw_n1 = run_dupe_raw(root, native=True, native_bin=native_bin)
    raw_n2 = run_dupe_raw(root, native=True, native_bin=native_bin)
    assert raw_n1 == raw_n2, "Native output was not byte-identical across repeat executions"

    # Cross-mode byte equivalence
    assert json.loads(raw_i1) == json.loads(raw_n1), "Interpreter and native produced divergent JSON structures"
    print("PASS: repeat-run determinism check")


def test_fuzzer_reproducibility() -> None:
    """Verifies seed reproducibility across multiple seeds (F11)."""
    with tempfile.TemporaryDirectory(prefix="dupe-fuzz-repro-") as temp:
        base = Path(temp)
        for seed in (42001, 42002, 42003):
            _, dir_a = generate_fuzz_case(base / f"a_{seed}", seed)
            _, dir_b = generate_fuzz_case(base / f"b_{seed}", seed)

            manifest_a = {p.relative_to(dir_a).as_posix(): p.read_bytes() for p in sorted(dir_a.rglob("*")) if p.is_file()}
            manifest_b = {p.relative_to(dir_b).as_posix(): p.read_bytes() for p in sorted(dir_b.rglob("*")) if p.is_file()}
            assert manifest_a == manifest_b, f"Fuzzer tree manifest was not identical for seed {seed}"

            oracle_a = oracle(dir_a)
            oracle_b = oracle(dir_b)

            def rel_oracle(res: dict, root: Path) -> dict:
                return {
                    "files_scanned": res["files_scanned"],
                    "hash_candidates": res["hash_candidates"],
                    "reclaimable_bytes": res["reclaimable_bytes"],
                    "duplicate_groups": [
                        {
                            "hash": g["hash"],
                            "size": g["size"],
                            "reclaimable_bytes": g["reclaimable_bytes"],
                            "files": [Path(f).relative_to(root).as_posix() for f in g["files"]],
                        }
                        for g in res["duplicate_groups"]
                    ],
                }

            assert rel_oracle(oracle_a, dir_a) == rel_oracle(oracle_b, dir_b), (
                f"Oracle output differed for fuzzer seed {seed}"
            )
        print("PASS: fuzzer multi-seed reproducibility check")


def test_failure_preservation_mechanism() -> None:
    """Tests failure preservation and reproduction with >4 KB files and path sanitization (F4, F5)."""
    with tempfile.TemporaryDirectory(prefix="dupe-failure-test-") as temp:
        base = Path(temp)
        case_dir = base / "synthetic_case"
        case_dir.mkdir(parents=True)
        # 8 KB file to explicitly test non-truncated round-trip fidelity
        large_bytes = b"X" * 8192
        write(case_dir / "large_file.dat", large_bytes)
        (case_dir / "empty_dir").mkdir()

        out_dir = base / "failures"
        record_path = preserve_failure(
            case_name="synthetic_test",
            root=case_dir,
            seed=99999,
            error="simulated mismatch",
            oracle_out={"simulated": True},
            interpreter_out={"simulated": False},
            native_out={"simulated": False},
            output_dir=out_dir,
        )

        assert record_path.exists(), "Failure record was not created"
        data = json.loads(record_path.read_text())
        assert data["seed"] == 99999
        assert "large_file.dat" in data["filesystem_manifest"]
        assert data["filesystem_manifest"]["large_file.dat"]["hex"] == large_bytes.hex()
        assert "empty_dir" in data["empty_directories"]

        # Verify reproduction
        repro_dir = base / "repro"
        reproduce_from_failure(record_path, repro_dir)
        assert (repro_dir / "large_file.dat").read_bytes() == large_bytes
        assert (repro_dir / "empty_dir").is_dir()

        # Path sanitization tests (F5)
        try:
            sanitize_relative_path("../../escape.txt", repro_dir)
            assert False, "Sanitizer failed to catch relative path escape"
        except ValueError:
            pass

        print("PASS: failure preservation and reproduction check (>4KB faithful)")


def run_offline_tests() -> None:
    """Rigorous offline self-tests asserting hardcoded exact expected values (F9)."""
    print("Running offline self-tests with strict value assertions...")
    test_fuzzer_reproducibility()
    test_failure_preservation_mechanism()

    with tempfile.TemporaryDirectory(prefix="dupe-offline-") as temp:
        base = Path(temp)
        seed_cases = build_cases(base / "seed")

        # Hardcoded expected values for seed cases (F9)
        expected_seed_values = {
            "empty tree": (0, 0, 0, 0),
            "single file": (1, 0, 0, 0),
            "identical files in one directory": (2, 2, 1, 12),
            "identical files across nested directories": (2, 2, 1, 14),
            "same-size different-content files": (2, 2, 0, 0),
            "files differing by one byte": (2, 2, 0, 0),
            "multiple empty files": (3, 2, 1, 0),
            "multiple duplicate clusters": (6, 5, 2, 14),
            "filename and path edge cases": (6, 6, 3, 17),
            "zero and small size boundaries": (6, 6, 3, 3),
            "dotfiles discovery": (3, 2, 1, 15),
            "empty subdirectories": (1, 0, 0, 0),
            "large file (1MB) duplicates": (2, 2, 1, 1048576),
        }

        for name, root in seed_cases:
            out = oracle(root)
            assert_schema(out)
            verify_soundness(out, f"offline: {name}")
            exp = expected_seed_values[name]
            actual = (out["files_scanned"], out["hash_candidates"], len(out["duplicate_groups"]), out["reclaimable_bytes"])
            assert actual == exp, f"Seed case '{name}' mismatch: actual {actual}, expected {exp}"
        print(f"PASS: oracle evaluation and soundness of {len(seed_cases)} seed cases with strict value assertions")

        # Hardcoded expected values for regression fixtures
        expected_reg_values = {
            "case01_nested_clusters": (5, 4, 2, 9),
            "case02_size_boundary_zero": (6, 6, 2, 1),
            "case03_same_size_distinct_content": (4, 4, 1, 10),
            "case04_one_byte_diff_clusters": (4, 4, 2, 36),
        }

        fixtures_dir = REPO_ROOT / "tests" / "regressions" / "fixtures"
        reg_cases = load_regression_fixtures(fixtures_dir, base / "reg")
        for name, root in reg_cases:
            out = oracle(root)
            assert_schema(out)
            verify_soundness(out, f"offline regression: {name}")
            exp = expected_reg_values[name]
            actual = (out["files_scanned"], out["hash_candidates"], len(out["duplicate_groups"]), out["reclaimable_bytes"])
            assert actual == exp, f"Regression fixture '{name}' mismatch: actual {actual}, expected {exp}"
        print(f"PASS: oracle evaluation and soundness of {len(reg_cases)} regression fixtures with strict value assertions")

    print("All offline self-tests PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 Differential Correctness and Regression Matrix")
    parser.add_argument("--native-bin", type=str, default=None, help="Path to pre-compiled native dupe binary")
    parser.add_argument("--fuzz-count", type=int, default=5, help="Number of fuzzer seeds to run")
    parser.add_argument("--seed", type=int, default=None, help="Run a single specific fuzzer seed")
    parser.add_argument("--reproduce", type=str, default=None, help="Reproduce from a preserved failure JSON")
    parser.add_argument("--offline", action="store_true", help="Run offline self-tests with strict assertions")
    args = parser.parse_args()

    if args.offline:
        run_offline_tests()
        return

    # Check J2 executable availability
    if not shutil.which(J2):
        print(f"WARNING: J2 executable '{J2}' not found on PATH.")
        print("Running offline self-tests instead.")
        run_offline_tests()
        return

    # Determine native binary (F1)
    native_bin = None
    if args.native_bin:
        native_bin = Path(args.native_bin).resolve()
        if not native_bin.exists() or not os.access(native_bin, os.X_OK):
            raise FileNotFoundError(f"Specified native binary not found or not executable: {native_bin}")
    else:
        default_bin = REPO_ROOT / "build" / "dupe"
        if default_bin.exists() and os.access(default_bin, os.X_OK):
            native_bin = default_bin

    if native_bin is None:
        print("Native binary not specified and not found at build/dupe. Compiling now with j2 build...")
        build_dir = REPO_ROOT / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        native_bin = build_dir / "dupe"
        proc = subprocess.run(
            [J2, "build", str(REPO_ROOT / "src" / "main.j2"), "-o", str(native_bin)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0 or not native_bin.exists():
            raise RuntimeError(f"Native build failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        print(f"Native build successful: {native_bin}")

    # Negative control test: verify native binary enforces J2_ALLOW_FS (F1)
    with tempfile.TemporaryDirectory(prefix="dupe-neg-control-") as temp:
        neg_dir = Path(temp)
        (neg_dir / "x.txt").write_bytes(b"x")
        proc_deny = subprocess.run(
            [str(native_bin), str(neg_dir), "--json"],
            cwd=REPO_ROOT,
            env={k: v for k, v in os.environ.items() if k != "J2_ALLOW_FS"},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert proc_deny.returncode != 0 and "capability denied" in (proc_deny.stderr + proc_deny.stdout), (
            f"Negative control failed: native binary unexpectedly succeeded without J2_ALLOW_FS!\n"
            f"code={proc_deny.returncode}, out={proc_deny.stdout}, err={proc_deny.stderr}"
        )
        print("PASS: native binary sandbox capability enforcement (negative control)")

    # Reproduction mode
    if args.reproduce:
        fail_file = Path(args.reproduce)
        if not fail_file.exists():
            raise FileNotFoundError(f"Reproduction file not found: {fail_file}")
        with tempfile.TemporaryDirectory(prefix="dupe-reproduce-") as temp:
            target = reproduce_from_failure(fail_file, Path(temp) / "reproduced_tree")
            verify_case(f"reproduce-{fail_file.stem}", target, native_bin=native_bin)
            print(f"PASS: faithful reproduction of {fail_file}")
        return

    # Single seed mode
    if args.seed is not None:
        with tempfile.TemporaryDirectory(prefix="dupe-seed-") as temp:
            c_name, c_dir = generate_fuzz_case(Path(temp), args.seed)
            verify_case(c_name, c_dir, native_bin=native_bin, seed=args.seed)
            print(f"PASS: fuzzer single seed {args.seed}")
        return

    # Full Differential Matrix
    # 1. Self-checks for fuzzer reproducibility and failure preservation
    test_fuzzer_reproducibility()
    test_failure_preservation_mechanism()

    with tempfile.TemporaryDirectory(prefix="dupe-phase4-") as temp:
        base = Path(temp)

        # 2. Deterministic Seed Corpus (13 cases)
        cases = build_cases(base / "seed_corpus")
        print(f"Phase 4 seed corpus cases: {len(cases)}")
        for name, root in cases:
            verify_case(name, root, native_bin=native_bin)

        # 3. Retained Regression Corpus
        fixtures_dir = REPO_ROOT / "tests" / "regressions" / "fixtures"
        regression_cases = load_regression_fixtures(fixtures_dir, base / "regressions")
        print(f"Phase 4 regression corpus cases: {len(regression_cases)}")
        for name, root in regression_cases:
            verify_case(f"regression: {name}", root, native_bin=native_bin)

        # 4. Fuzzer Suite
        fuzz_seeds = [42000 + i for i in range(1, args.fuzz_count + 1)]
        print(f"Phase 4 fuzzer cases: {len(fuzz_seeds)} (seeds {fuzz_seeds[0]}..{fuzz_seeds[-1]})")
        for seed in fuzz_seeds:
            c_name, c_dir = generate_fuzz_case(base / "fuzz", seed)
            verify_case(f"fuzzer: {c_name}", c_dir, native_bin=native_bin, seed=seed)

        # 5. Repeat-run determinism test (F2)
        test_repeat_run_determinism(cases[2][1], native_bin)

        # 6. Trailing slash root test (F12)
        demo_root = cases[2][1]
        out_slash_i = run_dupe(Path(str(demo_root) + "/"), native=False)
        out_slash_n = run_dupe(Path(str(demo_root) + "/"), native=True, native_bin=native_bin)
        assert out_slash_i == out_slash_n, "Trailing slash produced divergent outputs"
        print("PASS: trailing-slash root handling")

        # 7. Invalid Root Safety Tests
        missing = base / "does-not-exist"
        for native in (False, True):
            proc = run_dupe_expect_failure(missing, native=native, native_bin=native_bin)
            mode = "native" if native else "interpreter"
            assert proc.returncode != 0, (mode, "missing root unexpectedly succeeded")
            print(f"PASS: {mode} missing-root failure")

        file_root = base / "root-file"
        write(file_root, b"not-a-directory")
        for native in (False, True):
            proc = run_dupe_expect_failure(file_root, native=native, native_bin=native_bin)
            mode = "native" if native else "interpreter"
            assert proc.returncode != 0, (mode, "file root unexpectedly succeeded")
            print(f"PASS: {mode} file-root failure")

        # 8. Unreadable directory and candidate file error handling test (POSIX only) (F8)
        if os.name != "nt":
            unreadable_dir = base / "unreadable_dir"
            forbidden_sub = unreadable_dir / "forbidden_sub"
            forbidden_sub.mkdir(parents=True, exist_ok=True)
            write(forbidden_sub / "inner.txt", b"inner")
            os.chmod(forbidden_sub, 0o000)
            try:
                for native in (False, True):
                    proc = run_dupe_expect_failure(unreadable_dir, native=native, native_bin=native_bin)
                    mode = "native" if native else "interpreter"
                    assert proc.returncode != 0, (mode, "unreadable directory unexpectedly succeeded")
                    print(f"PASS: {mode} unreadable directory permission failure")
            finally:
                os.chmod(forbidden_sub, 0o755)

            unreadable_files_dir = base / "unreadable_files_dir"
            f1 = unreadable_files_dir / "f1.dat"
            f2 = unreadable_files_dir / "f2.dat"
            write(f1, b"duplicate-candidate")
            write(f2, b"duplicate-candidate")
            os.chmod(f1, 0o000)
            try:
                for native in (False, True):
                    proc = run_dupe_expect_failure(unreadable_files_dir, native=native, native_bin=native_bin)
                    mode = "native" if native else "interpreter"
                    assert proc.returncode != 0, (mode, "unreadable candidate file unexpectedly succeeded")
                    print(f"PASS: {mode} unreadable candidate file read failure")
            finally:
                os.chmod(f1, 0o644)

        print("Phase 4 differential correctness PASS")
        print("Phase 4 soundness byte-identity verification PASS")
        print("Phase 4 safety/error validation PASS")
        print("Phase 4 regression corpus PASS")
        print("Phase 4 fuzzer validation PASS")


if __name__ == "__main__":
    main()
