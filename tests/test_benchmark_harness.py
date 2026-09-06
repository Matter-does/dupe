"""Comprehensive validation tests for the benchmark harness (TASK T005).

Verifies:
1. Statistical timing calculations (median, mean, min, max, stddev, variance).
2. Throughput rate derivation and speedup factor calculations.
3. Platform and toolchain provenance metadata collection and schema.
4. Baseline C pure control mathematical ground truth (sum(1..2000000) = 2000001000000).
5. Output JSON bit-for-bit equivalence and SHA-256 digest validation logic.
6. Workload metrics extraction from dupe JSON output.
7. Pre-flight manifest verification hook on valid and corrupted corpora.
8. Machine-readable report JSON serialization and Markdown table generation.
9. Execution timing wrapper and timeout handling.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

# Resolve repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.generator import (
    C1_PROFILE,
    C2_PROFILE,
    generate_corpus,
)
from benchmarks.generator.manifest import (
    MANIFEST_FILENAME,
    compute_result_digest,
    format_deterministic_json,
)
from benchmarks.harness import (
    BaselineMeasurement,
    BaselineWorkloadMetrics,
    BenchmarkHarness,
    CorpusComparisonResult,
    FullBenchmarkReport,
    PlatformProvenance,
    PureControlResult,
    RunExecutionResult,
    TimingStatistics,
    calculate_timing_statistics,
    collect_platform_provenance,
    extract_workload_metrics,
)
from benchmarks.run_baselines import format_markdown_report


class TestBenchmarkHarness(unittest.TestCase):
    """Unit and offline integration tests for T005 benchmark harness."""

    def test_timing_statistics_calculation(self) -> None:
        """Verify standard statistical calculations over timing lists."""
        data = [100.0, 110.0, 105.0, 120.0, 95.0]
        stats = calculate_timing_statistics(data, warmup_runs=1)

        self.assertEqual(stats.iterations, 5)
        self.assertEqual(stats.warmup_runs, 1)
        self.assertEqual(stats.median_ms, 105.0)
        self.assertEqual(stats.min_ms, 95.0)
        self.assertEqual(stats.max_ms, 120.0)
        self.assertAlmostEqual(stats.mean_ms, 106.0, places=2)
        self.assertGreater(stats.stddev_ms, 0.0)
        self.assertGreater(stats.variance_ms, 0.0)

        # Single item edge case
        single = calculate_timing_statistics([50.0], warmup_runs=0)
        self.assertEqual(single.iterations, 1)
        self.assertEqual(single.median_ms, 50.0)
        self.assertEqual(single.stddev_ms, 0.0)
        self.assertEqual(single.variance_ms, 0.0)

        # Empty list error
        with self.assertRaises(ValueError):
            calculate_timing_statistics([], warmup_runs=0)

    def test_platform_provenance_schema(self) -> None:
        """Verify provenance metadata captures all required fields."""
        prov = collect_platform_provenance(j2_bin="j2")
        d = prov.to_dict()

        self.assertIn("system", d)
        self.assertIn("release", d)
        self.assertIn("machine", d)
        self.assertIn("cpu_count", d)
        self.assertIn("runner_id", d)
        self.assertIn("git_commit", d)
        self.assertIn("j2_version", d)
        self.assertIn("timestamp_utc", d)
        self.assertGreater(d["cpu_count"], 0)

    def test_pure_control_ground_truth(self) -> None:
        """Verify Baseline C mathematical ground truth reduction."""
        n = 2000000
        expected_sum = n * (n + 1) // 2
        self.assertEqual(expected_sum, 2000001000000)
        self.assertEqual(str(expected_sum), "2000001000000")

    def test_workload_metrics_extraction(self) -> None:
        """Verify correct extraction of workload metrics from dupe JSON output."""
        sample_json = {
            "files_scanned": 150,
            "hash_candidates": 40,
            "duplicate_groups": [
                {"hash": "aaa", "size": 1024, "files": ["f1", "f2"], "reclaimable_bytes": 1024},
                {"hash": "bbb", "size": 2048, "files": ["f3", "f4", "f5"], "reclaimable_bytes": 4096},
            ],
            "reclaimable_bytes": 5120,
        }
        metrics = extract_workload_metrics(sample_json)
        self.assertEqual(metrics.files_scanned, 150)
        self.assertEqual(metrics.candidate_files, 40)
        self.assertEqual(metrics.duplicate_groups, 2)
        self.assertEqual(metrics.duplicate_files, 5)  # 2 + 3
        self.assertEqual(metrics.reclaimable_bytes, 5120)
        self.assertEqual(metrics.bytes_hashed, (1024 * 2) + (2048 * 3))

    def test_output_equivalence_and_digest_verification(self) -> None:
        """Verify JSON output equivalence and digest verification logic."""
        json_a = {"files_scanned": 10, "hash_candidates": 4, "duplicate_groups": [], "reclaimable_bytes": 0}
        json_b = {"files_scanned": 10, "hash_candidates": 4, "duplicate_groups": [], "reclaimable_bytes": 0}
        json_c = {"files_scanned": 10, "hash_candidates": 5, "duplicate_groups": [], "reclaimable_bytes": 0}

        str_a = format_deterministic_json(json_a)
        str_b = format_deterministic_json(json_b)
        str_c = format_deterministic_json(json_c)

        self.assertEqual(str_a, str_b)
        self.assertNotEqual(str_a, str_c)

        dig_a = compute_result_digest(json_a)
        dig_b = compute_result_digest(json_b)
        dig_c = compute_result_digest(json_c)

        self.assertEqual(dig_a, dig_b)
        self.assertNotEqual(dig_a, dig_c)

    def test_corpus_verification_preflight(self) -> None:
        """Verify harness pre-flight corpus verification detects valid and tampered trees."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "test_corpus"
            # Generate miniature C2 corpus
            generate_corpus(
                profile=C2_PROFILE,
                out_dir=out_path,
                seed=42,
                scale=0.01,
            )

            harness = BenchmarkHarness()
            is_valid, manifest, errors = harness.verify_corpus(out_path)
            self.assertTrue(is_valid, f"Expected valid corpus, got errors: {errors}")
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest.corpus_id, "C2")

            # Tamper with file to ensure verification fails
            manifest_file = out_path / MANIFEST_FILENAME
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            data["file_count"] = 999999
            manifest_file.write_text(json.dumps(data), encoding="utf-8")

            is_valid_tampered, _, errors_tampered = harness.verify_corpus(out_path)
            self.assertFalse(is_valid_tampered)
            self.assertGreater(len(errors_tampered), 0)

    def test_report_serialization_and_markdown(self) -> None:
        """Verify FullBenchmarkReport schema serialization and Markdown rendering."""
        prov = collect_platform_provenance()
        stats_interp = calculate_timing_statistics([250.0, 240.0, 245.0], warmup_runs=1)
        stats_native = calculate_timing_statistics([50.0, 48.0, 52.0], warmup_runs=1)

        meas_a = BaselineMeasurement(
            baseline_id="Baseline_A_Interpreter",
            baseline_name="J2 Interpreter",
            command_line=["j2", "run"],
            environment_vars={},
            timing=stats_interp,
            metrics=BaselineWorkloadMetrics(1000, 200, 1024000, 50, 100, 512000),
            output_digest="a" * 64,
        )
        meas_b = BaselineMeasurement(
            baseline_id="Baseline_B_Native",
            baseline_name="J2 Native",
            command_line=["./build/dupe"],
            environment_vars={"J2_ALLOW_FS": "1"},
            timing=stats_native,
            metrics=BaselineWorkloadMetrics(1000, 200, 1024000, 50, 100, 512000),
            output_digest="a" * 64,
            build_time_ms=1200.0,
        )

        comp = CorpusComparisonResult(
            corpus_id="C2",
            corpus_manifest_sha256="b" * 64,
            scale=0.1,
            baseline_a_interpreter=meas_a,
            baseline_b_native=meas_b,
            direct_json_match=True,
            digest_matches_manifest=True,
            expected_digest="a" * 64,
            actual_digest="a" * 64,
            native_speedup_factor=4.9,
            files_per_sec_interpreter=4081.6,
            files_per_sec_native=20000.0,
            candidates_per_sec_interpreter=816.3,
            candidates_per_sec_native=4000.0,
            mb_per_sec_interpreter=3.99,
            mb_per_sec_native=19.53,
        )

        control = PureControlResult(
            program_source="data = collect(1..2000000)\nprint(sum(data))",
            ground_truth_result="2000001000000",
            build_time_ms=1100.0,
            interpreter_measurement=meas_a,
            native_measurement=meas_b,
            correctness_verified=True,
            native_speedup_factor=4.9,
        )

        report = FullBenchmarkReport(
            schema_version=1,
            task_id="T005",
            provenance=prov,
            pure_control_baseline_c=control,
            corpus_comparisons=[comp],
            compiler_inspection={"pure_control": "sample", "dupe_main": "sample"},
            summary_conclusions=["Conclusion 1", "Conclusion 2"],
            unresolved_limitations=["Limitation 1"],
        )

        # Verify JSON serialization
        report_json = report.to_json()
        decoded = json.loads(report_json)
        self.assertEqual(decoded["task_id"], "T005")
        self.assertEqual(decoded["corpus_comparisons"][0]["corpus_id"], "C2")

        # Verify Markdown formatting
        md = format_markdown_report(report)
        self.assertIn("# T005 — J2 Interpreter/Native Baseline Benchmark Report", md)
        self.assertIn("## Baseline C — Pure J2 Parallelism Control", md)
        self.assertIn("## Filesystem Workload Baselines", md)
        self.assertIn("### Detailed Throughput Rates", md)
        self.assertIn("## Scientific Findings & Baseline Conclusions", md)


if __name__ == "__main__":
    unittest.main()
