"""
Feature. Prefix-Suffix
등록 도메인에 하이픈(-)이 포함되어 있는지 판별한다.

반환값:
     1 : 하이픈 없음
    -1 : 하이픈 있음
"""

from features.domain_utils import get_registered_domain_from_url


def prefix_suffix_feature(url: str) -> int:
    try:
        registered_domain = get_registered_domain_from_url(url)
        if registered_domain is None:
            return -1

        return -1 if "-" in registered_domain else 1
    except Exception:
        return -1
