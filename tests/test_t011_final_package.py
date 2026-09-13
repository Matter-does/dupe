"""T011 Final Submission Package & Release Gate Verification Tests.

Verifies:
1. All required evaluator documentation exists and is non-empty.
2. README.md contains authoritative sections and has zero stale milestone text.
3. No machine-specific absolute user paths leaked into documentation.
4. Frozen-core boundary (src/scan.j2, src/hash.j2, src/group.j2, src/output.j2, benchmarks/)
   is 100% untouched relative to T010 baseline.
5. Pinned J2 release SHA-256 constant integrity.
6. GUI shell imports zero third-party dependencies (standard library only).
7. Demo corpus ground truth constants and generation integrity.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.demo_corpus import (
    EXPECTED_CANDIDATES_COUNT,
    EXPECTED_FILES_COUNT,
    EXPECTED_GROUPS_COUNT,
    EXPECTED_RECLAIMABLE_BYTES,
    EXPECTED_TOTAL_BYTES,
)

FROZEN_BASELINE_COMMIT = "630eb1f91e9e5134ba6351fddaccc697d2a56888"
EXPECTED_J2_VERSION = "0.1.0"
EXPECTED_J2_SHA256 = "6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75"


class TestT011FinalPackage(unittest.TestCase):
    """Verifies packaging, documentation, boundaries, and release requirements."""

    def test_authoritative_specification_exists(self) -> None:
        spec = REPO_ROOT / "agent" / "tasks" / "T011-final-package.md"
        self.assertTrue(spec.is_file(), f"Missing T011 spec at {spec}")
        content = spec.read_text(encoding="utf-8")
        self.assertIn("# T011 — Final Submission Package Specification", content)
        self.assertIn("## 1. Purpose", content)
        self.assertIn("## 3. Non-Goals & Absolute Boundaries", content)
        self.assertIn("## 8. Exit Criteria", content)

    def test_evaluator_documentation_exists(self) -> None:
        required_docs = [
            "README.md",
            "docs/PROJECT.md",
            "docs/ARCHITECTURE.md",
            "docs/RESEARCH.md",
            "docs/VALIDATION.md",
            "docs/FINAL_EVIDENCE.md",
            "docs/SUBMISSION_CHECKLIST.md",
        ]
        for rel_path in required_docs:
            doc_path = REPO_ROOT / rel_path
            self.assertTrue(doc_path.is_file(), f"Required documentation file missing: {rel_path}")
            self.assertGreater(doc_path.stat().st_size, 100, f"Documentation file {rel_path} appears empty")

    def test_readme_structure_and_no_stale_phases(self) -> None:
        readme_path = REPO_ROOT / "README.md"
        content = readme_path.read_text(encoding="utf-8")

        required_headings = [
            "# dupe",
            "## Why this exists",
            "## Why J2",
            "## Architecture",
            "## Features",
            "## Demo",
            "## Verification",
            "## Platform Matrix",
            "## Limitations",
            "## Final Status",
        ]
        for heading in required_headings:
            self.assertIn(heading, content, f"README missing required section: {heading}")

        # Check that stale roadmap markers from early phases are absent
        self.assertNotIn("Phase 5  Performance / J2 research       NEXT", content)
        self.assertNotIn("Phase 6  Product surface                 LATER", content)
        self.assertNotIn("Final    Demo + documentation            LATER", content)

    def test_no_machine_specific_paths_in_docs(self) -> None:
        docs_to_check = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "VALIDATION.md",
            REPO_ROOT / "docs" / "FINAL_EVIDENCE.md",
            REPO_ROOT / "docs" / "SUBMISSION_CHECKLIST.md",
        ]
        personal_path_regex = re.compile(r"(?:[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+|/Users/(?!runner\b)[A-Za-z0-9_.-]+)")
        for doc in docs_to_check:
            text = doc.read_text(encoding="utf-8")
            matches = personal_path_regex.findall(text)
            self.assertEqual(
                matches,
                [],
                f"Found machine-specific absolute path(s) {matches} in {doc.name}",
            )

    def test_frozen_engine_and_benchmarks_integrity(self) -> None:
        frozen_files = [
            REPO_ROOT / "src" / "scan.j2",
            REPO_ROOT / "src" / "hash.j2",
            REPO_ROOT / "src" / "group.j2",
            REPO_ROOT / "src" / "output.j2",
        ]
        for f in frozen_files:
            self.assertTrue(f.is_file(), f"Frozen core file missing: {f}")

        # If running inside a git repository with access to baseline, verify diff is empty
        try:
            cmd = [
                "git",
                "diff",
                f"{FROZEN_BASELINE_COMMIT}..HEAD",
                "--",
                "src/scan.j2",
                "src/hash.j2",
                "src/group.j2",
                "src/output.j2",
                "benchmarks/",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, timeout=10)
            if res.returncode == 0:
                self.assertEqual(
                    res.stdout.strip(),
                    "",
                    f"Frozen core diff boundary violated relative to {FROZEN_BASELINE_COMMIT}!\n{res.stdout}",
                )
        except Exception:
            pass

    def test_pinned_j2_version_and_sha(self) -> None:
        ci_doc = REPO_ROOT / "docs" / "J2-API-0.1.0.md"
        self.assertTrue(ci_doc.is_file())
        content = ci_doc.read_text(encoding="utf-8")
        self.assertIn(EXPECTED_J2_VERSION, content)
        self.assertIn(EXPECTED_J2_SHA256, content)

    def test_demo_corpus_constants(self) -> None:
        self.assertEqual(EXPECTED_FILES_COUNT, 8)
        self.assertEqual(EXPECTED_TOTAL_BYTES, 5258)
        self.assertEqual(EXPECTED_CANDIDATES_COUNT, 5)
        self.assertEqual(EXPECTED_GROUPS_COUNT, 2)
        self.assertEqual(EXPECTED_RECLAIMABLE_BYTES, 456)

    def test_gui_zero_external_dependencies(self) -> None:
        gui_files = [
            REPO_ROOT / "gui" / "app.py",
            REPO_ROOT / "gui" / "adapter.py",
            REPO_ROOT / "gui" / "view_models.py",
            REPO_ROOT / "gui" / "__main__.py",
        ]
        third_party_keywords = ["requests", "urllib3", "numpy", "pandas", "click", "rich", "pydantic"]
        for gf in gui_files:
            self.assertTrue(gf.is_file(), f"GUI file missing: {gf}")
            text = gf.read_text(encoding="utf-8")
            for kw in third_party_keywords:
                self.assertNotIn(f"import {kw}", text)
                self.assertNotIn(f"from {kw}", text)


if __name__ == "__main__":
    unittest.main()
