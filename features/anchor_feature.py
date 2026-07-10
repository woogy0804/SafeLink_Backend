"""
Feature. URL of Anchor
HTML a 태그의 href 중 외부/비정상 링크 비율을 계산한다.

반환값:
     1 : 비정상 anchor 비율 < 31%
     0 : 31% <= 비정상 anchor 비율 <= 67%
    -1 : 비정상 anchor 비율 > 67%
"""

from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 5
INVALID_ANCHOR_PREFIXES = ("#", "javascript:", "mailto:", "tel:", "data:")


def _get_hostname(url: str) -> Optional[str]:
    hostname = urlparse(url).hostname
    if hostname is None:
        return None

    hostname = hostname.lower()
    return hostname[4:] if hostname.startswith("www.") else hostname


def _is_invalid_href(href: Optional[str]) -> bool:
    if href is None:
        return True

    normalized_href = href.strip().lower()
    return normalized_href == "" or normalized_href.startswith(INVALID_ANCHOR_PREFIXES)


def _is_unsafe_anchor(href: Optional[str], base_url: str, base_hostname: str) -> bool:
    if _is_invalid_href(href):
        return True

    href_url = urljoin(base_url, href.strip())
    href_hostname = _get_hostname(href_url)

    return href_hostname is None or href_hostname != base_hostname


def _classify_unsafe_ratio(unsafe_ratio: float) -> int:
    if unsafe_ratio < 31:
        return 1
    if unsafe_ratio <= 67:
        return 0
    return -1


def anchor_feature(url: str) -> int:
    """
    a 태그 href의 비정상 링크 비율을 기준으로 URL을 분류한다.
    """
    try:
        base_hostname = _get_hostname(url)
        if base_hostname is None:
            return -1

        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        anchors = soup.find_all("a")

        if not anchors:
            return 1

        unsafe_count = sum(
            1 for anchor in anchors
            if _is_unsafe_anchor(anchor.get("href"), url, base_hostname)
        )
        unsafe_ratio = (unsafe_count / len(anchors)) * 100

        return _classify_unsafe_ratio(unsafe_ratio)
    except Exception:
        return -1
