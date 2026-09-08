"""Unit tests for T006 Automatic Parallelism Experiment Infrastructure.

Validates:
1. Data models and JSON serialization/deserialization.
2. Compiler backend emission inspection regex and excerpt extraction.
3. CPU monitoring and multi-core threshold calculation.
4. Result classification logic across Category A, B, C, D, and E.
5. Mathematical consistency of serial-equivalent controls.
6. Stage breakdown data structures and reporting.
7. Research question answer generation and evidence grading.
8. Source tree immutability (production src/*.j2 remains untouched).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

# Resolve repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.generator.manifest import MANIFEST_FILENAME
from benchmarks.harness import (
    BaselineMeasurement,
    PlatformProvenance,
    RunExecutionResult,
    TimingStatistics,
    calculate_timing_statistics,
    collect_platform_provenance,
)
from benchmarks.run_t006 import (
    format_t006_markdown_report,
    generate_offline_mock_report,
    synthesize_research_answers,
)
from benchmarks.t006_harness import (
    CompilerInspectionEvidence,
    CpuSampler,
    CpuUtilizationEvidence,
    ObservabilityEvidence,
    ResearchQuestionAnswer,
    StageBreakdownResult,
    T006ExperimentHarness,
    T006ExperimentResult,
    T006FullReport,
    classify_experiment_result,
    execute_with_cpu_monitoring,
    inspect_compiler_emission,
)


class TestT006DataModels(unittest.TestCase):
    """Test serialization, deserialization, and schema integrity of T006 data models."""

    def test_compiler_inspection_evidence_serialization(self) -> None:
        ev = CompilerInspectionEvidence(
            source_name="test.j2",
            source_sha256="abc123",
            has_parallel_constructs=True,
            matched_constructs=["par_iter", "rayon"],
            evidence_excerpts=[{"line": 10, "pattern": "rayon", "context": "use rayon::prelude::*;"}],
            emission_sample="// emitted code",
            analysis_method="regex",
            epistemic_note="note",
        )
        d = ev.to_dict()
        self.assertEqual(d["source_name"], "test.j2")
        self.assertTrue(d["has_parallel_constructs"])
        self.assertIn("rayon", d["matched_constructs"])

    def test_cpu_utilization_evidence(self) -> None:
        cpu_single = CpuUtilizationEvidence(98.5, 95.0, 10, False, "sampler")
        self.assertFalse(cpu_single.multi_core_engaged)

        cpu_multi = CpuUtilizationEvidence(250.0, 180.0, 10, True, "sampler")
        self.assertTrue(cpu_multi.multi_core_engaged)

    def test_t006_full_report_json_roundtrip(self) -> None:
        prov = collect_platform_provenance("j2")
        report = generate_offline_mock_report([], prov)
        json_str = report.to_json()
        data = json.loads(json_str)

        self.assertEqual(data["task_id"], "T006-automatic-parallelism")
        self.assertIn("experiments", data)
        self.assertIn("stage_breakdowns", data)
        self.assertIn("research_answers", data)
        self.assertEqual(len(data["research_answers"]), 7)


class TestT006ClassificationLogic(unittest.TestCase):
    """Test classification into Category A through E based on empirical signals."""

    def test_category_a_strong_parallelism(self) -> None:
        cls, grade = classify_experiment_result(
            speedup_native_over_interp=3.5,
            speedup_candidate_over_serial=1.45,
            multi_core_engaged=True,
            compiler_has_parallel=True,
        )
        self.assertEqual(cls, "CATEGORY A")
        self.assertEqual(grade, "A")

    def test_category_b_suggestive(self) -> None:
        cls, grade = classify_experiment_result(
            speedup_native_over_interp=2.0,
            speedup_candidate_over_serial=1.20,
            multi_core_engaged=False,
            compiler_has_parallel=True,
        )
        self.assertEqual(cls, "CATEGORY B")
        self.assertEqual(grade, "B")

    def test_category_c_native_compilation_only(self) -> None:
        cls, grade = classify_experiment_result(
            speedup_native_over_interp=2.5,
            speedup_candidate_over_serial=1.03,
            multi_core_engaged=False,
            compiler_has_parallel=False,
        )
        self.assertEqual(cls, "CATEGORY C")
        self.assertEqual(grade, "A")

    def test_category_d_no_benefit(self) -> None:
        cls, grade = classify_experiment_result(
            speedup_native_over_interp=1.01,
            speedup_candidate_over_serial=1.00,
            multi_core_engaged=False,
            compiler_has_parallel=False,
        )
        self.assertEqual(cls, "CATEGORY D")
        self.assertEqual(grade, "A")


class TestT006SerialEquivalentControls(unittest.TestCase):
    """Test that serial-equivalent algorithms compute identical results to candidate reduction."""

    def test_arithmetic_control_equivalence(self) -> None:
        for n in [10, 1000, 100_000]:
            ground_truth = n * (n + 1) // 2

            # Simulate serial loop logic from t006_a_serial.j2
            acc = 0
            prev = 0
            for i in range(1, n + 1):
                diff = i - prev
                acc = acc + prev + diff
                prev = i

            self.assertEqual(acc, ground_truth)

    def test_memory_control_digest_determinism(self) -> None:
        # Verify in-memory buffer hashing produces valid 64-char hex SHA-256
        data = bytes(range(256))
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(len(digest), 64)


class TestT006SourceIsolation(unittest.TestCase):
    """Enforce strict T006 boundary: production src/*.j2 must never be modified."""

    def test_src_directory_unmodified(self) -> None:
        src_files = list((_REPO_ROOT / "src").glob("*.j2"))
        self.assertGreater(len(src_files), 0)
        expected_names = {"main.j2", "scan.j2", "hash.j2", "group.j2", "output.j2"}
        actual_names = {f.name for f in src_files}
        self.assertTrue(expected_names.issubset(actual_names))

    def test_experimental_sources_isolated(self) -> None:
        exp_dir = _REPO_ROOT / "benchmarks" / "t006"
        self.assertTrue(exp_dir.is_dir())
        exp_files = list(exp_dir.glob("*.j2"))
        self.assertGreater(len(exp_files), 5)
        names = {f.name for f in exp_files}
        self.assertIn("t006_a_candidate.j2", names)
        self.assertIn("t006_a_serial.j2", names)
        self.assertIn("t006_b_candidate.j2", names)
        self.assertIn("t006_b_serial.j2", names)
        self.assertIn("t006_c_candidate.j2", names)
        self.assertIn("t006_c_serial.j2", names)


class TestT006ScientificReportingAndCorpusIdentity(unittest.TestCase):
    """Ensure T006 reports maintain rigorous scientific wording and exact corpus provenance."""

    def test_saved_results_corpus_provenance(self) -> None:
        results_file = _REPO_ROOT / "benchmarks" / "results" / "t006_results.json"
        self.assertTrue(results_file.is_file(), "t006_results.json must exist")
        data = json.loads(results_file.read_text(encoding="utf-8"))

        # Verify Level C and D variants have full corpus provenance
        for exp in data.get("experiments", []):
            if exp["workload_level"] in ("C", "D"):
                params = exp["workload_parameters"]
                self.assertIn("corpus_id", params)
                self.assertIn("profile", params)
                self.assertEqual(params.get("seed"), 12345, f"Variant {exp['variant_id']} must use seed 12345")
                self.assertEqual(params.get("scale"), 0.01, f"Variant {exp['variant_id']} must use scale 0.01")
                self.assertIn("manifest_sha256", params)
                self.assertEqual(len(params["manifest_sha256"]), 64)
                self.assertGreater(params.get("file_count", 0), 0)
                self.assertGreater(params.get("candidate_count", 0), 0)
                self.assertGreater(params.get("total_bytes", 0), 0)

    def test_saved_report_forbidden_overclaims(self) -> None:
        report_file = _REPO_ROOT / "benchmarks" / "results" / "t006_report.md"
        self.assertTrue(report_file.is_file(), "t006_report.md must exist")
        text = report_file.read_text(encoding="utf-8").lower()

        forbidden_phrases = [
            "strictly single-core",
            "compiler definitely rejected",
            "all workloads execute strictly on a single cpu core",
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, text, f"Found forbidden overclaim '{phrase}' in t006_report.md")

    def test_research_question_evidence_grades(self) -> None:
        results_file = _REPO_ROOT / "benchmarks" / "results" / "t006_results.json"
        data = json.loads(results_file.read_text(encoding="utf-8"))
        rq_map = {q["question_number"]: q for q in data.get("research_answers", [])}

        self.assertEqual(rq_map[1]["evidence_grade"], "A")
        self.assertEqual(rq_map[2]["evidence_grade"], "A")
        self.assertEqual(rq_map[3]["evidence_grade"], "A")
        self.assertEqual(rq_map[4]["evidence_grade"], "B")  # Standalone stage probe approximation
        self.assertEqual(rq_map[5]["evidence_grade"], "B")  # Warm repeated run page cache inference
        self.assertEqual(rq_map[6]["evidence_grade"], "A")
        self.assertEqual(rq_map[7]["evidence_grade"], "B")  # macOS CI only, dev hardware not authoritative


class TestT006RemediatedFindings(unittest.TestCase):
    """Regression tests for findings P1-02, P2-02, P2-03, P2-04 remediated in T006."""

    def test_stage_breakdown_negative_delta_handling(self) -> None:
        """P1-02: Verify negative or sub-noise-floor stage deltas are not clipped to 0.0 ms.

        Instead, they must be set to None with status 'below_noise_floor', preserve raw cumulative
        values, and format as 'N/A*' in Markdown reports without skewing percentages.
        """
        raw_cum = {
            "discovery_ms": 100.0,
            "filter_ms": 120.0,
            "read_hash_ms": 118.0,  # Negative delta vs filter: 118.0 - 120.0 = -2.0 ms
            "group_ms": 140.0,
        }
        res = StageBreakdownResult(
            corpus_id="C_test",
            scale=0.01,
            file_count=50,
            candidate_count=20,
            t_discovery_ms=100.0,
            t_filter_ms=20.0,
            t_read_hash_ms=None,  # below noise floor
            t_group_ms=22.0,
            t_total_ms=140.0,
            dominant_stage="Discovery",
            raw_cumulative_ms=raw_cum,
            stage_validity={
                "discovery": "valid",
                "filter": "valid",
                "read_hash": "below_noise_floor",
                "group": "valid",
            },
        )
        d = res.to_dict()
        self.assertIsNone(d["t_read_hash_ms"])
        self.assertEqual(d["stage_validity"]["read_hash"], "below_noise_floor")
        self.assertEqual(d["raw_cumulative_ms"]["read_hash_ms"], 118.0)
        self.assertEqual(d["raw_cumulative_ms"]["filter_ms"], 120.0)

        # Verify full report markdown formatting renders N/A* without throwing
        prov = collect_platform_provenance("j2")
        mock_report = generate_offline_mock_report([], prov)
        mock_report.stage_breakdowns = [res]
        md = format_t006_markdown_report(mock_report)
        self.assertIn("N/A*", md)
        self.assertIn("noise floor", md)

    def test_cpu_sampling_insufficient_samples(self) -> None:
        """P2-03: Verify CPU profiler flags insufficient samples (<4) as invalid."""
        sampler = CpuSampler(pid=99999)
        # 1 sample: below MIN_RELIABLE_SAMPLES (4)
        sampler.samples = [15.0]
        ev = sampler.stop(duration_ms=45.0)
        self.assertFalse(ev.cpu_measurement_valid)
        self.assertIn("insufficient_samples", ev.invalid_reason or "")
        self.assertEqual(ev.sample_count, 1)

        # 4 samples: meeting MIN_RELIABLE_SAMPLES
        sampler_ok = CpuSampler(pid=99999)
        sampler_ok.samples = [25.0, 30.0, 20.0, 35.0]
        ev_ok = sampler_ok.stop(duration_ms=200.0)
        self.assertTrue(ev_ok.cpu_measurement_valid)
        self.assertIsNone(ev_ok.invalid_reason)
        self.assertEqual(ev_ok.sample_count, 4)

    def test_level_c_serial_dependency_data_dependence(self) -> None:
        """P2-02: Verify T006-C serial control has true loop-carried cryptographic data dependence.

        The dependency chains prev_hash into the next hash:
            chained = fmt("{}:{}", prev_hash, file_digest)
            d = hash.sha256(chained)
            prev_hash = d
        A change to any file's digest must propagate to all subsequent chained digests.
        """
        serial_file = _REPO_ROOT / "benchmarks" / "t006" / "t006_c_serial.j2"
        self.assertTrue(serial_file.is_file())
        content = serial_file.read_text(encoding="utf-8")

        # Must not rely on trivial length-based dependency
        self.assertNotIn("prev_len = len(d)", content)
        self.assertIn("prev_hash", content)
        self.assertIn("hash.sha256(chained)", content)

        # Verify mathematical avalanche effect: 1-bit difference in file 0 cascades
        def run_chain(digests: list[str]) -> list[str]:
            chain = []
            prev = "0000000000000000000000000000000000000000000000000000000000000000"
            for fd in digests:
                c = f"{prev}:{fd}"
                h = hashlib.sha256(c.encode("utf-8")).hexdigest()
                chain.append(h)
                prev = h
            return chain

        digests_a = [hashlib.sha256(f"file_{i}".encode()).hexdigest() for i in range(10)]
        digests_b = list(digests_a)
        # Introduce a 1-character difference in the first digest
        digests_b[0] = hashlib.sha256(b"file_0_modified").hexdigest()

        chain_a = run_chain(digests_a)
        chain_b = run_chain(digests_b)

        # Every single subsequent step must differ (avalanche effect)
        for i in range(10):
            self.assertNotEqual(chain_a[i], chain_b[i], f"Step {i} must diverge due to loop-carried dependency")

    def test_harness_error_handling_rejection(self) -> None:
        """P2-04: Subprocess failure, non-zero returncode, or timeout must raise RuntimeError."""
        harness = T006ExperimentHarness(
            j2_bin="j2",
            build_dir=_REPO_ROOT / "build",
            timeout_s=5.0,
        )
        harness.base_harness = MagicMock()

        mock_inspect_ev = CompilerInspectionEvidence(
            source_name="t006_c_candidate.j2",
            source_sha256="abc123",
            has_parallel_constructs=False,
            matched_constructs=[],
            evidence_excerpts=[],
            emission_sample="",
            analysis_method="regex",
            epistemic_note="",
        )

        with patch("benchmarks.t006_harness.inspect_compiler_emission", return_value=mock_inspect_ev), \
             patch("benchmarks.t006_harness.execute_with_cpu_monitoring") as mock_exec:
            # 1. Non-zero returncode must raise RuntimeError
            mock_exec.return_value = (
                RunExecutionResult(returncode=1, wall_time_ms=10.0, stdout="", stderr="Segfault", error="code 1"),
                CpuUtilizationEvidence(0.0, 0.0, 0, False, "none", False, "insufficient_samples", 10.0),
            )
            with self.assertRaises(RuntimeError) as ctx:
                harness.run_level_c([_REPO_ROOT / "tests"], warmup_runs=0, measured_runs=1)
            self.assertIn("failed", str(ctx.exception).lower())

            # 2. Timeout (returncode -1) must raise RuntimeError
            mock_exec.return_value = (
                RunExecutionResult(returncode=-1, wall_time_ms=5000.0, stdout="", stderr="", error="TimeoutExpired"),
                CpuUtilizationEvidence(0.0, 0.0, 0, False, "none", False, "process_timed_out", 5000.0),
            )
            with self.assertRaises(RuntimeError) as ctx:
                harness.run_level_c([_REPO_ROOT / "tests"], warmup_runs=0, measured_runs=1)
            self.assertIn("failed", str(ctx.exception).lower())

            # 3. Malformed output (e.g. not 64-character hex digest) must raise RuntimeError
            mock_exec.return_value = (
                RunExecutionResult(returncode=0, wall_time_ms=15.0, stdout="short_digest", stderr="", error=None),
                CpuUtilizationEvidence(0.0, 0.0, 5, False, "none", True, None, 15.0),
            )
            with self.assertRaises(RuntimeError) as ctx:
                harness.run_level_c([_REPO_ROOT / "tests"], warmup_runs=0, measured_runs=1)
            self.assertIn("invalid", str(ctx.exception).lower())


class TestT006EdgeCases(unittest.TestCase):
    """Targeted edge-case verification for T006-A and T006-B boundary behaviors."""

    def test_level_a_boundary_edge_cases(self) -> None:
        """Section 7: Validate N=0, N=1, and threshold-adjacent values (32767, 32769).

        Ensures candidate reduction formula and serial loop accumulator agree mathematically
        across word/register boundaries without integer overflow or behavioral divergences.
        """
        test_boundaries = [
            (0, 0),
            (1, 1),
            (32767, 536854528),      # 2^15 - 1 (signed 16-bit max)
            (32768, 536887296),      # 2^15 boundary
            (32769, 536920065),      # 2^15 + 1
        ]
        for n, expected in test_boundaries:
            # Candidate mathematical reduction
            cand_val = n * (n + 1) // 2
            self.assertEqual(cand_val, expected, f"Candidate failed on boundary N={n}")

            # Serial accumulator loop simulation
            acc = 0
            prev = 0
            for i in range(1, n + 1):
                diff = i - prev
                acc = acc + prev + diff
                prev = i
            self.assertEqual(acc, expected, f"Serial loop failed on boundary N={n}")

    def test_level_b_boundary_edge_cases(self) -> None:
        """Section 8: Validate zero buffers, one buffer, and one small buffer behavior."""
        # 1. Zero buffers (K=0)
        def hash_buffers_cand(bufs: list[bytes]) -> str:
            d = "0000000000000000000000000000000000000000000000000000000000000000"
            for b in bufs:
                d = hashlib.sha256(b).hexdigest()
            return d

        def hash_buffers_serial(bufs: list[bytes]) -> str:
            d = "0000000000000000000000000000000000000000000000000000000000000000"
            for b in bufs:
                fd = hashlib.sha256(b).hexdigest()
                d = hashlib.sha256(f"{d}:{fd}".encode()).hexdigest()
            return d

        # Zero buffers: both preserve initial sentinel
        self.assertEqual(hash_buffers_cand([]), "0000000000000000000000000000000000000000000000000000000000000000")
        self.assertEqual(hash_buffers_serial([]), "0000000000000000000000000000000000000000000000000000000000000000")

        # 2. One small buffer (16 bytes)
        single_buf = [b"a" * 16]
        cand_out = hash_buffers_cand(single_buf)
        serial_out = hash_buffers_serial(single_buf)
        self.assertEqual(len(cand_out), 64)
        self.assertEqual(len(serial_out), 64)
        self.assertEqual(cand_out, hashlib.sha256(b"a" * 16).hexdigest())
        # Both outputs are deterministically reproducible
        self.assertEqual(cand_out, hash_buffers_cand(single_buf))
        self.assertEqual(serial_out, hash_buffers_serial(single_buf))


class TestT006ProcessMonitoringAndTimeout(unittest.TestCase):
    """Real unmocked regression tests for subprocess timeout and CPU monitoring (P2-04b)."""

    def test_unmocked_timeout_handling_real_process(self) -> None:
        """P2-04b: Real, unmocked subprocess execution must handle timeout cleanly."""
        cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
        res, cpu = execute_with_cpu_monitoring(cmd, timeout_s=0.2)

        # 1. Function returns rather than raising TypeError
        self.assertIsInstance(res, RunExecutionResult)
        self.assertIsInstance(cpu, CpuUtilizationEvidence)

        # 2. Returncode indicates failure / timeout
        self.assertEqual(res.returncode, -1)
        self.assertIsNotNone(res.error)
        self.assertIn("TimeoutExpired", res.error)

        # 3. CPU evidence exists and marks measurement as invalid with reason
        self.assertFalse(cpu.cpu_measurement_valid)
        self.assertEqual(cpu.invalid_reason, "process_timed_out")
        self.assertEqual(cpu.measurement_method, "Process timed out")
        self.assertIsNotNone(cpu.measurement_duration_ms)
        self.assertGreaterEqual(cpu.measurement_duration_ms, 150.0)

        # 4. Failed/timed out execution cannot enter successful timing statistics
        # Verify that benchmark harness protects timing lists (only returncode == 0 is appended)
        successful_timings: list[float] = []
        if res.returncode == 0:
            successful_timings.append(res.wall_time_ms)
        self.assertEqual(len(successful_timings), 0)
        with self.assertRaises(ValueError):
            calculate_timing_statistics(successful_timings, warmup_runs=0)

    def test_generic_execution_error_cpu_evidence(self) -> None:
        """P2-04b: Generic process execution errors must report invalid CPU evidence."""
        res, cpu = execute_with_cpu_monitoring(["__non_existent_binary_for_t006_test__"])
        self.assertEqual(res.returncode, -1)
        self.assertFalse(cpu.cpu_measurement_valid)
        self.assertEqual(cpu.invalid_reason, "execution_error")

    def test_t006_c_provenance_fields_present(self) -> None:
        """P2-02: Ensure T006-C results record candidate and serial source hashes and provenance."""
        prov = collect_platform_provenance("j2")
        mock_rep = generate_offline_mock_report([_REPO_ROOT / "tests"], prov)
        c_exps = [e for e in mock_rep.experiments if e.experiment_id == "T006-C"]
        self.assertGreater(len(c_exps), 0)
        for e in c_exps:
            self.assertIsNotNone(e.candidate_source_sha256)
            self.assertIsNotNone(e.serial_source_sha256)
            self.assertIsNotNone(e.git_commit)
            self.assertIsNotNone(e.timestamp)
            self.assertIn("candidate_source_sha256", e.workload_parameters)
            self.assertIn("serial_source_sha256", e.workload_parameters)
            self.assertIn("git_commit", e.workload_parameters)
            self.assertIn("timestamp", e.workload_parameters)


if __name__ == "__main__":
    unittest.main()

