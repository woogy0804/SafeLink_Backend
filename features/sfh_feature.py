"""
Feature. SFH(Server Form Handler)
HTML form 태그의 action 대상이 안전한지 판별한다.

반환값:
     1 : form action이 같은 도메인 또는 상대 경로
     0 : form action이 다른 도메인
    -1 : form action이 비어 있거나 about:blank
"""

from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 5


def _get_hostname(url: str) -> Optional[str]:
    hostname = urlparse(url).hostname
    if hostname is None:
        return None

    hostname = hostname.lower()
    return hostname[4:] if hostname.startswith("www.") else hostname


def _is_blank_action(action: Optional[str]) -> bool:
    if action is None:
        return True

    normalized_action = action.strip().lower()
    return normalized_action == "" or normalized_action == "about:blank"


def _classify_form_action(action: Optional[str], base_url: str, base_hostname: str) -> int:
    if _is_blank_action(action):
        return -1

    action_url = urljoin(base_url, action.strip())
    action_hostname = _get_hostname(action_url)

    if action_hostname is None:
        return 0
    if action_hostname != base_hostname:
        return 0
    return 1


def sfh_feature(url: str) -> int:
    """
    form action의 목적지를 기준으로 URL을 분류한다.
    """
    try:
        base_hostname = _get_hostname(url)
        if base_hostname is None:
            return -1

        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        forms = soup.find_all("form")

        if not forms:
            return 1

        results = [
            _classify_form_action(form.get("action"), url, base_hostname)
            for form in forms
        ]

        if -1 in results:
            return -1
        if 0 in results:
            return 0
        return 1
    except Exception:
        return -1
