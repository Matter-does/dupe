"""Unit, view-model, and integration tests for T010 demonstration package."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from gui.adapter import EngineAdapter, EngineResult
from gui.view_models import (
    ChecksumViewModel,
    DuplicateViewModel,
    format_bytes,
)
from tests.demo_corpus import (
    DEMO_CORPUS_SPEC,
    EXPECTED_CANDIDATES_COUNT,
    EXPECTED_FILES_COUNT,
    EXPECTED_GROUPS_COUNT,
    EXPECTED_RECLAIMABLE_BYTES,
    EXPECTED_TOTAL_BYTES,
    create_demo_corpus,
    verify_demo_corpus,
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


class TestT010DemoCorpus(unittest.TestCase):
    """Tests for deterministic demo corpus generation and ground truth assertions."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t010_corpus_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_demo_corpus_generation(self) -> None:
        corpus = self.temp_dir / "demo"
        create_demo_corpus(corpus)
        info = verify_demo_corpus(corpus)

        self.assertEqual(info["files_count"], EXPECTED_FILES_COUNT)
        self.assertEqual(info["total_bytes"], EXPECTED_TOTAL_BYTES)
        self.assertTrue((corpus / "empty_dir").is_dir())

        # Verify candidate sizes
        sizes = [len(payload) for _, payload in DEMO_CORPUS_SPEC]
        # Counts: 100: 3, 256: 2, 4096: 1, 350: 1, 0: 1
        self.assertEqual(sizes.count(100), 3)
        self.assertEqual(sizes.count(256), 2)
        self.assertEqual(sizes.count(4096), 1)
        self.assertEqual(sizes.count(350), 1)
        self.assertEqual(sizes.count(0), 1)

    def test_demo_corpus_determinism_and_idempotence(self) -> None:
        corpus_1 = self.temp_dir / "demo_1"
        corpus_2 = self.temp_dir / "demo_2"
        create_demo_corpus(corpus_1)
        create_demo_corpus(corpus_2)

        info_1 = verify_demo_corpus(corpus_1)
        info_2 = verify_demo_corpus(corpus_2)

        self.assertEqual(info_1["files"], info_2["files"])
        for (r1, s1, h1), (r2, s2, h2) in zip(info_1["files"], info_2["files"]):
            self.assertEqual(r1, r2)
            self.assertEqual(s1, s2)
            self.assertEqual(h1, h2)

    def test_verify_demo_corpus_detects_tamper(self) -> None:
        corpus = self.temp_dir / "demo_tampered"
        create_demo_corpus(corpus)

        # Tamper with a file
        target_file = corpus / "documents" / "report_draft.txt"
        target_file.write_bytes(b"tampered content")

        with self.assertRaises(AssertionError):
            verify_demo_corpus(corpus)


class TestT010DemoViewModels(unittest.TestCase):
    """Tests for ViewModels parsing expected demonstration ground truth payloads."""

    def test_duplicate_demo_view_model(self) -> None:
        demo_payload = {
            "files_scanned": EXPECTED_FILES_COUNT,
            "hash_candidates": EXPECTED_CANDIDATES_COUNT,
            "duplicate_groups": [
                {
                    "hash": "100_byte_hash",
                    "size": 100,
                    "files": [
                        "/corpus/documents/report_draft.txt",
                        "/corpus/documents/report_final.txt",
                        "/corpus/archive/old_backup/report_backup.txt",
                    ],
                    "reclaimable_bytes": 200,
                },
                {
                    "hash": "256_byte_hash",
                    "size": 256,
                    "files": [
                        "/corpus/images/banner.raw",
                        "/corpus/images/banner_copy.raw",
                    ],
                    "reclaimable_bytes": 256,
                },
            ],
            "reclaimable_bytes": EXPECTED_RECLAIMABLE_BYTES,
        }

        vm = DuplicateViewModel.from_engine_data(demo_payload)
        self.assertEqual(vm.files_scanned, 8)
        self.assertEqual(vm.hash_candidates, 5)
        self.assertEqual(vm.duplicate_groups_count, 2)
        self.assertEqual(vm.reclaimable_bytes, 456)
        self.assertEqual(vm.reclaimable_formatted, "456 B")
        self.assertEqual(len(vm.groups), 2)
        self.assertEqual(vm.groups[0].file_count, 3)
        self.assertEqual(vm.groups[0].reclaimable_bytes, 200)
        self.assertEqual(vm.groups[1].file_count, 2)
        self.assertEqual(vm.groups[1].reclaimable_bytes, 256)

    def test_checksum_demo_view_model(self) -> None:
        demo_payload = {
            "schema_version": 1,
            "workload": "checksum_inventory",
            "root": "/corpus",
            "summary": {
                "total_files": EXPECTED_FILES_COUNT,
                "total_bytes": EXPECTED_TOTAL_BYTES,
            },
            "entries": [
                {"path": f"/corpus/file_{i}.dat", "size": 657, "sha256": f"hash_{i}"}
                for i in range(8)
            ],
        }

        vm = ChecksumViewModel.from_engine_data(demo_payload)
        self.assertEqual(vm.total_files, 8)
        self.assertEqual(vm.total_bytes, 5258)
        self.assertIn("5.13 KB", vm.total_bytes_formatted)
        self.assertEqual(len(vm.entries), 8)


