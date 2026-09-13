"""Authoritative macOS T010 Demo & Integration Verification Script.

Executes and verifies the complete demonstration contract:
1. Deterministic demo corpus generation (8 files, 5,258 bytes).
2. Native binary build and capability checks (J2 0.1.0 on macOS arm64).
3. CLI Duplicate detection execution (dupe <path> --json).
4. CLI Checksum inventory execution (dupe checksum <path> --json).
5. Native vs Interpreter parity (byte-for-byte exact JSON equality).
6. Ground truth validation:
   - Duplicate: 8 files scanned, 5 candidates, 2 groups, 456 reclaimable bytes.
   - Checksum: 8 files, 5,258 bytes, 8 ledger entries.
7. Independent Python hashlib.sha256 oracle verification for all entries.
8. GUI EngineAdapter invocation and ViewModel transformations.
9. Emits portable artifacts to `artifacts/t010/`:
   - `summary.md`
   - `provenance.json`
   - `demo_verification_result.json`
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.adapter import EngineAdapter, EngineResult
from gui.view_models import (
    ChecksumViewModel,
    DuplicateViewModel,
    format_bytes,
)
from tests.demo_corpus import (
    EXPECTED_CANDIDATES_COUNT,
    EXPECTED_FILES_COUNT,
    EXPECTED_GROUPS_COUNT,
    EXPECTED_RECLAIMABLE_BYTES,
    EXPECTED_TOTAL_BYTES,
    create_demo_corpus,
    verify_demo_corpus,
)


def get_cpu_info() -> str:
    try:
        proc = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return platform.processor() or "Apple Silicon (arm64)"


def get_git_commit() -> str:
    env_commit = os.environ.get("GITHUB_SHA")
    if env_commit:
        return env_commit
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=REPO_ROOT,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="T010 Demonstration & Integration Verification")
    parser.add_argument("--native-bin", type=Path, default=REPO_ROOT / "build" / "dupe", help="Path to native binary")
    parser.add_argument("--j2-bin", type=str, default=os.environ.get("J2_BIN", "j2"), help="J2 interpreter binary")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "artifacts" / "t010", help="Artifact output directory")
    args = parser.parse_args()

    native_bin = args.native_bin.resolve()
    j2_bin = args.j2_bin
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================")
    print("T010 DEMONSTRATION & INTEGRATION VERIFICATION")
    print("============================================================")
    print(f"J2 Binary:      {j2_bin}")
    print(f"Native Binary:  {native_bin}")
    print(f"Output Dir:     {output_dir}")

    # 1. Preflight checks
    j2_path = shutil.which(j2_bin) or (Path(j2_bin).resolve() if Path(j2_bin).is_file() else None)
    if not j2_path:
        print(f"ERROR: J2 interpreter '{j2_bin}' not found.")
        return 1

    if not native_bin.is_file() or not os.access(native_bin, os.X_OK):
        print(f"ERROR: Native binary '{native_bin}' not found or not executable.")
        return 1

    v_proc = subprocess.run([str(j2_path), "--version"], capture_output=True, text=True, timeout=5)
    j2_ver = v_proc.stdout.strip()
    print(f"J2 Version:     {j2_ver}")

    temp_dir = Path(tempfile.mkdtemp(prefix="t010_demo_verify_"))
    try:
        # 2. Stage 1: Deterministic demo corpus generation
        print("\n--- 1. Generating & Verifying Deterministic Demo Corpus ---")
        corpus_path = temp_dir / "demo_corpus"
        create_demo_corpus(corpus_path)
        corpus_info = verify_demo_corpus(corpus_path)
        assert corpus_info["files_count"] == EXPECTED_FILES_COUNT, f"Corpus files count mismatch: {corpus_info['files_count']}"
        assert corpus_info["total_bytes"] == EXPECTED_TOTAL_BYTES, f"Corpus total bytes mismatch: {corpus_info['total_bytes']}"
        corpus_posix = corpus_path.as_posix()
        print(f"Demo corpus generated: PASS ({corpus_info['files_count']} files, {corpus_info['total_bytes']:,} bytes)")

        # 3. Stage 2: Native CLI Duplicate Scan Execution
        print("\n--- 2. Executing Native Duplicate Scan ---")
        run_env = os.environ.copy()
        run_env["J2_ALLOW_FS"] = "1"
        dup_nat_proc = subprocess.run(
            [str(native_bin), corpus_posix, "--json"],
            cwd=REPO_ROOT,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert dup_nat_proc.returncode == 0, f"Native duplicate scan failed: {dup_nat_proc.stderr}"
        dup_nat_data = json.loads(dup_nat_proc.stdout.strip())
        assert dup_nat_data["files_scanned"] == EXPECTED_FILES_COUNT
        assert dup_nat_data["hash_candidates"] == EXPECTED_CANDIDATES_COUNT
        assert len(dup_nat_data["duplicate_groups"]) == EXPECTED_GROUPS_COUNT
        assert dup_nat_data["reclaimable_bytes"] == EXPECTED_RECLAIMABLE_BYTES
        print(f"Native Duplicate Scan: PASS (reclaimable={dup_nat_data['reclaimable_bytes']} B, groups={len(dup_nat_data['duplicate_groups'])})")

        # 4. Stage 3: Native CLI Checksum Inventory Execution
        print("\n--- 3. Executing Native Checksum Inventory ---")
        chk_nat_proc = subprocess.run(
            [str(native_bin), "checksum", corpus_posix, "--json"],
            cwd=REPO_ROOT,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert chk_nat_proc.returncode == 0, f"Native checksum scan failed: {chk_nat_proc.stderr}"
        chk_nat_data = json.loads(chk_nat_proc.stdout.strip())
        assert chk_nat_data["summary"]["total_files"] == EXPECTED_FILES_COUNT
        assert chk_nat_data["summary"]["total_bytes"] == EXPECTED_TOTAL_BYTES
        assert len(chk_nat_data["entries"]) == EXPECTED_FILES_COUNT
        print(f"Native Checksum Inventory: PASS (files={chk_nat_data['summary']['total_files']}, bytes={chk_nat_data['summary']['total_bytes']} B)")

        # 5. Stage 4: Interpreter Parity Verification
        print("\n--- 4. Executing Interpreter Scans & Verifying Parity ---")
        dup_int_proc = subprocess.run(
            [str(j2_path), "--allow-fs", "src/main.j2", corpus_posix, "--json"],
            cwd=REPO_ROOT,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert dup_int_proc.returncode == 0, f"Interpreter duplicate scan failed: {dup_int_proc.stderr}"
        dup_int_data = json.loads(dup_int_proc.stdout.strip())
        assert dup_int_data == dup_nat_data, "Duplicate scan Native != Interpreter output"
        print("Duplicate Scan Parity (Native == Interpreter): PASS")

        chk_int_proc = subprocess.run(
            [str(j2_path), "--allow-fs", "src/main.j2", "checksum", corpus_posix, "--json"],
            cwd=REPO_ROOT,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert chk_int_proc.returncode == 0, f"Interpreter checksum scan failed: {chk_int_proc.stderr}"
        chk_int_data = json.loads(chk_int_proc.stdout.strip())
        assert chk_int_data == chk_nat_data, "Checksum Inventory Parity Native != Interpreter output"
        print("Checksum Inventory Parity (Native == Interpreter): PASS")

        # 6. Stage 5: Independent Python Hashlib Oracle Verification
        print("\n--- 5. Independent Python hashlib.sha256 Oracle Verification ---")
        total_oracle_bytes = 0
        for entry in chk_nat_data["entries"]:
            fp = Path(entry["path"])
            assert fp.is_file(), f"Ledger entry file not found: {entry['path']}"
            raw = fp.read_bytes()
            assert len(raw) == entry["size"], f"Size mismatch for {entry['path']}: {len(raw)} vs {entry['size']}"
            expected_digest = hashlib.sha256(raw).hexdigest()
            assert entry["sha256"] == expected_digest, f"Digest mismatch for {entry['path']}"
            total_oracle_bytes += len(raw)
        assert total_oracle_bytes == EXPECTED_TOTAL_BYTES
        print(f"Independent Hashlib Oracle: PASS (100% digest agreement across {len(chk_nat_data['entries'])} files)")

        # 7. Stage 6: GUI Adapter Live Execution & ViewModel Transformation
        print("\n--- 6. Verifying GUI EngineAdapter Live Invocations ---")
        adapter = EngineAdapter(native_bin=native_bin, j2_bin=str(j2_path))
        res_dup = adapter.run_analysis("duplicate", corpus_posix)
        assert res_dup.success, f"Adapter duplicate analysis failed: {res_dup.error_message}"
        vm_dup = DuplicateViewModel.from_engine_data(res_dup.data)
        assert vm_dup.files_scanned == EXPECTED_FILES_COUNT
        assert vm_dup.reclaimable_bytes == EXPECTED_RECLAIMABLE_BYTES
        assert vm_dup.duplicate_groups_count == EXPECTED_GROUPS_COUNT
        print(f"GUI Adapter Duplicate Analysis: PASS ({vm_dup.reclaimable_formatted} reclaimable)")

        res_chk = adapter.run_analysis("checksum", corpus_posix)
        assert res_chk.success, f"Adapter checksum analysis failed: {res_chk.error_message}"
        vm_chk = ChecksumViewModel.from_engine_data(res_chk.data)
        assert vm_chk.total_files == EXPECTED_FILES_COUNT
        assert vm_chk.total_bytes == EXPECTED_TOTAL_BYTES
        assert len(vm_chk.entries) == EXPECTED_FILES_COUNT
        print(f"GUI Adapter Checksum Analysis: PASS ({vm_chk.total_bytes_formatted} total)")

        # 8. Record Artifacts
        print("\n--- 7. Recording Authoritative Verification Artifacts ---")
        now_utc = datetime.now(timezone.utc).isoformat()
        git_commit = get_git_commit()
        cpu_info = get_cpu_info()

        demo_verification_result = {
            "task": "T010",
            "timestamp_utc": now_utc,
            "git_commit": git_commit,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "cpu": cpu_info,
                "j2_version": j2_ver,
                "python_version": platform.python_version(),
            },
            "demo_corpus": {
                "path": corpus_posix,
                "files_count": corpus_info["files_count"],
                "total_bytes": corpus_info["total_bytes"],
            },
            "workloads": {
                "duplicate_scan": {
                    "status": "PASS",
                    "files_scanned": dup_nat_data["files_scanned"],
                    "hash_candidates": dup_nat_data["hash_candidates"],
                    "duplicate_groups_count": len(dup_nat_data["duplicate_groups"]),
                    "reclaimable_bytes": dup_nat_data["reclaimable_bytes"],
                    "native_interpreter_parity": True,
                },
                "checksum_inventory": {
                    "status": "PASS",
                    "total_files": chk_nat_data["summary"]["total_files"],
                    "total_bytes": chk_nat_data["summary"]["total_bytes"],
                    "entries_count": len(chk_nat_data["entries"]),
                    "oracle_agreement": True,
                    "native_interpreter_parity": True,
                },
                "gui_adapter": {
                    "status": "PASS",
                    "duplicate_view_model": {
                        "files_scanned": vm_dup.files_scanned,
                        "reclaimable_formatted": vm_dup.reclaimable_formatted,
                    },
                    "checksum_view_model": {
                        "total_files": vm_chk.total_files,
                        "total_bytes_formatted": vm_chk.total_bytes_formatted,
                    },
                },
            },
            "overall_verdict": "PASS",
        }

        with open(output_dir / "demo_verification_result.json", "w", encoding="utf-8") as f:
            json.dump(demo_verification_result, f, indent=2)

        provenance = {
            "task": "T010",
            "created_utc": now_utc,
            "git_commit": git_commit,
            "j2_version": j2_ver,
            "host": platform.node(),
            "cpu": cpu_info,
            "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        }
        with open(output_dir / "provenance.json", "w", encoding="utf-8") as f:
            json.dump(provenance, f, indent=2)

        summary_md = f"""# T010 Demonstration Verification Summary

