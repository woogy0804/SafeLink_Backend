"""Feature 수집 전용 SSRF 방어 및 제한된 HTTP 클라이언트."""

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from typing import Set, Union
from urllib.parse import urljoin, urlparse, urlunsplit

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


class _PinnedResponse:
    """Small response adapter that owns an IP-pinned HTTP connection."""

    def __init__(self, response: http.client.HTTPResponse, connection) -> None:
        self._response = response
        self._connection = connection
        self.status_code = response.status
        self.headers = response.headers
        self.encoding = response.headers.get_content_charset() or "utf-8"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise SafeHttpError(f"HTTP request failed with status {self.status_code}")

    def iter_content(self, chunk_size: int):
        while True:
            chunk = self._response.read(chunk_size)
            if not chunk:
                return
            yield chunk

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            self._connection.close()


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, destination: ResolvedDestination, address) -> None:
        super().__init__(
            destination.hostname,
            destination.port,
            timeout=CONNECT_TIMEOUT,
        )
        self._destination = destination
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (str(self._address), self._destination.port),
            self.timeout,
            self.source_address,
        )
        self.sock.settimeout(READ_TIMEOUT)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, destination: ResolvedDestination, address) -> None:
        super().__init__(
            destination.hostname,
            destination.port,
            timeout=CONNECT_TIMEOUT,
            context=ssl.create_default_context(),
        )
        self._destination = destination
        self._address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (str(self._address), self._destination.port),
            self.timeout,
            self.source_address,
        )
        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self._destination.hostname,
            )
            self.sock.settimeout(READ_TIMEOUT)
        except Exception:
            raw_socket.close()
            raise


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


def _request_target(url: str) -> str:
    parsed_url = urlparse(url)
    return urlunsplit(("", "", parsed_url.path or "/", parsed_url.query, ""))


def _host_header(destination: ResolvedDestination) -> str:
    default_port = 443 if urlparse(destination.url).scheme.lower() == "https" else 80
    hostname = destination.hostname
    try:
        if ipaddress.ip_address(hostname).version == 6:
            hostname = f"[{hostname}]"
    except ValueError:
        pass
    if destination.port != default_port:
        return f"{hostname}:{destination.port}"
    return hostname


def _request_pinned_destination(destination: ResolvedDestination):
    """Connect only to IPs returned by the validated DNS lookup.

    The original hostname remains in the Host header and TLS SNI/certificate
    verification, but it is never resolved a second time by the HTTP client.
    """

    scheme = urlparse(destination.url).scheme.lower()
    last_error = None
    for address in destination.addresses:
        connection = None
        try:
            connection_class = (
                _PinnedHTTPSConnection if scheme == "https" else _PinnedHTTPConnection
            )
            connection = connection_class(destination, address)
            headers = {**REQUEST_HEADERS, "Host": _host_header(destination)}
            connection.request("GET", _request_target(destination.url), headers=headers)
            return _PinnedResponse(connection.getresponse(), connection)
        except (OSError, ssl.SSLError, http.client.HTTPException) as error:
            last_error = error
            if connection is not None:
                connection.close()

    if last_error is not None:
        raise last_error
    raise SafeHttpError("No validated public address is available")


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
        destination = resolve_public_destination(current_url)
        response = _request_pinned_destination(destination)

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
