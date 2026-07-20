"""
Feature. SFH(Server Form Handler)
HTML form 태그의 action 대상이 안전한지 판별한다.

반환값:
     1 : form action이 같은 호스트 또는 상대 경로
     0 : form action이 같은 등록 도메인의 다른 서브도메인
    -1 : form action이 외부 도메인, 공백 또는 about:blank
"""

from typing import Optional
from urllib.parse import urljoin

import requests

from features.domain_utils import (
    get_hostname,
    get_registered_domain_from_url,
)
from features.html_context import HtmlAnalysisContext, fetch_html_context


def _is_blank_action(action: Optional[str]) -> bool:
    if action is None:
        return True

    normalized_action = action.strip().lower()
    return normalized_action == "" or normalized_action == "about:blank"


def _classify_form_action(
    action: Optional[str],
    base_url: str,
    base_hostname: str,
    base_registered_domain: str,
) -> int:
    if _is_blank_action(action):
        return -1

    action_url = urljoin(base_url, action.strip())
    action_hostname = get_hostname(action_url, strip_www=True)
    action_registered_domain = get_registered_domain_from_url(action_url)

    if action_hostname is None or action_registered_domain is None:
        return -1
    if action_hostname == base_hostname:
        return 1
    if action_registered_domain == base_registered_domain:
        return 0
    return -1


def sfh_feature(
    url: str,
    html_context: Optional[HtmlAnalysisContext] = None,
) -> int:
    """
    form action의 목적지를 기준으로 URL을 분류한다.
    """
    try:
        base_hostname = get_hostname(url, strip_www=True)
        base_registered_domain = get_registered_domain_from_url(url)
        if base_hostname is None or base_registered_domain is None:
            return -1

        context = html_context or fetch_html_context(url)
        if context.fetch_failed or context.soup is None:
            return -1
        if context.static_unavailable:
            return 0

        soup = context.soup
        forms = soup.find_all("form")

        if not forms:
            return 1

        results = [
            _classify_form_action(
                form.get("action"),
                context.document_url,
                base_hostname,
                base_registered_domain,
            )
            for form in forms
        ]

        if -1 in results:
            return -1
        if 0 in results:
            return 0
        return 1
    except Exception:
        return -1
