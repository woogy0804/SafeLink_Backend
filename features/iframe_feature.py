"""
Feature. IFrame Redirection
HTML 안에 iframe/frame 태그가 존재하는지 판별한다.

반환값:
     1 : iframe/frame 없음
    -1 : iframe/frame 있음 또는 요청 실패
"""

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 5


def iframe_feature(url: str) -> int:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        return -1 if soup.find(["iframe", "frame"]) else 1
    except Exception:
        return -1
