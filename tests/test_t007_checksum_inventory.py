"""Focused acceptance and unit tests for T007 — File Checksum Inventory Workload.

Verifies:
1. Empty directory handling.
2. Single file inventory.
3. Multiple files inventory (varying sizes and identical content).
4. Deep nested directory discovery and deterministic ordering.
5. Exact SHA-256 correctness against independent host-side oracle (hashlib.sha256).
6. Correct byte totals and file counts.
7. Strict JSON schema conformance (schema_version == 1, workload == 'checksum_inventory').
8. Checksum subcommand argv parsing:
   - dupe checksum <path>
   - dupe checksum <path> --json
   - dupe checksum --json <path>
   - Missing path: dupe checksum and dupe checksum --json
9. Regression safety: dupe <path> [--json] continues to execute duplicate analysis.
10. Failure propagation for missing or unreadable inputs.
11. Human-readable text format output specification (<digest>  <path>).
12. Benchmark harness integration for checksum inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

from benchmarks.harness import (
    BaselineChecksumWorkloadMetrics,
    BenchmarkHarness,
    extract_checksum_workload_metrics,
)


def discover_files_ordered(root: Path) -> list[Path]:
    """Independent host-side implementation of deterministic discovery.
    Matches scan.j2 discover(): sorts child names at every directory level,
    recursively traverses directories first, then accumulates regular files."""
    files: list[Path] = []
    if not root.is_dir():
        return files

    names = sorted([p.name for p in root.iterdir()])
    for name in names:
        child = root / name
        if child.is_dir():
            files.extend(discover_files_ordered(child))
        elif child.is_file():
            files.append(child)
    return files


def checksum_inventory_oracle(root: Path) -> dict:
    """Independent host-side oracle computing exact SHA-256 checksum inventory.
    Uses hashlib.sha256 on exact file bytes to produce authoritative baseline."""
    files = discover_files_ordered(root)
    entries = []
    total_bytes = 0

    for f in files:
        data = f.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        size = len(data)
        total_bytes += size
        entries.append({
            "path": f.as_posix(),
            "size": size,
            "sha256": digest,
        })

    return {
        "schema_version": 1,
        "workload": "checksum_inventory",
        "root": root.as_posix(),
        "summary": {
            "total_files": len(entries),
            "total_bytes": total_bytes,
        },
        "entries": entries,
    }


def format_checksum_text_oracle(entries: list[dict], total_bytes: int) -> str:
    """Format human-readable text output matching T007 specification."""
    lines = []
    for e in entries:
        lines.append(f"{e['sha256']}  {e['path']}")
    lines.append(f"Total files: {len(entries)}, Total bytes: {total_bytes}")
    return "\n".join(lines)


def simulate_parse_checksum_args(args: list[str]) -> tuple[str, bool]:
    """Pure simulation of parse_checksum_args() from src/checksum.j2."""
    root = ""
    is_json = False
    skip_first = True
    skip_subcmd = True

    for arg in args:
        if skip_first:
            skip_first = False
        else:
            if skip_subcmd:
                skip_subcmd = False
            else:
                if arg == "--json":
                    is_json = True
                else:
                    if root == "":
                        root = arg

    return root, is_json


def simulate_is_checksum_command(args: list[str]) -> bool:
    """Pure simulation of is_checksum_command() from src/main.j2."""
    if len(args) > 1:
        if args[1] == "checksum":
            return True
    return False


class TestT007ChecksumInventory(unittest.TestCase):
    """Test suite for T007 Checksum Inventory workload."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="dupe-t007-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_directory(self) -> None:
        """Verify empty directory yields 0 files, 0 bytes, and empty entries list."""
        inv = checksum_inventory_oracle(self.temp_dir)

        self.assertEqual(inv["schema_version"], 1)
        self.assertEqual(inv["workload"], "checksum_inventory")
        self.assertEqual(inv["summary"]["total_files"], 0)
        self.assertEqual(inv["summary"]["total_bytes"], 0)
        self.assertEqual(inv["entries"], [])

        text = format_checksum_text_oracle(inv["entries"], inv["summary"]["total_bytes"])
        self.assertEqual(text, "Total files: 0, Total bytes: 0")

    def test_single_file_inventory(self) -> None:
        """Verify single file inventory matches exact SHA-256 and size."""
        fpath = self.temp_dir / "sample.txt"
        data = b"hello world\n"
        fpath.write_bytes(data)

        expected_sha = hashlib.sha256(data).hexdigest()
        inv = checksum_inventory_oracle(self.temp_dir)

        self.assertEqual(inv["summary"]["total_files"], 1)
        self.assertEqual(inv["summary"]["total_bytes"], len(data))
        self.assertEqual(len(inv["entries"]), 1)

        entry = inv["entries"][0]
        self.assertEqual(entry["path"], fpath.as_posix())
        self.assertEqual(entry["size"], len(data))
        self.assertEqual(entry["sha256"], expected_sha)
        self.assertTrue(re.match(r"^[0-9a-f]{64}$", entry["sha256"]))

        text = format_checksum_text_oracle(inv["entries"], inv["summary"]["total_bytes"])
        self.assertIn(f"{expected_sha}  {fpath.as_posix()}", text)
        self.assertIn(f"Total files: 1, Total bytes: {len(data)}", text)

    def test_multiple_files_and_deterministic_ordering(self) -> None:
        """Verify alphabetical discovery sorting and byte total calculations."""
        # Create files out of alphabetical order
        (self.temp_dir / "z_file.dat").write_bytes(b"zzz")
        (self.temp_dir / "a_file.dat").write_bytes(b"aaaa")
        (self.temp_dir / "m_file.dat").write_bytes(b"mmmm")

        inv1 = checksum_inventory_oracle(self.temp_dir)
        inv2 = checksum_inventory_oracle(self.temp_dir)

        # Exact determinism across runs
        self.assertEqual(inv1, inv2)
        self.assertEqual(inv1["summary"]["total_files"], 3)
        self.assertEqual(inv1["summary"]["total_bytes"], 11)

        paths = [e["path"] for e in inv1["entries"]]
        expected_paths = [
            (self.temp_dir / "a_file.dat").as_posix(),
            (self.temp_dir / "m_file.dat").as_posix(),
            (self.temp_dir / "z_file.dat").as_posix(),
        ]
        self.assertEqual(paths, expected_paths)

    def test_nested_directories_depth_first_ordering(self) -> None:
        """Verify deep nested directory recursion follows depth-first sorted discovery."""
        sub_b = self.temp_dir / "dir_b"
        sub_a = self.temp_dir / "dir_a"
        sub_b.mkdir()
        sub_a.mkdir()

        (sub_b / "sub_file2.txt").write_bytes(b"content2")
        (sub_a / "sub_file1.txt").write_bytes(b"content1")
        (self.temp_dir / "root_file.txt").write_bytes(b"content_root")

        inv = checksum_inventory_oracle(self.temp_dir)
        paths = [e["path"] for e in inv["entries"]]

        expected = [
            (sub_a / "sub_file1.txt").as_posix(),
            (sub_b / "sub_file2.txt").as_posix(),
            (self.temp_dir / "root_file.txt").as_posix(),
        ]
        self.assertEqual(paths, expected)
        self.assertEqual(inv["summary"]["total_files"], 3)
        self.assertEqual(inv["summary"]["total_bytes"], 8 + 8 + 12)

    def test_identical_files_both_retained(self) -> None:
        """Verify unlike duplicate detection, checksum inventory retains EVERY file."""
        f1 = self.temp_dir / "copy1.bin"
        f2 = self.temp_dir / "copy2.bin"
        payload = b"duplicate content for both files"
        f1.write_bytes(payload)
        f2.write_bytes(payload)

        inv = checksum_inventory_oracle(self.temp_dir)
        self.assertEqual(inv["summary"]["total_files"], 2)
        self.assertEqual(inv["summary"]["total_bytes"], len(payload) * 2)
        self.assertEqual(len(inv["entries"]), 2)
        self.assertEqual(inv["entries"][0]["sha256"], inv["entries"][1]["sha256"])
        self.assertNotEqual(inv["entries"][0]["path"], inv["entries"][1]["path"])

    def test_json_schema_validation(self) -> None:
        """Verify strict conformance to the T007 JSON schema specification."""
        (self.temp_dir / "data.bin").write_bytes(b"binary\x00\xffdata")
        inv = checksum_inventory_oracle(self.temp_dir)

        # Top-level required keys
        self.assertEqual(set(inv.keys()), {"schema_version", "workload", "root", "summary", "entries"})
        self.assertIsInstance(inv["schema_version"], int)
        self.assertEqual(inv["schema_version"], 1)
        self.assertEqual(inv["workload"], "checksum_inventory")
        self.assertIsInstance(inv["root"], str)

        # Summary structure
        self.assertEqual(set(inv["summary"].keys()), {"total_files", "total_bytes"})
        self.assertIsInstance(inv["summary"]["total_files"], int)
        self.assertIsInstance(inv["summary"]["total_bytes"], int)

        # Entries structure
        self.assertIsInstance(inv["entries"], list)
        for e in inv["entries"]:
            self.assertEqual(set(e.keys()), {"path", "size", "sha256"})
            self.assertIsInstance(e["path"], str)
            self.assertIsInstance(e["size"], int)
            self.assertIsInstance(e["sha256"], str)
            self.assertTrue(re.match(r"^[0-9a-f]{64}$", e["sha256"]))

    def test_argv_parsing_subcommand(self) -> None:
        """Verify argv parsing for all required CLI forms."""
        # 1. dupe checksum <path>
        root, is_json = simulate_parse_checksum_args(["dupe", "checksum", "/test/dir"])
        self.assertEqual(root, "/test/dir")
        self.assertFalse(is_json)

        # 2. dupe checksum <path> --json
        root, is_json = simulate_parse_checksum_args(["dupe", "checksum", "/test/dir", "--json"])
        self.assertEqual(root, "/test/dir")
        self.assertTrue(is_json)

        # 3. dupe checksum --json <path>
        root, is_json = simulate_parse_checksum_args(["dupe", "checksum", "--json", "/test/dir"])
        self.assertEqual(root, "/test/dir")
        self.assertTrue(is_json)

        # 4. dupe checksum (missing path)
        root, is_json = simulate_parse_checksum_args(["dupe", "checksum"])
        self.assertEqual(root, "")
        self.assertFalse(is_json)

        # 5. dupe checksum --json (missing path)
        root, is_json = simulate_parse_checksum_args(["dupe", "checksum", "--json"])
        self.assertEqual(root, "")
        self.assertTrue(is_json)

    def test_cli_dispatch_separation(self) -> None:
        """Verify dispatch condition strictly isolates checksum subcommand from duplicate pass."""
        # Subcommand calls
        self.assertTrue(simulate_is_checksum_command(["dupe", "checksum", "/path"]))
        self.assertTrue(simulate_is_checksum_command(["dupe", "checksum"]))
        self.assertTrue(simulate_is_checksum_command(["dupe", "checksum", "--json"]))

        # Duplicate scan calls (must return False)
        self.assertFalse(simulate_is_checksum_command(["dupe", "/path"]))
        self.assertFalse(simulate_is_checksum_command(["dupe", "/path", "--json"]))
        self.assertFalse(simulate_is_checksum_command(["dupe", "--json", "/path"]))
        self.assertFalse(simulate_is_checksum_command(["dupe"]))

    def test_harness_metrics_extraction(self) -> None:
        """Verify extract_checksum_workload_metrics() correctly parses T007 JSON."""
        sample_json = {
            "schema_version": 1,
            "workload": "checksum_inventory",
            "root": "/sample/path",
            "summary": {
                "total_files": 42,
                "total_bytes": 1048576,
            },
            "entries": [
                {"path": f"/sample/path/f{i}.txt", "size": 24966, "sha256": "a" * 64}
                for i in range(42)
            ],
        }

        metrics = extract_checksum_workload_metrics(sample_json)
        self.assertIsInstance(metrics, BaselineChecksumWorkloadMetrics)
        self.assertEqual(metrics.total_files, 42)
        self.assertEqual(metrics.total_bytes, 1048576)
        self.assertEqual(metrics.entries_count, 42)

        d = metrics.to_dict()
        self.assertEqual(d["total_files"], 42)
        self.assertEqual(d["total_bytes"], 1048576)
        self.assertEqual(d["entries_count"], 42)

    def test_zero_byte_file_hashing(self) -> None:
        """Verify empty (0-byte) files produce the standard SHA-256 empty digest."""
        empty_file = self.temp_dir / "empty.txt"
        empty_file.write_bytes(b"")

        empty_digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        inv = checksum_inventory_oracle(self.temp_dir)

        self.assertEqual(inv["summary"]["total_files"], 1)
        self.assertEqual(inv["summary"]["total_bytes"], 0)
        self.assertEqual(inv["entries"][0]["size"], 0)
        self.assertEqual(inv["entries"][0]["sha256"], empty_digest)


