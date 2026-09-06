"""Corpus profile definitions and named C1-C7 standard benchmark corpora.

Controlled Workload Dimensions (per T004 / docs/RESEARCH.md):
- Dimension A — File Count: 1K, 10K, 50K, 100K
- Dimension B — Total Data Size: 100 MB, 200 MB, 500 MB, 1 GB (CI), 5 GB (Dev only)
- Dimension C — Size Distribution (size_profile):
    tiny_heavy (<4 KB), small_heavy (4-64 KB), large_heavy (1-10 MB), mixed, same_size_adversarial
- Dimension D — Duplicate Ratio (duplicate_ratio = duplicate_files / total_files):
    0.0, 0.05, 0.10, 0.30, 0.50, 0.80, 0.90
- Dimension E — Same-Size Collision Density (collision_density):
    low, medium, high (adversarial)
- Dimension F — Tree Hierarchy (directory_shape):
    flat, shallow_wide, deep, mixed
- Dimension G — Content Similarity Structure (similarity_profile):
    distinct, shared_prefix, shared_suffix, exact
- Dimension H — Cache State (cache_state):
    initial_run, warm_repeated
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SizeProfile(str, Enum):
    TINY_HEAVY = "tiny_heavy"
    SMALL_HEAVY = "small_heavy"
    LARGE_HEAVY = "large_heavy"
    MIXED = "mixed"
    SAME_SIZE_ADVERSARIAL = "same_size_adversarial"


class DirectoryShape(str, Enum):
    FLAT = "flat"
    SHALLOW_WIDE = "shallow_wide"
    DEEP = "deep"
    MIXED = "mixed"


class SimilarityProfile(str, Enum):
    DISTINCT = "distinct"
    SHARED_PREFIX = "shared_prefix"
    SHARED_SUFFIX = "shared_suffix"
    EXACT = "exact"


class CacheState(str, Enum):
    INITIAL_RUN = "initial_run"
    WARM_REPEATED = "warm_repeated"


class CollisionDensity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Hard CI ceiling: 1 GB (1,073,741,824 bytes)
CI_STORAGE_CEILING_BYTES = 1024 * 1024 * 1024


@dataclass(frozen=True)
class CorpusProfile:
    corpus_id: str
    name: str
    description: str
    file_count: int
    target_bytes: int
    size_profile: SizeProfile
    directory_shape: DirectoryShape
    similarity_profile: SimilarityProfile
    duplicate_ratio: float
    collision_density: CollisionDensity
    cache_state: CacheState = CacheState.INITIAL_RUN
    developer_hardware_only: bool = False

    def validate(self) -> None:
        """Assert internal consistency and constraints."""
        if self.file_count <= 0:
            raise ValueError(f"file_count must be positive, got {self.file_count}")
        if self.target_bytes <= 0:
            raise ValueError(f"target_bytes must be positive, got {self.target_bytes}")
        if not (0.0 <= self.duplicate_ratio <= 1.0):
            raise ValueError(f"duplicate_ratio must be between 0.0 and 1.0, got {self.duplicate_ratio}")

        # Check CI storage ceiling
        if not self.developer_hardware_only and self.target_bytes > CI_STORAGE_CEILING_BYTES:
            raise ValueError(
                f"Corpus {self.corpus_id} has target_bytes={self.target_bytes} exceeding "
                f"CI storage ceiling ({CI_STORAGE_CEILING_BYTES} bytes) but is not marked developer_hardware_only"
            )

        # Ensure C3 is explicitly developer-hardware-only
        if self.corpus_id == "C3" and not self.developer_hardware_only:
            raise ValueError("Corpus C3 must be marked developer_hardware_only")

        # Ensure no cold cache terminology
        if "cold" in self.cache_state.value.lower():
            raise ValueError(f"Forbidden cache terminology '{self.cache_state.value}'. Must use warm-state/repeated-run.")


# Named standard corpora (C1–C7) per T004 specification and docs/RESEARCH.md
C1_PROFILE = CorpusProfile(
    corpus_id="C1",
    name="Metadata Heavy",
    description="Tiny files (<4 KB, avg 4 KB), wide tree, 5% duplicate ratio. Isolates discovery and metadata overhead.",
    file_count=50000,
    target_bytes=204800000,  # 50,000 * 4,096 bytes ~ 204.8 MB ~ 200 MB
    size_profile=SizeProfile.TINY_HEAVY,
    directory_shape=DirectoryShape.SHALLOW_WIDE,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.05,
    collision_density=CollisionDensity.MEDIUM,
    cache_state=CacheState.INITIAL_RUN,
    developer_hardware_only=False,
)

C2_PROFILE = CorpusProfile(
    corpus_id="C2",
    name="Balanced Baseline",
    description="Mixed sizes (avg 100 KB), balanced tree, 30% duplicate ratio. Realistic everyday filesystem baseline.",
    file_count=10000,
    target_bytes=1000000000,  # 10,000 * 100 KB = 1 GB (within CI limit)
    size_profile=SizeProfile.MIXED,
    directory_shape=DirectoryShape.MIXED,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.30,
    collision_density=CollisionDensity.MEDIUM,
    cache_state=CacheState.INITIAL_RUN,
    developer_hardware_only=False,
)

C3_PROFILE = CorpusProfile(
    corpus_id="C3",
    name="Large-File Throughput",
    description="Large files (1-10 MB), shallow tree, 10% duplicate ratio. Exceeds 1 GB CI cap; tests sequential I/O and hash throughput.",
    file_count=300,  # 200–500 files
    target_bytes=1500000000,  # ~1.5 GB (>1 GB CI limit, Developer-Hardware-Only)
    size_profile=SizeProfile.LARGE_HEAVY,
    directory_shape=DirectoryShape.SHALLOW_WIDE,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.10,
    collision_density=CollisionDensity.LOW,
    cache_state=CacheState.INITIAL_RUN,
    developer_hardware_only=True,
)

C4_PROFILE = CorpusProfile(
    corpus_id="C4",
    name="High Duplicate Density",
    description="80% duplicate ratio in large clusters. Stresses grouping, aggregation, and reclaimable-byte math.",
    file_count=10000,
    target_bytes=1000000000,  # ~1 GB
    size_profile=SizeProfile.MIXED,
    directory_shape=DirectoryShape.MIXED,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.80,
    collision_density=CollisionDensity.HIGH,
    cache_state=CacheState.INITIAL_RUN,
    developer_hardware_only=False,
)

C5_PROFILE = CorpusProfile(
    corpus_id="C5",
    name="Same-Size Adversarial",
    description="100% same-size candidate collision, distinct byte content. Forces all candidates into full SHA-256 hashing.",
    file_count=20000,
    target_bytes=1048560000,  # 20,000 * 52,428 bytes ~ 1 GB
    size_profile=SizeProfile.SAME_SIZE_ADVERSARIAL,
    directory_shape=DirectoryShape.SHALLOW_WIDE,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.30,
    collision_density=CollisionDensity.HIGH,
    cache_state=CacheState.INITIAL_RUN,
    developer_hardware_only=False,
)

C6_PROFILE = CorpusProfile(
    corpus_id="C6",
    name="Mixed Realistic",
    description="Power-law distribution, realistic hierarchy, 30% duplicates. Primary live demo workload.",
    file_count=10000,
    target_bytes=1000000000,  # ~1 GB
    size_profile=SizeProfile.MIXED,
    directory_shape=DirectoryShape.DEEP,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.30,
    collision_density=CollisionDensity.MEDIUM,
    cache_state=CacheState.INITIAL_RUN,
    developer_hardware_only=False,
)

C7_PROFILE = CorpusProfile(
    corpus_id="C7",
    name="Cache Transition",
    description="Repeated runs of C2/C6 (run 1 initial, runs 2-3 warm) to quantify warm-state transition and run-to-run variance.",
    file_count=10000,
    target_bytes=1000000000,  # ~1 GB
    size_profile=SizeProfile.MIXED,
    directory_shape=DirectoryShape.MIXED,
    similarity_profile=SimilarityProfile.DISTINCT,
    duplicate_ratio=0.30,
    collision_density=CollisionDensity.MEDIUM,
    cache_state=CacheState.WARM_REPEATED,
    developer_hardware_only=False,
)

NAMED_PROFILES: dict[str, CorpusProfile] = {
    "C1": C1_PROFILE,
    "C2": C2_PROFILE,
    "C3": C3_PROFILE,
    "C4": C4_PROFILE,
    "C5": C5_PROFILE,
    "C6": C6_PROFILE,
    "C7": C7_PROFILE,
}

# Self-validate all named profiles at import time
for p in NAMED_PROFILES.values():
    p.validate()
