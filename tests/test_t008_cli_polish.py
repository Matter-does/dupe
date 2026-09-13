"""Focused acceptance and unit tests for T008 — CLI / Product Surface Polish.

Verifies:
1. Help flag parsing and professional usage experience:
   - dupe --help, dupe -h, dupe help
   - dupe checksum --help, dupe checksum -h, dupe checksum help
2. CLI argument parsing and symmetry:
   - dupe <path> [--json]
   - dupe [--json] <path>
   - dupe checksum <path> [--json]
   - dupe checksum [--json] <path>
3. Missing argument validation:
   - dupe (no args) -> top-level usage
   - dupe --json (missing path) -> explicit error + usage
   - dupe checksum -> checksum usage
   - dupe checksum --json -> checksum usage
4. Unexpected / multiple argument validation:
   - dupe <path1> <path2>
   - dupe <path> --unknown
   - dupe checksum <path1> <path2>
   - dupe checksum <path> --unknown
5. JSON determinism across repeated executions.
6. Byte-for-byte argument order identity.
7. Frozen Phase 3 duplicate regression safety.
8. Nonexistent path failure propagation (non-zero exit code).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]


def is_help_flag_sim(arg: str) -> bool:
    return arg in ("--help", "-h", "help")


def simulate_parse_duplicate_args(args: list[str]) -> tuple[str, bool, int, bool]:
    """Pure simulation of parse_duplicate_args() from src/main.j2.
    Returns: (root, is_json, extra_count, is_help)
    """
    root = ""
    is_json = False
    is_help = False
    extra_count = 0
    skip_first = True

    for arg in args:
        if skip_first:
            skip_first = False
        else:
            if is_help_flag_sim(arg):
                is_help = True
            else:
                if arg == "--json":
                    is_json = True
                else:
                    if root == "":
                        root = arg
                    else:
                        extra_count += 1

    return root, is_json, extra_count, is_help


def simulate_parse_checksum_args_t008(args: list[str]) -> tuple[str, bool, int, bool]:
    """Pure simulation of parse_checksum_args() from src/checksum.j2.
    Returns: (root, is_json, extra_count, is_help)
    """
    root = ""
    is_json = False
    is_help = False
    extra_count = 0
    skip_first = True
    skip_subcmd = True

    for arg in args:
        if skip_first:
            skip_first = False
        else:
            if skip_subcmd:
                skip_subcmd = False
            else:
                if is_help_flag_sim(arg):
                    is_help = True
                else:
                    if arg == "--json":
                        is_json = True
                    else:
                        if root == "":
                            root = arg
                        else:
                            extra_count += 1

    return root, is_json, extra_count, is_help


def simulate_is_checksum_command(args: list[str]) -> bool:
    """Pure simulation of is_checksum_command() from src/main.j2."""
    if len(args) > 1:
        if args[1] == "checksum":
            return True
    return False


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


class TestT008CLIParsingLogic(unittest.TestCase):
    """Offline Python unit tests validating the T008 CLI parsing contract."""

    def test_duplicate_cli_parsing_valid(self) -> None:
        # Standard: dupe /path
        r, j, e, h = simulate_parse_duplicate_args(["dupe", "/data"])
        self.assertEqual(r, "/data")
        self.assertFalse(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

        # dupe /path --json
        r, j, e, h = simulate_parse_duplicate_args(["dupe", "/data", "--json"])
        self.assertEqual(r, "/data")
        self.assertTrue(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

        # Symmetry: dupe --json /path
        r, j, e, h = simulate_parse_duplicate_args(["dupe", "--json", "/data"])
        self.assertEqual(r, "/data")
        self.assertTrue(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

    def test_duplicate_cli_parsing_help(self) -> None:
        for flag in ("--help", "-h", "help"):
            r, j, e, h = simulate_parse_duplicate_args(["dupe", flag])
            self.assertTrue(h)
            self.assertEqual(r, "")
            self.assertEqual(e, 0)

    def test_duplicate_cli_parsing_missing_path(self) -> None:
        # dupe (no args)
        r, j, e, h = simulate_parse_duplicate_args(["dupe"])
        self.assertEqual(r, "")
        self.assertFalse(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

        # dupe --json
        r, j, e, h = simulate_parse_duplicate_args(["dupe", "--json"])
        self.assertEqual(r, "")
        self.assertTrue(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

    def test_duplicate_cli_parsing_multiple_roots_and_unknown(self) -> None:
        # Multiple roots: dupe /dir1 /dir2
        r, j, e, h = simulate_parse_duplicate_args(["dupe", "/dir1", "/dir2"])
        self.assertEqual(r, "/dir1")
        self.assertEqual(e, 1)

        # Unknown option: dupe /dir1 --unknown
        r, j, e, h = simulate_parse_duplicate_args(["dupe", "/dir1", "--unknown"])
        self.assertEqual(r, "/dir1")
        self.assertEqual(e, 1)

    def test_checksum_cli_parsing_valid(self) -> None:
        # dupe checksum /data
        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", "/data"])
        self.assertEqual(r, "/data")
        self.assertFalse(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

        # dupe checksum /data --json
        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", "/data", "--json"])
        self.assertEqual(r, "/data")
        self.assertTrue(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

        # Symmetry: dupe checksum --json /data
        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", "--json", "/data"])
        self.assertEqual(r, "/data")
        self.assertTrue(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

    def test_checksum_cli_parsing_help(self) -> None:
        for flag in ("--help", "-h", "help"):
            r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", flag])
            self.assertTrue(h)
            self.assertEqual(r, "")
            self.assertEqual(e, 0)

    def test_checksum_cli_parsing_missing_path(self) -> None:
        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum"])
        self.assertEqual(r, "")
        self.assertFalse(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", "--json"])
        self.assertEqual(r, "")
        self.assertTrue(j)
        self.assertEqual(e, 0)
        self.assertFalse(h)

    def test_checksum_cli_parsing_multiple_roots_and_unknown(self) -> None:
        # Multiple roots: dupe checksum /dir1 /dir2
        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", "/dir1", "/dir2"])
        self.assertEqual(r, "/dir1")
        self.assertEqual(e, 1)

        # Unknown option: dupe checksum /dir1 --unknown
        r, j, e, h = simulate_parse_checksum_args_t008(["dupe", "checksum", "/dir1", "--unknown"])
        self.assertEqual(r, "/dir1")
        self.assertEqual(e, 1)

    def test_cli_subcommand_dispatch_strictness(self) -> None:
        # Checksum subcommand calls
        self.assertTrue(simulate_is_checksum_command(["dupe", "checksum", "/path"]))
        self.assertTrue(simulate_is_checksum_command(["dupe", "checksum"]))
        self.assertTrue(simulate_is_checksum_command(["dupe", "checksum", "--json"]))

        # Duplicate scan calls (must strictly return False)
        self.assertFalse(simulate_is_checksum_command(["dupe", "/path"]))
        self.assertFalse(simulate_is_checksum_command(["dupe", "/path", "--json"]))
        self.assertFalse(simulate_is_checksum_command(["dupe", "--json", "/path"]))
        self.assertFalse(simulate_is_checksum_command(["dupe", "--help"]))
        self.assertFalse(simulate_is_checksum_command(["dupe"]))


class TestT008LiveJ2Execution(unittest.TestCase):
    """Real live execution tests for T008 CLI polish behaviors."""

    live_tests_executed: int = 0

    @classmethod
    def setUpClass(cls) -> None:
        cls.live_tests_executed = 0
        if not HAS_J2:
            print(f"\n[LIVE_J2_STATUS] LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN or 'j2'}' is unavailable.")
        else:
            print(f"\n[LIVE_J2_STATUS] J2 binary found at: {J2_BIN}. Running T008 live CLI tests.")

    def setUp(self) -> None:
        if not HAS_J2:
            self.skipTest(f"LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN or 'j2'}' is unavailable in environment.")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t008_live_j2_"))

    def tearDown(self) -> None:
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if HAS_J2:
            print(
                f"\n[LIVE_J2_STATUS] LIVE_J2_TESTS_PASS: {cls.live_tests_executed} "
                f"T008 live J2 tests passed successfully."
            )
        else:
            print(
                "\n[LIVE_J2_STATUS] LIVE_J2_TESTS_SKIPPED: All live J2 T008 tests "
                "skipped (J2 binary unavailable)."
            )

    def test_live_duplicate_help_flags(self) -> None:
        """Verify dupe --help, dupe -h, and dupe help show professional usage."""
        for flag in ("--help", "-h", "help"):
            res = run_live_j2([flag])
            self.assertEqual(res.returncode, 0, f"Help with {flag} returned non-zero")
            self.assertIn("dupe — filesystem intelligence engine", res.stdout_text)
            self.assertIn("dupe PATH [--json]", res.stdout_text)
            self.assertIn("dupe checksum PATH [--json]", res.stdout_text)
            self.assertIn("Workloads:", res.stdout_text)
            self.assertIn("duplicate (default)", res.stdout_text)
            self.assertIn("checksum", res.stdout_text)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_checksum_help_flags(self) -> None:
        """Verify dupe checksum --help, -h, and help show checksum usage."""
        for flag in ("--help", "-h", "help"):
            res = run_live_j2(["checksum", flag])
            self.assertEqual(res.returncode, 0, f"Checksum help with {flag} returned non-zero")
            self.assertIn("dupe — checksum inventory", res.stdout_text)
            self.assertIn("dupe checksum PATH [--json]", res.stdout_text)
            self.assertIn("Compute SHA-256 checksum inventory", res.stdout_text)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_duplicate_argument_symmetry(self) -> None:
        """Verify byte-for-byte exact equality between:
        dupe <path> --json  AND  dupe --json <path>
        """
        d = self.temp_dir / "sym_corpus"
        d.mkdir()
        content = b"symmetry test payload for duplicate scan"
        (d / "copy1.txt").write_bytes(content)
        (d / "copy2.txt").write_bytes(content)

        posix = d.as_posix()
        res1 = run_live_j2([posix, "--json"])
        res2 = run_live_j2(["--json", posix])

        self.assertEqual(res1.returncode, 0, f"Order 1 failed: {res1.stderr_text}")
        self.assertEqual(res2.returncode, 0, f"Order 2 failed: {res2.stderr_text}")
        self.assertEqual(
            res1.stdout_bytes,
            res2.stdout_bytes,
            "Byte mismatch between 'dupe <path> --json' and 'dupe --json <path>'",
        )

        data = json.loads(res1.stdout_text)
        self.assertEqual(data["files_scanned"], 2)
        self.assertEqual(data["hash_candidates"], 2)
        self.assertEqual(len(data["duplicate_groups"]), 1)
        self.assertEqual(data["reclaimable_bytes"], len(content))

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_checksum_argument_symmetry(self) -> None:
        """Verify byte-for-byte exact equality between:
        dupe checksum <path> --json  AND  dupe checksum --json <path>
        """
        d = self.temp_dir / "sym_check"
        d.mkdir()
        (d / "f1.dat").write_bytes(b"hello")
        (d / "f2.dat").write_bytes(b"world")

        posix = d.as_posix()
        res1 = run_live_j2(["checksum", posix, "--json"])
        res2 = run_live_j2(["checksum", "--json", posix])

        self.assertEqual(res1.returncode, 0)
        self.assertEqual(res2.returncode, 0)
        self.assertEqual(
            res1.stdout_bytes,
            res2.stdout_bytes,
            "Byte mismatch between 'checksum <path> --json' and 'checksum --json <path>'",
        )

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_duplicate_json_determinism(self) -> None:
        """Verify duplicate scan JSON output is byte-identical across consecutive executions."""
        d = self.temp_dir / "det_corpus"
        d.mkdir()
        (d / "a.bin").write_bytes(b"test1")
        (d / "b.bin").write_bytes(b"test1")
        (d / "c.bin").write_bytes(b"test2")

        posix = d.as_posix()
        res1 = run_live_j2([posix, "--json"])
        res2 = run_live_j2([posix, "--json"])

        self.assertEqual(res1.returncode, 0)
        self.assertEqual(res2.returncode, 0)
        self.assertEqual(res1.stdout_bytes, res2.stdout_bytes)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_checksum_json_determinism(self) -> None:
        """Verify checksum JSON output is byte-identical across consecutive executions."""
        d = self.temp_dir / "det_check"
        d.mkdir()
        (d / "x.bin").write_bytes(b"content-x")
        (d / "y.bin").write_bytes(b"content-y")

        posix = d.as_posix()
        res1 = run_live_j2(["checksum", posix, "--json"])
        res2 = run_live_j2(["checksum", posix, "--json"])

        self.assertEqual(res1.returncode, 0)
        self.assertEqual(res2.returncode, 0)
        self.assertEqual(res1.stdout_bytes, res2.stdout_bytes)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_duplicate_missing_argument(self) -> None:
        """Verify dupe with no arguments or missing path prints appropriate usage."""
        # 1. dupe (no args)
        res_empty = run_live_j2([])
        self.assertIn("dupe — filesystem intelligence engine", res_empty.stdout_text)
        self.assertIn("dupe PATH [--json]", res_empty.stdout_text)

        # 2. dupe --json (missing path)
        res_json_only = run_live_j2(["--json"])
        self.assertIn("Missing required path argument", res_json_only.stdout_text)
        self.assertIn("dupe PATH [--json]", res_json_only.stdout_text)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_checksum_missing_argument(self) -> None:
        """Verify dupe checksum with missing path prints checksum usage."""
        res1 = run_live_j2(["checksum"])
        self.assertIn("dupe checksum PATH", res1.stdout_text)

        res2 = run_live_j2(["checksum", "--json"])
        self.assertIn("dupe checksum PATH", res2.stdout_text)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_multiple_roots_validation(self) -> None:
        """Verify multiple roots or unexpected args fail gracefully with error messaging."""
        # Duplicate mode: dupe /dir1 /dir2
        res1 = run_live_j2(["/dir1", "/dir2"])
        self.assertIn("Multiple paths or unexpected arguments", res1.stdout_text)

        # Checksum mode: dupe checksum /dir1 /dir2
        res2 = run_live_j2(["checksum", "/dir1", "/dir2"])
        self.assertIn("Multiple paths or unexpected arguments", res2.stdout_text)

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_duplicate_regression(self) -> None:
        """Verify duplicate scanning preserves complete frozen Phase 3 JSON schema."""
        d = self.temp_dir / "reg_corpus"
        d.mkdir()
        c = b"duplicate regression verification bytes"
        (d / "r1.txt").write_bytes(c)
        (d / "r2.txt").write_bytes(c)

        res = run_live_j2([d.as_posix(), "--json"])
        self.assertEqual(res.returncode, 0)

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
        self.assertEqual(group["size"], len(c))
        self.assertEqual(len(group["files"]), 2)
        self.assertEqual(group["reclaimable_bytes"], len(c))

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_nonexistent_path_failure(self) -> None:
        """Verify nonexistent paths fail with non-zero exit code (RuntimeError from fs.list_dir)."""
        nonexistent = self.temp_dir / "nonexistent_target_123"

        # Duplicate scan on nonexistent path
        res_dup = run_live_j2([nonexistent.as_posix(), "--json"])
        self.assertNotEqual(res_dup.returncode, 0, "Duplicate scan on nonexistent path should fail non-zero")

        # Checksum on nonexistent path
        res_chk = run_live_j2(["checksum", nonexistent.as_posix(), "--json"])
        self.assertNotEqual(res_chk.returncode, 0, "Checksum scan on nonexistent path should fail non-zero")

        TestT008LiveJ2Execution.live_tests_executed += 1
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")


if __name__ == "__main__":
    unittest.main()
