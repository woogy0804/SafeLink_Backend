import ipaddress
import socket
from typing import Set, Union
from urllib.parse import urlparse


ALLOWED_SCHEMES = {"http", "https"}


def validate_public_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL을 입력해주세요.")

    normalized_url = url.strip()
    parsed_url = urlparse(normalized_url)

    if parsed_url.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("http 또는 https URL만 입력할 수 있습니다.")
    if not parsed_url.hostname:
        raise ValueError("올바른 URL 형식이 아닙니다.")
    if parsed_url.username or parsed_url.password:
        raise ValueError("사용자 정보가 포함된 URL은 입력할 수 없습니다.")

    hostname = parsed_url.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("로컬 또는 내부 네트워크 URL은 입력할 수 없습니다.")

    for address in _resolve_addresses(hostname):
        if not address.is_global:
            raise ValueError("로컬 또는 내부 네트워크 URL은 입력할 수 없습니다.")

    return normalized_url


def _resolve_addresses(
    hostname: str,
) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    try:
        return {ipaddress.ip_address(hostname)}
    except ValueError:
        pass

    try:
        address_info = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        # DNS 조회 실패 여부는 Feature 추출 단계에서 위험 신호로 처리한다.
        return set()

    return {ipaddress.ip_address(item[4][0]) for item in address_info}
