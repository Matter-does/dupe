"""View models transforming raw dupe engine output for GUI presentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def format_bytes(num_bytes: int) -> str:
    """Format byte counts into human-friendly strings with exact counts."""
    if num_bytes < 0:
        return f"{num_bytes} B"
    if num_bytes < 1024:
        return f"{num_bytes} B"

    units = ["KB", "MB", "GB", "TB", "PB"]
    val = float(num_bytes)
    unit_str = "KB"
    for u in units:
        val /= 1024.0
        unit_str = u
        if val < 1024.0:
            break

    return f"{val:.2f} {unit_str} ({num_bytes:,} bytes)"


@dataclass(frozen=True)
class DuplicateGroupItem:
    """Single duplicate group item for GUI presentation."""
    group_index: int
    digest: str
    size: int
    size_formatted: str
    reclaimable_bytes: int
    reclaimable_formatted: str
    file_count: int
    files: list[str]


@dataclass(frozen=True)
class DuplicateViewModel:
    """View model for duplicate analysis results."""
    files_scanned: int
    hash_candidates: int
    duplicate_groups_count: int
    reclaimable_bytes: int
    reclaimable_formatted: str
    groups: list[DuplicateGroupItem]

    @classmethod
    def from_engine_data(cls, data: dict[str, Any]) -> DuplicateViewModel:
        """Construct DuplicateViewModel from validated Phase 3 engine JSON."""
        files_scanned = int(data.get("files_scanned", 0))
        hash_candidates = int(data.get("hash_candidates", 0))
        reclaimable = int(data.get("reclaimable_bytes", 0))

        raw_groups = data.get("duplicate_groups", [])
        groups: list[DuplicateGroupItem] = []
        for idx, g in enumerate(raw_groups, start=1):
            digest = str(g.get("hash", ""))
            size = int(g.get("size", 0))
            rec = int(g.get("reclaimable_bytes", 0))
            files = [str(f) for f in g.get("files", [])]
            groups.append(
                DuplicateGroupItem(
                    group_index=idx,
                    digest=digest,
                    size=size,
                    size_formatted=format_bytes(size),
                    reclaimable_bytes=rec,
                    reclaimable_formatted=format_bytes(rec),
                    file_count=len(files),
                    files=files,
                )
            )

        return cls(
            files_scanned=files_scanned,
            hash_candidates=hash_candidates,
            duplicate_groups_count=len(groups),
            reclaimable_bytes=reclaimable,
            reclaimable_formatted=format_bytes(reclaimable),
            groups=groups,
        )


@dataclass(frozen=True)
class ChecksumEntryItem:
    """Single checksum entry for GUI presentation."""
    index: int
    path: str
    size: int
    size_formatted: str
    sha256: str


@dataclass(frozen=True)
class ChecksumViewModel:
    """View model for checksum inventory results."""
    root: str
    total_files: int
    total_bytes: int
    total_bytes_formatted: str
    entries: list[ChecksumEntryItem]

    @classmethod
    def from_engine_data(cls, data: dict[str, Any]) -> ChecksumViewModel:
        """Construct ChecksumViewModel from validated T007 engine JSON."""
        root = str(data.get("root", ""))
        summary = data.get("summary", {})
        total_files = int(summary.get("total_files", 0))
        total_bytes = int(summary.get("total_bytes", 0))

        raw_entries = data.get("entries", [])
        entries: list[ChecksumEntryItem] = []
        for idx, e in enumerate(raw_entries, start=1):
            path = str(e.get("path", ""))
            size = int(e.get("size", 0))
            digest = str(e.get("sha256", ""))
            entries.append(
                ChecksumEntryItem(
                    index=idx,
                    path=path,
                    size=size,
                    size_formatted=format_bytes(size),
                    sha256=digest,
                )
            )

        return cls(
            root=root,
            total_files=total_files,
            total_bytes=total_bytes,
            total_bytes_formatted=format_bytes(total_bytes),
            entries=entries,
        )
