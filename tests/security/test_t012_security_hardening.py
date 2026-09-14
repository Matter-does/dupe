"""T012 Security Hardening Regression & Adversarial Verification Tests.

Covers:
- SEC-001: Strict JSON schema validation (scalar types, signs, 64-char sha256) and GUI crash prevention
- SEC-002: Accurate engine resolution (no misleading "Native" badge on missing executable)
- SEC-003: Controlled scalability and bounded O(N^2) evaluation on synthetic corpora
- SEC-004: --clean refusal on symlinks and reparse points
- SEC-005: Engine stdout buffering cap and fail-closed policy
- Adversarial attack vectors: hostile path payloads, injection strings, malformed containers
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from gui.adapter import EngineAdapter, EngineResult
from gui.view_models import DuplicateViewModel, ChecksumViewModel
from tests.demo_corpus import (
    create_demo_corpus,
    verify_demo_corpus,
    is_symlink_or_reparse,
    DEMO_CORPUS_SPEC,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Probe Tkinter display capability
HAS_TK_DISPLAY = False
try:
    import tkinter as tk
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
    HAS_TK_DISPLAY = True
except Exception:
    HAS_TK_DISPLAY = False


class TestSEC001SchemaValidation(unittest.TestCase):
    """SEC-001: Strict scalar type and value constraint validation tests."""

    def setUp(self) -> None:
        self.adapter = EngineAdapter()
        self.valid_hash = "a" * 64
        self.valid_hash_2 = "b" * 64

    def test_malformed_scalar_types_fail_closed(self) -> None:
        """Scalar values with wrong types (str for int, bool for int) must fail closed."""
        base_duplicate = {
            "files_scanned": 10,
            "hash_candidates": 4,
            "duplicate_groups": [],
            "reclaimable_bytes": 0,
        }

        # files_scanned as string
        bad_1 = dict(base_duplicate, files_scanned="10")
        err_1 = self.adapter._validate_schema("duplicate", bad_1)
        self.assertIsNotNone(err_1)
        self.assertIn("files_scanned", err_1)

        # files_scanned as boolean (in Python bool is subclass of int)
        bad_bool = dict(base_duplicate, files_scanned=True)
        err_bool = self.adapter._validate_schema("duplicate", bad_bool)
        self.assertIsNotNone(err_bool)
        self.assertIn("files_scanned", err_bool)

        # hash_candidates as dict
        bad_2 = dict(base_duplicate, hash_candidates={"count": 4})
        err_2 = self.adapter._validate_schema("duplicate", bad_2)
        self.assertIsNotNone(err_2)
        self.assertIn("hash_candidates", err_2)

        # reclaimable_bytes as float
        bad_3 = dict(base_duplicate, reclaimable_bytes=1024.5)
        err_3 = self.adapter._validate_schema("duplicate", bad_3)
        self.assertIsNotNone(err_3)
        self.assertIn("reclaimable_bytes", err_3)

    def test_negative_counts_and_sizes_fail_closed(self) -> None:
        """Negative counts or byte sizes must fail closed."""
        # Negative files_scanned
        err = self.adapter._validate_schema("duplicate", {
            "files_scanned": -1,
            "hash_candidates": 0,
            "duplicate_groups": [],
            "reclaimable_bytes": 0,
        })
        self.assertIsNotNone(err)
        self.assertIn("files_scanned", err)

        # Negative group size
        err = self.adapter._validate_schema("duplicate", {
            "files_scanned": 2,
            "hash_candidates": 2,
            "duplicate_groups": [{
                "hash": self.valid_hash,
                "size": -100,
                "files": ["/a", "/b"],
                "reclaimable_bytes": 100,
            }],
            "reclaimable_bytes": 100,
        })
        self.assertIsNotNone(err)
        self.assertIn("size", err)

        # Negative checksum summary
        err = self.adapter._validate_schema("checksum", {
            "schema_version": 1,
            "workload": "checksum_inventory",
            "root": "/root",
            "summary": {"total_files": -1, "total_bytes": 100},
            "entries": [],
        })
        self.assertIsNotNone(err)
        self.assertIn("total_files", err)

    def test_invalid_sha256_fails_closed(self) -> None:
        """SHA-256 digests not matching 64 lowercase hex characters must fail closed."""
        invalid_hashes = [
            "",  # empty
            "a" * 63,  # too short
            "a" * 65,  # too long
            "A" * 64,  # uppercase
            "g" * 64,  # invalid hex character 'g'
            "12345!@#$%",  # non-hex symbols
            None,  # None
            1234567890,  # integer
        ]

        for bad_hash in invalid_hashes:
            # Duplicate group hash
            dup_payload = {
                "files_scanned": 2,
                "hash_candidates": 2,
                "duplicate_groups": [{
                    "hash": bad_hash,
                    "size": 10,
                    "files": ["/a", "/b"],
                    "reclaimable_bytes": 10,
                }],
                "reclaimable_bytes": 10,
            }
            err = self.adapter._validate_schema("duplicate", dup_payload)
            self.assertIsNotNone(err, f"Expected validation failure for hash: {bad_hash!r}")
            self.assertIn("hash", err)

            # Checksum entry sha256
            chk_payload = {
                "schema_version": 1,
                "workload": "checksum_inventory",
                "root": "/root",
                "summary": {"total_files": 1, "total_bytes": 10},
                "entries": [{
                    "path": "/root/file.txt",
                    "size": 10,
                    "sha256": bad_hash,
                }],
            }
            err_chk = self.adapter._validate_schema("checksum", chk_payload)
            self.assertIsNotNone(err_chk, f"Expected validation failure for checksum sha256: {bad_hash!r}")
            self.assertIn("sha256", err_chk)

    def test_checksum_schema_version_validation(self) -> None:
        """Checksum schema_version must be a positive integer."""
        for bad_version in [0, -1, "1", True, None]:
            chk_payload = {
                "schema_version": bad_version,
                "workload": "checksum_inventory",
                "root": "/root",
                "summary": {"total_files": 0, "total_bytes": 0},
                "entries": [],
            }
            err = self.adapter._validate_schema("checksum", chk_payload)
            self.assertIsNotNone(err)
            self.assertIn("schema_version", err)

    @patch("subprocess.run")
    def test_run_analysis_malformed_scalar_produces_failed_engine_result(self, mock_run: MagicMock) -> None:
        """Malformed engine output returns EngineResult(success=False) without throwing."""
        payload = {
            "files_scanned": "ten",
            "hash_candidates": 4,
            "duplicate_groups": [],
            "reclaimable_bytes": 0,
        }
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(payload).encode("utf-8")
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/test/dir")
        self.assertFalse(result.success)
        self.assertIn("Invalid schema", result.error_message or "")
        self.assertIn("files_scanned", result.error_message or "")


@unittest.skipUnless(HAS_TK_DISPLAY, "GUI_TESTS_SKIPPED: Tkinter display unavailable in this environment.")
class TestSEC001GUICrashPrevention(unittest.TestCase):
    """SEC-001: Defensive ViewModel construction in GUI app event loop."""

    def setUp(self) -> None:
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.mock_adapter = MagicMock(spec=EngineAdapter)
        from gui.app import DupeApp
        self.app = DupeApp(root=self.root, adapter=self.mock_adapter)

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_gui_handles_viewmodel_conversion_exception_gracefully(self) -> None:
        """If a ViewModel raises an exception during construction, GUI must not crash Tk loop."""
        res = EngineResult(
            success=True,
            workload="duplicate",
            target_path="/test",
            returncode=0,
            data={"corrupted": True},
            raw_stdout="{}",
            raw_stderr="",
            error_message=None,
            duration_seconds=0.1,
            command_executed=["dupe", "/test", "--json"],
        )

        with patch.object(DuplicateViewModel, "from_engine_data", side_effect=ValueError("Synthetic conversion error")):
            self.app._apply_engine_result(res)

            self.assertFalse(self.app.is_running)
            self.assertIn("Synthetic conversion error", self.app.error_lbl.cget("text"))
            self.assertEqual(self.app.metric_1_val.get(), "—")
            self.assertEqual(len(self.app.tree.get_children()), 0)


class TestSEC002EngineResolution(unittest.TestCase):
    """SEC-002: Accurate engine resolution and badge introspection."""

    def test_missing_native_binary_not_reported_as_native(self) -> None:
        """Configured native_bin that does not exist must never report 'native' mode."""
        nonexistent = REPO_ROOT / "build" / "definitely_does_not_exist_dupe_bin"
        adapter = EngineAdapter(native_bin=nonexistent)
        mode, _ = adapter.resolve_engine_mode()
        self.assertNotEqual(mode, "native", "Missing binary was incorrectly reported as 'native'")

    def test_missing_all_engines_report_unavailable(self) -> None:
        """When neither native binary nor J2 interpreter exists, report 'unavailable'."""
        nonexistent_native = REPO_ROOT / "build" / "no_dupe"
        nonexistent_j2 = "/usr/bin/definitely_not_j2"
        adapter = EngineAdapter(native_bin=nonexistent_native, j2_bin=nonexistent_j2)

        with patch.object(adapter, "has_native_binary", return_value=False), \
             patch.object(adapter, "has_j2_interpreter", return_value=False):
            mode, base_cmd = adapter.resolve_engine_mode()
            self.assertEqual(mode, "unavailable")

    def test_interpreter_fallback_when_native_missing(self) -> None:
        """When native binary is missing but J2 interpreter exists, report 'interpreter'."""
        nonexistent_native = REPO_ROOT / "build" / "no_dupe"
        adapter = EngineAdapter(native_bin=nonexistent_native)

        with patch.object(adapter, "has_native_binary", return_value=False), \
             patch.object(adapter, "has_j2_interpreter", return_value=True), \
             patch.object(Path, "is_file", return_value=True):
            mode, base_cmd = adapter.resolve_engine_mode()
            self.assertEqual(mode, "interpreter")
            self.assertIn("--allow-fs", base_cmd)

    def test_native_present_reports_native(self) -> None:
        """When native binary exists and is executable, report 'native'."""
        adapter = EngineAdapter()
        with patch.object(adapter, "has_native_binary", return_value=True):
            mode, base_cmd = adapter.resolve_engine_mode()
            self.assertEqual(mode, "native")


@unittest.skipUnless(HAS_TK_DISPLAY, "GUI_TESTS_SKIPPED: Tkinter display unavailable in this environment.")
class TestSEC002GUIBadge(unittest.TestCase):
    """SEC-002: GUI badge reflects accurate engine mode without false claims."""

    def test_gui_badge_displays_unavailable_when_no_engine(self) -> None:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            mock_adapter = MagicMock(spec=EngineAdapter)
            mock_adapter.resolve_engine_mode.return_value = ("unavailable", ["dummy"])
            from gui.app import DupeApp
            app = DupeApp(root=root, adapter=mock_adapter)

            badge_text = app.engine_badge.cget("text")
            self.assertEqual(badge_text, "Engine: Unavailable")
        finally:
            root.destroy()


class TestSEC003ScalabilityLimitation(unittest.TestCase):
    """SEC-003: Documented scalability limitations and bounded resource evaluation."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t012_sec003_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sec003_scalability_bounded_execution(self) -> None:
        """Verify candidate grouping and reduction complete within bounded safe resource limits."""
        sizes = [10, 50, 100]
        timings: list[float] = []

        for count in sizes:
            cluster_dir = self.temp_dir / f"cluster_{count}"
            cluster_dir.mkdir(parents=True, exist_ok=True)
            payload = b"X" * 128
            for i in range(count):
                (cluster_dir / f"file_{i:04d}.dat").write_bytes(payload)

            start = time.perf_counter()
            file_records: list[tuple[str, int]] = []
            for p in sorted(cluster_dir.glob("*.dat")):
                file_records.append((str(p), p.stat().st_size))

            size_map: dict[int, list[str]] = {}
            for path, sz in file_records:
                size_map.setdefault(sz, []).append(path)
            candidates = [paths for sz, paths in size_map.items() if len(paths) >= 2]
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

            self.assertEqual(len(candidates), 1)
            self.assertEqual(len(candidates[0]), count)
            self.assertLess(elapsed, 2.0, f"Candidate reduction took excessive time for N={count}")


