"""Build compact SQLite snapshots for Tranco and backlink feature data."""

import argparse
import csv
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from features.domain_utils import get_registered_domain


DEFAULT_TRANCO_DATABASE = (
    Path(__file__).resolve().parents[1] / "features" / "tranco_ranks.sqlite3"
)
DEFAULT_BACKLINK_DATABASE = (
    Path(__file__).resolve().parents[1] / "features" / "backlink_counts.sqlite3"
)


def _normalized_domain(value: str) -> Optional[str]:
    return get_registered_domain(value.strip())


def _temporary_database_path(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    os.close(descriptor)
    return Path(temporary_name)


def _initialize_metadata(
    connection: sqlite3.Connection,
    metadata: dict[str, str],
) -> None:
    connection.execute(
        "CREATE TABLE snapshot_metadata "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID"
    )
    connection.executemany(
        "INSERT INTO snapshot_metadata (key, value) VALUES (?, ?)",
        sorted(metadata.items()),
    )


def _finalize_database(
    connection: sqlite3.Connection,
    temporary_path: Path,
    output_path: Path,
) -> None:
    connection.commit()
    check_result = connection.execute("PRAGMA quick_check").fetchone()
    if check_result != ("ok",):
        raise ValueError("생성된 SQLite 스냅샷 검증에 실패했습니다.")
    connection.close()
    temporary_path.replace(output_path)


def _cleanup_failed_build(
    connection: Optional[sqlite3.Connection],
    temporary_path: Path,
) -> None:
    if connection is not None:
        connection.close()
    try:
        temporary_path.unlink()
    except FileNotFoundError:
        pass


def build_tranco_database(
    input_csv: Path,
    output_path: Path = DEFAULT_TRANCO_DATABASE,
    *,
    source: str = "local-csv",
    snapshot_id: str = "unknown",
    minimum_rows: int = 1,
) -> int:
    temporary_path = _temporary_database_path(output_path)
    connection = None
    try:
        connection = sqlite3.connect(temporary_path)
        connection.execute(
            "CREATE TABLE tranco_ranks "
            "(domain TEXT PRIMARY KEY, rank INTEGER NOT NULL CHECK(rank > 0)) "
            "WITHOUT ROWID"
        )

        with input_csv.open(encoding="utf-8-sig", newline="") as input_file:
            for row in csv.reader(input_file):
                if len(row) < 2:
                    continue
                try:
                    rank = int(row[0].strip().replace(",", ""))
                except ValueError:
                    continue
                domain = _normalized_domain(row[1])
                if domain is None or rank < 1:
                    continue
                connection.execute(
                    "INSERT INTO tranco_ranks (domain, rank) VALUES (?, ?) "
                    "ON CONFLICT(domain) DO UPDATE SET rank = MIN(rank, excluded.rank)",
                    (domain, rank),
                )

        row_count = int(
            connection.execute("SELECT COUNT(*) FROM tranco_ranks").fetchone()[0]
        )
        if row_count < minimum_rows:
            raise ValueError(
                f"Tranco 유효 행이 너무 적습니다: {row_count} < {minimum_rows}"
            )

        _initialize_metadata(
            connection,
            {
                "built_at": datetime.now(timezone.utc).isoformat(),
                "row_count": str(row_count),
                "snapshot_id": snapshot_id,
                "source": source,
                "type": "tranco",
            },
        )
        _finalize_database(connection, temporary_path, output_path)
        connection = None
        return row_count
    except Exception:
        _cleanup_failed_build(connection, temporary_path)
        raise


def build_backlink_database(
    input_csv: Path,
    output_path: Path = DEFAULT_BACKLINK_DATABASE,
    *,
    source: str,
    observed_at: str,
    minimum_rows: int = 1,
) -> int:
    temporary_path = _temporary_database_path(output_path)
    connection = None
    try:
        connection = sqlite3.connect(temporary_path)
        connection.execute(
            "CREATE TABLE backlink_counts "
            "(domain TEXT PRIMARY KEY, count INTEGER NOT NULL CHECK(count >= 0)) "
            "WITHOUT ROWID"
        )

        with input_csv.open(encoding="utf-8-sig", newline="") as input_file:
            for row in csv.reader(input_file):
                if len(row) < 2:
                    continue
                domain = _normalized_domain(row[0])
                try:
                    count = int(row[1].strip().replace(",", ""))
                except ValueError:
                    continue
                if domain is None or count < 0:
                    continue
                connection.execute(
                    "INSERT INTO backlink_counts (domain, count) VALUES (?, ?) "
                    "ON CONFLICT(domain) DO UPDATE SET count = MAX(count, excluded.count)",
                    (domain, count),
                )

        row_count = int(
            connection.execute("SELECT COUNT(*) FROM backlink_counts").fetchone()[0]
        )
        if row_count < minimum_rows:
            raise ValueError(
                f"백링크 유효 행이 너무 적습니다: {row_count} < {minimum_rows}"
            )

        _initialize_metadata(
            connection,
            {
                "built_at": datetime.now(timezone.utc).isoformat(),
                "observed_at": observed_at,
                "row_count": str(row_count),
                "source": source,
                "type": "backlink",
            },
        )
        _finalize_database(connection, temporary_path, output_path)
        connection = None
        return row_count
    except Exception:
        _cleanup_failed_build(connection, temporary_path)
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    tranco_parser = subparsers.add_parser("tranco")
    tranco_parser.add_argument("input_csv", type=Path)
    tranco_parser.add_argument("--output", type=Path, default=DEFAULT_TRANCO_DATABASE)
    tranco_parser.add_argument("--source", default="local-csv")
    tranco_parser.add_argument("--snapshot-id", default="unknown")
    tranco_parser.add_argument("--minimum-rows", type=int, default=100_000)

    backlink_parser = subparsers.add_parser("backlinks")
    backlink_parser.add_argument("input_csv", type=Path)
    backlink_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BACKLINK_DATABASE,
    )
    backlink_parser.add_argument("--source", required=True)
    backlink_parser.add_argument("--observed-at", required=True)
    backlink_parser.add_argument("--minimum-rows", type=int, default=1)
    return parser


def main() -> None:
    arguments = _build_parser().parse_args()
    if arguments.command == "tranco":
        row_count = build_tranco_database(
            arguments.input_csv,
            arguments.output,
            source=arguments.source,
            snapshot_id=arguments.snapshot_id,
            minimum_rows=arguments.minimum_rows,
        )
    else:
        row_count = build_backlink_database(
            arguments.input_csv,
            arguments.output,
            source=arguments.source,
            observed_at=arguments.observed_at,
            minimum_rows=arguments.minimum_rows,
        )
    print(f"완료: {row_count:,}개 도메인 -> {arguments.output}")


if __name__ == "__main__":
    main()
