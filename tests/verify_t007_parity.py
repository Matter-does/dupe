"""Authoritative macOS native/interpreter parity and oracle verification for T007.

Verifies:
1. Controlled corpus creation with multiple topologies:
   - empty directory
   - single file
   - nested directories
   - binary file (non-UTF8)
   - zero-byte file
   - multiple files
   - duplicate-content files
   - filenames with spaces
2. Real interpreter execution:
   `j2 --allow-fs src/main.j2 checksum <path> --json`
   `j2 --allow-fs src/main.j2 checksum --json <path>`
3. Genuine native binary execution:
   `./build/dupe checksum <path> --json` (with J2_ALLOW_FS=1)
   `./build/dupe checksum --json <path>` (with J2_ALLOW_FS=1)
4. Byte-for-byte exact equality between interpreter and native modes.
5. Byte-for-byte exact equality across argument permutations.
6. Complete validation against independent host-side Python oracle (hashlib.sha256).
7. Regression test for existing duplicate analysis CLI (`dupe <path> --json`).
8. Full provenance and artifact recording.
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

from tests.test_t007_checksum_inventory import checksum_inventory_oracle

PINNED_J2_SHA256 = "6fda8338791730cf7937362acd03e29247719e65785458e62988e1789c842e75"


def create_test_corpus(base_dir: Path) -> Path:
    """Create controlled multi-topology test corpus matching T007 requirements."""
    corpus = base_dir / "t007_parity_corpus"
    corpus.mkdir(parents=True, exist_ok=True)

    # 1. Empty directory
    (corpus / "empty_dir").mkdir(exist_ok=True)

    # 2. Single text file
    (corpus / "single.txt").write_bytes(b"hello world of t007 parity\n")

    # 3. Zero-byte file
    (corpus / "zero_byte.dat").write_bytes(b"")

    # 4. Binary non-UTF8 file
    binary_bytes = bytes(range(256)) + b"\x00\xff\xfe\x01\x80\xaa\xbb\xcc\xdd\xee"
    (corpus / "binary.bin").write_bytes(binary_bytes)

    # 5. Nested directories
    n1 = corpus / "nested" / "sub_a"
    n2 = corpus / "nested" / "sub_b" / "deep"
    n1.mkdir(parents=True, exist_ok=True)
    n2.mkdir(parents=True, exist_ok=True)

    (n1 / "file_a.txt").write_bytes(b"nested alpha content")
    (n2 / "deep_file.txt").write_bytes(b"deep nested beta content")

    # 6. Filename with spaces
    (corpus / "file with spaces.txt").write_bytes(b"content in file with spaces")

    # 7. Duplicate-content files (same bytes, different paths)
    dup_payload = b"duplicate checksum payload shared across multiple files"
    (corpus / "dup_1.dat").write_bytes(dup_payload)
    (corpus / "dup_2.dat").write_bytes(dup_payload)
    (n1 / "dup_3.dat").write_bytes(dup_payload)

    return corpus


def get_cpu_info() -> str:
    """Extract CPU information where practical."""
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
    """Extract current git commit SHA."""
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


def verify_against_oracle(data: dict, oracle: dict) -> None:
    """Assert full schema and entry-level equivalence against Python hashlib oracle."""
    assert data["schema_version"] == 1, f"Expected schema_version 1, got {data.get('schema_version')}"
    assert data["workload"] == "checksum_inventory", (
        f"Expected workload 'checksum_inventory', got {data.get('workload')}"
    )
    assert data["summary"]["total_files"] == oracle["summary"]["total_files"], (
        f"File count mismatch: {data['summary']['total_files']} != {oracle['summary']['total_files']}"
    )
    assert data["summary"]["total_bytes"] == oracle["summary"]["total_bytes"], (
        f"Byte total mismatch: {data['summary']['total_bytes']} != {oracle['summary']['total_bytes']}"
    )
    assert len(data["entries"]) == len(oracle["entries"]), (
        f"Entries length mismatch: {len(data['entries'])} != {len(oracle['entries'])}"
    )

    for i, (act, exp) in enumerate(zip(data["entries"], oracle["entries"])):
        assert act["path"] == exp["path"], f"Entry {i} path mismatch: {act['path']} != {exp['path']}"
        assert act["size"] == exp["size"], f"Entry {i} size mismatch: {act['size']} != {exp['size']}"
        assert act["sha256"] == exp["sha256"], f"Entry {i} sha256 mismatch: {act['sha256']} != {exp['sha256']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="T007 Native/Interpreter Parity & Oracle Verification")
    parser.add_argument("--native-bin", type=Path, default=REPO_ROOT / "build" / "dupe", help="Path to native binary")
    parser.add_argument("--j2-bin", type=str, default=os.environ.get("J2_BIN", "j2"), help="J2 interpreter binary")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "artifacts" / "t007", help="Artifact output directory")
    parser.add_argument("--keep-corpus", action="store_true", help="Do not delete temporary test corpus")
    args = parser.parse_args()

    native_bin = args.native_bin.resolve()
    j2_bin = args.j2_bin
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("============================================================")
    print("T007 AUTHORITATIVE MACOS PARITY & ORACLE VERIFICATION")
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

    # Check J2 version
    v_proc = subprocess.run([str(j2_path), "--version"], capture_output=True, text=True, timeout=5)
    j2_ver = v_proc.stdout.strip()
    print(f"J2 Version:     {j2_ver}")

    # 2. Build controlled corpus
    temp_dir = Path(tempfile.mkdtemp(prefix="t007_parity_"))
    try:
        corpus = create_test_corpus(temp_dir)
        corpus_posix = corpus.as_posix()
        print(f"Created corpus at: {corpus_posix}")

        # 3. Independent host-side Python oracle
        print("\nComputing independent Python oracle (hashlib.sha256)...")
        oracle_data = checksum_inventory_oracle(corpus)
        oracle_file = output_dir / "oracle.json"
        oracle_file.write_text(json.dumps(oracle_data, indent=2) + "\n", encoding="utf-8")
        print(f"Oracle: {oracle_data['summary']['total_files']} files, {oracle_data['summary']['total_bytes']} bytes")

        # 4. Interpreter execution: checksum <path> --json
        main_j2 = (REPO_ROOT / "src" / "main.j2").as_posix()
        cmd_interp_1 = [str(j2_path), "--allow-fs", main_j2, "checksum", corpus_posix, "--json"]
        print(f"\nRunning Interpreter (order 1): {' '.join(cmd_interp_1)}")
        res_interp_1 = subprocess.run(cmd_interp_1, cwd=REPO_ROOT, capture_output=True, timeout=60)
        assert res_interp_1.returncode == 0, f"Interpreter failed: {res_interp_1.stderr.decode()}"
        interp_bytes = res_interp_1.stdout

        # Interpreter execution: checksum --json <path>
        cmd_interp_2 = [str(j2_path), "--allow-fs", main_j2, "checksum", "--json", corpus_posix]
        print(f"Running Interpreter (order 2): {' '.join(cmd_interp_2)}")
        res_interp_2 = subprocess.run(cmd_interp_2, cwd=REPO_ROOT, capture_output=True, timeout=60)
        assert res_interp_2.returncode == 0, f"Interpreter order 2 failed: {res_interp_2.stderr.decode()}"
        assert res_interp_1.stdout == res_interp_2.stdout, (
            "Interpreter argument order stdout mismatch!"
        )

        (output_dir / "interpreter.json").write_bytes(interp_bytes)

        # 5. Native binary execution: checksum <path> --json
        native_env = {**os.environ, "J2_ALLOW_FS": "1"}
        cmd_native_1 = [str(native_bin), "checksum", corpus_posix, "--json"]
        print(f"\nRunning Native Binary (order 1): {' '.join(cmd_native_1)}")
        res_native_1 = subprocess.run(cmd_native_1, cwd=REPO_ROOT, env=native_env, capture_output=True, timeout=60)
        assert res_native_1.returncode == 0, f"Native binary failed: {res_native_1.stderr.decode()}"
        native_bytes = res_native_1.stdout

        # Native binary execution: checksum --json <path>
        cmd_native_2 = [str(native_bin), "checksum", "--json", corpus_posix]
        print(f"Running Native Binary (order 2): {' '.join(cmd_native_2)}")
        res_native_2 = subprocess.run(cmd_native_2, cwd=REPO_ROOT, env=native_env, capture_output=True, timeout=60)
        assert res_native_2.returncode == 0, f"Native order 2 failed: {res_native_2.stderr.decode()}"
        assert res_native_1.stdout == res_native_2.stdout, (
            "Native argument order stdout mismatch!"
        )

        (output_dir / "native.json").write_bytes(native_bytes)

        # 6. BYTE-FOR-BYTE EXACT PARITY ASSERTION
        print("\n============================================================")
        print("ASSERTING BYTE-FOR-BYTE PARITY (INTERPRETER == NATIVE)")
        print("============================================================")
        interp_sha = hashlib.sha256(interp_bytes).hexdigest()
        native_sha = hashlib.sha256(native_bytes).hexdigest()
        print(f"Interpreter stdout bytes: {len(interp_bytes)} (SHA-256: {interp_sha})")
        print(f"Native stdout bytes:      {len(native_bytes)} (SHA-256: {native_sha})")

        assert interp_bytes == native_bytes, (
            f"BYTE PARITY FAILURE: interpreter ({len(interp_bytes)} bytes) != native ({len(native_bytes)} bytes)!\n"
            f"Interpreter SHA-256: {interp_sha}\n"
            f"Native SHA-256:      {native_sha}\n"
        )
        print("PARITY VERIFIED: interpreter stdout == native stdout BYTE-FOR-BYTE!")

        # 7. Independent Oracle Validation
        print("\nVerifying against host-side Python oracle...")
        interp_data = json.loads(interp_bytes.decode("utf-8"))
        verify_against_oracle(interp_data, oracle_data)
        print("ORACLE VERIFIED: JSON schema, counts, sizes, sha256, and ordering match 100%!")

        # 8. Duplicate Scan Regression Check
        print("\nRunning duplicate CLI regression: dupe <path> --json...")
        cmd_reg_interp = [str(j2_path), "--allow-fs", main_j2, corpus_posix, "--json"]
        res_reg_interp = subprocess.run(cmd_reg_interp, cwd=REPO_ROOT, capture_output=True, timeout=60)
        assert res_reg_interp.returncode == 0, f"Duplicate CLI interpreter failed: {res_reg_interp.stderr.decode()}"

        cmd_reg_native = [str(native_bin), corpus_posix, "--json"]
        res_reg_native = subprocess.run(cmd_reg_native, cwd=REPO_ROOT, env=native_env, capture_output=True, timeout=60)
        assert res_reg_native.returncode == 0, f"Duplicate CLI native failed: {res_reg_native.stderr.decode()}"

        reg_data = json.loads(res_reg_interp.stdout.decode("utf-8"))
        assert "duplicate_groups" in reg_data, "Duplicate regression JSON missing duplicate_groups"
        assert len(reg_data["duplicate_groups"]) == 1, (
            f"Expected 1 duplicate group in regression, got {len(reg_data['duplicate_groups'])}"
        )
        print("REGRESSION PASS: dupe <path> --json behaves correctly.")

        # 9. Record Full Provenance and Parity Artifacts
        now_utc = datetime.now(timezone.utc).isoformat()
        git_commit = get_git_commit()
        cpu_info = get_cpu_info()

        parity_result = {
            "status": "PASS",
            "byte_for_byte_identical": True,
            "stdout_size_bytes": len(interp_bytes),
            "stdout_sha256": interp_sha,
            "interpreter_sha256": interp_sha,
            "native_sha256": native_sha,
            "argument_order_parity": True,
            "oracle_verified": True,
            "duplicate_regression_pass": True,
            "total_files": oracle_data["summary"]["total_files"],
            "total_bytes": oracle_data["summary"]["total_bytes"],
            "entries_count": len(oracle_data["entries"]),
        }
        (output_dir / "parity_result.json").write_text(json.dumps(parity_result, indent=2) + "\n", encoding="utf-8")

        provenance = {
            "workflow": "t007-checksum-inventory.yml",
            "git_commit": git_commit,
            "j2_version": j2_ver,
            "j2_release_archive_sha256": PINNED_J2_SHA256,
            "runner_os": platform.platform(),
            "architecture": platform.machine(),
            "cpu_info": cpu_info,
            "timestamp_utc": now_utc,
            "execution_commands": {
                "interpreter_order_1": cmd_interp_1,
                "interpreter_order_2": cmd_interp_2,
                "native_order_1": cmd_native_1,
                "native_order_2": cmd_native_2,
                "regression_interpreter": cmd_reg_interp,
                "regression_native": cmd_reg_native,
            },
            "corpus_parameters": {
                "total_files": oracle_data["summary"]["total_files"],
                "total_bytes": oracle_data["summary"]["total_bytes"],
                "topologies": [
                    "empty_directory",
                    "single_file",
                    "zero_byte_file",
                    "binary_non_utf8",
                    "nested_directories",
                    "filenames_with_spaces",
                    "duplicate_content_cluster",
                ],
            },
            "parity_result": parity_result,
        }
        (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

        # Markdown summary report
        summary_lines = [
            "# T007 Checksum Inventory macOS Parity Verification",
            "",
            "## Parity Verdict",
            "**STATUS: PASS** — Interpreter and Compiled Native Binary produced **byte-for-byte identical** JSON output.",
            "",
            "## Provenance Information",
            f"- **Workflow:** `t007-checksum-inventory.yml`",
            f"- **Commit SHA:** `{git_commit}`",
            f"- **J2 Version:** `{j2_ver}`",
            f"- **J2 Archive SHA-256:** `{PINNED_J2_SHA256}`",
            f"- **Runner OS:** `{platform.platform()}`",
            f"- **Architecture:** `{platform.machine()}`",
            f"- **CPU:** `{cpu_info}`",
            f"- **Timestamp (UTC):** `{now_utc}`",
            "",
            "## Verification Matrix",
            "| Check | Result | Detail |",
            "|---|---|---|",
            f"| **Byte-for-byte Parity** | PASS | `interpreter stdout == native stdout` ({len(interp_bytes)} bytes) |",
            f"| **Output SHA-256** | PASS | `{interp_sha}` |",
            f"| **Argument Order Parity** | PASS | `checksum <path> --json` == `checksum --json <path>` |",
            f"| **Independent Oracle** | PASS | Validated against Python `hashlib.sha256` ({oracle_data['summary']['total_files']} files, {oracle_data['summary']['total_bytes']} bytes) |",
            "| **Duplicate Regression** | PASS | `dupe <path> --json` correctly retained duplicate group analysis |",
            "",
            "## Artifacts Generated",
            "- `interpreter.json` — raw stdout bytes from J2 interpreter",
            "- `native.json` — raw stdout bytes from J2 compiled native binary",
            "- `oracle.json` — independent Python oracle output",
            "- `parity_result.json` — structured parity assertion metrics",
            "- `provenance.json` — comprehensive environment and execution provenance",
            "",
        ]
        summary_md = "\n".join(summary_lines)
        (output_dir / "summary.md").write_text(summary_md, encoding="utf-8")

        print("\n============================================================")
        print("ALL T007 VERIFICATION CHECKS PASSED")
        print(f"Artifacts successfully written to: {output_dir}")
        print("============================================================")
        return 0

    finally:
        if not args.keep_corpus and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
