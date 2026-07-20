"""
Feature. Links in Tags
meta, script, link 태그가 참조하는 외부 도메인 URL의 비율을 계산한다.

반환값:
     1 : 외부 링크 비율 < 17%
     0 : 17% <= 외부 링크 비율 <= 81%
    -1 : 외부 링크 비율 > 81% 또는 페이지 요청 실패
"""

import re
from typing import Optional
from urllib.parse import urljoin

import requests

from features.domain_utils import (
    get_registered_domain_from_url,
    is_same_registered_domain,
)
from features.html_context import HtmlAnalysisContext, fetch_html_context


META_URL_PATTERN = re.compile(r"(?:^|;)\s*url\s*=\s*['\"]?([^'\";]+)", re.IGNORECASE)


def _get_tag_url(tag) -> Optional[str]:
    if tag.name == "script":
        return tag.get("src")
    if tag.name == "link":
        return tag.get("href")
    if tag.name == "meta":
        content = tag.get("content", "")
        match = META_URL_PATTERN.search(content)
        return match.group(1).strip() if match else None
    return None


def _classify_external_ratio(external_ratio: float) -> int:
    if external_ratio < 17:
        return 1
    if external_ratio <= 81:
        return 0
    return -1


def links_in_tags_feature(
    url: str,
    html_context: Optional[HtmlAnalysisContext] = None,
) -> int:
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
        tag_urls = [
            tag_url
            for tag in soup.find_all(("meta", "script", "link"))
            if (tag_url := _get_tag_url(tag))
        ]
        if not tag_urls:
            return 1

        external_count = sum(
            1
            for tag_url in tag_urls
            if not is_same_registered_domain(
                urljoin(context.document_url, tag_url), base_registered_domain
            )
        )
        return _classify_external_ratio((external_count / len(tag_urls)) * 100)
    except Exception:
        return -1
