"""Feature 수집 전용 SSRF 방어 및 제한된 HTTP 클라이언트."""

import ipaddress
import socket
from dataclasses import dataclass
from typing import Set, Union
from urllib.parse import urljoin, urlparse

import requests

from features.domain_utils import normalize_hostname


ALLOWED_SCHEMES = {"http", "https"}
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
ALLOWED_HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
CONNECT_TIMEOUT = 3
READ_TIMEOUT = 5
REQUEST_HEADERS = {"User-Agent": "SafeLink-FeatureBot/1.0"}


class SafeHttpError(Exception):
    """안전한 HTML 수집 과정에서 발생하는 기본 예외."""


class UnsafeDestinationError(SafeHttpError):
    """사설망, 루프백 또는 잘못된 목적지를 차단했을 때 발생한다."""


class RedirectLimitError(SafeHttpError):
    """허용된 리다이렉트 횟수를 초과했을 때 발생한다."""


class ResponseTooLargeError(SafeHttpError):
    """응답 본문이 최대 크기를 초과했을 때 발생한다."""


class UnsupportedContentTypeError(SafeHttpError):
    """HTML이 아닌 응답을 거부했을 때 발생한다."""


@dataclass(frozen=True)
class HtmlDocument:
    final_url: str
    text: str


@dataclass(frozen=True)
class ResolvedDestination:
    url: str
    hostname: str
    port: int
    addresses: tuple[Union[ipaddress.IPv4Address, ipaddress.IPv6Address], ...]


def _resolve_addresses(
    hostname: str,
    port: int,
) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    hostname = normalize_hostname(hostname)
    if hostname is None:
        raise UnsafeDestinationError("대상 도메인 형식이 올바르지 않습니다.")

    try:
        return {ipaddress.ip_address(hostname)}
    except ValueError:
        pass

    try:
        address_info = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as error:
        raise UnsafeDestinationError("대상 도메인의 DNS를 확인할 수 없습니다.") from error

    addresses = {ipaddress.ip_address(item[4][0]) for item in address_info}
    if not addresses:
        raise UnsafeDestinationError("대상 도메인의 IP를 확인할 수 없습니다.")
    return addresses


def resolve_public_destination(url: str) -> ResolvedDestination:
    """Validate a URL and return the exact public IPs resolved for it."""

    parsed_url = urlparse(url)
    if parsed_url.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeDestinationError("http 또는 https URL만 요청할 수 있습니다.")
    if not parsed_url.hostname:
        raise UnsafeDestinationError("요청할 URL에 hostname이 없습니다.")
    if parsed_url.username or parsed_url.password:
        raise UnsafeDestinationError("사용자 정보가 포함된 URL은 요청할 수 없습니다.")

    hostname = normalize_hostname(parsed_url.hostname)
    if hostname is None:
        raise UnsafeDestinationError("대상 도메인 형식이 올바르지 않습니다.")

    try:
        port = parsed_url.port
    except ValueError as error:
        raise UnsafeDestinationError("URL 포트 번호가 올바르지 않습니다.") from error
    if port is None:
        port = 443 if parsed_url.scheme.lower() == "https" else 80
    if not 1 <= port <= 65535:
        raise UnsafeDestinationError("URL 포트 번호가 올바르지 않습니다.")

    addresses = _resolve_addresses(hostname, port)
    if any(not address.is_global for address in addresses):
        raise UnsafeDestinationError("사설망 또는 루프백 목적지는 요청할 수 없습니다.")
    sorted_addresses = tuple(
        sorted(addresses, key=lambda address: (address.version, int(address)))
    )
    return ResolvedDestination(
        url=url,
        hostname=hostname,
        port=port,
        addresses=sorted_addresses,
    )


def validate_public_destination(url: str) -> str:
    """HTTP(S) URL의 모든 해석 IP가 공인 주소인지 확인한다."""

    resolve_public_destination(url)
    return url


def _response_headers(response) -> dict:
    headers = getattr(response, "headers", None)
    return headers if headers is not None else {}


def _close_response(response) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        close()


def _validate_content_type(response) -> None:
    content_type = _response_headers(response).get("Content-Type", "")
    if not content_type:
        return

    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in ALLOWED_HTML_CONTENT_TYPES and not media_type.endswith("+html"):
        raise UnsupportedContentTypeError("HTML 응답만 분석할 수 있습니다.")


def _read_limited_text(response) -> str:
    content_length = _response_headers(response).get("Content-Length")
    if content_length:
        try:
            if int(content_length) > MAX_RESPONSE_BYTES:
                raise ResponseTooLargeError("HTML 응답이 최대 크기를 초과했습니다.")
        except ValueError:
            pass

    iter_content = getattr(response, "iter_content", None)
    if not callable(iter_content):
        text = str(getattr(response, "text", ""))
        if len(text.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise ResponseTooLargeError("HTML 응답이 최대 크기를 초과했습니다.")
        return text

    body = bytearray()
    for chunk in iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ResponseTooLargeError("HTML 응답이 최대 크기를 초과했습니다.")

    encoding = getattr(response, "encoding", None) or "utf-8"
    return bytes(body).decode(encoding, errors="replace")


def fetch_html_document(url: str) -> HtmlDocument:
    """리다이렉트마다 목적지를 검증하며 제한된 크기의 HTML을 가져온다."""

    current_url = url.strip()

    for redirect_count in range(MAX_REDIRECTS + 1):
        validate_public_destination(current_url)
        response = requests.get(
            current_url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            allow_redirects=False,
            stream=True,
            headers=REQUEST_HEADERS,
        )

        try:
            status_code = int(getattr(response, "status_code", 200))
            if status_code in REDIRECT_STATUS_CODES:
                location = _response_headers(response).get("Location")
                if not location:
                    raise SafeHttpError("리다이렉트 응답에 Location이 없습니다.")
                if redirect_count >= MAX_REDIRECTS:
                    raise RedirectLimitError("허용된 리다이렉트 횟수를 초과했습니다.")

                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            _validate_content_type(response)
            return HtmlDocument(
                final_url=current_url,
                text=_read_limited_text(response),
            )
        finally:
            _close_response(response)

    raise RedirectLimitError("허용된 리다이렉트 횟수를 초과했습니다.")
