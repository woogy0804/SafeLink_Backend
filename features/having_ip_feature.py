"""
Feature 1. Having IP Address
URL의 호스트(host)가 IP 주소인지 판별한다.

반환값:
    -1 : IP 주소 사용 (피싱 의심)
     1 : 도메인 사용 (정상)
"""

import ipaddress
import re
from typing import Optional
from urllib.parse import unquote, urlparse

from features.domain_utils import normalize_hostname


_DECIMAL_COMPONENT = re.compile(r"^[0-9]+$")
_HEX_COMPONENT = re.compile(r"^0[xX][0-9a-fA-F]+$")
_OCTAL_COMPONENT = re.compile(r"^0[0-7]+$")


def _parse_ipv4_component(component: str) -> Optional[int]:
    if _HEX_COMPONENT.fullmatch(component):
        return int(component[2:], 16)
    if _OCTAL_COMPONENT.fullmatch(component) and len(component) > 1:
        return int(component, 8)
    if _DECIMAL_COMPONENT.fullmatch(component):
        return int(component, 10)
    return None


def _is_legacy_ipv4(hostname: str) -> bool:
    """Detect browser-compatible integer, hexadecimal and short IPv4 forms."""

    components = hostname.split(".")
    if not 1 <= len(components) <= 4 or any(not item for item in components):
        return False

    values = [_parse_ipv4_component(item) for item in components]
    if any(value is None for value in values):
        return False

    numeric_values = [int(value) for value in values]
    if len(numeric_values) == 1:
        limits = [0xFFFFFFFF]
    elif len(numeric_values) == 2:
        limits = [0xFF, 0xFFFFFF]
    elif len(numeric_values) == 3:
        limits = [0xFF, 0xFF, 0xFFFF]
    else:
        limits = [0xFF, 0xFF, 0xFF, 0xFF]

    return all(value <= limit for value, limit in zip(numeric_values, limits))


def _is_ip_hostname(hostname: str) -> bool:
    normalized = normalize_hostname(unquote(hostname))
    if normalized is None:
        return False

    try:
        ipaddress.ip_address(normalized)
        return True
    except ValueError:
        return _is_legacy_ipv4(normalized)


def having_ip_feature(url: str) -> int:
    """Return -1 for direct IP hostnames, otherwise 1."""

    try:
        hostname = urlparse(url).hostname
        if hostname is None:
            return -1
        return -1 if _is_ip_hostname(hostname) else 1
    except Exception:
        return -1