@unittest.skipUnless(HAS_TK_DISPLAY, "GUI_TESTS_SKIPPED: Tkinter display unavailable in this environment.")
class TestT010GUIIntegration(unittest.TestCase):
    """Tests for GUI demonstration polish and interactive demo corpus loading."""

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

    def test_engine_mode_and_badge(self) -> None:
        self.assertTrue(hasattr(self.app, "engine_mode"))
        self.assertTrue(hasattr(self.app, "engine_badge"))
        badge_text = self.app.engine_badge.cget("text")
        self.assertIn("Engine:", badge_text)

    def test_workload_description_updating(self) -> None:
        self.app.set_workload("duplicate")
        desc_dup = self.app.workload_desc_var.get()
        self.assertIn("Exact Duplicate Scan", desc_dup)

        self.app.set_workload("checksum")
        desc_chk = self.app.workload_desc_var.get()
        self.assertIn("Checksum Inventory", desc_chk)

    def test_on_load_demo_corpus(self) -> None:
        self.app.on_load_demo_corpus()
        target = self.app.path_var.get()
        self.assertIn("demo_corpus", target)
        self.assertIn("Demo corpus loaded", self.app.status_var.get())


class TestT010LiveJ2Demo(unittest.TestCase):
    """Live J2 execution tests on demo corpus."""

    def setUp(self) -> None:
        if not HAS_J2:
            self.skipTest(f"LIVE_J2_TESTS_SKIPPED: J2 binary '{J2_BIN}' is unavailable in environment.")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="t010_live_demo_"))
        self.corpus = self.temp_dir / "demo_corpus"
        create_demo_corpus(self.corpus)

    def tearDown(self) -> None:
        if hasattr(self, "temp_dir"):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_live_duplicate_demo(self) -> None:
        env = os.environ.copy()
        env["J2_ALLOW_FS"] = "1"
        proc = subprocess.run(
            [J2_BIN, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), str(self.corpus), "--json"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, f"Live duplicate demo failed: {proc.stderr}")
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data["files_scanned"], EXPECTED_FILES_COUNT)
        self.assertEqual(data["hash_candidates"], EXPECTED_CANDIDATES_COUNT)
        self.assertEqual(len(data["duplicate_groups"]), EXPECTED_GROUPS_COUNT)
        self.assertEqual(data["reclaimable_bytes"], EXPECTED_RECLAIMABLE_BYTES)

    def test_live_checksum_demo(self) -> None:
        env = os.environ.copy()
        env["J2_ALLOW_FS"] = "1"
        proc = subprocess.run(
            [J2_BIN, "--allow-fs", str(REPO_ROOT / "src" / "main.j2"), "checksum", str(self.corpus), "--json"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, f"Live checksum demo failed: {proc.stderr}")
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data["summary"]["total_files"], EXPECTED_FILES_COUNT)
        self.assertEqual(data["summary"]["total_bytes"], EXPECTED_TOTAL_BYTES)
        self.assertEqual(len(data["entries"]), EXPECTED_FILES_COUNT)


if __name__ == "__main__":
    unittest.main()
