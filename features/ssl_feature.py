"""
Feature. SSL Final State
HTTPS 사용 여부와 SSL 인증서 유효성을 확인한다.

반환값:
     1 : HTTPS이며 인증서가 유효함
     0 : HTTPS이지만 인증서 검증 실패
    -1 : HTTPS가 아니거나 인증서가 만료됨
"""

import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

from features.safe_http import (
    ResolvedDestination,
    UnsafeDestinationError,
    resolve_public_destination,
)


REQUEST_TIMEOUT = 5


def _parse_cert_expiry(not_after: str) -> datetime:
    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
    return expiry.replace(tzinfo=timezone.utc)


def _fetch_verified_certificate(
    destination: ResolvedDestination,
) -> dict:
    context = ssl.create_default_context()
    last_error = None

    for address in destination.addresses:
        try:
            with socket.create_connection(
                (str(address), destination.port),
                timeout=REQUEST_TIMEOUT,
            ) as sock:
                with context.wrap_socket(
                    sock,
                    server_hostname=destination.hostname,
                ) as ssl_sock:
                    return ssl_sock.getpeercert()
        except (OSError, ssl.SSLError) as error:
            last_error = error

    if last_error is not None:
        raise last_error
    raise OSError("연결 가능한 공인 IP가 없습니다.")


def ssl_feature(url: str) -> int:
    try:
        parsed_url = urlparse(url)

        if parsed_url.scheme.lower() != "https":
            return -1

        destination = resolve_public_destination(url)
        cert = _fetch_verified_certificate(destination)

        not_after = cert.get("notAfter")
        if not not_after:
            return 0

        expiry_date = _parse_cert_expiry(not_after)
        now = datetime.now(timezone.utc)
        if expiry_date <= now:
            return -1

        not_before = cert.get("notBefore")
        if not_before and _parse_cert_expiry(not_before) > now:
            return -1
        return 1
    except ssl.SSLCertVerificationError as error:
        # OpenSSL verify code 9/10은 아직 유효하지 않거나 만료된 인증서다.
        if getattr(error, "verify_code", None) in {9, 10}:
            return -1
        return 0
    except UnsafeDestinationError:
        return -1
    except (OSError, ValueError, ssl.SSLError):
        # DNS, timeout, 연결 실패 및 해석 불가 인증서는 피싱으로 확정하지 않는다.
        return 0
    except Exception:
        return 0
