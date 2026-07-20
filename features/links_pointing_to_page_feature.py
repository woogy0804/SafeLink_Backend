"""
Feature. Links Pointing to Page
로컬 백링크 CSV에서 등록 도메인을 가리키는 외부 링크 개수를 조회한다.

기본 파일: features/backlink_counts.csv (domain,count)
반환값:
     1 : 백링크 3개 이상
     0 : 백링크 1~2개 또는 데이터 파일 없음
    -1 : 백링크 없음
"""

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from features.domain_utils import get_registered_domain, get_registered_domain_from_url
from features.file_snapshot import FileSnapshot, get_file_snapshot
from features.metric_database import is_sqlite_path, query_backlink_count


DEFAULT_BACKLINK_FILE = Path(__file__).parent / "backlink_counts.csv"
DEFAULT_BACKLINK_DATABASE = Path(__file__).parent / "backlink_counts.sqlite3"


def _backlink_file_path() -> Path:
    configured_path = os.getenv("SAFELINK_BACKLINK_FILE")
    if configured_path:
        return Path(configured_path)
    if DEFAULT_BACKLINK_DATABASE.is_file():
        return DEFAULT_BACKLINK_DATABASE
    return DEFAULT_BACKLINK_FILE


@lru_cache(maxsize=4)
def _load_backlink_counts_snapshot(
    snapshot: FileSnapshot,
) -> Optional[Dict[str, int]]:
    path = Path(snapshot.path)

    counts = {}
    with path.open(encoding="utf-8-sig", newline="") as backlink_file:
        for row in csv.reader(backlink_file):
            if len(row) < 2:
                continue
            try:
                count = int(row[1].strip().replace(",", ""))
            except ValueError:
                continue
            registered_domain = get_registered_domain(row[0].strip())
            if registered_domain is None or count < 0:
                continue
            counts[registered_domain] = max(
                count,
                counts.get(registered_domain, 0),
            )
    return counts or None


def _load_backlink_counts(path_string: str) -> Optional[Dict[str, int]]:
    snapshot = get_file_snapshot(Path(path_string))
    if snapshot is None:
        return None
    return _load_backlink_counts_snapshot(snapshot)


def clear_backlink_cache() -> None:
    _load_backlink_counts_snapshot.cache_clear()


def links_pointing_to_page_feature(url: str) -> int:
    try:
        registered_domain = get_registered_domain_from_url(url)
        if registered_domain is None:
            return -1

        backlink_path = _backlink_file_path()
        if is_sqlite_path(backlink_path):
            query_result = query_backlink_count(
                backlink_path,
                registered_domain,
            )
            if not query_result.available or query_result.value is None:
                return 0
            backlink_count = query_result.value
            if backlink_count < 0:
                return 0
            if backlink_count == 0:
                return -1
            if backlink_count <= 2:
                return 0
            return 1

        counts = _load_backlink_counts(str(backlink_path))
        if counts is None:
            return 0

        backlink_count = counts.get(registered_domain)
        if backlink_count is None:
            # 데이터에 없는 도메인은 '0개로 관측됨'이 아니라 '미수집'이다.
            return 0
        if backlink_count == 0:
            return -1
        if backlink_count <= 2:
            return 0
        return 1
    except Exception:
        return 0
