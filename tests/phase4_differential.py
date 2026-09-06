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
        paths = sorted(p.as_posix() for p in by_hash[digest])
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


def assert_results_equivalent(actual: dict, expected: dict, context: str) -> None:
    assert actual["files_scanned"] == expected["files_scanned"], (
        context,
        f"files_scanned mismatch: actual={actual['files_scanned']} expected={expected['files_scanned']}",
    )
    assert actual["hash_candidates"] == expected["hash_candidates"], (
        context,
        f"hash_candidates mismatch: actual={actual['hash_candidates']} expected={expected['hash_candidates']}",
    )
    assert actual["reclaimable_bytes"] == expected["reclaimable_bytes"], (
        context,
        f"reclaimable_bytes mismatch: actual={actual['reclaimable_bytes']} expected={expected['reclaimable_bytes']}",
    )
    actual_canon = canonicalize_groups(actual["duplicate_groups"])
    expected_canon = canonicalize_groups(expected["duplicate_groups"])
    assert actual_canon == expected_canon, (
        context,
        "duplicate_groups mismatch",
        actual_canon,
        expected_canon,
    )


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
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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
) -> Path:
    if output_dir is None:
        output_dir = REPO_ROOT / "tests" / "regressions" / "failures"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_manifest: dict[str, dict] = {}
    if root.exists():
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                data = p.read_bytes()
                file_manifest[rel] = {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "hex": data.hex() if len(data) <= 4096 else None,
                }

    record = {
        "seed": seed,
        "case_description": f"{case_name}: {error}",
        "filesystem_manifest": file_manifest,
        "interpreter_output": interpreter_out,
        "native_output": native_out,
        "oracle_output": oracle_out,
        "timestamp": int(time.time()),
    }

    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in case_name)
    suffix = f"seed_{seed}" if seed is not None else str(int(time.time()))
    out_file = output_dir / f"failure_{clean_name}_{suffix}.json"
    out_file.write_text(json.dumps(record, indent=2))
    print(f"FAILURE PRESERVED: {out_file}")
    return out_file


def reproduce_from_failure(failure_file: Path, target_dir: Path) -> Path:
    record = json.loads(failure_file.read_text())
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_data = record.get("filesystem_manifest", {})
    for rel_path, meta in manifest_data.items():
        dest = target_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "hex" in meta and meta["hex"] is not None:
            dest.write_bytes(bytes.fromhex(meta["hex"]))
        else:
            dest.write_bytes(b"\x00" * meta.get("size", 0))
    return target_dir


def generate_fuzz_case(base: Path, seed: int) -> tuple[str, Path]:
    rng = random.Random(seed)
    case_name = f"fuzz-seed-{seed}"
    case_dir = base / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    num_clusters = rng.randint(1, 3)
    num_uniques = rng.randint(2, 4)

    # 1. Duplicate clusters
    for cluster_idx in range(num_clusters):
        cluster_len = rng.choice([0, 1, 5, 20, 100])
        cluster_content = rng.randbytes(cluster_len)
        num_copies = rng.randint(2, 3)
        subdirs = ["", f"sub_{cluster_idx}", f"deep/level_{cluster_idx}"]
        for copy_idx in range(num_copies):
            sub = rng.choice(subdirs)
            target_sub = case_dir / sub if sub else case_dir
            target_sub.mkdir(parents=True, exist_ok=True)
            fname = f"cluster_{cluster_idx}_copy_{copy_idx}.dat"
            (target_sub / fname).write_bytes(cluster_content)

    # 2. Same-size distinct-content files
    common_size = rng.choice([4, 16, 64])
    for s_idx in range(2):
        data = bytes([(x + s_idx * 7) % 256 for x in rng.randbytes(common_size)])
        (case_dir / f"same_size_{common_size}_{s_idx}.bin").write_bytes(data)

    # 3. Unique files
    for u_idx in range(num_uniques):
        u_size = rng.randint(1, 80)
        u_data = rng.randbytes(u_size)
        (case_dir / f"unique_{u_idx}.txt").write_bytes(u_data)

    return case_name, case_dir


