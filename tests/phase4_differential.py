from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
J2 = os.environ.get("J2_BIN", "j2")


def oracle(root: Path) -> dict:
    files = sorted(p for p in root.rglob("*") if p.is_file())

    by_size: dict[int, list[Path]] = {}
    for path in files:
        by_size.setdefault(path.stat().st_size, []).append(path)

    candidates = [
        path
        for size in sorted(by_size)
        if len(by_size[size]) >= 2
        for path in by_size[size]
    ]
    by_hash: dict[str, list[Path]] = {}
    sizes: dict[str, int] = {}
    for path in candidates:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        by_hash.setdefault(digest, []).append(path)
        sizes[digest] = len(data)

    groups = []
    for digest in sorted(by_hash):
        paths = sorted(str(p) for p in by_hash[digest])
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


def run_dupe(root: Path, native: bool) -> dict:
    env = dict(os.environ)
    if native:
        env["J_FORCE_NATIVE"] = "1"
    else:
        env.pop("J_FORCE_NATIVE", None)

    proc = subprocess.run(
        [J2, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), str(root), "--json"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        mode = "native" if native else "interpreter"
        raise AssertionError(
            f"dupe {mode} failed for {root}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        mode = "native" if native else "interpreter"
        raise AssertionError(f"dupe {mode} returned invalid JSON: {proc.stdout!r}") from exc


def run_dupe_expect_failure(root: Path, *, native: bool = False) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if native:
        env["J_FORCE_NATIVE"] = "1"
    else:
        env.pop("J_FORCE_NATIVE", None)

    return subprocess.run(
        [J2, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), str(root), "--json"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def manifest(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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


def build_cases(base: Path) -> list[tuple[str, Path]]:
    cases: list[tuple[str, Path]] = []

    empty = base / "empty"
    empty.mkdir()
    cases.append(("empty tree", empty))

    single = base / "single"
    write(single / "one.txt", b"one")
    cases.append(("single file", single))

    same_dir = base / "same-dir"
    write(same_dir / "a.txt", b"same-content")
    write(same_dir / "b.txt", b"same-content")
    cases.append(("identical files in one directory", same_dir))

    nested = base / "nested"
    write(nested / "root.txt", b"nested-content")
    write(nested / "deep" / "copy.bin", b"nested-content")
    cases.append(("identical files across nested directories", nested))

    same_size = base / "same-size-different-content"
    write(same_size / "left.txt", b"abcdef")
    write(same_size / "right.txt", b"abcdeg")
    cases.append(("same-size different-content files", same_size))

    one_byte = base / "one-byte-difference"
    write(one_byte / "left.bin", b"0123456789")
    write(one_byte / "right.bin", b"0123456788")
    cases.append(("files differing by one byte", one_byte))

    empty_dupes = base / "empty-dupes"
    write(empty_dupes / "empty-a", b"")
    write(empty_dupes / "empty-b", b"")
    write(empty_dupes / "nonempty", b"x")
    cases.append(("multiple empty files", empty_dupes))

    clusters = base / "clusters"
    write(clusters / "alpha-1", b"alpha")
    write(clusters / "alpha-2", b"alpha")
    write(clusters / "alpha-3", b"alpha")
    write(clusters / "beta-1", b"beta")
    write(clusters / "nested" / "beta-2", b"beta")
    write(clusters / "unique", b"unique")
    cases.append(("multiple duplicate clusters", clusters))

    names = base / "filename-torture"
    write(names / "space name.txt", b"space")
    write(names / "copy space name.txt", b"space")
    write(names / "unicode-☃.txt", b"snow")
    write(names / "nested dir" / "unicode-☃-copy.txt", b"snow")
    write(names / "[brackets](test){x}.bin", b"brackets")
    write(names / "[copy] {x}.bin", b"brackets")
    cases.append(("filename and path edge cases", names))

    boundaries = base / "size-boundaries"
    write(boundaries / "zero-a", b"")
    write(boundaries / "zero-b", b"")
    write(boundaries / "one-a", b"x")
    write(boundaries / "one-b", b"x")
    write(boundaries / "two-a", b"xy")
    write(boundaries / "two-b", b"xy")
    cases.append(("zero and small size boundaries", boundaries))

    return cases


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dupe-phase4-") as temp:
        base = Path(temp)
        cases = build_cases(base)
        print(f"Phase 4 cases: {len(cases)}")

        for name, root in cases:
            before = manifest(root)
            expected = oracle(root)
            interpreter = run_dupe(root, native=False)
            native = run_dupe(root, native=True)

            assert_schema(interpreter)
            assert_schema(native)
            assert interpreter == expected, (name, "interpreter != oracle", expected, interpreter)
            assert native == expected, (name, "native != oracle", expected, native)
            assert interpreter == native, (name, "interpreter != native", interpreter, native)
            assert manifest(root) == before, (name, "dupe modified input tree")
            print(f"PASS: {name}")

        missing = base / "does-not-exist"
        for native in (False, True):
            proc = run_dupe_expect_failure(missing, native=native)
            mode = "native" if native else "interpreter"
            assert proc.returncode != 0, (mode, "missing root unexpectedly succeeded")
            print(f"PASS: {mode} missing-root failure")

        file_root = base / "root-file"
        write(file_root, b"not-a-directory")
        for native in (False, True):
            proc = run_dupe_expect_failure(file_root, native=native)
            mode = "native" if native else "interpreter"
            assert proc.returncode != 0, (mode, "file root unexpectedly succeeded")
            print(f"PASS: {mode} file-root failure")

        print("Phase 4 differential correctness PASS")
        print("Phase 4 safety/error validation PASS")


if __name__ == "__main__":
    main()
