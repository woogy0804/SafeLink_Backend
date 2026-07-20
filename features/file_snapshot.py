"""Helpers for caching local metric files without serving stale replacements."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    modified_ns: int
    size: int


def get_file_snapshot(path: Path) -> Optional[FileSnapshot]:
    """Return a cache key that changes when a local file is replaced."""

    try:
        resolved_path = path.resolve(strict=True)
        metadata = resolved_path.stat()
    except OSError:
        return None

    if not resolved_path.is_file():
        return None
    return FileSnapshot(
        path=str(resolved_path),
        modified_ns=metadata.st_mtime_ns,
        size=metadata.st_size,
    )
