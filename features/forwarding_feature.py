"""
Feature. Website Forwarding
HTTP redirect 횟수를 기준으로 URL을 분류한다.

반환값:
     1 : redirect 1회 이하
     0 : redirect 2~4회
    -1 : redirect 5회 이상 또는 요청 실패
"""

import requests


REQUEST_TIMEOUT = 5


def _classify_redirect_count(redirect_count: int) -> int:
    if redirect_count <= 1:
        return 1
    if redirect_count <= 4:
        return 0
    return -1


def forwarding_feature(url: str) -> int:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()

        return _classify_redirect_count(len(response.history))
    except Exception:
        return -1