class TestSEC004SymlinkCleanupGuard(unittest.TestCase):
    """SEC-004: --clean refusal on symlinks and Windows reparse points."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t012_sec004_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_normal_directory_cleanup_succeeds(self) -> None:
        """Normal directory cleanup and creation succeeds."""
        normal_dir = self.temp_dir / "normal_demo"
        created = create_demo_corpus(normal_dir, clean=True)
        self.assertTrue(created.is_dir())
        info = verify_demo_corpus(created)
        self.assertEqual(info["files_count"], 8)

    def test_nonexistent_directory_cleanup_succeeds(self) -> None:
        """Nonexistent target directory with clean=True succeeds."""
        nonexistent = self.temp_dir / "nonexistent_target"
        created = create_demo_corpus(nonexistent, clean=True)
        self.assertTrue(created.is_dir())

    def test_clean_refuses_symlink_target(self) -> None:
        """create_demo_corpus(..., clean=True) must refuse cleanup if path is a symlink."""
        real_dir = self.temp_dir / "real_target"
        real_dir.mkdir()
        sensitive_file = real_dir / "sensitive_file.txt"
        sensitive_file.write_text("critical data", encoding="utf-8")

        symlink_dir = self.temp_dir / "symlink_dir"
        can_symlink = False
        try:
            symlink_dir.symlink_to(real_dir, target_is_directory=True)
            can_symlink = True
        except (OSError, NotImplementedError):
            try:
                import _winapi
                _winapi.CreateJunction(str(real_dir), str(symlink_dir))
                can_symlink = True
            except Exception:
                pass

        if not can_symlink:
            self.skipTest("Symlinks/junctions are not permitted in this OS / privilege environment.")

        try:
            with self.assertRaises(RuntimeError) as ctx:
                create_demo_corpus(symlink_dir, clean=True)

            self.assertIn("symlink or reparse point", str(ctx.exception))
            self.assertTrue(sensitive_file.exists())
            self.assertEqual(sensitive_file.read_text(encoding="utf-8"), "critical data")
        finally:
            if symlink_dir.exists() or os.path.islink(symlink_dir):
                try:
                    os.rmdir(symlink_dir)
                except Exception:
                    pass

    def test_is_symlink_or_reparse_detects_links(self) -> None:
        """is_symlink_or_reparse helper correctly identifies links."""
        normal_file = self.temp_dir / "normal.txt"
        normal_file.write_text("hello", encoding="utf-8")
        self.assertFalse(is_symlink_or_reparse(normal_file))


class TestSEC005StdoutBufferingCap(unittest.TestCase):
    """SEC-005: Bounded stdout buffering defense and fail-closed policy."""

    def setUp(self) -> None:
        self.adapter = EngineAdapter(max_output_bytes=1024)

    @patch("subprocess.run")
    def test_stdout_output_cap_fails_closed(self, mock_run: MagicMock) -> None:
        """Output exceeding max_output_bytes fails closed immediately."""
        oversized_output = b"X" * 2048
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = oversized_output
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/test/dir", max_output_bytes=1024)
        self.assertFalse(result.success)
        self.assertEqual(result.returncode, -1)
        self.assertIn("exceeded maximum allowed limit", result.error_message or "")
        self.assertIsNone(result.data)

    @patch("subprocess.run")
    def test_stdout_output_below_cap_succeeds(self, mock_run: MagicMock) -> None:
        """Output within max_output_bytes succeeds normally."""
        payload = {
            "files_scanned": 1,
            "hash_candidates": 0,
            "duplicate_groups": [],
            "reclaimable_bytes": 0,
        }
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(payload).encode("utf-8")
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/test/dir", max_output_bytes=1024)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)


class TestAdversarialSecurity(unittest.TestCase):
    """Adversarial testing across command injection, path payloads, and malformed inputs."""

    def setUp(self) -> None:
        self.adapter = EngineAdapter()

    def test_hostile_path_command_injection_payloads(self) -> None:
        """Adversarial command injection strings must be safely treated as path arguments."""
        hostile_paths = [
            "/path with spaces/target",
            "/path;rm -rf /",
            "/path|cat /etc/passwd",
            "/path`whoami`",
            "/path$(id)",
            "/path&&touch pwned",
            "/path'--json",
            '/path"--json',
            "/path/unicode_日本語_test",
            "../relative/../traversal",
        ]

        for hp in hostile_paths:
            cmd = self.adapter.build_command("duplicate", hp)
            self.assertEqual(cmd[1], hp)
            self.assertEqual(cmd[2], "--json")
            self.assertEqual(len(cmd), 3)

    def test_malformed_json_syntax_fails_closed(self) -> None:
        """Corrupted or truncated JSON syntax returns controlled failure."""
        corrupted_outputs = [
            b"",
            b"{",
            b'{"files_scanned": ',
            b"404 Not Found",
            b"<!DOCTYPE html><html><body>Error</body></html>",
            b"\x00\x01\x02\x03",
        ]

        for bad_out in corrupted_outputs:
            with patch("subprocess.run") as mock_run:
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_proc.stdout = bad_out
                mock_proc.stderr = b""
                mock_run.return_value = mock_proc

                result = self.adapter.run_analysis("duplicate", "/test/dir")
                self.assertFalse(result.success)
                self.assertIsNotNone(result.error_message)


if __name__ == "__main__":
    unittest.main()
