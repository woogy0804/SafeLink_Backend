"""
Feature. Age of Domain
WHOIS 생성일을 기준으로 도메인 나이를 판별한다.

반환값:
     1 : 도메인 생성 후 6개월 이상
    -1 : 도메인 생성 후 6개월 미만 또는 조회 실패
"""

import re
import subprocess
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse


DOMAIN_AGE_THRESHOLD_DAYS = 180
WHOIS_TIMEOUT = 10
CREATION_DATE_PATTERNS = (
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d.%m.%Y",
)


def _get_hostname(url: str) -> Optional[str]:
    hostname = urlparse(url).hostname
    if hostname is None:
        return None

    hostname = hostname.lower()
    return hostname[4:] if hostname.startswith("www.") else hostname


def _parse_creation_date(whois_text: str) -> Optional[datetime]:
    for line in whois_text.splitlines():
        if not re.search(r"creation date|created|registered on", line, re.IGNORECASE):
            continue

        _, _, raw_date = line.partition(":")
        raw_date = raw_date.strip()

        for pattern in CREATION_DATE_PATTERNS:
            try:
                parsed_date = datetime.strptime(raw_date, pattern)
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                return parsed_date.astimezone(timezone.utc)
            except ValueError:
                continue

    return None


def _get_domain_creation_date(hostname: str) -> Optional[datetime]:
    result = subprocess.run(
        ["whois", hostname],
        capture_output=True,
        text=True,
        timeout=WHOIS_TIMEOUT,
        check=False,
    )

    if result.returncode != 0:
        return None

    return _parse_creation_date(result.stdout)


def domain_age_feature(url: str) -> int:
    try:
        hostname = _get_hostname(url)
        if hostname is None:
            return -1

        creation_date = _get_domain_creation_date(hostname)
        if creation_date is None:
            return -1

        domain_age_days = (datetime.now(timezone.utc) - creation_date).days
        return 1 if domain_age_days >= DOMAIN_AGE_THRESHOLD_DAYS else -1
    except Exception:
        return -1
