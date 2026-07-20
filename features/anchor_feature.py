"""
Feature. URL of Anchor
HTML a 태그의 href 중 외부/비정상 링크 비율을 계산한다.

반환값:
     1 : 비정상 anchor 비율 < 31%
     0 : 31% <= 비정상 anchor 비율 <= 67%
    -1 : 비정상 anchor 비율 > 67%
"""

from typing import Optional
from urllib.parse import urljoin

import requests

from features.domain_utils import (
    get_registered_domain_from_url,
    is_same_registered_domain,
)
from features.html_context import HtmlAnalysisContext, fetch_html_context


INVALID_ANCHOR_PREFIXES = ("#", "javascript:", "mailto:", "tel:", "data:")


def _is_invalid_href(href: Optional[str]) -> bool:
    if href is None:
        return True

    normalized_href = href.strip().lower()
    return normalized_href == "" or normalized_href.startswith(INVALID_ANCHOR_PREFIXES)


def _is_unsafe_anchor(
    href: Optional[str], base_url: str, base_registered_domain: str
) -> bool:
    if _is_invalid_href(href):
        return True

    href_url = urljoin(base_url, href.strip())
    return not is_same_registered_domain(href_url, base_registered_domain)


def _classify_unsafe_ratio(unsafe_ratio: float) -> int:
    if unsafe_ratio < 31:
        return 1
    if unsafe_ratio <= 67:
        return 0
    return -1


def anchor_feature(
    url: str,
    html_context: Optional[HtmlAnalysisContext] = None,
) -> int:
    """
    a 태그 href의 비정상 링크 비율을 기준으로 URL을 분류한다.
    """
    try:
        base_registered_domain = get_registered_domain_from_url(url)
        if base_registered_domain is None:
            return -1

        context = html_context or fetch_html_context(url)
        if context.fetch_failed or context.soup is None:
            return -1
        if context.static_unavailable:
            return 0

        soup = context.soup
        anchors = soup.find_all("a")

        if not anchors:
            return 1

        unsafe_count = sum(
            1 for anchor in anchors
            if _is_unsafe_anchor(
                anchor.get("href"),
                context.document_url,
                base_registered_domain,
            )
        )
        unsafe_ratio = (unsafe_count / len(anchors)) * 100

        return _classify_unsafe_ratio(unsafe_ratio)
    except Exception:
        return -1
