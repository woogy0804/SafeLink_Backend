"""
Feature. Request URL
HTML 문서 안의 img, video, audio 리소스 중 외부 도메인에서 로드되는 비율을 계산한다.

반환값:
     1 : 외부 리소스 비율 < 22%
     0 : 22% <= 외부 리소스 비율 <= 61%
    -1 : 외부 리소스 비율 > 61%
"""

from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from features.domain_utils import (
    get_registered_domain_from_url,
    is_same_registered_domain,
)
from features.html_context import HtmlAnalysisContext, fetch_html_context


RESOURCE_TAGS = ("img", "video", "audio")


def _get_resource_urls(soup: BeautifulSoup, base_url: str) -> List[str]:
    resource_urls = []

    for tag in soup.find_all(RESOURCE_TAGS):
        src = tag.get("src")
        if src:
            resource_urls.append(urljoin(base_url, src))

    return resource_urls


def _is_external_resource(resource_url: str, base_registered_domain: str) -> bool:
    return not is_same_registered_domain(resource_url, base_registered_domain)


def _classify_external_ratio(external_ratio: float) -> int:
    if external_ratio < 22:
        return 1
    if external_ratio <= 61:
        return 0
    return -1


def request_url_feature(
    url: str,
    html_context: HtmlAnalysisContext | None = None,
) -> int:
    """
    img/video/audio 리소스의 외부 도메인 비율을 기준으로 URL을 분류한다.
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

        resource_urls = _get_resource_urls(context.soup, context.document_url)

        if not resource_urls:
            return 1

        external_count = sum(
            1 for resource_url in resource_urls
            if _is_external_resource(resource_url, base_registered_domain)
        )
        external_ratio = (external_count / len(resource_urls)) * 100

        return _classify_external_ratio(external_ratio)
    except Exception:
        return -1
