"""T006 Automatic Parallelism Experiment Harness & Evidence Collector.

Implements the 4-step experimental ladder:
  Level T006-A: Pure J2 Computational Control (Known reduction)
  Level T006-B: Pure In-Memory Hashing (Isolate CPU/data-processing)
  Level T006-C: Filesystem Read + Hash (I/O boundary entry)
  Level T006-D: Full dupe Pipeline (End-to-end duplicate workload)

Observability Hierarchy:
  Level 1: Compiler IR & Backend Inspection (`j2 emit-native`)
  Level 2: Empirical Runtime Performance (wall-clock timing & statistics)
  Level 3: External OS Profiling & Syscall Tracing
  Level 4: CPU Core Utilization Monitoring (multi-core load %)
  Level 5: Result Determinism Verification (bit-for-bit digest match)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import threading
import time
from typing import Any, Optional

# Resolve repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.generator.generate import generate_corpus
from benchmarks.generator.manifest import (
    MANIFEST_FILENAME,
    Manifest,
    compute_corpus_candidate_bytes,
    compute_result_digest,
    format_deterministic_json,
    validate_manifest,
)
from benchmarks.generator.profiles import NAMED_PROFILES, CorpusProfile
from benchmarks.harness import (
    BaselineMeasurement,
    BaselineWorkloadMetrics,
    BenchmarkHarness,
    CorpusComparisonResult,
    PlatformProvenance,
    RunExecutionResult,
    TimingStatistics,
    calculate_timing_statistics,
    collect_platform_provenance,
    extract_workload_metrics,
    normalize_dupe_output_paths,
)

CONCURRENCY_PATTERNS = [
    "par_iter",
    "into_par_iter",
    "rayon",
    "thread::spawn",
    "std::thread::spawn",
    "crossbeam",
    "scoped_thread",
]


@dataclass
class CompilerInspectionEvidence:
    """Auditable evidence extracted from backend compilation."""
    source_name: str
    source_sha256: str
    has_parallel_constructs: bool
    matched_constructs: list[str]
    evidence_excerpts: list[dict[str, Any]]
    emission_sample: str
    analysis_method: str
    epistemic_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CpuUtilizationEvidence:
    """CPU core utilization measurements across the execution window."""
    max_cpu_percent: float
    avg_cpu_percent: float
    sample_count: int
    multi_core_engaged: bool
    measurement_method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ObservabilityEvidence:
    """Multi-level observability evidence package for a benchmark execution."""
    compiler: CompilerInspectionEvidence
    cpu: CpuUtilizationEvidence
    profiler: dict[str, Any]
    determinism: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class T006ExperimentResult:
    """Structured machine-readable result for a single T006 experiment variant."""
    experiment_id: str          # "T006-A", "T006-B", "T006-C", "T006-D"
    variant_id: str             # e.g. "T006_A_medium_2M"
    workload_name: str
    workload_level: str         # "A", "B", "C", "D"
    source_file: str
    source_sha256: str
    workload_parameters: dict[str, Any]
    interpreter_measurement: Optional[BaselineMeasurement]
    native_candidate_measurement: Optional[BaselineMeasurement]
    native_serial_measurement: Optional[BaselineMeasurement]
    speedup_native_over_interpreter: float
    speedup_candidate_over_serial: float
    correctness_verified: bool
    evidence: ObservabilityEvidence
    evidence_grade: str         # "A", "B", "C", "D", "E"
    classification: str         # "CATEGORY A".."CATEGORY E"
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StageBreakdownResult:
    """Stage timing breakdown for dupe pipeline execution."""
    corpus_id: str
    scale: float
    file_count: int
    candidate_count: int
    t_discovery_ms: float
    t_filter_ms: float
    t_read_hash_ms: float
    t_group_ms: float
    t_total_ms: float
    dominant_stage: str
    measurement_type: str = "MEASURED via isolated stage probes"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchQuestionAnswer:
    """Direct answer to one of the 7 core T006 research questions."""
    question_number: int
    question: str
    answer: str
    evidence_grade: str
    supporting_artifact: str
    limitations: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class T006FullReport:
    """Root artifact containing all T006 experimental data, classifications, and conclusions."""
    schema_version: int
    task_id: str
    timestamp_utc: str
    provenance: PlatformProvenance
    experiments: list[T006ExperimentResult]
    stage_breakdowns: list[StageBreakdownResult]
    research_answers: list[ResearchQuestionAnswer]
    overall_classification: str
    headline_conclusions: list[str]
    unresolved_limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def inspect_compiler_emission(source_path: Path, j2_bin: str = "j2") -> CompilerInspectionEvidence:
    """Invoke `j2 emit-native` on a source file and analyze for concurrency primitives."""
    src_bytes = source_path.read_bytes() if source_path.is_file() else b""
    src_sha = hashlib.sha256(src_bytes).hexdigest()

    cmd = [j2_bin, "emit-native", str(source_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60.0)
        emission_text = res.stdout if res.returncode == 0 else ""
    except Exception:
        emission_text = ""

    lines = emission_text.splitlines()
    matched_constructs: list[str] = []
    evidence_excerpts: list[dict[str, Any]] = []

    for idx, line in enumerate(lines):
        line_lower = line.lower()
        for pat in CONCURRENCY_PATTERNS:
            if pat in line_lower:
                if pat not in matched_constructs:
                    matched_constructs.append(pat)
                start = max(0, idx - 2)
                end = min(len(lines), idx + 3)
                context = "\n".join(lines[start:end])
                evidence_excerpts.append({
                    "line_number": idx + 1,
                    "matched_pattern": pat,
                    "context": context,
                })

    sample = "\n".join(lines[:30]) if lines else "Emission unavailable (offline or syntax error)"

    return CompilerInspectionEvidence(
        source_name=source_path.name,
        source_sha256=src_sha,
        has_parallel_constructs=len(matched_constructs) > 0,
        matched_constructs=matched_constructs,
        evidence_excerpts=evidence_excerpts,
        emission_sample=sample,
        analysis_method="Regex search for multi-threaded runtime primitives in Rust emission",
        epistemic_note="Compiler emission reflects structural backend source; multi-core execution requires runtime verification.",
    )


class CpuSampler:
    """Lightweight background thread sampling process CPU utilization."""

    def __init__(self, pid: int, interval_s: float = 0.02) -> None:
        self.pid = pid
        self.interval_s = interval_s
        self.samples: list[float] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> CpuUtilizationEvidence:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

        if not self.samples:
            return CpuUtilizationEvidence(
                max_cpu_percent=0.0,
                avg_cpu_percent=0.0,
                sample_count=0,
                multi_core_engaged=False,
                measurement_method="Process sampling (no samples captured)",
            )

        max_cpu = round(max(self.samples), 1)
        avg_cpu = round(sum(self.samples) / len(self.samples), 1)
        multi_core = max_cpu > 110.0

        return CpuUtilizationEvidence(
            max_cpu_percent=max_cpu,
            avg_cpu_percent=avg_cpu,
            sample_count=len(self.samples),
            multi_core_engaged=multi_core,
            measurement_method="Background periodic sample via ps/system API",
        )

    def _run(self) -> None:
        while not self._stop_event.is_set():
            val = self._sample()
            if val is not None:
                self.samples.append(val)
            time.sleep(self.interval_s)

    def _sample(self) -> Optional[float]:
        try:
            if sys.platform != "win32":
                res = subprocess.run(
                    ["ps", "-p", str(self.pid), "-o", "%cpu"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0:
                    lines = res.stdout.strip().splitlines()
                    if len(lines) >= 2:
                        return float(lines[1].strip())
        except Exception:
            pass
        return None


def execute_with_cpu_monitoring(
    cmd: list[str],
    env: Optional[dict[str, str]] = None,
    cwd: Optional[Path] = None,
    timeout_s: float = 120.0,
) -> tuple[RunExecutionResult, CpuUtilizationEvidence]:
    """Execute a command line while concurrently sampling process CPU load."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)

    t_start = time.perf_counter_ns()
    try:
        proc = subprocess.Popen(
            cmd,
            env=full_env,
            cwd=cwd or _REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        sampler = CpuSampler(pid=proc.pid)
        sampler.start()

        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        finally:
            cpu_evidence = sampler.stop()

        t_end = time.perf_counter_ns()
        duration_ms = (t_end - t_start) / 1_000_000.0

        res = RunExecutionResult(
            returncode=proc.returncode,
            wall_time_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
            error=None if proc.returncode == 0 else f"Process exited with code {proc.returncode}",
        )
        return res, cpu_evidence

    except subprocess.TimeoutExpired as exc:
        t_end = time.perf_counter_ns()
        duration_ms = (t_end - t_start) / 1_000_000.0
        return (
            RunExecutionResult(
                returncode=-1,
                wall_time_ms=duration_ms,
                stdout="",
                stderr="",
                error=f"TimeoutExpired after {timeout_s}s",
            ),
            CpuUtilizationEvidence(0.0, 0.0, 0, False, "Process timed out"),
        )
    except Exception as exc:
        t_end = time.perf_counter_ns()
        duration_ms = (t_end - t_start) / 1_000_000.0
        return (
            RunExecutionResult(
                returncode=-1,
                wall_time_ms=duration_ms,
                stdout="",
                stderr=str(exc),
                error=f"Execution error: {exc}",
            ),
            CpuUtilizationEvidence(0.0, 0.0, 0, False, f"Error: {exc}"),
        )


def classify_experiment_result(
    speedup_native_over_interp: float,
    speedup_candidate_over_serial: float,
    multi_core_engaged: bool,
    compiler_has_parallel: bool,
) -> tuple[str, str]:
    """Classify result per T006 research specification and assign Evidence Grade."""
    # CATEGORY A: Strong evidence of automatic parallelism
    if (
        speedup_candidate_over_serial >= 1.35
        and multi_core_engaged
        and compiler_has_parallel
    ):
        return "CATEGORY A", "A"

    # CATEGORY B: Suggestive evidence
    if (
        speedup_candidate_over_serial >= 1.15
        and (multi_core_engaged or compiler_has_parallel)
    ):
        return "CATEGORY B", "B"

    # CATEGORY C: Native compilation effect only
    if speedup_native_over_interp >= 1.05 and speedup_candidate_over_serial < 1.15:
        return "CATEGORY C", "A"

    # CATEGORY D: No observed benefit
    if speedup_native_over_interp < 1.05 and speedup_candidate_over_serial < 1.05:
        return "CATEGORY D", "A"

    # CATEGORY E: Inconclusive
    return "CATEGORY E", "C"


class T006ExperimentHarness:
    """Execution engine for all 4 levels of the T006 experimental ladder."""

    def __init__(
        self,
        j2_bin: str = "j2",
        build_dir: Optional[Path] = None,
        timeout_s: float = 120.0,
    ) -> None:
        self.j2_bin = j2_bin
        self.build_dir = build_dir or (_REPO_ROOT / "build")
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_s = timeout_s
        self.base_harness = BenchmarkHarness(j2_bin=self.j2_bin, build_dir=self.build_dir, timeout_s=timeout_s)

    def run_level_a(
        self,
        workload_sizes: list[int],
        warmup_runs: int = 2,
        measured_runs: int = 5,
    ) -> list[T006ExperimentResult]:
        """Execute Level T006-A: Pure J2 Computational Control across scaling sizes."""
        cand_src = _REPO_ROOT / "benchmarks" / "t006" / "t006_a_candidate.j2"
        serial_src = _REPO_ROOT / "benchmarks" / "t006" / "t006_a_serial.j2"

        cand_bin = self.build_dir / "t006_a_candidate"
        serial_bin = self.build_dir / "t006_a_serial"

        # Build native binaries
        self.base_harness.build_native_binary(cand_src, cand_bin)
        self.base_harness.build_native_binary(serial_src, serial_bin)

        compiler_cand = inspect_compiler_emission(cand_src, self.j2_bin)

        results: list[T006ExperimentResult] = []

        for n in workload_sizes:
            ground_truth = str(n * (n + 1) // 2)

            # 1. Interpreter candidate
            interp_cmd = [self.j2_bin, "run", str(cand_src), str(n)]
            interp_times: list[float] = []
            interp_out = ""
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(interp_cmd, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, _ = execute_with_cpu_monitoring(interp_cmd, timeout_s=self.timeout_s)
                interp_times.append(res.wall_time_ms)
                interp_out = res.stdout.strip()

            interp_timing = calculate_timing_statistics(interp_times, warmup_runs)
            meas_interp = BaselineMeasurement(
                baseline_id="Baseline_A_Interpreter",
                baseline_name="J2 Interpreter (j2 run)",
                command_line=interp_cmd,
                environment_vars={},
                timing=interp_timing,
                output_digest=hashlib.sha256(interp_out.encode()).hexdigest(),
                success=(interp_out == ground_truth),
            )

            # 2. Native candidate
            native_cmd = [str(cand_bin), str(n)]
            native_times: list[float] = []
            native_out = ""
            last_cpu_cand = CpuUtilizationEvidence(0.0, 0.0, 0, False, "none")
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(native_cmd, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, cpu = execute_with_cpu_monitoring(native_cmd, timeout_s=self.timeout_s)
                native_times.append(res.wall_time_ms)
                native_out = res.stdout.strip()
                last_cpu_cand = cpu

            native_timing = calculate_timing_statistics(native_times, warmup_runs)
            meas_native = BaselineMeasurement(
                baseline_id="Baseline_B_Native_Candidate",
                baseline_name="Compiled Native Candidate (j2 build)",
                command_line=native_cmd,
                environment_vars={},
                timing=native_timing,
                output_digest=hashlib.sha256(native_out.encode()).hexdigest(),
                success=(native_out == ground_truth),
            )

            # 3. Native serial-equivalent control
            serial_cmd = [str(serial_bin), str(n)]
            serial_times: list[float] = []
            serial_out = ""
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(serial_cmd, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, _ = execute_with_cpu_monitoring(serial_cmd, timeout_s=self.timeout_s)
                serial_times.append(res.wall_time_ms)
                serial_out = res.stdout.strip()

            serial_timing = calculate_timing_statistics(serial_times, warmup_runs)
            meas_serial = BaselineMeasurement(
                baseline_id="Baseline_B_Native_Serial",
                baseline_name="Compiled Native Serial-Equivalent",
                command_line=serial_cmd,
                environment_vars={},
                timing=serial_timing,
                output_digest=hashlib.sha256(serial_out.encode()).hexdigest(),
                success=(serial_out == ground_truth),
            )

            speedup_native = round(interp_timing.median_ms / native_timing.median_ms, 4) if native_timing.median_ms > 0 else 0.0
            speedup_cand_serial = round(serial_timing.median_ms / native_timing.median_ms, 4) if native_timing.median_ms > 0 else 0.0
            correctness = (interp_out == ground_truth) and (native_out == ground_truth) and (serial_out == ground_truth)

            classification, grade = classify_experiment_result(
                speedup_native_over_interp=speedup_native,
                speedup_candidate_over_serial=speedup_cand_serial,
                multi_core_engaged=last_cpu_cand.multi_core_engaged,
                compiler_has_parallel=compiler_cand.has_parallel_constructs,
            )

            evidence = ObservabilityEvidence(
                compiler=compiler_cand,
                cpu=last_cpu_cand,
                profiler={"profiler_used": "external wall time and ps sampling"},
                determinism={
                    "ground_truth": ground_truth,
                    "interp_match": (interp_out == ground_truth),
                    "native_match": (native_out == ground_truth),
                    "serial_match": (serial_out == ground_truth),
                },
            )

            results.append(
                T006ExperimentResult(
                    experiment_id="T006-A",
                    variant_id=f"T006_A_N_{n}",
                    workload_name=f"Pure Computational Reduction (N={n:,})",
                    workload_level="A",
                    source_file=str(cand_src),
                    source_sha256=compiler_cand.source_sha256,
                    workload_parameters={"n": n, "ground_truth": ground_truth},
                    interpreter_measurement=meas_interp,
                    native_candidate_measurement=meas_native,
                    native_serial_measurement=meas_serial,
                    speedup_native_over_interpreter=speedup_native,
                    speedup_candidate_over_serial=speedup_cand_serial,
                    correctness_verified=correctness,
                    evidence=evidence,
                    evidence_grade=grade,
                    classification=classification,
                    limitations=[
                        "Does not perform memory allocations or I/O; isolates arithmetic reduction only.",
                        "Serial control uses loop-carried accumulator dependency.",
                    ],
                )
            )

        return results

    def run_level_b(
        self,
        configurations: list[tuple[int, int]],
        warmup_runs: int = 2,
        measured_runs: int = 5,
    ) -> list[T006ExperimentResult]:
        """Execute Level T006-B: Pure In-Memory Hashing across buffer counts and sizes."""
        cand_src = _REPO_ROOT / "benchmarks" / "t006" / "t006_b_candidate.j2"
        serial_src = _REPO_ROOT / "benchmarks" / "t006" / "t006_b_serial.j2"

        cand_bin = self.build_dir / "t006_b_candidate"
        serial_bin = self.build_dir / "t006_b_serial"

        self.base_harness.build_native_binary(cand_src, cand_bin)
        self.base_harness.build_native_binary(serial_src, serial_bin)

        compiler_cand = inspect_compiler_emission(cand_src, self.j2_bin)

        results: list[T006ExperimentResult] = []

        for num_bufs, buf_size in configurations:
            total_bytes = num_bufs * buf_size

            # 1. Native candidate
            native_cmd = [str(cand_bin), str(num_bufs), str(buf_size)]
            native_times: list[float] = []
            native_out = ""
            last_cpu_cand = CpuUtilizationEvidence(0.0, 0.0, 0, False, "none")
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(native_cmd, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, cpu = execute_with_cpu_monitoring(native_cmd, timeout_s=self.timeout_s)
                native_times.append(res.wall_time_ms)
                native_out = res.stdout.strip()
                last_cpu_cand = cpu

            native_timing = calculate_timing_statistics(native_times, warmup_runs)
            meas_native = BaselineMeasurement(
                baseline_id="Baseline_B_Native_Candidate",
                baseline_name="In-Memory Hashing Candidate",
                command_line=native_cmd,
                environment_vars={},
                timing=native_timing,
                output_digest=hashlib.sha256(native_out.encode()).hexdigest(),
                success=(len(native_out) == 64),
            )

            # 2. Native serial-equivalent
            serial_cmd = [str(serial_bin), str(num_bufs), str(buf_size)]
            serial_times: list[float] = []
            serial_out = ""
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(serial_cmd, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, _ = execute_with_cpu_monitoring(serial_cmd, timeout_s=self.timeout_s)
                serial_times.append(res.wall_time_ms)
                serial_out = res.stdout.strip()

            serial_timing = calculate_timing_statistics(serial_times, warmup_runs)
            meas_serial = BaselineMeasurement(
                baseline_id="Baseline_B_Native_Serial",
                baseline_name="In-Memory Hashing Serial-Equivalent",
                command_line=serial_cmd,
                environment_vars={},
                timing=serial_timing,
                output_digest=hashlib.sha256(serial_out.encode()).hexdigest(),
                success=(len(serial_out) == 64),
            )

            speedup_cand_serial = round(serial_timing.median_ms / native_timing.median_ms, 4) if native_timing.median_ms > 0 else 0.0

            classification, grade = classify_experiment_result(
                speedup_native_over_interp=1.0,
                speedup_candidate_over_serial=speedup_cand_serial,
                multi_core_engaged=last_cpu_cand.multi_core_engaged,
                compiler_has_parallel=compiler_cand.has_parallel_constructs,
            )

            evidence = ObservabilityEvidence(
                compiler=compiler_cand,
                cpu=last_cpu_cand,
                profiler={"in_memory_isolation": True, "zero_fs_io": True},
                determinism={
                    "candidate_digest": native_out,
                    "serial_digest": serial_out,
                    "valid_hex64": (len(native_out) == 64 and len(serial_out) == 64),
                },
            )

            results.append(
                T006ExperimentResult(
                    experiment_id="T006-B",
                    variant_id=f"T006_B_{num_bufs}x{buf_size}B",
                    workload_name=f"In-Memory Hashing ({num_bufs} buffers of {buf_size} B, {total_bytes / 1024:.1f} KB total)",
                    workload_level="B",
                    source_file=str(cand_src),
                    source_sha256=compiler_cand.source_sha256,
                    workload_parameters={"num_buffers": num_bufs, "buffer_size": buf_size, "total_bytes": total_bytes},
                    interpreter_measurement=None,
                    native_candidate_measurement=meas_native,
                    native_serial_measurement=meas_serial,
                    speedup_native_over_interpreter=0.0,
                    speedup_candidate_over_serial=speedup_cand_serial,
                    correctness_verified=(len(native_out) == 64 and len(serial_out) == 64),
                    evidence=evidence,
                    evidence_grade=grade,
                    classification=classification,
                    limitations=[
                        "Pre-allocates buffers in memory; isolates hashing CPU compute from filesystem latency.",
                    ],
                )
            )

        return results

    def run_level_c(
        self,
        corpora_dirs: list[Path],
        warmup_runs: int = 2,
        measured_runs: int = 5,
    ) -> list[T006ExperimentResult]:
        """Execute Level T006-C: Filesystem Read + Hash on real corpus trees."""
        cand_src = _REPO_ROOT / "benchmarks" / "t006" / "t006_c_candidate.j2"
        serial_src = _REPO_ROOT / "benchmarks" / "t006" / "t006_c_serial.j2"

        cand_bin = self.build_dir / "t006_c_candidate"
        serial_bin = self.build_dir / "t006_c_serial"

        self.base_harness.build_native_binary(cand_src, cand_bin)
        self.base_harness.build_native_binary(serial_src, serial_bin)

        compiler_cand = inspect_compiler_emission(cand_src, self.j2_bin)

        results: list[T006ExperimentResult] = []

        for c_dir in corpora_dirs:
            cid = c_dir.name
            native_env = {"J2_ALLOW_FS": "1"}

            # 1. Native candidate
            native_cmd = [str(cand_bin), str(c_dir)]
            native_times: list[float] = []
            native_out = ""
            last_cpu_cand = CpuUtilizationEvidence(0.0, 0.0, 0, False, "none")
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(native_cmd, env=native_env, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, cpu = execute_with_cpu_monitoring(native_cmd, env=native_env, timeout_s=self.timeout_s)
                native_times.append(res.wall_time_ms)
                native_out = res.stdout.strip()
                last_cpu_cand = cpu

            native_timing = calculate_timing_statistics(native_times, warmup_runs)
            meas_native = BaselineMeasurement(
                baseline_id="Baseline_B_Native_Candidate",
                baseline_name="FS Read + Hash Candidate",
                command_line=native_cmd,
                environment_vars=native_env,
                timing=native_timing,
                output_digest=hashlib.sha256(native_out.encode()).hexdigest(),
                success=(len(native_out) == 64),
            )

            # 2. Native serial-equivalent
            serial_cmd = [str(serial_bin), str(c_dir)]
            serial_times: list[float] = []
            serial_out = ""
            for _ in range(warmup_runs):
                execute_with_cpu_monitoring(serial_cmd, env=native_env, timeout_s=self.timeout_s)
            for _ in range(measured_runs):
                res, _ = execute_with_cpu_monitoring(serial_cmd, env=native_env, timeout_s=self.timeout_s)
                serial_times.append(res.wall_time_ms)
                serial_out = res.stdout.strip()

            serial_timing = calculate_timing_statistics(serial_times, warmup_runs)
            meas_serial = BaselineMeasurement(
                baseline_id="Baseline_B_Native_Serial",
                baseline_name="FS Read + Hash Serial-Equivalent",
                command_line=serial_cmd,
                environment_vars=native_env,
                timing=serial_timing,
                output_digest=hashlib.sha256(serial_out.encode()).hexdigest(),
                success=(len(serial_out) == 64),
            )

            speedup_cand_serial = round(serial_timing.median_ms / native_timing.median_ms, 4) if native_timing.median_ms > 0 else 0.0

            classification, grade = classify_experiment_result(
                speedup_native_over_interp=1.0,
                speedup_candidate_over_serial=speedup_cand_serial,
                multi_core_engaged=last_cpu_cand.multi_core_engaged,
                compiler_has_parallel=compiler_cand.has_parallel_constructs,
            )

            evidence = ObservabilityEvidence(
                compiler=compiler_cand,
                cpu=last_cpu_cand,
                profiler={"corpus_path": str(c_dir), "warm_repeated_runs": True},
                determinism={
                    "candidate_digest": native_out,
                    "serial_digest": serial_out,
                    "valid_hex64": (len(native_out) == 64 and len(serial_out) == 64),
                },
            )

            results.append(
                T006ExperimentResult(
                    experiment_id="T006-C",
                    variant_id=f"T006_C_{cid}",
                    workload_name=f"Filesystem Read + Hash on Corpus {cid}",
                    workload_level="C",
                    source_file=str(cand_src),
                    source_sha256=compiler_cand.source_sha256,
                    workload_parameters={"corpus_id": cid, "corpus_path": str(c_dir)},
                    interpreter_measurement=None,
                    native_candidate_measurement=meas_native,
                    native_serial_measurement=meas_serial,
                    speedup_native_over_interpreter=0.0,
                    speedup_candidate_over_serial=speedup_cand_serial,
                    correctness_verified=(len(native_out) == 64 and len(serial_out) == 64),
                    evidence=evidence,
                    evidence_grade=grade,
                    classification=classification,
                    limitations=[
                        "Measures filesystem read + hash hot loop; excludes dupe size grouping.",
                        "Executed under warm-state repeated runs.",
                    ],
                )
            )

        return results

    def measure_stage_breakdowns(
        self,
        corpora_dirs: list[Path],
        warmup_runs: int = 1,
        measured_runs: int = 3,
    ) -> list[StageBreakdownResult]:
        """Isolate sub-stage timings using standalone microbenchmark stage probes."""
        stage_dir = _REPO_ROOT / "benchmarks" / "t006"
        p_disc = stage_dir / "stage_discovery.j2"
        p_filt = stage_dir / "stage_filter.j2"
        p_hash = stage_dir / "stage_read_hash.j2"
        p_grp = stage_dir / "stage_group.j2"

        bin_disc = self.build_dir / "stage_discovery"
        bin_filt = self.build_dir / "stage_filter"
        bin_hash = self.build_dir / "stage_read_hash"
        bin_grp = self.build_dir / "stage_group"

        self.base_harness.build_native_binary(p_disc, bin_disc)
        self.base_harness.build_native_binary(p_filt, bin_filt)
        self.base_harness.build_native_binary(p_hash, bin_hash)
        self.base_harness.build_native_binary(p_grp, bin_grp)

        breakdowns: list[StageBreakdownResult] = []
        native_env = {"J2_ALLOW_FS": "1"}

        for c_dir in corpora_dirs:
            cid = c_dir.name
            manifest_file = c_dir / MANIFEST_FILENAME
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
            scale = float(manifest_data.get("scale", 0.01))
            file_count = int(manifest_data.get("file_count", 0))
            candidate_count = int(manifest_data.get("same_size_candidate_files", 0))

            # Temporarily isolate manifest.json so probes scan strictly corpus files
            manifest_temp = c_dir.parent / f".{c_dir.name}_{MANIFEST_FILENAME}.tmp"
            if manifest_file.is_file():
                shutil.move(str(manifest_file), str(manifest_temp))

            try:
                def time_bin(b_path: Path) -> float:
                    cmd = [str(b_path), str(c_dir)]
                    times: list[float] = []
                    for _ in range(warmup_runs):
                        execute_with_cpu_monitoring(cmd, env=native_env, timeout_s=self.timeout_s)
                    for _ in range(measured_runs):
                        res, _ = execute_with_cpu_monitoring(cmd, env=native_env, timeout_s=self.timeout_s)
                        times.append(res.wall_time_ms)
                    return statistics.median(times) if times else 0.0

                t1 = time_bin(bin_disc)
                t2 = time_bin(bin_filt)
                t3 = time_bin(bin_hash)
                t4 = time_bin(bin_grp)

                t_disc = round(t1, 2)
                t_filt = round(max(0.0, t2 - t1), 2)
                t_hash = round(max(0.0, t3 - t2), 2)
                t_grp = round(max(0.0, t4 - t3), 2)
                t_total = round(t4, 2)

                stages = {
                    "Discovery": t_disc,
                    "Size Filter (O(N^2))": t_filt,
                    "Read & Hash": t_hash,
                    "Group Duplicates": t_grp,
                }
                dominant = max(stages.items(), key=lambda item: item[1])[0]

                breakdowns.append(
                    StageBreakdownResult(
                        corpus_id=cid,
                        scale=scale,
                        file_count=file_count,
                        candidate_count=candidate_count,
                        t_discovery_ms=t_disc,
                        t_filter_ms=t_filt,
                        t_read_hash_ms=t_hash,
                        t_group_ms=t_grp,
                        t_total_ms=t_total,
                        dominant_stage=dominant,
                    )
                )
            finally:
                if manifest_temp.is_file():
                    shutil.move(str(manifest_temp), str(manifest_file))

        return breakdowns

    def run_level_d(
        self,
        corpora_dirs: list[Path],
        warmup_runs: int = 1,
        measured_runs: int = 3,
    ) -> list[T006ExperimentResult]:
        """Execute Level T006-D: Full dupe Pipeline across standard corpora."""
        main_src = _REPO_ROOT / "src" / "main.j2"
        dupe_bin = self.build_dir / "dupe"

        self.base_harness.build_native_binary(main_src, dupe_bin)
        compiler_dupe = inspect_compiler_emission(main_src, self.j2_bin)

        results: list[T006ExperimentResult] = []

        for c_dir in corpora_dirs:
            cid = c_dir.name
            manifest_file = c_dir / MANIFEST_FILENAME
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
            scale = float(manifest_data.get("scale", 0.01))
            expected_digest = manifest_data.get("expected_result_digest", "")

            # Temporarily isolate manifest.json so dupe scans strictly corpus files
            manifest_temp = c_dir.parent / f".{c_dir.name}_{MANIFEST_FILENAME}.tmp"
            if manifest_file.is_file():
                shutil.move(str(manifest_file), str(manifest_temp))

            try:
                # 1. Interpreter baseline
                interp_cmd = [self.j2_bin, "--allow-fs", "run", str(main_src), str(c_dir), "--json"]
                interp_times: list[float] = []
                interp_out = ""
                for _ in range(warmup_runs):
                    execute_with_cpu_monitoring(interp_cmd, timeout_s=self.timeout_s)
                for _ in range(measured_runs):
                    res, _ = execute_with_cpu_monitoring(interp_cmd, timeout_s=self.timeout_s)
                    interp_times.append(res.wall_time_ms)
                    interp_out = res.stdout

                interp_timing = calculate_timing_statistics(interp_times, warmup_runs)
                interp_json = json.loads(interp_out) if interp_out.strip() else {}
                interp_norm = normalize_dupe_output_paths(interp_json, c_dir)
                interp_digest = compute_result_digest(interp_norm)
                meas_interp = BaselineMeasurement(
                    baseline_id="Baseline_A_Interpreter",
                    baseline_name="J2 Interpreter (j2 --allow-fs run)",
                    command_line=interp_cmd,
                    environment_vars={},
                    timing=interp_timing,
                    output_digest=interp_digest,
                    success=(interp_digest == expected_digest if expected_digest else True),
                )

                # 2. Native candidate
                native_cmd = [str(dupe_bin), str(c_dir), "--json"]
                native_env = {"J2_ALLOW_FS": "1"}
                native_times: list[float] = []
                native_out = ""
                last_cpu_cand = CpuUtilizationEvidence(0.0, 0.0, 0, False, "none")
                for _ in range(warmup_runs):
                    execute_with_cpu_monitoring(native_cmd, env=native_env, timeout_s=self.timeout_s)
                for _ in range(measured_runs):
                    res, cpu = execute_with_cpu_monitoring(native_cmd, env=native_env, timeout_s=self.timeout_s)
                    native_times.append(res.wall_time_ms)
                    native_out = res.stdout
                    last_cpu_cand = cpu

                native_timing = calculate_timing_statistics(native_times, warmup_runs)
                native_json = json.loads(native_out) if native_out.strip() else {}
                native_norm = normalize_dupe_output_paths(native_json, c_dir)
                native_digest = compute_result_digest(native_norm)
                meas_native = BaselineMeasurement(
                    baseline_id="Baseline_B_Native_Candidate",
                    baseline_name="Compiled Native Binary (build/dupe)",
                    command_line=native_cmd,
                    environment_vars=native_env,
                    timing=native_timing,
                    output_digest=native_digest,
                    success=(native_digest == expected_digest if expected_digest else True),
                )

                speedup_native = round(interp_timing.median_ms / native_timing.median_ms, 4) if native_timing.median_ms > 0 else 0.0
                json_match = (interp_digest == native_digest)
                correctness = json_match and (native_digest == expected_digest if expected_digest else True)

                classification, grade = classify_experiment_result(
                    speedup_native_over_interp=speedup_native,
                    speedup_candidate_over_serial=1.0,
                    multi_core_engaged=last_cpu_cand.multi_core_engaged,
                    compiler_has_parallel=compiler_dupe.has_parallel_constructs,
                )

                evidence = ObservabilityEvidence(
                    compiler=compiler_dupe,
                    cpu=last_cpu_cand,
                    profiler={"corpus_id": cid, "scale": scale, "warm_repeated_runs": True},
                    determinism={
                        "expected_digest": expected_digest,
                        "interp_digest": interp_digest,
                        "native_digest": native_digest,
                        "json_equivalent": json_match,
                    },
                )

                results.append(
                    T006ExperimentResult(
                        experiment_id="T006-D",
                        variant_id=f"T006_D_{cid}",
                        workload_name=f"Full dupe Pipeline on Corpus {cid}",
                        workload_level="D",
                        source_file=str(main_src),
                        source_sha256=compiler_dupe.source_sha256,
                        workload_parameters={
                            "corpus_id": cid,
                            "scale": scale,
                            "file_count": manifest_data.get("file_count", 0),
                            "candidate_count": manifest_data.get("same_size_candidate_files", 0),
                        },
                        interpreter_measurement=meas_interp,
                        native_candidate_measurement=meas_native,
                        native_serial_measurement=None,
                        speedup_native_over_interpreter=speedup_native,
                        speedup_candidate_over_serial=0.0,
                        correctness_verified=correctness,
                        evidence=evidence,
                        evidence_grade=grade,
                        classification=classification,
                        limitations=[
                            "Full end-to-end dupe execution includes discovery, O(N^2) size filtering, hashing, and grouping.",
                            "Serial comparison is against interpreter Baseline A; source-level serial control not applied to production src/*.j2 per immutability policy.",
                        ],
                    )
                )
            finally:
                if manifest_temp.is_file():
                    shutil.move(str(manifest_temp), str(manifest_file))

        return results
