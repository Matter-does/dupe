"""Focused acceptance, unit, view-model, and integration tests for T009 GUI Shell."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from gui.adapter import EngineAdapter, EngineResult
from gui.view_models import (
    ChecksumViewModel,
    DuplicateViewModel,
    format_bytes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# Probe J2 interpreter availability
J2_BIN = os.environ.get("J2_BIN") or shutil.which("j2") or (str(Path.home() / ".j2" / "bin" / "j2"))
HAS_J2 = False
if J2_BIN and shutil.which(J2_BIN):
    try:
        p = subprocess.run([J2_BIN, "--version"], capture_output=True, timeout=5)
        if p.returncode == 0:
            HAS_J2 = True
    except Exception:
        HAS_J2 = False


# Probe Tkinter graphical display capability
HAS_TK_DISPLAY = False
try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.destroy()
    HAS_TK_DISPLAY = True
except Exception:
    HAS_TK_DISPLAY = False


class TestT009EngineAdapter(unittest.TestCase):
    """Unit tests for the GUI engine adapter."""

    def setUp(self) -> None:
        self.adapter = EngineAdapter()

    def test_command_construction_duplicate(self) -> None:
        cmd = self.adapter.build_command("duplicate", "/target/directory")
        self.assertIn("/target/directory", cmd)
        self.assertIn("--json", cmd)
        self.assertNotIn("checksum", cmd)

    def test_command_construction_checksum(self) -> None:
        cmd = self.adapter.build_command("checksum", "/target/directory")
        self.assertIn("checksum", cmd)
        self.assertIn("/target/directory", cmd)
        self.assertIn("--json", cmd)

    def test_command_construction_unknown_workload(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.build_command("unsupported", "/target/directory")

    def test_run_analysis_empty_path(self) -> None:
        result = self.adapter.run_analysis("duplicate", "")
        self.assertFalse(result.success)
        self.assertEqual(result.returncode, 1)
        self.assertIn("No target directory specified", result.error_message or "")

    @patch("subprocess.run")
    def test_run_analysis_success_duplicate(self, mock_run: MagicMock) -> None:
        payload = {
            "files_scanned": 10,
            "hash_candidates": 4,
            "duplicate_groups": [
                {
                    "hash": "abc123hash",
                    "size": 1024,
                    "files": ["/a/f1.txt", "/a/f2.txt"],
                    "reclaimable_bytes": 1024,
                }
            ],
            "reclaimable_bytes": 1024,
        }
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(payload).encode("utf-8")
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/valid/dir")
        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.data["files_scanned"], 10)
        self.assertEqual(len(result.data["duplicate_groups"]), 1)
        self.assertIsNone(result.error_message)

    @patch("subprocess.run")
    def test_run_analysis_success_checksum(self, mock_run: MagicMock) -> None:
        payload = {
            "schema_version": 1,
            "workload": "checksum_inventory",
            "root": "/valid/dir",
            "summary": {"total_files": 2, "total_bytes": 2048},
            "entries": [
                {"path": "/valid/dir/a.txt", "size": 1024, "sha256": "1111"},
                {"path": "/valid/dir/b.txt", "size": 1024, "sha256": "2222"},
            ],
        }
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(payload).encode("utf-8")
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("checksum", "/valid/dir")
        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.data["summary"]["total_files"], 2)
        self.assertEqual(len(result.data["entries"]), 2)

    @patch("subprocess.run")
    def test_run_analysis_non_zero_exit(self, mock_run: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 2
        mock_proc.stdout = b""
        mock_proc.stderr = b"RuntimeError: fs.list_dir failed: directory does not exist"
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/nonexistent")
        self.assertFalse(result.success)
        self.assertEqual(result.returncode, 2)
        self.assertIn("fs.list_dir failed", result.error_message or "")
        self.assertIn("fs.list_dir failed", result.raw_stderr)

    @patch("subprocess.run")
    def test_run_analysis_malformed_json(self, mock_run: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"Not valid json string output"
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/bad/json")
        self.assertFalse(result.success)
        self.assertIn("malformed JSON", result.error_message or "")

    @patch("subprocess.run")
    def test_run_analysis_invalid_schema(self, mock_run: MagicMock) -> None:
        # Missing 'duplicate_groups'
        bad_payload = {"files_scanned": 5, "reclaimable_bytes": 0}
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(bad_payload).encode("utf-8")
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        result = self.adapter.run_analysis("duplicate", "/schema/err")
        self.assertFalse(result.success)
        self.assertIn("Invalid schema", result.error_message or "")

    @patch("subprocess.run")
    def test_run_analysis_async(self, mock_run: MagicMock) -> None:
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

        received: list[EngineResult] = []
        done_event = threading.Event()

        def callback(res: EngineResult) -> None:
            received.append(res)
            done_event.set()

        thread = self.adapter.run_analysis_async("duplicate", "/test/async", callback)
        self.assertTrue(thread.is_alive() or done_event.is_set())
        self.assertTrue(done_event.wait(timeout=5))
        self.assertEqual(len(received), 1)
        self.assertTrue(received[0].success)


class TestT009ViewModels(unittest.TestCase):
    """Unit tests for GUI view models and formatters."""

    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.00 KB (1,024 bytes)")
        self.assertEqual(format_bytes(1572864), "1.50 MB (1,572,864 bytes)")
        self.assertEqual(format_bytes(2147483648), "2.00 GB (2,147,483,648 bytes)")

    def test_duplicate_view_model(self) -> None:
        data = {
            "files_scanned": 8,
            "hash_candidates": 4,
            "duplicate_groups": [
                {
                    "hash": "hash123",
                    "size": 5000,
                    "files": ["/data/a.txt", "/data/b.txt", "/data/c.txt"],
                    "reclaimable_bytes": 10000,
                }
            ],
            "reclaimable_bytes": 10000,
        }
        vm = DuplicateViewModel.from_engine_data(data)
        self.assertEqual(vm.files_scanned, 8)
        self.assertEqual(vm.hash_candidates, 4)
        self.assertEqual(vm.duplicate_groups_count, 1)
        self.assertEqual(vm.reclaimable_bytes, 10000)
        self.assertIn("KB", vm.reclaimable_formatted)
        self.assertEqual(len(vm.groups), 1)

        group = vm.groups[0]
        self.assertEqual(group.group_index, 1)
        self.assertEqual(group.digest, "hash123")
        self.assertEqual(group.size, 5000)
        self.assertEqual(group.file_count, 3)
        self.assertEqual(len(group.files), 3)

    def test_checksum_view_model(self) -> None:
        data = {
            "schema_version": 1,
            "workload": "checksum_inventory",
            "root": "/my/root",
            "summary": {"total_files": 2, "total_bytes": 2048},
            "entries": [
                {"path": "/my/root/1.bin", "size": 1024, "sha256": "aaaa"},
                {"path": "/my/root/2.bin", "size": 1024, "sha256": "bbbb"},
            ],
        }
        vm = ChecksumViewModel.from_engine_data(data)
        self.assertEqual(vm.root, "/my/root")
        self.assertEqual(vm.total_files, 2)
        self.assertEqual(vm.total_bytes, 2048)
        self.assertIn("2.00 KB", vm.total_bytes_formatted)
        self.assertEqual(len(vm.entries), 2)
        self.assertEqual(vm.entries[0].index, 1)
        self.assertEqual(vm.entries[0].sha256, "aaaa")


@unittest.skipUnless(HAS_TK_DISPLAY, "GUI_TESTS_SKIPPED: Tkinter display is unavailable in this environment.")
class TestT009GUIComponents(unittest.TestCase):
    """Headless tests for DupeApp widget state and interactions."""

    def setUp(self) -> None:
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()  # keep offscreen
        self.mock_adapter = MagicMock(spec=EngineAdapter)
        from gui.app import DupeApp
        self.app = DupeApp(root=self.root, adapter=self.mock_adapter)

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_initial_state(self) -> None:
        self.assertEqual(self.app.path_var.get(), "")
        self.assertEqual(self.app.workload_var.get(), "duplicate")
        self.assertIn("Ready", self.app.status_var.get())
        self.assertFalse(self.app.is_running)

    def test_set_target_path(self) -> None:
        self.app.set_target_path("/test/path")
        self.assertIn("test", self.app.path_var.get())
        self.assertIn("Target selected", self.app.status_var.get())

    def test_set_workload(self) -> None:
        self.app.set_workload("checksum")
        self.assertEqual(self.app.workload_var.get(), "checksum")
        self.assertEqual(self.app.metric_1_title.get(), "Total Regular Files")

        self.app.set_workload("duplicate")
        self.assertEqual(self.app.workload_var.get(), "duplicate")
        self.assertEqual(self.app.metric_1_title.get(), "Files Scanned")

    def test_apply_duplicate_results(self) -> None:
        data = {
            "files_scanned": 12,
            "hash_candidates": 6,
            "duplicate_groups": [
                {
                    "hash": "hash_sample_1",
                    "size": 4096,
                    "files": ["/p/f1.txt", "/p/f2.txt"],
                    "reclaimable_bytes": 4096,
                }
            ],
            "reclaimable_bytes": 4096,
        }
        res = EngineResult(
            success=True,
            workload="duplicate",
            target_path="/test",
            returncode=0,
            data=data,
            raw_stdout="{}",
            raw_stderr="",
            error_message=None,
            duration_seconds=0.42,
            command_executed=["dupe", "/test", "--json"],
        )
        self.app._apply_engine_result(res)

        self.assertEqual(self.app.metric_1_val.get(), "12")
        self.assertEqual(self.app.metric_2_val.get(), "6")
        self.assertEqual(self.app.metric_3_val.get(), "1")
        self.assertIn("KB", self.app.metric_4_val.get())
        self.assertIn("complete in 0.42s", self.app.status_var.get())
        self.assertEqual(len(self.app.tree.get_children()), 1)

    def test_apply_checksum_results(self) -> None:
        data = {
            "schema_version": 1,
            "workload": "checksum_inventory",
            "root": "/test",
            "summary": {"total_files": 3, "total_bytes": 6144},
            "entries": [
                {"path": "/test/1.txt", "size": 2048, "sha256": "h1"},
                {"path": "/test/2.txt", "size": 2048, "sha256": "h2"},
                {"path": "/test/3.txt", "size": 2048, "sha256": "h3"},
            ],
        }
        res = EngineResult(
            success=True,
            workload="checksum",
            target_path="/test",
            returncode=0,
            data=data,
            raw_stdout="{}",
            raw_stderr="",
            error_message=None,
            duration_seconds=0.15,
            command_executed=["dupe", "checksum", "/test", "--json"],
        )
        self.app._apply_engine_result(res)

        self.assertEqual(self.app.metric_1_val.get(), "3")
        self.assertIn("6.00 KB", self.app.metric_2_val.get())
        self.assertEqual(self.app.metric_3_val.get(), "3")
        self.assertIn("complete in 0.15s", self.app.status_var.get())
        self.assertEqual(len(self.app.tree.get_children()), 3)

    def test_apply_error_result(self) -> None:
        res = EngineResult(
            success=False,
            workload="duplicate",
            target_path="/invalid",
            returncode=1,
            data=None,
            raw_stdout="",
            raw_stderr="RuntimeError: fs.list_dir failed",
            error_message="RuntimeError: fs.list_dir failed",
            duration_seconds=0.05,
            command_executed=["dupe", "/invalid", "--json"],
        )
        self.app._apply_engine_result(res)

        self.assertIn("failed", self.app.status_var.get())
        self.assertIn("RuntimeError", self.app.error_lbl.cget("text"))
        self.assertEqual(self.app.metric_1_val.get(), "—")
        self.assertEqual(len(self.app.tree.get_children()), 0)


class TestT009LiveJ2Integration(unittest.TestCase):
    """Real J2 engine execution via GUI EngineAdapter."""

    @classmethod
    def setUpClass(cls) -> None:
        if not HAS_J2:
            print(f"\n[LIVE_J2_STATUS] LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN or 'j2'}' unavailable.")
        else:
            print(f"\n[LIVE_J2_STATUS] J2 binary found at: {J2_BIN}. Running T009 live integration tests.")

    def setUp(self) -> None:
        if not HAS_J2:
            self.skipTest(f"LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN or 'j2'}' is unavailable in environment.")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t009_gui_test_"))
        self.adapter = EngineAdapter(j2_bin=J2_BIN)

    def tearDown(self) -> None:
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_live_duplicate_scan_via_adapter(self) -> None:
        # Create small test corpus with 2 duplicates and 1 unique
        payload = b"shared duplicate test payload in t009"
        (self.temp_dir / "dup1.txt").write_bytes(payload)
        (self.temp_dir / "dup2.txt").write_bytes(payload)
        (self.temp_dir / "unique.txt").write_bytes(b"unique content")

        result = self.adapter.run_analysis("duplicate", self.temp_dir.as_posix())
        self.assertTrue(result.success, f"Duplicate analysis failed: {result.error_message}")
        self.assertEqual(result.returncode, 0)
        self.assertIsNotNone(result.data)

        vm = DuplicateViewModel.from_engine_data(result.data)
        self.assertEqual(vm.files_scanned, 3)
        self.assertEqual(vm.hash_candidates, 2)
        self.assertEqual(vm.duplicate_groups_count, 1)
        self.assertEqual(vm.reclaimable_bytes, len(payload))
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_checksum_inventory_via_adapter(self) -> None:
        (self.temp_dir / "c1.bin").write_bytes(b"test1")
        (self.temp_dir / "c2.bin").write_bytes(b"test2")

        result = self.adapter.run_analysis("checksum", self.temp_dir.as_posix())
        self.assertTrue(result.success, f"Checksum analysis failed: {result.error_message}")
        self.assertEqual(result.returncode, 0)
        self.assertIsNotNone(result.data)

        vm = ChecksumViewModel.from_engine_data(result.data)
        self.assertEqual(vm.total_files, 2)
        self.assertEqual(vm.total_bytes, 10)
        self.assertEqual(len(vm.entries), 2)
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")

    def test_live_nonexistent_path_failure_via_adapter(self) -> None:
        nonexistent = self.temp_dir / "does_not_exist_abc123"
        result = self.adapter.run_analysis("duplicate", nonexistent.as_posix())
        self.assertFalse(result.success)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(result.error_message)
        print(f"\nLIVE_J2_TESTS_PASS: {self._testMethodName}")


if __name__ == "__main__":
    unittest.main()
