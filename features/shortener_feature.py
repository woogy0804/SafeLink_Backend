"""
Feature 3: URL Shortening Service
URL 단축 서비스는 원래 정상적인 용도로도 많이 사용된다 
하지만 피싱 공격자는 실제 목적지를 숨기기 위해 단축 URL을 자주 사용한다
단축 URL을 사용한다면 -1을 반환하고 사용하지않는다면 1을 반환한다
"""

from pathlib import Path
from urllib.parse import urlparse

DOMAIN_FILE = Path(__file__).parent / "shortener_domains.txt"

with open(DOMAIN_FILE, encoding="utf-8") as f:
    SHORTENING_SERVICES = {
        line.strip().lower()
        for line in f
        if line.strip() and not line.lstrip().startswith("#")
    }


def shortener_feature(url: str) -> int:
    """
    URL 단축 서비스 사용 여부
    Returns:
        -1 : 단축 URL 사용
         1 : 일반 URL
    """
    try:
        hostname = urlparse(url).hostname

        if hostname is None:
            return -1

        hostname = hostname.lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]

        return -1 if hostname in SHORTENING_SERVICES else 1
    except Exception:
        return -1
