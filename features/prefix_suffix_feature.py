"""
Feature. Prefix-Suffix
등록 도메인에 하이픈(-)이 포함되어 있는지 판별한다.

반환값:
     1 : 하이픈 없음
    -1 : 하이픈 있음
"""

from typing import Optional
from urllib.parse import urlparse


COMMON_SECOND_LEVEL_TLDS = {
    "ac",
    "co",
    "com",
    "edu",
    "go",
    "gov",
    "net",
    "or",
    "org",
    "re",
}


def _get_registered_domain_label(hostname: str) -> Optional[str]:
    labels = hostname.split(".")

    if len(labels) < 2:
        return None

    if len(labels) >= 3 and labels[-2] in COMMON_SECOND_LEVEL_TLDS:
        return labels[-3]

    return labels[-2]


def prefix_suffix_feature(url: str) -> int:
    try:
        hostname = urlparse(url).hostname
        if hostname is None:
            return -1

        hostname = hostname.lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        registered_domain = _get_registered_domain_label(hostname)
        if registered_domain is None:
            return -1

        return -1 if "-" in registered_domain else 1
    except Exception:
        return -1
