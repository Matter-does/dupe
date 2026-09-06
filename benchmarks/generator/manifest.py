"""Corpus manifest schema definition, serialization, and validation.

Schema Version 1 Specification (per T004 / docs/RESEARCH.md §12.3):
{
  "schema_version": 1,
  "corpus_id": "C5",
  "seed": 12345,
  "generator_version": "git-sha",
  "file_count": 20000,
  "total_bytes": 1073741824,
  "duplicate_ratio": 0.3,
  "duplicate_groups": 1500,
  "duplicate_files": 6000,
  "same_size_candidate_files": 20000,
  "size_profile": "same_size_adversarial",
  "directory_shape": "shallow_wide",
  "similarity_profile": "distinct",
  "expected_reclaimable_bytes": 241172480,
  "expected_result_digest": "sha256-of-deterministic-json-output",
  "developer_hardware_only": false
}
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Optional

if __package__ is None or __package__ == "":
    _repo_root = str(Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from benchmarks.generator.profiles import (
        CI_STORAGE_CEILING_BYTES,
        DirectoryShape,
        SimilarityProfile,
        SizeProfile,
    )
else:
    from .profiles import (
        CI_STORAGE_CEILING_BYTES,
        DirectoryShape,
        SimilarityProfile,
        SizeProfile,
    )

SCHEMA_VERSION = 1
MANIFEST_FILENAME = "manifest.json"


@dataclass
class Manifest:
    schema_version: int
    corpus_id: str
    seed: int
    generator_version: str
    file_count: int
    total_bytes: int
    duplicate_ratio: float
    duplicate_groups: int
    duplicate_files: int
    same_size_candidate_files: int
    size_profile: str
    directory_shape: str
    similarity_profile: str
    expected_reclaimable_bytes: int
    expected_result_digest: str
    developer_hardware_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = {
            "schema_version": self.schema_version,
            "corpus_id": self.corpus_id,
            "seed": self.seed,
            "generator_version": self.generator_version,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "duplicate_ratio": round(float(self.duplicate_ratio), 6),
            "duplicate_groups": self.duplicate_groups,
            "duplicate_files": self.duplicate_files,
            "same_size_candidate_files": self.same_size_candidate_files,
            "size_profile": self.size_profile,
            "directory_shape": self.directory_shape,
            "similarity_profile": self.similarity_profile,
            "expected_reclaimable_bytes": self.expected_reclaimable_bytes,
            "expected_result_digest": self.expected_result_digest,
            "developer_hardware_only": self.developer_hardware_only,
        }
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manifest:
        return cls(
            schema_version=int(data["schema_version"]),
            corpus_id=str(data["corpus_id"]),
            seed=int(data["seed"]),
            generator_version=str(data["generator_version"]),
            file_count=int(data["file_count"]),
            total_bytes=int(data["total_bytes"]),
            duplicate_ratio=float(data["duplicate_ratio"]),
            duplicate_groups=int(data["duplicate_groups"]),
            duplicate_files=int(data["duplicate_files"]),
            same_size_candidate_files=int(data["same_size_candidate_files"]),
            size_profile=str(data["size_profile"]),
            directory_shape=str(data["directory_shape"]),
            similarity_profile=str(data["similarity_profile"]),
            expected_reclaimable_bytes=int(data["expected_reclaimable_bytes"]),
            expected_result_digest=str(data["expected_result_digest"]),
            developer_hardware_only=bool(data.get("developer_hardware_only", False)),
        )

    @classmethod
    def from_file(cls, path: Path | str) -> Manifest:
        p = Path(path)
        if p.is_dir():
            p = p / MANIFEST_FILENAME
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def discover_corpus_files(root: Path) -> list[Path]:
    """Recursively discover regular files in deterministic depth-first directory order,
    sorting entry names in each directory (matching J2 scan.j2 and Phase 4 oracle).
    Excludes manifest.json metadata file."""
    files: list[Path] = []
    if not root.is_dir():
        return files
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.is_dir():
            files.extend(discover_corpus_files(entry))
        elif entry.is_file():
            # Exclude manifest.json itself from corpus payload
            if entry.name == MANIFEST_FILENAME and entry.parent == root:
                continue
            files.append(entry)
    return files


def compute_oracle_result(corpus_root: Path) -> dict[str, Any]:
    """Independent reference oracle producing the deterministic JSON output structure.
    Paths in 'files' are relative to corpus_root (forward slashes)."""
    files = discover_corpus_files(corpus_root)

    by_size: dict[int, list[Path]] = {}
    for path in files:
        by_size.setdefault(path.stat().st_size, []).append(path)

    # Size filtering preserving discovery order
    candidates = [p for p in files if len(by_size[p.stat().st_size]) >= 2]

    by_hash: dict[str, list[str]] = {}
    sizes: dict[str, int] = {}
    hash_order: list[str] = []

    for path in candidates:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest not in by_hash:
            by_hash[digest] = []
            sizes[digest] = len(data)
            hash_order.append(digest)
        # Relative posix path
        rel_posix = path.relative_to(corpus_root).as_posix()
        by_hash[digest].append(rel_posix)

    groups = []
    for digest in hash_order:
        paths = by_hash[digest]
        if len(paths) < 2:
            continue
        size = sizes[digest]
        groups.append(
            {
                "hash": digest,
                "size": size,
                "files": paths,
                "reclaimable_bytes": (len(paths) - 1) * size,
            }
        )

    return {
        "files_scanned": len(files),
        "hash_candidates": len(candidates),
        "duplicate_groups": groups,
        "reclaimable_bytes": sum(g["reclaimable_bytes"] for g in groups),
    }


def format_deterministic_json(oracle_result: dict[str, Any]) -> str:
    """Format oracle result into the exact compact deterministic JSON string
    emitted by dupe (zero whitespace around separators)."""
    return json.dumps(oracle_result, separators=(",", ":"))


def compute_result_digest(oracle_result_or_json: dict[str, Any] | str) -> str:
    """Compute the SHA-256 digest of the UTF-8 bytes of deterministic JSON output."""
    if isinstance(oracle_result_or_json, dict):
        json_str = format_deterministic_json(oracle_result_or_json)
    else:
        json_str = oracle_result_or_json
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def validate_manifest(
    target: Path | str,
    raise_on_error: bool = False,
) -> tuple[bool, list[str]]:
    """Strictly validate a manifest and its corresponding corpus file tree.
    Returns (is_valid, list_of_errors)."""
    errors: list[str] = []
    p = Path(target)
    if p.is_dir():
        manifest_file = p / MANIFEST_FILENAME
        corpus_root = p
    else:
        manifest_file = p
        corpus_root = p.parent

    if not manifest_file.is_file():
        errors.append(f"Manifest file not found: {manifest_file}")
        if raise_on_error:
            raise FileNotFoundError(errors[-1])
        return False, errors

    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Manifest JSON decode error: {exc}")
        if raise_on_error:
            raise ValueError(errors[-1]) from exc
        return False, errors

    # Required fields per T004 specification
    required_fields = {
        "schema_version": int,
        "corpus_id": str,
        "seed": int,
        "generator_version": str,
        "file_count": int,
        "total_bytes": int,
        "duplicate_ratio": (float, int),
        "duplicate_groups": int,
        "duplicate_files": int,
        "same_size_candidate_files": int,
        "size_profile": str,
        "directory_shape": str,
        "similarity_profile": str,
        "expected_reclaimable_bytes": int,
        "expected_result_digest": str,
    }

    for field, exp_type in required_fields.items():
        if field not in data:
            errors.append(f"Missing required field in manifest: '{field}'")
        elif not isinstance(data[field], exp_type):
            errors.append(
                f"Field '{field}' has invalid type: expected {exp_type}, got {type(data[field])}"
            )

    if errors:
        if raise_on_error:
            raise ValueError("; ".join(errors))
        return False, errors

    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(
            f"Unsupported schema_version: expected {SCHEMA_VERSION}, got {data['schema_version']}"
        )

    # Validate closed enums
    valid_size_profiles = {e.value for e in SizeProfile}
    if data["size_profile"] not in valid_size_profiles:
        errors.append(
            f"Invalid size_profile '{data['size_profile']}', must be one of {sorted(valid_size_profiles)}"
        )

    valid_shapes = {e.value for e in DirectoryShape}
    if data["directory_shape"] not in valid_shapes:
        errors.append(
            f"Invalid directory_shape '{data['directory_shape']}', must be one of {sorted(valid_shapes)}"
        )

    valid_sims = {e.value for e in SimilarityProfile}
    if data["similarity_profile"] not in valid_sims:
        errors.append(
            f"Invalid similarity_profile '{data['similarity_profile']}', must be one of {sorted(valid_sims)}"
        )

    # Validate digest format (64-char lowercase hex)
    if not re.fullmatch(r"[0-9a-f]{64}", data["expected_result_digest"]):
        errors.append(
            f"Invalid expected_result_digest format: '{data['expected_result_digest']}' (must be 64-char lowercase hex)"
        )

    # Validate mathematical consistency of manifest fields
    file_count = data["file_count"]
    dup_files = data["duplicate_files"]
    dup_groups = data["duplicate_groups"]
    dup_ratio = float(data["duplicate_ratio"])
    expected_ratio = round(dup_files / file_count, 6) if file_count > 0 else 0.0

    if abs(dup_ratio - expected_ratio) > 0.001:
        errors.append(
            f"duplicate_ratio mismatch: manifest says {dup_ratio}, but duplicate_files/file_count = {expected_ratio}"
        )

    if dup_groups > 0 and dup_files < 2 * dup_groups:
        errors.append(
            f"duplicate_files ({dup_files}) must be >= 2 * duplicate_groups ({dup_groups})"
        )

    if data["same_size_candidate_files"] < dup_files:
        errors.append(
            f"same_size_candidate_files ({data['same_size_candidate_files']}) must be >= duplicate_files ({dup_files})"
        )

    dev_only = bool(data.get("developer_hardware_only", False))
    if not dev_only and data["total_bytes"] > CI_STORAGE_CEILING_BYTES:
        errors.append(
            f"total_bytes ({data['total_bytes']}) exceeds CI ceiling ({CI_STORAGE_CEILING_BYTES}) "
            f"but developer_hardware_only is not True"
        )

    if data["corpus_id"] == "C3" and not dev_only:
        errors.append("Corpus C3 must have developer_hardware_only: true")

    # Validate filesystem tree against manifest
    actual_files = discover_corpus_files(corpus_root)
    if len(actual_files) != file_count:
        errors.append(
            f"File count mismatch: manifest says {file_count}, actual tree has {len(actual_files)}"
        )

    actual_total_bytes = sum(f.stat().st_size for f in actual_files)
    if actual_total_bytes != data["total_bytes"]:
        errors.append(
            f"Total bytes mismatch: manifest says {data['total_bytes']}, actual tree has {actual_total_bytes}"
        )

    # Run reference oracle and compare
    oracle_out = compute_oracle_result(corpus_root)
    if oracle_out["files_scanned"] != file_count:
        errors.append(
            f"Oracle files_scanned mismatch: expected {file_count}, got {oracle_out['files_scanned']}"
        )

    if oracle_out["hash_candidates"] != data["same_size_candidate_files"]:
        errors.append(
            f"Candidate files mismatch: manifest says {data['same_size_candidate_files']}, "
            f"oracle found {oracle_out['hash_candidates']}"
        )

    if len(oracle_out["duplicate_groups"]) != dup_groups:
        errors.append(
            f"Duplicate groups count mismatch: manifest says {dup_groups}, "
            f"oracle found {len(oracle_out['duplicate_groups'])}"
        )

    actual_dup_files = sum(len(g["files"]) for g in oracle_out["duplicate_groups"])
    if actual_dup_files != dup_files:
        errors.append(
            f"Duplicate files count mismatch: manifest says {dup_files}, "
            f"oracle found {actual_dup_files}"
        )

    if oracle_out["reclaimable_bytes"] != data["expected_reclaimable_bytes"]:
        errors.append(
            f"Reclaimable bytes mismatch: manifest says {data['expected_reclaimable_bytes']}, "
            f"oracle calculated {oracle_out['reclaimable_bytes']}"
        )

    # Verify soundness: check all duplicates in each group are byte-identical
    for group in oracle_out["duplicate_groups"]:
        g_files = group["files"]
        if len(g_files) < 2:
            errors.append(f"Duplicate group has < 2 files: {group}")
            continue
        first_bytes = (corpus_root / g_files[0]).read_bytes()
        for other in g_files[1:]:
            other_bytes = (corpus_root / other).read_bytes()
            if other_bytes != first_bytes:
                errors.append(
                    f"Soundness failure in group: {g_files[0]} and {other} are not byte-identical!"
                )

    # Verify deterministic JSON digest
    computed_digest = compute_result_digest(oracle_out)
    if computed_digest != data["expected_result_digest"]:
        errors.append(
            f"expected_result_digest mismatch: manifest says {data['expected_result_digest']}, "
            f"computed {computed_digest}"
        )

    if errors and raise_on_error:
        raise ValueError("; ".join(errors))

    return len(errors) == 0, errors
