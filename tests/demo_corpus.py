"""Representative deterministic demonstration corpus generator for dupe.

Generates a compact, deterministic, multi-topology demonstration filesystem
corpus suitable for demonstrating both duplicate detection and checksum inventory.

Expected Ground Truth:
- 8 regular files, 1 empty directory, nested subdirectories
- Total Scanned Bytes: 5,258 bytes
- Candidate Filter: 5 hash candidates (100B and 256B), 3 unique sizes filtered out
- Duplicate Groups: 2 groups
    * Group 1: 3 files of 100 bytes (reclaimable: 200 bytes)
    * Group 2: 2 files of 256 bytes (reclaimable: 256 bytes)
- Total Reclaimable Bytes: 456 bytes
- Checksum Inventory: 8 files, 5,258 bytes, verifiable against hashlib.sha256
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import random
import shutil
import sys

# Fixed deterministic payloads
_PAYLOAD_100_BASE = (
    b"DUPE DEMO REPORT - J2 Filesystem Engine\n"
    b"Cluster: Alpha\n"
)
PAYLOAD_100 = _PAYLOAD_100_BASE + b"=" * (100 - len(_PAYLOAD_100_BASE))

PAYLOAD_256 = bytes(range(256))

_rng_4096 = random.Random(20260913)
PAYLOAD_4096 = _rng_4096.randbytes(4096)

_PAYLOAD_350_BASE = (
    b"# Dupe Demonstration Notes\n\n"
    b"- Workload A: Exact duplicate detection via size-filtering and full SHA-256.\n"
    b"- Workload B: Checksum inventory producing verifiable SHA-256 ledgers.\n"
    b"- J2 automatic parallelism: Independent per-candidate and per-file evaluation.\n"
    b"- Decoupled presentation: Unified CLI and lightweight Tk desktop GUI shell.\n"
)
PAYLOAD_350 = _PAYLOAD_350_BASE + b" " * (350 - len(_PAYLOAD_350_BASE))

PAYLOAD_ZERO = b""

# Corpus file layout specification: (relative_path, payload)
DEMO_CORPUS_SPEC: list[tuple[str, bytes]] = [
    ("documents/report_draft.txt", PAYLOAD_100),
    ("documents/report_final.txt", PAYLOAD_100),
    ("archive/old_backup/report_backup.txt", PAYLOAD_100),
    ("images/banner.raw", PAYLOAD_256),
    ("images/banner_copy.raw", PAYLOAD_256),
    ("archive/system.iso", PAYLOAD_4096),
    ("notes/meeting_notes.md", PAYLOAD_350),
    ("zero_byte.dat", PAYLOAD_ZERO),
]

EXPECTED_FILES_COUNT = 8
EXPECTED_TOTAL_BYTES = 5258
EXPECTED_CANDIDATES_COUNT = 5
EXPECTED_GROUPS_COUNT = 2
EXPECTED_RECLAIMABLE_BYTES = 456


def get_expected_sha256(payload: bytes) -> str:
    """Compute exact hexadecimal SHA-256 digest for payload."""
    return hashlib.sha256(payload).hexdigest()


def create_demo_corpus(target_dir: Path | str, *, clean: bool = False) -> Path:
    """Create the deterministic demonstration corpus at the specified target directory.

    Args:
        target_dir: Path to directory where demo corpus should be generated.
        clean: If True and target_dir exists, wipe and recreate it.

    Returns:
        Path to the generated demo corpus directory.
    """
    out = Path(target_dir).resolve()
    if out.exists():
        if clean:
            shutil.rmtree(out)
            out.mkdir(parents=True, exist_ok=True)
    else:
        out.mkdir(parents=True, exist_ok=True)

    # 1. Create empty directory
    (out / "empty_dir").mkdir(exist_ok=True)

    # 2. Write all specified files
    for rel_path, payload in DEMO_CORPUS_SPEC:
        file_path = out / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(payload)

    return out


def verify_demo_corpus(target_dir: Path | str) -> dict[str, any]:
    """Inspect and verify a generated demo corpus against ground truth."""
    root = Path(target_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Demo corpus root not found: {root}")

    found_files: list[tuple[str, int, str]] = []
    total_bytes = 0

    for rel_path, expected_payload in DEMO_CORPUS_SPEC:
        fp = root / rel_path
        if not fp.is_file():
            raise AssertionError(f"Expected demo file missing: {rel_path}")
        actual_bytes = fp.read_bytes()
        if actual_bytes != expected_payload:
            raise AssertionError(
                f"Payload mismatch for {rel_path}: expected {len(expected_payload)}B, got {len(actual_bytes)}B"
            )
        digest = hashlib.sha256(actual_bytes).hexdigest()
        size = len(actual_bytes)
        total_bytes += size
        found_files.append((rel_path, size, digest))

    if not (root / "empty_dir").is_dir():
        raise AssertionError("Expected empty_dir missing in demo corpus")

    return {
        "root": str(root),
        "files_count": len(found_files),
        "total_bytes": total_bytes,
        "files": found_files,
        "valid": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic demonstration corpus for dupe")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="demo_corpus",
        help="Target output directory for demo corpus (default: demo_corpus)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing directory before generation",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    created = create_demo_corpus(out_path, clean=args.clean)
    verified = verify_demo_corpus(created)

    print(f"Demo corpus successfully created at: {created}")
    print(f"Total regular files: {verified['files_count']}")
    print(f"Total size: {verified['total_bytes']:,} bytes")
    print("\nExpected Workload Results:")
    print(f"  Exact Duplicate Scan: 8 files scanned, 5 candidates, 2 duplicate groups, 456 bytes reclaimable")
    print(f"  Checksum Inventory:   8 files, 5,258 bytes with verified SHA-256 digests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
