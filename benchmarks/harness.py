"""Benchmark execution harness for dupe (TASK T005).

Provides:
- Machine and provenance metadata logging (OS, kernel, CPU, RAM, runner ID, J2 version, commit SHA).
- High-precision external wall-clock timing using time.perf_counter_ns().
- Explicit interpreter (Baseline A), native binary (Baseline B), and pure J2 control (Baseline C) executions.
- Pre-flight corpus manifest validation.
- Output JSON bit-for-bit equivalence checking and expected digest verification.
- Warm-up and repeated iteration protocols with full raw timing data preservation.
- Statistical aggregation (median, mean, min, max, stddev, variance) and derived throughput rates.
- Failure preservation (capturing non-zero returncodes, stdout, stderr, and timeouts).
- Compiler backend inspection via `j2 emit-native`.
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
import time
from typing import Any, Callable, Optional

# Resolve repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.generator.manifest import (
    MANIFEST_FILENAME,
    Manifest,
    compute_result_digest,
    format_deterministic_json,
    validate_manifest,
)


@dataclass
class PlatformProvenance:
    """Hardware, OS, runtime, and git environment metadata."""
    system: str
    release: str
    machine: str
    cpu_count: int
    ram_bytes: Optional[int]
    ram_gb: Optional[float]
    runner_id: str
    git_commit: str
    j2_version: str
    j2_path: str
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_git_commit(cwd: Optional[Path] = None) -> str:
    """Retrieve current git commit SHA."""
    target_cwd = cwd or _REPO_ROOT
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_j2_version(j2_bin: str = "j2") -> str:
    """Retrieve exact J2 version output."""
    try:
        res = subprocess.run(
            [j2_bin, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_total_ram_bytes() -> Optional[int]:
    """Retrieve total system RAM in bytes across macOS, Linux, and Windows."""
    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            return int(out.strip())
        elif sys.platform.startswith("linux"):
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        # Value in kB
                        kb = int(line.split()[1])
                        return kb * 1024
        elif sys.platform == "win32":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys)
    except Exception:
        pass
    return None


def collect_platform_provenance(j2_bin: str = "j2") -> PlatformProvenance:
    """Capture full hardware, OS, toolchain, and repository provenance."""
    ram_bytes = get_total_ram_bytes()
    ram_gb = round(ram_bytes / (1024 ** 3), 2) if ram_bytes else None

    runner_id = (
        os.environ.get("GITHUB_RUN_ID")
        or os.environ.get("RUNNER_NAME")
        or platform.node()
        or "local"
    )

    j2_path_resolved = shutil.which(j2_bin) or j2_bin

    return PlatformProvenance(
        system=platform.system(),
        release=platform.release(),
        machine=platform.machine(),
        cpu_count=os.cpu_count() or 1,
        ram_bytes=ram_bytes,
        ram_gb=ram_gb,
        runner_id=str(runner_id),
        git_commit=get_git_commit(),
        j2_version=get_j2_version(j2_bin),
        j2_path=j2_path_resolved,
        timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


@dataclass
class RunExecutionResult:
    """Individual execution run result."""
    returncode: int
    wall_time_ms: float
    stdout: str
    stderr: str
    error: Optional[str] = None


@dataclass
class TimingStatistics:
    """Statistical metrics for repeated benchmark executions."""
    iterations: int
    warmup_runs: int
    raw_wall_time_ms: list[float]
    median_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    stddev_ms: float
    variance_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_timing_statistics(
    measured_times_ms: list[float], warmup_runs: int = 0
) -> TimingStatistics:
    """Compute standard statistical metrics over raw wall-clock timings."""
    if not measured_times_ms:
        raise ValueError("Cannot calculate statistics over empty timing list")

    n = len(measured_times_ms)
    med = statistics.median(measured_times_ms)
    avg = statistics.mean(measured_times_ms)
    lo = min(measured_times_ms)
    hi = max(measured_times_ms)
    std = statistics.stdev(measured_times_ms) if n > 1 else 0.0
    var = statistics.variance(measured_times_ms) if n > 1 else 0.0

    return TimingStatistics(
        iterations=n,
        warmup_runs=warmup_runs,
        raw_wall_time_ms=[round(t, 4) for t in measured_times_ms],
        median_ms=round(med, 4),
        mean_ms=round(avg, 4),
        min_ms=round(lo, 4),
        max_ms=round(hi, 4),
        stddev_ms=round(std, 4),
        variance_ms=round(var, 4),
    )


def execute_command_with_timing(
    cmd: list[str],
    env: Optional[dict[str, str]] = None,
    cwd: Optional[Path] = None,
    timeout_s: float = 120.0,
) -> RunExecutionResult:
    """Execute a command line externally and measure exact wall-clock duration in ms."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)

    t_start = time.perf_counter_ns()
    try:
        proc = subprocess.run(
            cmd,
            env=full_env,
            cwd=cwd or _REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        t_end = time.perf_counter_ns()
        duration_ms = (t_end - t_start) / 1_000_000.0
        return RunExecutionResult(
            returncode=proc.returncode,
            wall_time_ms=duration_ms,
            stdout=proc.stdout,
            stderr=proc.stderr,
            error=None if proc.returncode == 0 else f"Process exited with code {proc.returncode}",
        )
    except subprocess.TimeoutExpired as exc:
        t_end = time.perf_counter_ns()
        duration_ms = (t_end - t_start) / 1_000_000.0
        return RunExecutionResult(
            returncode=-1,
            wall_time_ms=duration_ms,
            stdout=exc.stdout or "" if isinstance(exc.stdout, str) else "",
            stderr=exc.stderr or "" if isinstance(exc.stderr, str) else "",
            error=f"TimeoutExpired after {timeout_s}s",
        )
    except Exception as exc:
        t_end = time.perf_counter_ns()
        duration_ms = (t_end - t_start) / 1_000_000.0
        return RunExecutionResult(
            returncode=-1,
            wall_time_ms=duration_ms,
            stdout="",
            stderr=str(exc),
            error=f"Execution failed: {exc}",
        )


@dataclass
class BaselineWorkloadMetrics:
    """Metrics extracted from dupe execution output."""
    files_scanned: int
    candidate_files: int
    bytes_hashed: int
    duplicate_groups: int
    duplicate_files: int
    reclaimable_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_workload_metrics(
    parsed_json: dict[str, Any], corpus_manifest: Optional[Manifest] = None
) -> BaselineWorkloadMetrics:
    """Extract standard workload metrics from dupe JSON output and optional manifest."""
    files_scanned = int(parsed_json.get("files_scanned", 0))
    candidate_files = int(parsed_json.get("hash_candidates", 0))
    groups = parsed_json.get("duplicate_groups", [])
    duplicate_groups = len(groups)
    duplicate_files = sum(len(g.get("files", [])) for g in groups)
    reclaimable_bytes = int(parsed_json.get("reclaimable_bytes", 0))

    # Calculate total bytes hashed
    if corpus_manifest is not None and candidate_files == corpus_manifest.same_size_candidate_files:
        # In exact candidate reduction, all candidates are read and hashed
        # If all files are candidates (like C5), bytes_hashed = total_bytes
        # Otherwise sum from duplicate groups + unique same-size files
        bytes_hashed = sum(g.get("size", 0) * len(g.get("files", [])) for g in groups)
    else:
        bytes_hashed = sum(g.get("size", 0) * len(g.get("files", [])) for g in groups)

    return BaselineWorkloadMetrics(
        files_scanned=files_scanned,
        candidate_files=candidate_files,
        bytes_hashed=bytes_hashed,
        duplicate_groups=duplicate_groups,
        duplicate_files=duplicate_files,
        reclaimable_bytes=reclaimable_bytes,
    )


def normalize_dupe_output_paths(
    dupe_json: dict[str, Any], corpus_root: Path
) -> dict[str, Any]:
    """Normalize file paths in dupe JSON output to POSIX paths relative to corpus_root.

    This matches the reference oracle representation used to compute
    manifest.expected_result_digest, allowing deterministic digest comparison
    independent of absolute working directory prefixes.
    """
    resolved_root = corpus_root.resolve()
    normalized = dict(dupe_json)
    normalized_groups = []
    for group in dupe_json.get("duplicate_groups", []):
        g = dict(group)
        norm_files = []
        for f in group.get("files", []):
            p = Path(f).resolve()
            try:
                rel = p.relative_to(resolved_root).as_posix()
            except ValueError:
                try:
                    rel = (corpus_root / f).resolve().relative_to(resolved_root).as_posix()
                except Exception:
                    rel = Path(f).as_posix()
            norm_files.append(rel)
        g["files"] = norm_files
        normalized_groups.append(g)
    normalized["duplicate_groups"] = normalized_groups
    return normalized


@dataclass
class BaselineMeasurement:
    """Full benchmark measurement for a single baseline execution leg."""
    baseline_id: str  # "Baseline_A", "Baseline_B", "Baseline_C"
    baseline_name: str
    command_line: list[str]
    environment_vars: dict[str, str]
    timing: TimingStatistics
    metrics: Optional[BaselineWorkloadMetrics] = None
    output_digest: Optional[str] = None
    build_time_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class CorpusComparisonResult:
    """Comparison result for a single corpus across Baseline A and Baseline B."""
    corpus_id: str
    corpus_manifest_sha256: str
    scale: float
    baseline_a_interpreter: BaselineMeasurement
    baseline_b_native: BaselineMeasurement
    direct_json_match: bool
    digest_matches_manifest: bool
    expected_digest: str
    actual_digest: str
    native_speedup_factor: float
    files_per_sec_interpreter: float
    files_per_sec_native: float
    candidates_per_sec_interpreter: float
    candidates_per_sec_native: float
    mb_per_sec_interpreter: float
    mb_per_sec_native: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PureControlResult:
    """Pure J2 automatic-parallelism control benchmark result (Baseline C)."""
    program_source: str
    ground_truth_result: str
    build_time_ms: float
    interpreter_measurement: BaselineMeasurement
    native_measurement: BaselineMeasurement
    correctness_verified: bool
    native_speedup_factor: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FullBenchmarkReport:
    """Top-level machine-readable benchmark report."""
    schema_version: int
    task_id: str
    provenance: PlatformProvenance
    pure_control_baseline_c: Optional[PureControlResult]
    corpus_comparisons: list[CorpusComparisonResult]
    compiler_inspection: dict[str, Any]
    summary_conclusions: list[str]
    unresolved_limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class BenchmarkHarness:
    """Orchestrator for executing, verifying, and measuring dupe baselines."""

    def __init__(
        self,
        j2_bin: str = "j2",
        dupe_source_path: Optional[Path] = None,
        build_dir: Optional[Path] = None,
        timeout_s: float = 180.0,
    ) -> None:
        self.j2_bin = j2_bin
        self.dupe_source = dupe_source_path or (_REPO_ROOT / "src" / "main.j2")
        self.build_dir = build_dir or (_REPO_ROOT / "build")
        self.timeout_s = timeout_s
        self.provenance = collect_platform_provenance(j2_bin)

    def verify_corpus(self, corpus_path: Path) -> tuple[bool, Manifest, list[str]]:
        """Pre-flight validation of corpus before every benchmark run."""
        manifest_file = corpus_path / MANIFEST_FILENAME
        if not manifest_file.is_file():
            return False, None, [f"Manifest file not found: {manifest_file}"]

        is_valid, errors = validate_manifest(corpus_path, raise_on_error=False)
        if not is_valid:
            return False, None, errors

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest = Manifest.from_dict(manifest_data)
        return True, manifest, []

    def build_native_binary(
        self, source_path: Path, output_binary_path: Path
    ) -> tuple[float, RunExecutionResult]:
        """Compile J2 source into genuine native binary and record build wall-clock time."""
        output_binary_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [self.j2_bin, "build", str(source_path), "-o", str(output_binary_path)]
        res = execute_command_with_timing(cmd, timeout_s=self.timeout_s)
        if res.returncode != 0:
            raise RuntimeError(
                f"Failed to build native binary '{output_binary_path}' from '{source_path}':\n"
                f"returncode: {res.returncode}\nstderr: {res.stderr}\nstdout: {res.stdout}"
            )
        return res.wall_time_ms, res

    def inspect_compiler_emission(self, source_path: Path) -> str:
        """Run `j2 emit-native` on source and capture backend source emission."""
        cmd = [self.j2_bin, "emit-native", str(source_path)]
        res = execute_command_with_timing(cmd, timeout_s=self.timeout_s)
        if res.returncode != 0:
            return f"FAILED (code {res.returncode}): {res.stderr}"
        return res.stdout

    def run_pure_control(
        self,
        control_source_path: Path,
        warmup_runs: int = 3,
        measured_runs: int = 7,
    ) -> PureControlResult:
        """Execute Baseline C (official pure computation parallelism control)."""
        ground_truth = "2000001000000"  # sum(1..2000000) = 2000000 * 2000001 / 2
        control_src = control_source_path.read_text(encoding="utf-8")

        # 1. Interpreter Baseline C
        interp_cmd = [self.j2_bin, "run", str(control_source_path)]
        for _ in range(warmup_runs):
            execute_command_with_timing(interp_cmd, timeout_s=self.timeout_s)

        interp_times: list[float] = []
        interp_stdout = ""
        for _ in range(measured_runs):
            res = execute_command_with_timing(interp_cmd, timeout_s=self.timeout_s)
            if res.returncode != 0:
                raise RuntimeError(f"Pure control interpreter run failed: {res.stderr}")
            interp_times.append(res.wall_time_ms)
            interp_stdout = res.stdout.strip()

        interp_timing = calculate_timing_statistics(interp_times, warmup_runs=warmup_runs)
        interp_meas = BaselineMeasurement(
            baseline_id="Baseline_C_Interpreter",
            baseline_name="Pure Control (Interpreter: j2 run)",
            command_line=interp_cmd,
            environment_vars={},
            timing=interp_timing,
            output_digest=hashlib.sha256(interp_stdout.encode("utf-8")).hexdigest(),
            success=(interp_stdout == ground_truth),
        )

        # 2. Native Baseline C
        native_bin = self.build_dir / "pure_control"
        build_time_ms, _ = self.build_native_binary(control_source_path, native_bin)

        native_cmd = [str(native_bin)]
        for _ in range(warmup_runs):
            execute_command_with_timing(native_cmd, timeout_s=self.timeout_s)

        native_times: list[float] = []
        native_stdout = ""
        for _ in range(measured_runs):
            res = execute_command_with_timing(native_cmd, timeout_s=self.timeout_s)
            if res.returncode != 0:
                raise RuntimeError(f"Pure control native run failed: {res.stderr}")
            native_times.append(res.wall_time_ms)
            native_stdout = res.stdout.strip()

        native_timing = calculate_timing_statistics(native_times, warmup_runs=warmup_runs)
        native_meas = BaselineMeasurement(
            baseline_id="Baseline_C_Native",
            baseline_name="Pure Control (Compiled Native: j2 build)",
            command_line=native_cmd,
            environment_vars={},
            timing=native_timing,
            build_time_ms=build_time_ms,
            output_digest=hashlib.sha256(native_stdout.encode("utf-8")).hexdigest(),
            success=(native_stdout == ground_truth),
        )

        correctness = (interp_stdout == ground_truth) and (native_stdout == ground_truth)
        speedup = (
            round(interp_timing.median_ms / native_timing.median_ms, 4)
            if native_timing.median_ms > 0
            else 0.0
        )

        return PureControlResult(
            program_source=control_src,
            ground_truth_result=ground_truth,
            build_time_ms=build_time_ms,
            interpreter_measurement=interp_meas,
            native_measurement=native_meas,
            correctness_verified=correctness,
            native_speedup_factor=speedup,
        )

    def measure_corpus_baselines(
        self,
        corpus_path: Path,
        warmup_runs: int = 1,
        measured_runs: int = 3,
        native_binary_path: Optional[Path] = None,
    ) -> CorpusComparisonResult:
        """Measure Baseline A (interpreter) and Baseline B (native binary) on a corpus."""
        # 1. Pre-flight manifest validation
        is_valid, manifest, errors = self.verify_corpus(corpus_path)
        if not is_valid:
            raise ValueError(f"Corpus verification FAILED for '{corpus_path}': {errors}")

        manifest_file = corpus_path / MANIFEST_FILENAME
        manifest_sha256 = hashlib.sha256(manifest_file.read_bytes()).hexdigest()

        # 2. Prepare native binary if not provided
        bin_path = native_binary_path or (self.build_dir / "dupe")
        build_time_ms: Optional[float] = None
        if not bin_path.is_file():
            build_time_ms, _ = self.build_native_binary(self.dupe_source, bin_path)

        # 3. Baseline A: Interpreter (`j2 --allow-fs src/main.j2 <corpus> --json`)
        interp_cmd = [
            self.j2_bin,
            "--allow-fs",
            str(self.dupe_source),
            str(corpus_path),
            "--json",
        ]

        for w_i in range(warmup_runs):
            w_res = execute_command_with_timing(interp_cmd, timeout_s=self.timeout_s)
            if w_res.returncode != 0:
                raise RuntimeError(
                    f"Baseline A (interpreter) warmup run {w_i+1}/{warmup_runs} failed on {corpus_path.name} "
                    f"(code {w_res.returncode}, time {w_res.wall_time_ms:.1f}ms):\n{w_res.stderr or w_res.error}"
                )

        interp_times: list[float] = []
        interp_last_res: Optional[RunExecutionResult] = None
        for m_i in range(measured_runs):
            res = execute_command_with_timing(interp_cmd, timeout_s=self.timeout_s)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Baseline A (interpreter) measured run {m_i+1}/{measured_runs} failed on {corpus_path.name} "
                    f"(code {res.returncode}, time {res.wall_time_ms:.1f}ms):\n{res.stderr or res.error}"
                )
            interp_times.append(res.wall_time_ms)
            interp_last_res = res

        interp_timing = calculate_timing_statistics(interp_times, warmup_runs=warmup_runs)
        interp_json_str = interp_last_res.stdout.strip() if interp_last_res else ""
        try:
            interp_json = json.loads(interp_json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Baseline A (interpreter) returned invalid JSON on {corpus_path.name}:\n"
                f"cmd: {interp_cmd}\n"
                f"duration_ms: {interp_last_res.wall_time_ms if interp_last_res else 'none'}\n"
                f"stdout: {repr(interp_last_res.stdout if interp_last_res else '')}\n"
                f"stderr: {repr(interp_last_res.stderr if interp_last_res else '')}\n"
                f"returncode: {interp_last_res.returncode if interp_last_res else 'none'}"
            ) from exc
        interp_digest = compute_result_digest(interp_json)
        norm_interp_json = normalize_dupe_output_paths(interp_json, corpus_path)
        norm_interp_digest = compute_result_digest(norm_interp_json)
        interp_metrics = extract_workload_metrics(interp_json, corpus_manifest=manifest)

        meas_a = BaselineMeasurement(
            baseline_id="Baseline_A_Interpreter",
            baseline_name="J2 Interpreter (j2 --allow-fs)",
            command_line=interp_cmd,
            environment_vars={},
            timing=interp_timing,
            metrics=interp_metrics,
            output_digest=norm_interp_digest,
            success=True,
        )

        # 4. Baseline B: Compiled Native (`J2_ALLOW_FS=1 ./build/dupe <corpus> --json`)
        native_cmd = [str(bin_path), str(corpus_path), "--json"]
        native_env = {"J2_ALLOW_FS": "1"}

        for w_i in range(warmup_runs):
            w_res = execute_command_with_timing(
                native_cmd, env=native_env, timeout_s=self.timeout_s
            )
            if w_res.returncode != 0:
                raise RuntimeError(
                    f"Baseline B (native) warmup run {w_i+1}/{warmup_runs} failed on {corpus_path.name} "
                    f"(code {w_res.returncode}, time {w_res.wall_time_ms:.1f}ms):\n{w_res.stderr or w_res.error}"
                )

        native_times: list[float] = []
        native_last_res: Optional[RunExecutionResult] = None
        for m_i in range(measured_runs):
            res = execute_command_with_timing(
                native_cmd, env=native_env, timeout_s=self.timeout_s
            )
            if res.returncode != 0:
                raise RuntimeError(
                    f"Baseline B (native) measured run {m_i+1}/{measured_runs} failed on {corpus_path.name} "
                    f"(code {res.returncode}, time {res.wall_time_ms:.1f}ms):\n{res.stderr or res.error}"
                )
            native_times.append(res.wall_time_ms)
            native_last_res = res

        native_timing = calculate_timing_statistics(native_times, warmup_runs=warmup_runs)
        native_json_str = native_last_res.stdout.strip() if native_last_res else ""
        try:
            native_json = json.loads(native_json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Baseline B (native) returned invalid JSON on {corpus_path.name}:\n"
                f"cmd: {native_cmd}\n"
                f"duration_ms: {native_last_res.wall_time_ms if native_last_res else 'none'}\n"
                f"stdout: {repr(native_last_res.stdout if native_last_res else '')}\n"
                f"stderr: {repr(native_last_res.stderr if native_last_res else '')}\n"
                f"returncode: {native_last_res.returncode if native_last_res else 'none'}"
            ) from exc
        native_digest = compute_result_digest(native_json)
        norm_native_json = normalize_dupe_output_paths(native_json, corpus_path)
        norm_native_digest = compute_result_digest(norm_native_json)
        native_metrics = extract_workload_metrics(native_json, corpus_manifest=manifest)

        meas_b = BaselineMeasurement(
            baseline_id="Baseline_B_Native",
            baseline_name="J2 Compiled Native Binary (J2_ALLOW_FS=1 ./build/dupe)",
            command_line=native_cmd,
            environment_vars=native_env,
            timing=native_timing,
            metrics=native_metrics,
            output_digest=norm_native_digest,
            build_time_ms=build_time_ms,
            success=True,
        )

        # 5. Output equivalence and manifest digest verification
        direct_match = (
            interp_json_str == native_json_str
            or format_deterministic_json(interp_json) == format_deterministic_json(native_json)
        )
        digest_matches = (
            norm_interp_digest == manifest.expected_result_digest
            and norm_native_digest == manifest.expected_result_digest
        )

        if not direct_match:
            raise ValueError(
                f"Determinism violation on {corpus_path.name}: "
                f"Baseline A output != Baseline B output!\n"
                f"Interp digest: {interp_digest}\nNative digest: {native_digest}"
            )
        if not digest_matches:
            raise ValueError(
                f"Soundness violation on {corpus_path.name}: "
                f"Actual normalized digest {norm_native_digest} does not match expected {manifest.expected_result_digest}!"
            )

        # 6. Derived throughput rates (using median wall time in seconds)
        sec_a = interp_timing.median_ms / 1000.0
        sec_b = native_timing.median_ms / 1000.0

        files_sec_a = round(interp_metrics.files_scanned / sec_a, 2) if sec_a > 0 else 0.0
        files_sec_b = round(native_metrics.files_scanned / sec_b, 2) if sec_b > 0 else 0.0

        cand_sec_a = round(interp_metrics.candidate_files / sec_a, 2) if sec_a > 0 else 0.0
        cand_sec_b = round(native_metrics.candidate_files / sec_b, 2) if sec_b > 0 else 0.0

        mb_sec_a = (
            round((interp_metrics.bytes_hashed / (1024 * 1024)) / sec_a, 2)
            if sec_a > 0
            else 0.0
        )
        mb_sec_b = (
            round((native_metrics.bytes_hashed / (1024 * 1024)) / sec_b, 2)
            if sec_b > 0
            else 0.0
        )

        speedup = round(sec_a / sec_b, 4) if sec_b > 0 else 0.0

        return CorpusComparisonResult(
            corpus_id=manifest.corpus_id,
            corpus_manifest_sha256=manifest_sha256,
            scale=manifest.scale,
            baseline_a_interpreter=meas_a,
            baseline_b_native=meas_b,
            direct_json_match=direct_match,
            digest_matches_manifest=digest_matches,
            expected_digest=manifest.expected_result_digest,
            actual_digest=norm_native_digest,
            native_speedup_factor=speedup,
            files_per_sec_interpreter=files_sec_a,
            files_per_sec_native=files_sec_b,
            candidates_per_sec_interpreter=cand_sec_a,
            candidates_per_sec_native=cand_sec_b,
            mb_per_sec_interpreter=mb_sec_a,
            mb_per_sec_native=mb_sec_b,
        )
