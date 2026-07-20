"""Fetch live referring-root-domain counts from DataForSEO in batches."""

import argparse
import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

from features.domain_utils import get_registered_domain
from scripts.build_metric_snapshot import (
    DEFAULT_BACKLINK_DATABASE,
    build_backlink_database,
)


API_URL = "https://api.dataforseo.com/v3/backlinks/bulk_referring_domains/live"
DEFAULT_CSV = Path(__file__).resolve().parents[1] / "features" / "backlink_counts.csv"
MAX_TARGETS_PER_REQUEST = 1000
REQUEST_TIMEOUT_SECONDS = 30
COUNT_DEFINITION = "live_referring_main_domains"


class DataForSeoError(RuntimeError):
    pass


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def load_domains(path: Path) -> list[str]:
    domains = set()
    with path.open(encoding="utf-8-sig", newline="") as input_file:
        for row in csv.reader(input_file):
            if not row:
                continue
            domain = get_registered_domain(row[0].strip())
            if domain is not None:
                domains.add(domain)
    if not domains:
        raise ValueError(f"No valid domains were found in {path}")
    return sorted(domains)


def parse_counts(payload: dict, expected_targets: set[str]) -> dict[str, int]:
    if payload.get("status_code") != 20000:
        raise DataForSeoError(
            f"DataForSEO request failed: {payload.get('status_code')} "
            f"{payload.get('status_message', '')}".strip()
        )

    counts: dict[str, int] = {}
    for task in payload.get("tasks") or []:
        if task.get("status_code") != 20000:
            raise DataForSeoError(
                f"DataForSEO task failed: {task.get('status_code')} "
                f"{task.get('status_message', '')}".strip()
            )
        for result in task.get("result") or []:
            for item in result.get("items") or []:
                target = get_registered_domain(str(item.get("target", "")))
                count = item.get("referring_main_domains")
                if target in expected_targets and isinstance(count, int) and count >= 0:
                    counts[target] = count

    missing = expected_targets.difference(counts)
    if missing:
        preview = ", ".join(sorted(missing)[:5])
        raise DataForSeoError(
            f"DataForSEO omitted {len(missing)} requested targets: {preview}"
        )
    return counts


def fetch_counts(
    domains: list[str],
    *,
    login: str,
    password: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for batch in _chunks(domains, MAX_TARGETS_PER_REQUEST):
        response = requests.post(
            API_URL,
            auth=(login, password),
            json=[{"targets": batch}],
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        counts.update(parse_counts(response.json(), set(batch)))
    return counts


def write_csv_atomic(path: Path, counts: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(("domain", "count"))
            writer.writerows(sorted(counts.items()))
        Path(temporary_name).replace(path)
    except Exception:
        try:
            Path(temporary_name).unlink()
        except FileNotFoundError:
            pass
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domains", type=Path, help="CSV/text file; domain in column 1")
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-db", type=Path, default=DEFAULT_BACKLINK_DATABASE)
    parser.add_argument("--minimum-rows", type=int, default=1)
    return parser


def main() -> None:
    arguments = _build_parser().parse_args()
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise SystemExit("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required")

    domains = load_domains(arguments.domains)
    counts = fetch_counts(domains, login=login, password=password)
    write_csv_atomic(arguments.output_csv, counts)
    observed_at = datetime.now(timezone.utc).isoformat()
    row_count = build_backlink_database(
        arguments.output_csv,
        arguments.output_db,
        source="dataforseo-bulk-referring-domains-live",
        observed_at=observed_at,
        count_definition=COUNT_DEFINITION,
        minimum_rows=arguments.minimum_rows,
    )
    print(f"Updated {row_count:,} backlink domain counts at {observed_at}")


if __name__ == "__main__":
    main()