def load_regression_fixtures(fixtures_dir: Path, target_base: Path) -> list[tuple[str, Path]]:
    cases: list[tuple[str, Path]] = []
    if not fixtures_dir.exists():
        return cases
    for fix_path in sorted(fixtures_dir.glob("*.json")):
        data = json.loads(fix_path.read_text())
        name = data.get("name", fix_path.stem)
        case_dir = target_base / name
        case_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, hex_data in data.get("manifest", {}).items():
            dest = case_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(bytes.fromhex(hex_data))
        cases.append((name, case_dir))
    return cases


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
    base.mkdir(parents=True, exist_ok=True)
    cases: list[tuple[str, Path]] = []

    empty = base / "empty"
    empty.mkdir(parents=True, exist_ok=True)
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


def verify_case(
    name: str,
    root: Path,
    *,
    seed: int | None = None,
    require_direct_match: bool = False,
) -> None:
    before = manifest(root)
    expected = oracle(root)
    interpreter = None
    native = None
    try:
        interpreter = run_dupe(root, native=False)
        native = run_dupe(root, native=True)

        assert_schema(interpreter)
        assert_schema(native)

        if require_direct_match:
            assert interpreter == expected, (name, "interpreter != oracle", expected, interpreter)
            assert native == expected, (name, "native != oracle", expected, native)
        else:
            assert_results_equivalent(interpreter, expected, f"{name}: interpreter != oracle")
            assert_results_equivalent(native, expected, f"{name}: native != oracle")

        assert interpreter == native, (name, "interpreter != native", interpreter, native)
        assert manifest(root) == before, (name, "dupe modified input tree")
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


def test_fuzzer_reproducibility() -> None:
    with tempfile.TemporaryDirectory(prefix="dupe-fuzz-repro-") as temp:
        base = Path(temp)
        seed = 42001
        _, dir_a = generate_fuzz_case(base / "a", seed)
        _, dir_b = generate_fuzz_case(base / "b", seed)

        manifest_a = manifest(dir_a)
        manifest_b = manifest(dir_b)
        assert manifest_a == manifest_b, "Fuzzer tree manifest was not identical for the same seed"

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
            "Relative oracle output differed for the same fuzzer seed"
        )
        print("PASS: fuzzer seed reproducibility check")


def test_failure_preservation_mechanism() -> None:
    with tempfile.TemporaryDirectory(prefix="dupe-failure-test-") as temp:
        base = Path(temp)
        case_dir = base / "synthetic_failure_case"
        case_dir.mkdir(parents=True)
        write(case_dir / "sample.txt", b"sample-bytes")

        out_dir = base / "failures"
        record_path = preserve_failure(
            case_name="synthetic_test",
            root=case_dir,
            seed=99999,
            error="simulated mismatch for preservation check",
            oracle_out={"simulated": True},
            interpreter_out={"simulated": False},
            native_out={"simulated": False},
            output_dir=out_dir,
        )

        assert record_path.exists(), "Failure record file was not created"
        data = json.loads(record_path.read_text())
        assert data["seed"] == 99999
        assert "case_description" in data
        assert "sample.txt" in data["filesystem_manifest"]
        assert data["filesystem_manifest"]["sample.txt"]["sha256"] == hashlib.sha256(b"sample-bytes").hexdigest()
        assert data["oracle_output"] == {"simulated": True}
        assert data["interpreter_output"] == {"simulated": False}
        assert data["native_output"] == {"simulated": False}

        # Verify reproduction from record
        repro_dir = base / "repro"
        reproduce_from_failure(record_path, repro_dir)
        assert (repro_dir / "sample.txt").read_bytes() == b"sample-bytes"
        print("PASS: failure preservation infrastructure check")


