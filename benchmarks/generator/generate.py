"""Deterministic benchmark corpus generator.

Generates reproducible filesystem workloads according to T004 specification and
named standard corpus profiles (C1–C7).
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
from typing import Any, Optional

if __package__ is None or __package__ == "":
    _repo_root = str(Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from benchmarks.generator.manifest import (
        MANIFEST_FILENAME,
        Manifest,
        compute_oracle_result,
        compute_result_digest,
        validate_manifest,
    )
    from benchmarks.generator.profiles import (
        CI_STORAGE_CEILING_BYTES,
        C1_PROFILE,
        C2_PROFILE,
        C3_PROFILE,
        C4_PROFILE,
        C5_PROFILE,
        C6_PROFILE,
        C7_PROFILE,
        CollisionDensity,
        CorpusProfile,
        DirectoryShape,
        NAMED_PROFILES,
        SimilarityProfile,
        SizeProfile,
    )
else:
    from .manifest import (
        MANIFEST_FILENAME,
        Manifest,
        compute_oracle_result,
        compute_result_digest,
        validate_manifest,
    )
    from .profiles import (
        CI_STORAGE_CEILING_BYTES,
        C1_PROFILE,
        C2_PROFILE,
        C3_PROFILE,
        C4_PROFILE,
        C5_PROFILE,
        C6_PROFILE,
        C7_PROFILE,
        CollisionDensity,
        CorpusProfile,
        DirectoryShape,
        NAMED_PROFILES,
        SimilarityProfile,
        SizeProfile,
    )


def get_generator_version() -> str:
    """Obtain current git commit hash or fallback version string."""
    try:
        repo_root = Path(__file__).resolve().parents[2]
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "0.1.0-t004"


def check_disk_space(target_dir: Path, bytes_needed: int, safety_margin_mb: int = 50) -> None:
    """Pre-flight check to prevent runner disk exhaustion.
    Validates available disk space before writing files."""
    target_dir.mkdir(parents=True, exist_ok=True)
    margin_bytes = safety_margin_mb * 1024 * 1024
    stat = shutil.disk_usage(target_dir)
    if stat.free < bytes_needed + margin_bytes:
        raise RuntimeError(
            f"Pre-flight disk space safety check FAILED: Insufficient disk space in {target_dir}: "
            f"{bytes_needed} bytes required + {margin_bytes} bytes margin ({safety_margin_mb} MB), "
            f"but only {stat.free} bytes available on volume."
        )


def build_directory_paths(
    shape: DirectoryShape, file_count: int, rng: random.Random
) -> list[str]:
    """Generate deterministic directory prefixes according to DirectoryShape."""
    if shape == DirectoryShape.FLAT:
        return [""]

    if shape == DirectoryShape.SHALLOW_WIDE:
        # 1-2 levels, 10 to 50 directories
        num_dirs = max(2, min(50, file_count // 100))
        return [f"dir_{i:02d}" for i in range(num_dirs)]

    if shape == DirectoryShape.DEEP:
        # 8-15 nested levels
        depth = rng.randint(8, 12)
        prefixes = []
        chain = []
        for d in range(depth):
            chain.append(f"level_{d:02d}")
            prefixes.append("/".join(chain))
        # Add some branching at deeper levels
        for b in range(4):
            prefixes.append(f"{prefixes[-1]}/branch_{b}")
        return prefixes

    # DirectoryShape.MIXED
    # Balanced tree structure (branching 3-5, depth 2-4)
    prefixes = [""]
    for i in range(4):
        p1 = f"sub_{i:02d}"
        prefixes.append(p1)
        for j in range(3):
            p2 = f"{p1}/nested_{j:02d}"
            prefixes.append(p2)
            for k in range(2):
                prefixes.append(f"{p2}/leaf_{k:02d}")
    return prefixes


def generate_content(
    length: int,
    similarity: SimilarityProfile,
    rng: random.Random,
    shared_prefix_bytes: Optional[bytes] = None,
    shared_suffix_bytes: Optional[bytes] = None,
) -> bytes:
    """Generate deterministic byte payload according to SimilarityProfile."""
    if length == 0:
        return b""

    if similarity == SimilarityProfile.EXACT or similarity == SimilarityProfile.DISTINCT:
        return rng.randbytes(length)

    if similarity == SimilarityProfile.SHARED_PREFIX:
        half = length // 2
        prefix = shared_prefix_bytes[:half] if shared_prefix_bytes else b"\xaa" * half
        suffix = rng.randbytes(length - len(prefix))
        return prefix + suffix

    if similarity == SimilarityProfile.SHARED_SUFFIX:
        half = length // 2
        suffix = shared_suffix_bytes[:half] if shared_suffix_bytes else b"\x55" * half
        prefix = rng.randbytes(length - len(suffix))
        return prefix + suffix

    return rng.randbytes(length)


def sample_sizes(
    profile: CorpusProfile, file_count: int, target_bytes: int, rng: random.Random
) -> list[int]:
    """Sample deterministic file sizes matching SizeProfile and total byte target."""
    if file_count <= 0:
        return []

    avg_size = max(1, target_bytes // file_count)

    if profile.size_profile == SizeProfile.SAME_SIZE_ADVERSARIAL:
        # Uniform size across all files
        sizes = [avg_size] * file_count
        # Adjust remainder on last file if needed, but for C5 exact uniform is preferred
        return sizes

    if profile.size_profile == SizeProfile.TINY_HEAVY:
        # Tiny files (<4 KB, avg 4 KB)
        # For C1: avg 4096, distributed in [1024, 7168] with avg ~4096
        sizes = []
        for _ in range(file_count):
            s = int(rng.gauss(avg_size, avg_size * 0.25))
            sizes.append(max(64, min(8192, s)))
        # Normalize sum to target_bytes
        current_sum = sum(sizes)
        if current_sum > 0:
            scale = target_bytes / current_sum
            sizes = [max(64, int(s * scale)) for s in sizes]
        return sizes

    if profile.size_profile == SizeProfile.LARGE_HEAVY:
        # Large files (1-10 MB)
        sizes = []
        for _ in range(file_count):
            s = rng.randint(max(1024 * 1024, avg_size // 2), min(10 * 1024 * 1024, avg_size * 2))
            sizes.append(s)
        current_sum = sum(sizes)
        if current_sum > 0:
            scale = target_bytes / current_sum
            sizes = [max(1024 * 1024, int(s * scale)) for s in sizes]
        return sizes

    # Mixed / Pareto power-law distribution
    sizes = []
    for _ in range(file_count):
        # Pareto distribution: many small files, some medium, few large
        val = rng.paretovariate(alpha=1.3)
        sizes.append(val)
    current_sum = sum(sizes)
    scale = target_bytes / current_sum
    res_sizes = [max(64, int(s * scale)) for s in sizes]
    return res_sizes


def generate_corpus(
    profile: CorpusProfile,
    out_dir: Path | str,
    seed: int = 12345,
    scale: float = 1.0,
    allow_developer_hardware: bool = False,
    safety_margin_mb: int = 50,
) -> tuple[Path, Manifest]:
    """Generate a deterministic benchmark corpus on disk and emit manifest.json.

    Args:
        profile: CorpusProfile to generate.
        out_dir: Directory where the corpus files and manifest.json will be written.
        seed: PRNG seed for deterministic reproducibility.
        scale: Scale factor (0.0 < scale <= 1.0) for miniature test execution.
        allow_developer_hardware: Mandatory confirmation to generate C3 / developer-only corpora.
        safety_margin_mb: Pre-flight disk space margin in megabytes.

    Returns:
        (out_dir_path, Manifest)
    """
    out_path = Path(out_dir).resolve()

    if profile.developer_hardware_only and not allow_developer_hardware:
        raise PermissionError(
            f"Corpus '{profile.corpus_id}' is marked Developer-Hardware-Only "
            f"({profile.target_bytes / (1024*1024):.0f} MB target size). "
            f"You must pass allow_developer_hardware=True (or --allow-developer-hardware) to generate it."
        )

    # Scale adjustments
    if scale <= 0.0 or scale > 1.0:
        raise ValueError(f"scale must be in (0.0, 1.0], got {scale}")

    file_count = max(10, int(round(profile.file_count * scale)))
    target_bytes = max(10000, int(round(profile.target_bytes * scale)))

    # Pre-flight disk space safety check
    check_disk_space(out_path, target_bytes, safety_margin_mb=safety_margin_mb)

    # Clean target directory if exists, ensure fresh state
    if out_path.exists():
        # Remove any existing files in target
        for item in out_path.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        out_path.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    # Calculate duplicate files and clusters
    # Formal definition: duplicate_ratio = duplicate_files / total_files
    target_dup_files = int(round(file_count * profile.duplicate_ratio))
    # Duplicate groups must have at least 2 files
    if target_dup_files < 2 and profile.duplicate_ratio > 0.0:
        target_dup_files = 2
    if target_dup_files > file_count:
        target_dup_files = file_count

    # Determine cluster sizes
    cluster_specs: list[int] = []  # list of cluster copy counts
    dup_remaining = target_dup_files

    if profile.duplicate_ratio >= 0.70:
        # Large clusters (e.g. C4 high density: 10 to 50 copies)
        while dup_remaining >= 2:
            max_c = min(dup_remaining, max(2, file_count // 20))
            min_c = min(dup_remaining, 4)
            c_size = rng.randint(min_c, max(min_c, max_c))
            cluster_specs.append(c_size)
            dup_remaining -= c_size
    else:
        # Small clusters (pairs, 3-packs, 4-packs)
        while dup_remaining >= 2:
            if dup_remaining == 3:
                c_size = 3
            elif dup_remaining == 2:
                c_size = 2
            else:
                c_size = rng.choice([2, 2, 2, 3, 4])
                if c_size > dup_remaining:
                    c_size = dup_remaining
                if dup_remaining - c_size == 1:
                    c_size = dup_remaining  # absorb odd single
            cluster_specs.append(c_size)
            dup_remaining -= c_size

    actual_dup_files = sum(cluster_specs)
    num_unique_files = file_count - actual_dup_files
    num_clusters = len(cluster_specs)

    # Directories
    dir_prefixes = build_directory_paths(profile.directory_shape, file_count, rng)

    # Sample base sizes for all files
    raw_sizes = sample_sizes(profile, file_count, target_bytes, rng)

    # Assign sizes and contents
    # 1. Duplicate clusters
    cluster_payloads: list[bytes] = []
    cluster_sizes: list[int] = []

    shared_prefix = rng.randbytes(128)
    shared_suffix = rng.randbytes(128)

    size_idx = 0
    for c_idx, c_size in enumerate(cluster_specs):
        s = raw_sizes[size_idx]
        size_idx += 1
        payload = generate_content(
            s, profile.similarity_profile, rng, shared_prefix, shared_suffix
        )
        cluster_sizes.append(len(payload))
        cluster_payloads.append(payload)

    # 2. Non-duplicate unique files
    unique_sizes: list[int] = []
    unique_payloads: list[bytes] = []

    if profile.size_profile == SizeProfile.SAME_SIZE_ADVERSARIAL:
        # C5: ALL unique files share the EXACT SAME size as cluster files!
        common_size = cluster_sizes[0] if cluster_sizes else raw_sizes[0]
        for u_idx in range(num_unique_files):
            # Generate distinct content with identical size
            # Distinctness guaranteed by embedding unique file index
            data = bytearray(generate_content(common_size, profile.similarity_profile, rng))
            header = f"uniq_{u_idx:08d}_".encode("ascii")
            if len(data) >= len(header):
                data[:len(header)] = header
            unique_payloads.append(bytes(data))
            unique_sizes.append(common_size)
    else:
        # Regular size allocation
        used_cluster_hashes = {hashlib.sha256(p).hexdigest() for p in cluster_payloads}
        for u_idx in range(num_unique_files):
            s = raw_sizes[size_idx % len(raw_sizes)]
            size_idx += 1

            # Adjust size for collision density
            if profile.collision_density == CollisionDensity.LOW:
                # Ensure size doesn't collide with cluster sizes if possible
                if s in cluster_sizes:
                    s += (u_idx + 1)
            elif profile.collision_density == CollisionDensity.HIGH:
                # Intentionally collide with existing cluster sizes to force candidate hashing
                if cluster_sizes:
                    s = cluster_sizes[u_idx % len(cluster_sizes)]

            data = bytearray(generate_content(s, profile.similarity_profile, rng, shared_prefix, shared_suffix))
            header = f"uniq_{u_idx:08d}_".encode("ascii")
            if len(data) >= len(header):
                data[:len(header)] = header
            data_bytes = bytes(data)
            # Ensure unique payload does not collide with any cluster
            while hashlib.sha256(data_bytes).hexdigest() in used_cluster_hashes:
                data = bytearray(rng.randbytes(s))
                data[:len(header)] = header
                data_bytes = bytes(data)

            unique_payloads.append(data_bytes)
            unique_sizes.append(len(data_bytes))

    # Build full file list: (rel_path, payload)
    files_to_write: list[tuple[str, bytes]] = []

    # Distribute duplicate copies across distinct paths
    file_counter = 0
    for c_idx, c_size in enumerate(cluster_specs):
        payload = cluster_payloads[c_idx]
        used_dirs: set[str] = set()
        for copy_idx in range(c_size):
            # Pick distinct directories when available
            avail_dirs = [d for d in dir_prefixes if d not in used_dirs] or dir_prefixes
            d = rng.choice(avail_dirs)
            used_dirs.add(d)
            fname = f"cluster_{c_idx:04d}_copy_{copy_idx:03d}.dat"
            rel = f"{d}/{fname}" if d else fname
            files_to_write.append((rel, payload))
            file_counter += 1

    # Add unique files
    for u_idx, payload in enumerate(unique_payloads):
        d = rng.choice(dir_prefixes)
        fname = f"file_{u_idx:06d}.bin"
        rel = f"{d}/{fname}" if d else fname
        files_to_write.append((rel, payload))
        file_counter += 1

    # Sort files deterministically by relative path
    files_to_write.sort(key=lambda item: item[0])

    # Write files to disk
    actual_total_bytes = 0
    for rel_path, payload in files_to_write:
        full_p = out_path / rel_path
        full_p.parent.mkdir(parents=True, exist_ok=True)
        full_p.write_bytes(payload)
        actual_total_bytes += len(payload)

    # Run reference oracle on generated corpus
    oracle_out = compute_oracle_result(out_path)
    result_digest = compute_result_digest(oracle_out)

    actual_dup_files_count = sum(len(g["files"]) for g in oracle_out["duplicate_groups"])
    actual_dup_ratio = round(actual_dup_files_count / file_count, 6)

    manifest = Manifest(
        schema_version=1,
        corpus_id=profile.corpus_id,
        seed=seed,
        generator_version=get_generator_version(),
        file_count=file_count,
        total_bytes=actual_total_bytes,
        duplicate_ratio=actual_dup_ratio,
        duplicate_groups=len(oracle_out["duplicate_groups"]),
        duplicate_files=actual_dup_files_count,
        same_size_candidate_files=oracle_out["hash_candidates"],
        size_profile=profile.size_profile.value,
        directory_shape=profile.directory_shape.value,
        similarity_profile=profile.similarity_profile.value,
        expected_reclaimable_bytes=oracle_out["reclaimable_bytes"],
        expected_result_digest=result_digest,
        developer_hardware_only=profile.developer_hardware_only,
    )

    manifest_file = out_path / MANIFEST_FILENAME
    manifest_file.write_text(manifest.to_json(), encoding="utf-8")

    # Strict post-generation self-validation
    is_valid, errors = validate_manifest(manifest_file, raise_on_error=True)
    assert is_valid, f"Generated corpus self-validation failed: {errors}"

    return out_path, manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Corpus Generator for dupe (TASK T004)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--corpus",
        type=str,
        choices=list(NAMED_PROFILES.keys()),
        default="C2",
        help="Named standard corpus profile (C1–C7). Default: C2",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Target output directory for the generated corpus (default: benchmarks/corpora/<CORPUS_ID>)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Deterministic PRNG seed (default: 12345)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor (0.0 < scale <= 1.0) for testing/miniature runs (default: 1.0)",
    )
    parser.add_argument(
        "--allow-developer-hardware",
        action="store_true",
        help="Mandatory flag required to generate C3 or Developer-Hardware-Only corpora (>1 GB)",
    )
    parser.add_argument(
        "--validate",
        type=str,
        default=None,
        help="Validate an existing corpus against its manifest.json",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available named standard corpora profiles (C1–C7) and exit",
    )
    args = parser.parse_args()

    if args.list:
        print("Named Standard Benchmark Corpora (C1-C7):")
        print("=" * 78)
        print(f"{'ID':<4} {'Name':<24} {'Files':<8} {'Target Size':<12} {'Tier':<10} {'Duplicate Ratio'}")
        print("-" * 78)
        for cid, prof in NAMED_PROFILES.items():
            tier = "DEV ONLY" if prof.developer_hardware_only else "CI"
            target_str = f"~{prof.target_bytes // (1024*1024)} MB"
            print(
                f"{cid:<4} {prof.name:<24} {prof.file_count:<8} {target_str:<12} {tier:<10} {prof.duplicate_ratio*100:.0f}%"
            )
            print(f"     Description: {prof.description}")
        return

    if args.validate:
        target_path = Path(args.validate)
        print(f"Validating corpus manifest at: {target_path}")
        is_valid, errors = validate_manifest(target_path)
        if is_valid:
            print("PASS: Manifest and corpus tree are 100% sound, verified, and consistent.")
            sys.exit(0)
        else:
            print(f"FAIL: Manifest validation encountered {len(errors)} errors:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    profile = NAMED_PROFILES[args.corpus]
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = Path(args.out_dir) if args.out_dir else (repo_root / "benchmarks" / "corpora" / args.corpus)

    tier_label = "[DEVELOPER-HARDWARE-ONLY]" if profile.developer_hardware_only else "[CI]"
    print(f"Generating Benchmark Corpus: {profile.corpus_id} ({profile.name}) {tier_label}")
    print(f"  Target directory: {out_dir}")
    print(f"  Seed:             {args.seed}")
    print(f"  Scale:            {args.scale}")

    try:
        out_path, manifest = generate_corpus(
            profile=profile,
            out_dir=out_dir,
            seed=args.seed,
            scale=args.scale,
            allow_developer_hardware=args.allow_developer_hardware,
        )
        print("Corpus generation SUCCESS:")
        print(f"  Files written:              {manifest.file_count}")
        print(f"  Total bytes:                {manifest.total_bytes} ({manifest.total_bytes / (1024*1024):.2f} MB)")
        print(f"  Duplicate ratio:            {manifest.duplicate_ratio * 100:.1f}%")
        print(f"  Duplicate groups:           {manifest.duplicate_groups}")
        print(f"  Duplicate files:            {manifest.duplicate_files}")
        print(f"  Same-size candidates:       {manifest.same_size_candidate_files}")
        print(f"  Expected reclaimable bytes: {manifest.expected_reclaimable_bytes}")
        print(f"  Expected result digest:     {manifest.expected_result_digest}")
        print(f"  Manifest written to:        {out_path / MANIFEST_FILENAME}")
    except PermissionError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