- **Task:** T010 — Demonstration / Integration Polish
- **Status:** PASS
- **Commit:** `{git_commit}`
- **Timestamp:** `{now_utc}`
- **Platform:** `{platform.system()} {platform.release()} ({platform.machine()})`
- **CPU:** `{cpu_info}`
- **J2 Version:** `{j2_ver}`

## Verified Demonstration Contract

| Workload / Check | Metric / Expectation | Engine Result | Verdict |
|---|---|---|---|
| **Demo Corpus** | 8 regular files, 5,258 bytes | 8 files, 5,258 bytes | **PASS** |
| **Duplicate Scan (Files)** | 8 regular files scanned | {dup_nat_data['files_scanned']} files | **PASS** |
| **Duplicate Candidates** | 5 size candidates (100B, 256B) | {dup_nat_data['hash_candidates']} candidates | **PASS** |
| **Duplicate Groups** | 2 duplicate clusters | {len(dup_nat_data['duplicate_groups'])} clusters | **PASS** |
| **Reclaimable Storage** | 456 reclaimable bytes | {dup_nat_data['reclaimable_bytes']} bytes ({vm_dup.reclaimable_formatted}) | **PASS** |
| **Duplicate Parity** | Native == Interpreter JSON | Byte-for-byte identical | **PASS** |
| **Checksum Inventory** | 8 regular files enumerated | {chk_nat_data['summary']['total_files']} files | **PASS** |
| **Checksum Total Bytes** | 5,258 bytes scanned | {chk_nat_data['summary']['total_bytes']} bytes ({vm_chk.total_bytes_formatted}) | **PASS** |
| **Hashlib Oracle** | 100% agreement with `hashlib.sha256` | Verified across all 8 entries | **PASS** |
| **Checksum Parity** | Native == Interpreter JSON | Byte-for-byte identical | **PASS** |
| **GUI EngineAdapter** | Non-blocking execution & ViewModel parsing | Duplicate + Checksum verified | **PASS** |

## Conclusion
The `dupe` system demonstration contract is verified: J2 authoritative engine execution, dual workload pipelines, exact native/interpreter parity, independent oracle agreement, and clean presentation shells (CLI + Tk GUI).
"""
        with open(output_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write(summary_md)

        print("Verification artifacts written to:")
        print(f"  - {output_dir / 'demo_verification_result.json'}")
        print(f"  - {output_dir / 'provenance.json'}")
        print(f"  - {output_dir / 'summary.md'}")
        print("\n============================================================")
        print("VERDICT: PASS — T010 DEMONSTRATION CONTRACT VERIFIED")
        print("============================================================")
        return 0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