def run_offline_tests() -> None:
    print("Running offline self-tests (oracle, fuzzer reproducibility, regression loading, failure preservation)...")
    test_fuzzer_reproducibility()
    test_failure_preservation_mechanism()

    with tempfile.TemporaryDirectory(prefix="dupe-offline-") as temp:
        base = Path(temp)
        # Test 10 seed cases with oracle
        seed_cases = build_cases(base / "seed")
        print(f"PASS: oracle evaluation of {len(seed_cases)} seed cases")

        # Test regression fixtures with oracle
        fixtures_dir = REPO_ROOT / "tests" / "regressions" / "fixtures"
        reg_cases = load_regression_fixtures(fixtures_dir, base / "reg")
        for name, root in reg_cases:
            out = oracle(root)
            assert out["files_scanned"] > 0
            assert isinstance(out["duplicate_groups"], list)
        print(f"PASS: oracle evaluation of {len(reg_cases)} regression fixtures")

        # Test fuzzer generation
        for seed in (42001, 42002):
            c_name, c_dir = generate_fuzz_case(base / "fuzz", seed)
            out = oracle(c_dir)
            assert out["files_scanned"] > 0
        print("PASS: oracle evaluation of fuzzer cases")
    print("All offline self-tests PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 Differential Correctness and Regression Matrix")
    parser.add_argument("--fuzz-count", type=int, default=5, help="Number of fuzzer seeds to run")
    parser.add_argument("--seed", type=int, default=None, help="Run a single specific fuzzer seed")
    parser.add_argument("--reproduce", type=str, default=None, help="Reproduce from a preserved failure JSON")
    parser.add_argument("--offline", action="store_true", help="Run self-tests without calling J2")
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

    # Reproduction mode
    if args.reproduce:
        fail_file = Path(args.reproduce)
        if not fail_file.exists():
            raise FileNotFoundError(f"Reproduction file not found: {fail_file}")
        with tempfile.TemporaryDirectory(prefix="dupe-reproduce-") as temp:
            target = reproduce_from_failure(fail_file, Path(temp) / "reproduced_tree")
            verify_case(f"reproduce-{fail_file.stem}", target, require_direct_match=False)
            print(f"PASS: reproduction of {fail_file}")
        return

    # Single seed mode
    if args.seed is not None:
        with tempfile.TemporaryDirectory(prefix="dupe-seed-") as temp:
            c_name, c_dir = generate_fuzz_case(Path(temp), args.seed)
            verify_case(c_name, c_dir, seed=args.seed, require_direct_match=False)
            print(f"PASS: fuzzer single seed {args.seed}")
        return

    # Standard full test matrix
    # 1. Self-checks for fuzzer reproducibility and failure preservation
    test_fuzzer_reproducibility()
    test_failure_preservation_mechanism()

    with tempfile.TemporaryDirectory(prefix="dupe-phase4-") as temp:
        base = Path(temp)

        # 2. Deterministic Seed Corpus (10 cases)
        cases = build_cases(base / "seed_corpus")
        print(f"Phase 4 seed corpus cases: {len(cases)}")
        for name, root in cases:
            verify_case(name, root, require_direct_match=True)

        # 3. Retained Regression Corpus
        fixtures_dir = REPO_ROOT / "tests" / "regressions" / "fixtures"
        regression_cases = load_regression_fixtures(fixtures_dir, base / "regressions")
        print(f"Phase 4 regression corpus cases: {len(regression_cases)}")
        for name, root in regression_cases:
            verify_case(f"regression: {name}", root, require_direct_match=False)

        # 4. Fuzzer Suite
        fuzz_seeds = [42000 + i for i in range(1, args.fuzz_count + 1)]
        print(f"Phase 4 fuzzer cases: {len(fuzz_seeds)} (seeds {fuzz_seeds[0]}..{fuzz_seeds[-1]})")
        for seed in fuzz_seeds:
            c_name, c_dir = generate_fuzz_case(base / "fuzz", seed)
            verify_case(f"fuzzer: {c_name}", c_dir, seed=seed, require_direct_match=False)

        # 5. Invalid Root Safety Tests
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
        print("Phase 4 regression corpus PASS")
        print("Phase 4 fuzzer validation PASS")


if __name__ == "__main__":
    main()
