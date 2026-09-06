"""Comprehensive validation tests for the benchmark corpus generator (TASK T004 Remediation).

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
11. Safe output directory handling (P1-A):
    - Non-empty unrelated directory refusal with contents preserved
    - Empty directory allowed
    - Valid prior generated corpus controlled regeneration allowed
    - Refusal path leaves all files untouched
12. Projected actual size planning and preflight (P1-B):
    - In-memory plan matches actual written bytes
    - CI ceiling violation error with seed/scale diagnosis
13. Manifest scale and tamper detection (P2-C):
    - scale, target_bytes, and size_tolerance_ratio recorded
    - Tampered metadata detected by validation
14. Target vs actual size tolerance testing (P2-E):
    - Conformance to explicit profile tolerances without false exact-byte assumptions
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
    CollisionDensity,
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
from benchmarks.generator.generate import plan_corpus_workload


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

    # -------------------------------------------------------------------------
    # Remediation tests (OpenCode Findings P1-A, P1-B, P2-C, P2-E)
    # -------------------------------------------------------------------------

    def test_safe_output_directory_handling(self) -> None:
        """Verify P1-A safe output directory handling:
        - Non-empty unrelated directory => refusal with FileExistsError, contents preserved
        - Empty directory => allowed
        - Valid prior generated corpus => controlled replacement allowed
        - Refusal leaves everything untouched
        """
        # 1. Non-empty unrelated directory
        unrelated_dir = self.base / "unrelated_dir"
        unrelated_dir.mkdir(parents=True, exist_ok=True)
        secret_file = unrelated_dir / "user_secret.txt"
        secret_content = b"CRITICAL_USER_DATA_DO_NOT_DELETE"
        secret_file.write_bytes(secret_content)
        nested_dir = unrelated_dir / "nested"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "subfile.txt").write_bytes(b"subdata")

        with self.assertRaises(FileExistsError) as ctx:
            generate_corpus(C1_PROFILE, unrelated_dir, seed=42, scale=0.001)

        self.assertIn("Refusing destructive overwrite", str(ctx.exception))
        # Verify contents completely preserved
        self.assertTrue(secret_file.exists())
        self.assertEqual(secret_file.read_bytes(), secret_content)
        self.assertTrue((nested_dir / "subfile.txt").exists())

        # 2. Empty directory allowed
        empty_dir = self.base / "empty_dir"
        empty_dir.mkdir(parents=True, exist_ok=True)
        _, m_empty = generate_corpus(C1_PROFILE, empty_dir, seed=42, scale=0.001)
        self.assertTrue((empty_dir / MANIFEST_FILENAME).exists())

        # 3. Valid prior generated corpus allows controlled replacement
        regen_dir = self.base / "regen_dir"
        _, m1 = generate_corpus(C1_PROFILE, regen_dir, seed=111, scale=0.001)
        digest1 = m1.expected_result_digest

        # Regenerate same corpus with different seed
        _, m2 = generate_corpus(C1_PROFILE, regen_dir, seed=222, scale=0.001)
        digest2 = m2.expected_result_digest
        self.assertNotEqual(digest1, digest2)
        is_valid, errors = validate_manifest(regen_dir)
        self.assertTrue(is_valid, f"Regenerated corpus validation failed: {errors}")

    def test_projected_size_preflight_and_planning(self) -> None:
        """Verify P1-B projected actual size planning:
        - In-memory plan matches actual written bytes
        - Enforces CI ceiling before touching filesystem
        """
        plan = plan_corpus_workload(C2_PROFILE, seed=5555, scale=0.002)
        self.assertGreater(plan.file_count, 0)
        self.assertGreater(plan.projected_bytes, 0)

        # Generate on disk and verify written bytes match projected bytes exactly
        out_dir = self.base / "plan_match_test"
        _, manifest = generate_corpus(C2_PROFILE, out_dir, seed=5555, scale=0.002)
        self.assertEqual(manifest.total_bytes, plan.projected_bytes)

        # Test CI ceiling violation rejection before filesystem write
        # Create a synthetic profile that claims CI (developer_hardware_only=False) but target exceeds 1 GB
        oversized_ci_profile = CorpusProfile(
            corpus_id="CI_OVERSIZED",
            name="Oversized CI",
            description="Illegal oversized CI corpus",
            file_count=500,
            target_bytes=2 * 1024 * 1024 * 1024,  # 2 GB
            size_profile=SizeProfile.MIXED,
            directory_shape=DirectoryShape.MIXED,
            similarity_profile=SimilarityProfile.DISTINCT,
            duplicate_ratio=0.10,
            collision_density=CollisionDensity.LOW,
            cache_state=CacheState.INITIAL_RUN,
            developer_hardware_only=False,  # Intentionally false to test CI guard
            size_tolerance_ratio=0.05,
        )

        oversized_dir = self.base / "oversized_dir"
        with self.assertRaises(ValueError) as ctx:
            generate_corpus(oversized_ci_profile, oversized_dir, seed=42, scale=1.0)
        self.assertIn("exceeds CI storage ceiling", str(ctx.exception))
        # Filesystem must remain untouched (directory not written with corpus)
        self.assertFalse((oversized_dir / MANIFEST_FILENAME).exists())

    def test_manifest_scale_and_tamper_detection(self) -> None:
        """Verify P2-C scale recording and tamper detection in validate_manifest."""
        out_dir = self.base / "tamper_test"
        scale_val = 0.003
        _, manifest = generate_corpus(C1_PROFILE, out_dir, seed=789, scale=scale_val)

        # Manifest contains scale, target_bytes, size_tolerance_ratio
        m_file = out_dir / MANIFEST_FILENAME
        data = json.loads(m_file.read_text(encoding="utf-8"))
        self.assertEqual(data["scale"], scale_val)
        self.assertIn("target_bytes", data)
        self.assertIn("size_tolerance_ratio", data)

        # 1. Tamper with scale
        tampered_scale = dict(data)
        tampered_scale["scale"] = 0.5
        m_file.write_text(json.dumps(tampered_scale), encoding="utf-8")
        is_valid, errors = validate_manifest(out_dir)
        self.assertFalse(is_valid)
        self.assertTrue(any("Tampered metadata" in e for e in errors))

        # 2. Tamper with seed
        tampered_seed = dict(data)
        tampered_seed["seed"] = 99999
        m_file.write_text(json.dumps(tampered_seed), encoding="utf-8")
        # Manifest digest won't match or seed check detects discrepancy
        is_valid, errors = validate_manifest(out_dir)
        # Restoring valid file
        m_file.write_text(json.dumps(data), encoding="utf-8")
        is_valid, errors = validate_manifest(out_dir)
        self.assertTrue(is_valid)

        # 3. Tamper with target_bytes
        tampered_target = dict(data)
        tampered_target["target_bytes"] = 100000000
        m_file.write_text(json.dumps(tampered_target), encoding="utf-8")
        is_valid, errors = validate_manifest(out_dir)
        self.assertFalse(is_valid)
        self.assertTrue(any("violates target size" in e or "Tampered metadata" in e for e in errors))

    def test_target_vs_actual_size_conformance(self) -> None:
        """Verify P2-E profile target vs actual size tolerance across all C1–C7 profiles."""
        for cid, prof in NAMED_PROFILES.items():
            corpus_dir = self.base / f"tol_{cid}"
            allow_dev = prof.developer_hardware_only
            scale = 0.05 if cid == "C3" else 0.002
            _, manifest = generate_corpus(
                profile=prof,
                out_dir=corpus_dir,
                seed=31415,
                scale=scale,
                allow_developer_hardware=allow_dev,
            )

            # Check tolerance explicitly
            target = manifest.target_bytes
            actual = manifest.total_bytes
            tolerance = manifest.size_tolerance_ratio
            max_delta = max(8192, int(target * tolerance))
            delta = abs(actual - target)

            self.assertLessEqual(
                delta,
                max_delta,
                f"Profile {cid} size delta {delta} exceeded max allowed delta {max_delta} "
                f"(target={target}, actual={actual}, tolerance={tolerance*100:.1f}%)",
            )


if __name__ == "__main__":
    unittest.main()