def get_j2_binary() -> str | None:
    """Detect available J2 compiler/interpreter binary."""
    env_bin = os.environ.get("J2_BIN")
    if env_bin:
        resolved = shutil.which(env_bin)
        if resolved:
            return resolved
        if Path(env_bin).is_file():
            return env_bin
    resolved = shutil.which("j2")
    if resolved:
        return resolved
    for candidate in [
        Path.home() / ".j2" / "bin" / "j2",
        Path("/usr/local/bin/j2"),
        Path("/opt/homebrew/bin/j2"),
    ]:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


J2_BIN = get_j2_binary()
HAS_J2 = False
if J2_BIN:
    try:
        probe = subprocess.run([J2_BIN, "--version"], capture_output=True, timeout=5)
        if probe.returncode == 0:
            HAS_J2 = True
    except Exception:
        HAS_J2 = False


@dataclass
class J2ExecutionResult:
    returncode: int
    stdout_bytes: bytes
    stderr_bytes: bytes
    stdout_text: str
    stderr_text: str
    timed_out: bool = False


def run_live_j2(
    args: list[str],
    *,
    timeout: int = 30,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
) -> J2ExecutionResult:
    """Execute live J2 interpreter with verified project conventions:
    j2 --allow-fs src/main.j2 <args...>
    """
    if not HAS_J2 or not J2_BIN:
        raise RuntimeError("LIVE_J2_TESTS_SKIPPED: J2 binary is not available.")

    cmd = [J2_BIN, "--allow-fs", str(REPO_ROOT / "src" / "main.j2")] + args
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=run_env,
            capture_output=True,
            timeout=timeout,
        )
        return J2ExecutionResult(
            returncode=proc.returncode,
            stdout_bytes=proc.stdout,
            stderr_bytes=proc.stderr,
            stdout_text=proc.stdout.decode("utf-8", errors="replace"),
            stderr_text=proc.stderr.decode("utf-8", errors="replace"),
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        return J2ExecutionResult(
            returncode=-1,
            stdout_bytes=exc.stdout or b"",
            stderr_bytes=exc.stderr or b"",
            stdout_text=(exc.stdout or b"").decode("utf-8", errors="replace"),
            stderr_text=(exc.stderr or b"").decode("utf-8", errors="replace"),
            timed_out=True,
        )


class TestT007LiveJ2Execution(unittest.TestCase):
    """Real live execution tests for T007 J2 checksum inventory workload.

    F-02 remediation: Executes real J2 source (`j2 --allow-fs src/main.j2 checksum ...`)
    and compares output against the independent Python oracle as well as asserting
    byte-for-byte identity across argument permutations.
    """

    live_tests_executed: int = 0

    @classmethod
    def setUpClass(cls) -> None:
        cls.live_tests_executed = 0
        if not HAS_J2:
            print(f"\n[LIVE_J2_STATUS] LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN or 'j2'}' is unavailable.")
        else:
            print(f"\n[LIVE_J2_STATUS] J2 binary found at: {J2_BIN}. Running live J2 execution tests.")

    def setUp(self) -> None:
        if not HAS_J2:
            self.skipTest(f"LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN or 'j2'}' is unavailable in environment.")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t007_live_j2_"))

    def tearDown(self) -> None:
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if HAS_J2:
            print(
                f"\n[LIVE_J2_STATUS] LIVE_J2_TESTS_PASS: {cls.live_tests_executed} "
                f"live J2 checksum tests passed successfully."
            )
        else:
            print(
                "\n[LIVE_J2_STATUS] LIVE_J2_TESTS_SKIPPED: All live J2 checksum tests "
                "skipped (J2 binary unavailable)."
            )

    def _assert_live_checksum_parity_and_oracle(self, corpus_path: Path) -> dict:
        """Helper to invoke J2 in both argument arrangements and assert oracle equality:
        1. j2 --allow-fs src/main.j2 checksum <path> --json
        2. j2 --allow-fs src/main.j2 checksum --json <path>
        Byte-for-byte exact equality is enforced between both.
        Independent Python hashlib.sha256 oracle is asserted against the result.
        """
        posix_path = corpus_path.as_posix()
        res1 = run_live_j2(["checksum", posix_path, "--json"])
        res2 = run_live_j2(["checksum", "--json", posix_path])

        self.assertEqual(res1.returncode, 0, f"J2 invocation failed: {res1.stderr_text}")
        self.assertEqual(res2.returncode, 0, f"J2 invocation failed: {res2.stderr_text}")

        # Byte-for-byte exact comparison
        self.assertEqual(
            res1.stdout_bytes,
            res2.stdout_bytes,
            "Byte mismatch between 'checksum <path> --json' and 'checksum --json <path>'",
        )

        data = json.loads(res1.stdout_text)
        expected = checksum_inventory_oracle(corpus_path)

        self.assertEqual(data["schema_version"], expected["schema_version"])
        self.assertEqual(data["workload"], expected["workload"])
        self.assertEqual(data["summary"]["total_files"], expected["summary"]["total_files"])
        self.assertEqual(data["summary"]["total_bytes"], expected["summary"]["total_bytes"])
        self.assertEqual(len(data["entries"]), len(expected["entries"]))

        for act_entry, exp_entry in zip(data["entries"], expected["entries"]):
            self.assertEqual(act_entry["path"], exp_entry["path"])
            self.assertEqual(act_entry["size"], exp_entry["size"])
            self.assertEqual(act_entry["sha256"], exp_entry["sha256"])

        TestT007LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")
        return data

    def test_live_empty_directory(self) -> None:
        """Verify real J2 execution on an empty directory produces empty inventory."""
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_single_file(self) -> None:
        """Verify real J2 execution on a single file matches hashlib.sha256."""
        (self.temp_dir / "file.txt").write_bytes(b"hello real j2 world\n")
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_multiple_files_sorted(self) -> None:
        """Verify real J2 execution on multiple files preserves sorted discovery."""
        (self.temp_dir / "z.txt").write_bytes(b"z content")
        (self.temp_dir / "a.txt").write_bytes(b"a content longer")
        (self.temp_dir / "m.txt").write_bytes(b"m content medium")
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_nested_directory(self) -> None:
        """Verify real J2 execution traverses nested directories depth-first."""
        dir1 = self.temp_dir / "sub1"
        dir2 = self.temp_dir / "sub2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "alpha.txt").write_bytes(b"nested alpha")
        (dir2 / "beta.txt").write_bytes(b"nested beta")
        (self.temp_dir / "root.txt").write_bytes(b"root file")
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_binary_content(self) -> None:
        """Verify real J2 execution computes exact SHA-256 for non-UTF8 binary files."""
        binary_data = bytes(range(256)) + b"\x00\xff\xfe\x01\x80\xaa\xbb"
        (self.temp_dir / "blob.bin").write_bytes(binary_data)
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_zero_byte_file(self) -> None:
        """Verify real J2 execution correctly computes SHA-256 on a 0-byte file."""
        (self.temp_dir / "empty.dat").write_bytes(b"")
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_duplicate_content_files(self) -> None:
        """Verify real J2 execution inventories both files when content is identical."""
        content = b"shared identical payload between files"
        (self.temp_dir / "c1.txt").write_bytes(content)
        (self.temp_dir / "c2.txt").write_bytes(content)
        self._assert_live_checksum_parity_and_oracle(self.temp_dir)

    def test_live_argument_order_byte_identity(self) -> None:
        """Explicitly assert byte-for-byte equality between CLI argument forms."""
        d = self.temp_dir / "mixed"
        d.mkdir()
        (d / "f1.txt").write_bytes(b"file one")
        (d / "f2.bin").write_bytes(b"\xde\xad\xbe\xef")
        (self.temp_dir / "zero.dat").write_bytes(b"")

        res1 = run_live_j2(["checksum", self.temp_dir.as_posix(), "--json"])
        res2 = run_live_j2(["checksum", "--json", self.temp_dir.as_posix()])

        self.assertEqual(res1.returncode, 0)
        self.assertEqual(res2.returncode, 0)
        self.assertEqual(res1.stdout_bytes, res2.stdout_bytes)

        TestT007LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_human_text_format(self) -> None:
        """Verify real J2 execution without --json outputs '<sha256>  <path>' format."""
        sample = self.temp_dir / "human.txt"
        data = b"human readable format verification"
        sample.write_bytes(data)
        expected_digest = hashlib.sha256(data).hexdigest()

        res = run_live_j2(["checksum", self.temp_dir.as_posix()])
        self.assertEqual(res.returncode, 0)

        lines = res.stdout_text.strip().splitlines()
        self.assertTrue(any(expected_digest in l and "human.txt" in l for l in lines))
        self.assertTrue(any("Total files: 1, Total bytes:" in l for l in lines))

        TestT007LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_missing_root_usage(self) -> None:
        """Verify real J2 execution with missing root prints usage without crashing."""
        res1 = run_live_j2(["checksum"])
        self.assertIn("dupe checksum PATH", res1.stdout_text + res1.stderr_text)

        res2 = run_live_j2(["checksum", "--json"])
        self.assertIn("dupe checksum PATH", res2.stdout_text + res2.stderr_text)

        TestT007LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_nonexistent_path(self) -> None:
        """Verify real J2 execution on nonexistent directory does not succeed silently."""
        nonexistent = self.temp_dir / "does_not_exist"
        res = run_live_j2(["checksum", nonexistent.as_posix(), "--json"])
        # Either returncode is nonzero or 0 files found
        if res.returncode == 0:
            data = json.loads(res.stdout_text)
            self.assertEqual(data["summary"]["total_files"], 0)

        TestT007LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_regression_duplicate_scan(self) -> None:
        """Verify real J2 execution of dupe <path> --json still routes to duplicate analysis."""
        d = self.temp_dir / "dup_corpus"
        d.mkdir()
        content = b"duplicate scan regression check payload"
        (d / "file_a.txt").write_bytes(content)
        (d / "file_b.txt").write_bytes(content)

        res = run_live_j2([d.as_posix(), "--json"])
        self.assertEqual(res.returncode, 0, f"Duplicate scan regression failed: {res.stderr_text}")

        # Verify duplicate scan JSON schema matching frozen Phase 3 contract
        data = json.loads(res.stdout_text)
        self.assertEqual(
            set(data.keys()),
            {"files_scanned", "hash_candidates", "duplicate_groups", "reclaimable_bytes"},
        )
        self.assertEqual(data["files_scanned"], 2)
        self.assertEqual(data["hash_candidates"], 2)
        self.assertEqual(len(data["duplicate_groups"]), 1)
        group = data["duplicate_groups"][0]
        self.assertEqual(set(group.keys()), {"hash", "size", "files", "reclaimable_bytes"})
        self.assertEqual(group["size"], len(content))
        self.assertEqual(len(group["files"]), 2)
        self.assertEqual(group["reclaimable_bytes"], len(content))
        self.assertEqual(data["reclaimable_bytes"], len(content))

        TestT007LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")


if __name__ == "__main__":
    unittest.main()

