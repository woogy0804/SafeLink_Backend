"""
Feature. Domain Registration Length
RDAP 만료일까지 남은 등록 기간을 판별한다.

반환값:
     1 : 만료일까지 1년 초과
    -1 : 만료일까지 1년 이하
     0 : RDAP 조회 또는 날짜 해석 불가
"""

from datetime import datetime, timezone
from typing import Optional

from features.domain_context import DomainAnalysisContext, fetch_domain_context
from features.domain_utils import get_registered_domain_from_url


REGISTRATION_LENGTH_THRESHOLD_DAYS = 365


def domain_registration_length_feature(
    url: str,
    domain_context: Optional[DomainAnalysisContext] = None,
) -> int:
    try:
        registered_domain = get_registered_domain_from_url(url)
        if registered_domain is None:
            return -1

        context = domain_context or fetch_domain_context(url)
        if context.lookup_failed or context.expiration_date is None:
            return 0

        remaining_days = (context.expiration_date - datetime.now(timezone.utc)).days
        return 1 if remaining_days > REGISTRATION_LENGTH_THRESHOLD_DAYS else -1
    except Exception:
        return 0
