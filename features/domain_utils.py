"""도메인 기반 feature가 공통으로 사용하는 URL/호스트 유틸리티."""

import ipaddress
from typing import Optional
from urllib.parse import urlparse

import idna
import tldextract


# 내장 Public Suffix List 스냅샷만 사용해 요청 처리 중 외부 다운로드가
# 발생하지 않도록 한다. github.io 같은 PRIVATE suffix도 서로 다른 사용자의
# 사이트를 동일 도메인으로 오인하지 않도록 포함한다.
_PSL_EXTRACTOR = tldextract.TLDExtract(
    suffix_list_urls=(),
    cache_dir=None,
    include_psl_private_domains=True,
)


def normalize_hostname(hostname: str) -> Optional[str]:
    normalized = hostname.strip().lower().rstrip(".")
    if not normalized:
        return None

    try:
        return str(ipaddress.ip_address(normalized))
    except ValueError:
        pass

    try:
        return idna.encode(
            normalized,
            uts46=True,
            transitional=False,
            std3_rules=True,
        ).decode("ascii")
    except idna.IDNAError:
        return None


def get_hostname(url: str, strip_www: bool = False) -> Optional[str]:
    hostname = urlparse(url).hostname
    if hostname is None:
        return None

    hostname = normalize_hostname(hostname)
    if hostname is None:
        return None
    if strip_www and hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def get_registered_domain(hostname: str) -> Optional[str]:
    hostname = normalize_hostname(hostname)
    if hostname is None:
        return None

    try:
        ipaddress.ip_address(hostname)
        return hostname
    except ValueError:
        pass

    extracted = _PSL_EXTRACTOR(hostname)
    registered_domain = extracted.top_domain_under_public_suffix
    if not registered_domain:
        return None
    return registered_domain.lower()


def get_registered_domain_from_url(url: str) -> Optional[str]:
    hostname = get_hostname(url)
    return get_registered_domain(hostname) if hostname else None


def is_same_registered_domain(url: str, base_registered_domain: str) -> bool:
    registered_domain = get_registered_domain_from_url(url)
    return registered_domain == base_registered_domain


def get_subdomain_labels(hostname: str) -> list[str]:
    hostname = normalize_hostname(hostname)
    if hostname is None:
        return []

    registered_domain = get_registered_domain(hostname)
    if registered_domain is None or registered_domain == hostname:
        return []

    suffix = f".{registered_domain}"
    if not hostname.endswith(suffix):
        return []

    prefix = hostname[: -len(suffix)]
    labels = [label for label in prefix.split(".") if label]
    if labels and labels[0] == "www":
        labels = labels[1:]
    return labels
