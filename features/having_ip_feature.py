"""
Feature 1. Having IP Address
URL의 호스트(host)가 IP 주소인지 판별한다.
반환값:
    -1 : IP 주소 사용 (피싱 의심)
     1 : 도메인 사용 (정상)
"""

import ipaddress
from urllib.parse import urlparse

def having_ip_feature(url):
    """
    URL의 호스트가 IP 주소인지 판별
    Return:
        -1 : IP 주소 사용
         1 : 도메인 사용
    """
    
    try:
        hostname = urlparse(url).hostname
        
        if hostname is None:
            return -1

        ipaddress.ip_address(hostname)
        return -1
    except ValueError:
        return 1
    
    except Exception:
        return -1
    