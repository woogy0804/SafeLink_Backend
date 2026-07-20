"""
Feature. Web Traffic
로컬 Tranco 형식 CSV에서 등록 도메인의 순위를 조회한다.

기본 파일: features/tranco_top_domains.csv (rank,domain)
반환값:
     1 : 100,000위 이내
     0 : 100,000위 밖 또는 순위 데이터 파일 없음
    -1 : 순위 데이터에는 있으나 대상 도메인이 없음
"""

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from features.domain_utils import get_registered_domain, get_registered_domain_from_url
from features.file_snapshot import FileSnapshot, get_file_snapshot
from features.metric_database import is_sqlite_path, query_tranco_rank


DEFAULT_RANK_FILE = Path(__file__).parent / "tranco_top_domains.csv"
DEFAULT_RANK_DATABASE = Path(__file__).parent / "tranco_ranks.sqlite3"
SAFE_RANK_THRESHOLD = 100_000


def _rank_file_path() -> Path:
    configured_path = os.getenv("SAFELINK_TRANCO_FILE")
    if configured_path:
        return Path(configured_path)
    if DEFAULT_RANK_DATABASE.is_file():
        return DEFAULT_RANK_DATABASE
    return DEFAULT_RANK_FILE


@lru_cache(maxsize=4)
def _load_domain_ranks_snapshot(snapshot: FileSnapshot) -> Optional[Dict[str, int]]:
    path = Path(snapshot.path)

    ranks = {}
    with path.open(encoding="utf-8-sig", newline="") as rank_file:
        for row in csv.reader(rank_file):
            if len(row) < 2:
                continue
            try:
                rank = int(row[0].strip().replace(",", ""))
            except ValueError:
                continue
            registered_domain = get_registered_domain(row[1].strip())
            if registered_domain is None or rank < 1:
                continue
            current_rank = ranks.get(registered_domain)
            if current_rank is None or rank < current_rank:
                ranks[registered_domain] = rank
    return ranks or None


def _load_domain_ranks(path_string: str) -> Optional[Dict[str, int]]:
    snapshot = get_file_snapshot(Path(path_string))
    if snapshot is None:
        return None
    return _load_domain_ranks_snapshot(snapshot)


def clear_web_traffic_cache() -> None:
    _load_domain_ranks_snapshot.cache_clear()


def web_traffic_feature(url: str) -> int:
    try:
        registered_domain = get_registered_domain_from_url(url)
        if registered_domain is None:
            return -1

        rank_path = _rank_file_path()
        if is_sqlite_path(rank_path):
            query_result = query_tranco_rank(rank_path, registered_domain)
            if not query_result.available:
                return 0
            rank = query_result.value
            if rank is None:
                return -1
            return 1 if rank <= SAFE_RANK_THRESHOLD else 0

        ranks = _load_domain_ranks(str(rank_path))
        if ranks is None:
            return 0

        rank = ranks.get(registered_domain)
        if rank is None:
            return -1
        return 1 if rank <= SAFE_RANK_THRESHOLD else 0
    except Exception:
        return 0
