"""
Feature. Request URL
HTML 문서 안의 img, video, audio 리소스 중 외부 도메인에서 로드되는 비율을 계산한다.

반환값:
     1 : 외부 리소스 비율 < 22%
     0 : 22% <= 외부 리소스 비율 <= 61%
    -1 : 외부 리소스 비율 > 61%
"""

from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 5
RESOURCE_TAGS = ("img", "video", "audio")


def _get_hostname(url: str) -> Optional[str]:
    hostname = urlparse(url).hostname
    if hostname is None:
        return None

    hostname = hostname.lower()
    return hostname[4:] if hostname.startswith("www.") else hostname


def _get_resource_urls(soup: BeautifulSoup, base_url: str) -> List[str]:
    resource_urls = []

    for tag in soup.find_all(RESOURCE_TAGS):
        src = tag.get("src")
        if src:
            resource_urls.append(urljoin(base_url, src))

    return resource_urls


def _is_external_resource(resource_url: str, base_hostname: str) -> bool:
    resource_hostname = _get_hostname(resource_url)
    return resource_hostname is not None and resource_hostname != base_hostname


def _classify_external_ratio(external_ratio: float) -> int:
    if external_ratio < 22:
        return 1
    if external_ratio <= 61:
        return 0
    return -1


def request_url_feature(url: str) -> int:
    """
    img/video/audio 리소스의 외부 도메인 비율을 기준으로 URL을 분류한다.
    """
    try:
        base_hostname = _get_hostname(url)
        if base_hostname is None:
            return -1

        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        resource_urls = _get_resource_urls(soup, url)

        if not resource_urls:
            return 1

        external_count = sum(
            1 for resource_url in resource_urls
            if _is_external_resource(resource_url, base_hostname)
        )
        external_ratio = (external_count / len(resource_urls)) * 100

        return _classify_external_ratio(external_ratio)
    except Exception:
        return -1
