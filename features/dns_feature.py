"""
Feature. DNS Record
URL의 hostname이 DNS로 해석 가능한지 판별한다.

반환값:
     1 : DNS 조회 성공
    -1 : DNS 조회 실패
"""

import socket
from urllib.parse import urlparse


def dns_feature(url: str) -> int:
    try:
        hostname = urlparse(url).hostname
        if hostname is None:
            return -1

        socket.gethostbyname(hostname)
        return 1
    except Exception:
        return -1
