"""
Feature. SSL Final State
HTTPS 사용 여부와 SSL 인증서 유효성을 확인한다.

반환값:
     1 : HTTPS이며 인증서가 유효함
     0 : HTTPS이지만 인증서 검증 실패
    -1 : HTTPS가 아니거나 인증서가 만료/조회 실패
"""

import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse


REQUEST_TIMEOUT = 5


def _parse_cert_expiry(not_after: str) -> datetime:
    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
    return expiry.replace(tzinfo=timezone.utc)


def ssl_feature(url: str) -> int:
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if parsed_url.scheme != "https" or hostname is None:
            return -1

        port = parsed_url.port or 443
        context = ssl.create_default_context()

        with socket.create_connection((hostname, port), timeout=REQUEST_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssl_sock:
                cert = ssl_sock.getpeercert()

        not_after = cert.get("notAfter")
        if not not_after:
            return -1

        expiry_date = _parse_cert_expiry(not_after)
        return 1 if expiry_date > datetime.now(timezone.utc) else -1
    except ssl.SSLCertVerificationError:
        return 0
    except Exception:
        return -1
