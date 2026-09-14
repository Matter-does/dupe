"""Engine adapter connecting GUI shell to the existing dupe J2 CLI engine.

Responsible for:
1. Engine binary resolution (native compiled binary or J2 interpreter).
2. Symmetrical command line construction conforming to T008 CLI contract.
3. Asynchronous execution in background thread without freezing UI event loop.
4. Exit-code, stdout, and stderr capture.
5. Established JSON schema parsing and error propagation.
6. Absolute non-reimplementation of analysis, hashing, or traversal logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_MAX_OUTPUT_BYTES = int(os.environ.get("DUPE_MAX_OUTPUT_BYTES", str(16 * 1024 * 1024)))


@dataclass(frozen=True)
class EngineResult:
    """Structured result returned by the dupe engine adapter."""
    success: bool
    workload: str
    target_path: str
    returncode: int
    data: dict[str, Any] | None
    raw_stdout: str
    raw_stderr: str
    error_message: str | None
    duration_seconds: float
    command_executed: list[str]


class EngineAdapter:
    """Adapter invoking the authoritative dupe CLI engine."""

    def __init__(
        self,
        *,
        native_bin: Path | str | None = None,
        j2_bin: Path | str | None = None,
        main_j2: Path | str | None = None,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    ) -> None:
        self.native_bin = Path(native_bin).resolve() if native_bin else (REPO_ROOT / "build" / "dupe")
        self.j2_bin = str(j2_bin) if j2_bin else (os.environ.get("J2_BIN") or shutil.which("j2") or "j2")
        self.main_j2 = Path(main_j2).resolve() if main_j2 else (REPO_ROOT / "src" / "main.j2")
        self.max_output_bytes = max_output_bytes

    def has_native_binary(self) -> bool:
        """Check whether genuine native compiled binary is available."""
        return self.native_bin.is_file() and os.access(self.native_bin, os.X_OK)

    def has_j2_interpreter(self) -> bool:
        """Check whether J2 interpreter is available."""
        resolved = shutil.which(self.j2_bin)
        if resolved:
            return True
        if Path(self.j2_bin).is_file() and os.access(self.j2_bin, os.X_OK):
            return True
        return False

    def resolve_engine_mode(self) -> tuple[str, list[str]]:
        """Resolve available engine command prefix.
        Returns (mode, base_cmd).
        Priority:
        1. Native binary (build/dupe)
        2. J2 interpreter (j2 --allow-fs src/main.j2)
        3. Unavailable (neither executable is present on disk)
        """
        if self.has_native_binary():
            return "native", [str(self.native_bin)]
        if self.has_j2_interpreter() and self.main_j2.is_file():
            return "interpreter", [str(self.j2_bin), "--allow-fs", str(self.main_j2)]
        fallback_cmd = [str(self.native_bin)] if self.native_bin else [str(self.j2_bin), "--allow-fs", str(self.main_j2)]
        return "unavailable", fallback_cmd

    def build_command(self, workload: str, target_path: str) -> list[str]:
        """Construct exact command line arguments according to T008 CLI contract.
        - Duplicate scan: dupe <path> --json
        - Checksum inventory: dupe checksum <path> --json
        """
        target_str = str(target_path).strip()
        _, base_cmd = self.resolve_engine_mode()

        if workload == "checksum":
            return base_cmd + ["checksum", target_str, "--json"]
        elif workload == "duplicate":
            return base_cmd + [target_str, "--json"]
        else:
            raise ValueError(f"Unknown workload: '{workload}'. Must be 'duplicate' or 'checksum'.")

    def run_analysis(
        self,
        workload: str,
        target_path: str,
        *,
        timeout: int = 300,
        env: dict[str, str] | None = None,
        max_output_bytes: int | None = None,
    ) -> EngineResult:
        """Execute dupe engine synchronously and parse structured JSON results."""
        target_str = str(target_path).strip()
        if not target_str:
            return EngineResult(
                success=False,
                workload=workload,
                target_path=target_str,
                returncode=1,
                data=None,
                raw_stdout="",
                raw_stderr="",
                error_message="No target directory specified.",
                duration_seconds=0.0,
                command_executed=[],
            )

        cmd = self.build_command(workload, target_str)
        run_env = os.environ.copy()
        run_env["J2_ALLOW_FS"] = "1"
        if env:
            run_env.update(env)

        limit = max_output_bytes if max_output_bytes is not None else self.max_output_bytes
        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                env=run_env,
                capture_output=True,
                timeout=timeout,
            )
            duration = time.perf_counter() - start_time

            raw_out = proc.stdout if isinstance(proc.stdout, bytes) else proc.stdout.encode("utf-8")
            raw_err = proc.stderr if isinstance(proc.stderr, bytes) else proc.stderr.encode("utf-8")

            if len(raw_out) > limit:
                return EngineResult(
                    success=False,
                    workload=workload,
                    target_path=target_str,
                    returncode=-1,
                    data=None,
                    raw_stdout="",
                    raw_stderr="",
                    error_message=f"Engine stdout exceeded maximum allowed limit of {limit} bytes.",
                    duration_seconds=duration,
                    command_executed=cmd,
                )

            stdout_text = raw_out.decode("utf-8", errors="replace").strip()
            stderr_text = raw_err.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                err_msg = stderr_text if stderr_text else (
                    stdout_text if stdout_text else f"Engine exited with status {proc.returncode}"
                )
                return EngineResult(
                    success=False,
                    workload=workload,
                    target_path=target_str,
                    returncode=proc.returncode,
                    data=None,
                    raw_stdout=stdout_text,
                    raw_stderr=stderr_text,
                    error_message=err_msg,
                    duration_seconds=duration,
                    command_executed=cmd,
                )

            # Parse established JSON schema
            try:
                data = json.loads(stdout_text)
            except json.JSONDecodeError as exc:
                return EngineResult(
                    success=False,
                    workload=workload,
                    target_path=target_str,
                    returncode=proc.returncode,
                    data=None,
                    raw_stdout=stdout_text,
                    raw_stderr=stderr_text,
                    error_message=f"Engine emitted malformed JSON: {exc}. Raw output: {stdout_text[:200]}",
                    duration_seconds=duration,
                    command_executed=cmd,
                )

            # Validate schema contract
            schema_err = self._validate_schema(workload, data)
            if schema_err:
                return EngineResult(
                    success=False,
                    workload=workload,
                    target_path=target_str,
                    returncode=proc.returncode,
                    data=data,
                    raw_stdout=stdout_text,
                    raw_stderr=stderr_text,
                    error_message=f"Invalid schema: {schema_err}",
                    duration_seconds=duration,
                    command_executed=cmd,
                )

            return EngineResult(
                success=True,
                workload=workload,
                target_path=target_str,
                returncode=0,
                data=data,
                raw_stdout=stdout_text,
                raw_stderr=stderr_text,
                error_message=None,
                duration_seconds=duration,
                command_executed=cmd,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start_time
            stdout_text = (exc.stdout or b"").decode("utf-8", errors="replace").strip() if isinstance(exc.stdout, bytes) else str(exc.stdout or "").strip()
            stderr_text = (exc.stderr or b"").decode("utf-8", errors="replace").strip() if isinstance(exc.stderr, bytes) else str(exc.stderr or "").strip()
            return EngineResult(
                success=False,
                workload=workload,
                target_path=target_str,
                returncode=-1,
                data=None,
                raw_stdout=stdout_text,
                raw_stderr=stderr_text,
                error_message=f"Execution timed out after {timeout} seconds.",
                duration_seconds=duration,
                command_executed=cmd,
            )
        except Exception as exc:
            duration = time.perf_counter() - start_time
            return EngineResult(
                success=False,
                workload=workload,
                target_path=target_str,
                returncode=-1,
                data=None,
                raw_stdout="",
                raw_stderr=str(exc),
                error_message=f"Failed to launch engine process: {exc}",
                duration_seconds=duration,
                command_executed=cmd,
            )

    def run_analysis_async(
        self,
        workload: str,
        target_path: str,
        on_complete: Callable[[EngineResult], None],
        *,
        timeout: int = 300,
        env: dict[str, str] | None = None,
        max_output_bytes: int | None = None,
    ) -> threading.Thread:
        """Run analysis in a background daemon thread to maintain UI responsiveness."""
        def worker() -> None:
            result = self.run_analysis(
                workload,
                target_path,
                timeout=timeout,
                env=env,
                max_output_bytes=max_output_bytes,
            )
            on_complete(result)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    @staticmethod
    def _is_strict_int(val: Any, min_val: int = 0) -> bool:
        """Verify val is a strict integer (not bool) satisfying min_val."""
        if not isinstance(val, int) or isinstance(val, bool):
            return False
        return val >= min_val

    @staticmethod
    def _is_valid_sha256(digest: Any) -> bool:
        """Verify digest is exactly 64 lowercase hexadecimal characters."""
        if not isinstance(digest, str) or len(digest) != 64:
            return False
        return all(c in "0123456789abcdef" for c in digest)

    @classmethod
    def _validate_schema(cls, workload: str, data: dict[str, Any]) -> str | None:
        """Verify output adheres strictly to established Phase 3 / T007 JSON schemas.

        Validates both structural shape and scalar types/constraints to prevent
        untrusted or malformed engine output from crashing presenter view models.
        """
        if not isinstance(data, dict):
            return "Output must be a JSON object"

        if workload == "duplicate":
            required_keys = {"files_scanned", "hash_candidates", "duplicate_groups", "reclaimable_bytes"}
            missing = required_keys - set(data.keys())
            if missing:
                return f"Missing required duplicate keys: {sorted(missing)}"

            if not cls._is_strict_int(data["files_scanned"]):
                return "'files_scanned' must be a non-negative integer"
            if not cls._is_strict_int(data["hash_candidates"]):
                return "'hash_candidates' must be a non-negative integer"
            if not cls._is_strict_int(data["reclaimable_bytes"]):
                return "'reclaimable_bytes' must be a non-negative integer"

            if not isinstance(data["duplicate_groups"], list):
                return "'duplicate_groups' must be a list"

            for idx, g in enumerate(data["duplicate_groups"]):
                if not isinstance(g, dict):
                    return f"Duplicate group {idx} is not an object"
                g_missing = {"hash", "size", "files", "reclaimable_bytes"} - set(g.keys())
                if g_missing:
                    return f"Duplicate group {idx} missing keys: {sorted(g_missing)}"

                if not cls._is_valid_sha256(g["hash"]):
                    return f"Duplicate group {idx} 'hash' must be a 64-character lowercase hexadecimal SHA-256 digest"
                if not cls._is_strict_int(g["size"]):
                    return f"Duplicate group {idx} 'size' must be a non-negative integer"
                if not cls._is_strict_int(g["reclaimable_bytes"]):
                    return f"Duplicate group {idx} 'reclaimable_bytes' must be a non-negative integer"
                if not isinstance(g["files"], list):
                    return f"Duplicate group {idx} 'files' must be a list"
                if len(g["files"]) < 1:
                    return f"Duplicate group {idx} 'files' must not be empty"
                for f_idx, f in enumerate(g["files"]):
                    if not isinstance(f, str):
                        return f"Duplicate group {idx} file {f_idx} is not a string"

        elif workload == "checksum":
            required_keys = {"schema_version", "workload", "root", "summary", "entries"}
            missing = required_keys - set(data.keys())
            if missing:
                return f"Missing required checksum keys: {sorted(missing)}"

            if not cls._is_strict_int(data["schema_version"], min_val=1):
                return "'schema_version' must be a positive integer"
            if data.get("workload") != "checksum_inventory":
                return f"Expected workload 'checksum_inventory', got '{data.get('workload')}'"
            if not isinstance(data.get("root"), str):
                return "'root' must be a string"

            summary = data.get("summary")
            if not isinstance(summary, dict) or "total_files" not in summary or "total_bytes" not in summary:
                return "'summary' must be an object with 'total_files' and 'total_bytes'"
            if not cls._is_strict_int(summary["total_files"]):
                return "'summary.total_files' must be a non-negative integer"
            if not cls._is_strict_int(summary["total_bytes"]):
                return "'summary.total_bytes' must be a non-negative integer"

            if not isinstance(data.get("entries"), list):
                return "'entries' must be a list"

            for idx, e in enumerate(data["entries"]):
                if not isinstance(e, dict):
                    return f"Checksum entry {idx} is not an object"
                e_missing = {"path", "size", "sha256"} - set(e.keys())
                if e_missing:
                    return f"Checksum entry {idx} missing keys: {sorted(e_missing)}"

                if not isinstance(e["path"], str):
                    return f"Checksum entry {idx} 'path' must be a string"
                if not cls._is_strict_int(e["size"]):
                    return f"Checksum entry {idx} 'size' must be a non-negative integer"
                if not cls._is_valid_sha256(e["sha256"]):
                    return f"Checksum entry {idx} 'sha256' must be a 64-character lowercase hexadecimal SHA-256 digest"

        return None
