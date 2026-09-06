"""Comprehensive validation tests for the benchmark corpus generator (TASK T004).

Verifies:
1. Seed-based determinism and exact reproducibility.
2. Different seed variance.
3. Manifest schema validation and strict error handling.
4. C1 arithmetic consistency (50K files, ~200 MB, avg 4 KB, 5% duplicates).
5. C3 Developer-Hardware-Only gating and explicit labeling.
6. C7 cache state terminology (warm-state / repeated-run, no cold cache).
7. CI storage budget enforcement (<= 1 GB for all CI profiles).
8. Pre-flight disk space safety check.
9. Reference oracle determinism and digest soundness.
10. Full matrix generation and validation across C1–C7 profiles.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.generator import (
    C1_PROFILE,
    C2_PROFILE,
    C3_PROFILE,
    C4_PROFILE,
    C5_PROFILE,
    C6_PROFILE,
    C7_PROFILE,
    CI_STORAGE_CEILING_BYTES,
    CacheState,
    CorpusProfile,
    DirectoryShape,
    MANIFEST_FILENAME,
    Manifest,
    NAMED_PROFILES,
    SimilarityProfile,
    SizeProfile,
    check_disk_space,
    compute_oracle_result,
    compute_result_digest,
    discover_corpus_files,
    format_deterministic_json,
    generate_corpus,
    validate_manifest,
)


class TestBenchmarkCorpusGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="dupe-test-corpus-")
        self.base = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_seed_reproducibility(self) -> None:
        """Identical seed and profile must produce byte-identical file trees and identical manifests."""
        dir_a = self.base / "repro_a"
        dir_b = self.base / "repro_b"
        seed = 424242

        # Use C2 with small scale for fast execution
        _, manifest_a = generate_corpus(C2_PROFILE, dir_a, seed=seed, scale=0.002)
        _, manifest_b = generate_corpus(C2_PROFILE, dir_b, seed=seed, scale=0.002)

        # 1. Manifests are identical
        self.assertEqual(manifest_a.to_dict(), manifest_b.to_dict())

        # 2. Relative file paths are identical
        files_a = [p.relative_to(dir_a).as_posix() for p in discover_corpus_files(dir_a)]
        files_b = [p.relative_to(dir_b).as_posix() for p in discover_corpus_files(dir_b)]
        self.assertEqual(files_a, files_b)

        # 3. Every file is byte-for-byte identical
        for rel in files_a:
            bytes_a = (dir_a / rel).read_bytes()
            bytes_b = (dir_b / rel).read_bytes()
            self.assertEqual(bytes_a, bytes_b, f"File {rel} differed across identical seeds!")

    def test_different_seed_variance(self) -> None:
        """Different seeds must produce different payloads and different result digests."""
        dir_a = self.base / "seed_1"
        dir_b = self.base / "seed_2"

        _, manifest_a = generate_corpus(C2_PROFILE, dir_a, seed=1001, scale=0.002)
        _, manifest_b = generate_corpus(C2_PROFILE, dir_b, seed=1002, scale=0.002)

        self.assertNotEqual(
            manifest_a.expected_result_digest, manifest_b.expected_result_digest
        )

    def test_manifest_schema_and_validation(self) -> None:
        """Verify strict manifest schema checking."""
        out_dir = self.base / "schema_test"
        _, manifest = generate_corpus(C1_PROFILE, out_dir, seed=999, scale=0.001)

        manifest_file = out_dir / MANIFEST_FILENAME
        self.assertTrue(manifest_file.is_file())

        # Valid manifest passes
        is_valid, errors = validate_manifest(out_dir)
        self.assertTrue(is_valid, f"Validation failed on fresh corpus: {errors}")
        self.assertEqual(errors, [])

        # Corrupt a field and assert validation detects it
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        bad_data = dict(data)
        bad_data["file_count"] = bad_data["file_count"] + 5
        manifest_file.write_text(json.dumps(bad_data), encoding="utf-8")

        is_valid, errors = validate_manifest(out_dir)
        self.assertFalse(is_valid)
        self.assertTrue(any("File count mismatch" in e or "duplicate_ratio" in e for e in errors))

        # Test invalid digest format
        bad_data2 = dict(data)
        bad_data2["expected_result_digest"] = "invalid-not-64-hex"
        manifest_file.write_text(json.dumps(bad_data2), encoding="utf-8")
        is_valid, errors = validate_manifest(out_dir)
        self.assertFalse(is_valid)
        self.assertTrue(any("expected_result_digest" in e for e in errors))

    def test_c1_arithmetic_consistency(self) -> None:
        """Verify C1 arithmetic consistency: 50,000 files, ~200 MB, avg 4 KB, 5% duplicates."""
        c1 = C1_PROFILE
        self.assertEqual(c1.file_count, 50000)
        # Average size is 4,096 bytes (4 KB)
        avg_size = c1.target_bytes / c1.file_count
        self.assertAlmostEqual(avg_size, 4096.0, delta=100)
        # Target size ~200 MB (specifically 204.8 MB)
        self.assertLessEqual(c1.target_bytes, CI_STORAGE_CEILING_BYTES)
        # Duplicate ratio: 5%
        self.assertEqual(c1.duplicate_ratio, 0.05)
        # 50,000 * 0.05 = 2,500 duplicate files
        expected_dup_files = int(c1.file_count * c1.duplicate_ratio)
        self.assertEqual(expected_dup_files, 2500)
        # Size profile is tiny_heavy (<4 KB)
        self.assertEqual(c1.size_profile, SizeProfile.TINY_HEAVY)
        self.assertFalse(c1.developer_hardware_only)

    def test_c3_developer_hardware_only_protection(self) -> None:
        """Verify C3 is Developer-Hardware-Only and protected against accidental CI generation."""
        c3 = C3_PROFILE
        self.assertTrue(c3.developer_hardware_only)
        self.assertGreater(c3.target_bytes, CI_STORAGE_CEILING_BYTES)

        out_dir = self.base / "c3_attempt"
        # Must fail without allow_developer_hardware=True
        with self.assertRaises(PermissionError) as ctx:
            generate_corpus(c3, out_dir, seed=77, scale=0.01, allow_developer_hardware=False)
        self.assertIn("Developer-Hardware-Only", str(ctx.exception))

        # Must succeed with allow_developer_hardware=True
        _, manifest = generate_corpus(c3, out_dir, seed=77, scale=0.05, allow_developer_hardware=True)
        self.assertTrue(manifest.developer_hardware_only)
        self.assertEqual(manifest.corpus_id, "C3")

    def test_c7_cache_state_terminology(self) -> None:
        """Verify C7 uses warm-state / repeated-run terminology, never cold cache."""
        c7 = C7_PROFILE
        self.assertEqual(c7.cache_state, CacheState.WARM_REPEATED)
        self.assertNotIn("cold", c7.cache_state.value.lower())
        self.assertNotIn("cold", c7.description.lower())
        for prof in NAMED_PROFILES.values():
            self.assertNotIn("cold", prof.cache_state.value.lower())

    def test_ci_storage_limits(self) -> None:
        """All standard CI profiles (C1, C2, C4, C5, C6, C7) must not exceed 1 GB."""
        ci_ids = ["C1", "C2", "C4", "C5", "C6", "C7"]
        for cid in ci_ids:
            prof = NAMED_PROFILES[cid]
            self.assertFalse(
                prof.developer_hardware_only, f"{cid} must be marked CI (developer_hardware_only=False)"
            )
            self.assertLessEqual(
                prof.target_bytes,
                CI_STORAGE_CEILING_BYTES,
                f"{cid} exceeds 1 GB CI storage ceiling: {prof.target_bytes} > {CI_STORAGE_CEILING_BYTES}",
            )

    def test_preflight_disk_space_check(self) -> None:
        """Verify check_disk_space fails safely if requested space exceeds available space."""
        # Request an impossibly large number of bytes (e.g. 100 Petabytes)
        impossible_bytes = 100 * 1024 * 1024 * 1024 * 1024 * 1024
        with self.assertRaises(RuntimeError) as ctx:
            check_disk_space(self.base, impossible_bytes)
        self.assertIn("Insufficient disk space", str(ctx.exception))

    def test_oracle_digest_soundness(self) -> None:
        """Verify reference oracle evaluation, soundness byte-identity, and digest determinism."""
        out_dir = self.base / "oracle_soundness"
        _, manifest = generate_corpus(C4_PROFILE, out_dir, seed=123, scale=0.005)

        oracle_out = compute_oracle_result(out_dir)
        # Verify soundness: all files in duplicate groups are byte-identical
        for group in oracle_out["duplicate_groups"]:
            first_path = out_dir / group["files"][0]
            first_bytes = first_path.read_bytes()
            for other_rel in group["files"][1:]:
                other_bytes = (out_dir / other_rel).read_bytes()
                self.assertEqual(first_bytes, other_bytes, f"Group file {other_rel} differed from first file!")

        # Verify digest
        expected_digest = compute_result_digest(oracle_out)
        self.assertEqual(manifest.expected_result_digest, expected_digest)

    def test_full_c1_c7_miniature_matrix(self) -> None:
        """Generate and validate miniature versions of all 7 named profiles."""
        for cid, prof in NAMED_PROFILES.items():
            corpus_dir = self.base / f"mini_{cid}"
            allow_dev = prof.developer_hardware_only
            # Small scale (0.001 - 0.05) to test all generator logic rapidly
            scale = 0.05 if cid == "C3" else 0.002
            _, manifest = generate_corpus(
                profile=prof,
                out_dir=corpus_dir,
                seed=2026,
                scale=scale,
                allow_developer_hardware=allow_dev,
            )
            is_valid, errors = validate_manifest(corpus_dir)
            self.assertTrue(
                is_valid, f"Miniature corpus {cid} failed validation: {errors}"
            )
            self.assertEqual(manifest.corpus_id, cid)
            self.assertEqual(manifest.size_profile, prof.size_profile.value)
            self.assertEqual(manifest.directory_shape, prof.directory_shape.value)


if __name__ == "__main__":
    unittest.main()
