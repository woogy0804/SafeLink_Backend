"""
Feature. Having Sub Domain
등록 도메인 앞에 붙은 서브도메인의 개수를 판별한다. 관례적인 www는 제외한다.

반환값:
     1 : 서브도메인 없음
     0 : 서브도메인 1개
    -1 : 서브도메인 2개 이상 또는 잘못된 URL
"""

from features.domain_utils import get_hostname, get_subdomain_labels


def subdomain_feature(url: str) -> int:
    try:
        hostname = get_hostname(url)
        if hostname is None:
            return -1

        subdomain_count = len(get_subdomain_labels(hostname))
        if subdomain_count == 0:
            return 1
        if subdomain_count == 1:
            return 0
        return -1
    except Exception:
        return -1
