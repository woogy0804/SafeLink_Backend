"""Read-only SQLite access for large external feature metric snapshots."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


@dataclass(frozen=True)
class MetricQueryResult:
    available: bool
    value: Optional[int]


def is_sqlite_path(path: Path) -> bool:
    return path.suffix.lower() in SQLITE_SUFFIXES


def _query_metric(
    path: Path,
    *,
    query: str,
    domain: str,
) -> MetricQueryResult:
    if not path.is_file():
        return MetricQueryResult(available=False, value=None)

    connection = None
    try:
        database_uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(
            database_uri,
            uri=True,
            timeout=1,
        )
        row = connection.execute(query, (domain,)).fetchone()
        if row is None:
            return MetricQueryResult(available=True, value=None)
        return MetricQueryResult(available=True, value=int(row[0]))
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return MetricQueryResult(available=False, value=None)
    finally:
        if connection is not None:
            connection.close()


def query_tranco_rank(path: Path, domain: str) -> MetricQueryResult:
    return _query_metric(
        path,
        query="SELECT rank FROM tranco_ranks WHERE domain = ?",
        domain=domain,
    )


def query_backlink_count(path: Path, domain: str) -> MetricQueryResult:
    return _query_metric(
        path,
        query="SELECT count FROM backlink_counts WHERE domain = ?",
        domain=domain,
    )
