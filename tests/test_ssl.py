import ssl
import ipaddress
import unittest
from unittest.mock import patch

from features.ssl_feature import ssl_feature
from features.safe_http import ResolvedDestination, UnsafeDestinationError


class FakeSocket:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


class FakeSslSocket:
    def __init__(self, cert):
        self.cert = cert

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def getpeercert(self):
        return self.cert


class FakeSslContext:
    def __init__(self, cert=None, error=None):
        self.cert = cert
        self.error = error
        self.server_hostname = None

    def wrap_socket(self, sock, server_hostname):
        self.server_hostname = server_hostname
        if self.error:
            raise self.error
        return FakeSslSocket(self.cert)


class TestSslFeature(unittest.TestCase):
    def setUp(self):
        destination_patcher = patch(
            "features.ssl_feature.resolve_public_destination",
            side_effect=lambda url: ResolvedDestination(
                url=url,
                hostname="example.com",
                port=443,
                addresses=(ipaddress.ip_address("93.184.216.34"),),
            ),
        )
        destination_patcher.start()
        self.addCleanup(destination_patcher.stop)

    def test_legitimate_when_https_certificate_is_valid(self):
        cert = {"notAfter": "Jan 01 00:00:00 2999 GMT"}

        with patch("features.ssl_feature.socket.create_connection", return_value=FakeSocket()):
            with patch("features.ssl_feature.ssl.create_default_context", return_value=FakeSslContext(cert)):
                self.assertEqual(ssl_feature("https://example.com"), 1)

    def test_phishing_when_url_is_not_https(self):
        self.assertEqual(ssl_feature("http://example.com"), -1)

    def test_phishing_when_port_is_zero(self):
        with patch(
            "features.ssl_feature.resolve_public_destination",
            side_effect=UnsafeDestinationError("invalid port"),
        ):
            self.assertEqual(ssl_feature("https://example.com:0"), -1)

    def test_suspicious_when_certificate_verification_fails(self):
        error = ssl.SSLCertVerificationError("certificate verify failed")

        with patch("features.ssl_feature.socket.create_connection", return_value=FakeSocket()):
            with patch("features.ssl_feature.ssl.create_default_context", return_value=FakeSslContext(error=error)):
                self.assertEqual(ssl_feature("https://example.com"), 0)

    def test_phishing_when_certificate_is_expired(self):
        cert = {"notAfter": "Jan 01 00:00:00 2000 GMT"}

        with patch("features.ssl_feature.socket.create_connection", return_value=FakeSocket()):
            with patch("features.ssl_feature.ssl.create_default_context", return_value=FakeSslContext(cert)):
                self.assertEqual(ssl_feature("https://example.com"), -1)

    def test_phishing_when_certificate_is_not_yet_valid(self):
        cert = {
            "notBefore": "Jan 01 00:00:00 2998 GMT",
            "notAfter": "Jan 01 00:00:00 2999 GMT",
        }

        with patch("features.ssl_feature.socket.create_connection", return_value=FakeSocket()):
            with patch("features.ssl_feature.ssl.create_default_context", return_value=FakeSslContext(cert)):
                self.assertEqual(ssl_feature("https://example.com"), -1)

    def test_suspicious_when_certificate_expiry_is_missing(self):
        with patch("features.ssl_feature.socket.create_connection", return_value=FakeSocket()):
            with patch("features.ssl_feature.ssl.create_default_context", return_value=FakeSslContext({})):
                self.assertEqual(ssl_feature("https://example.com"), 0)

    def test_suspicious_when_tls_connection_fails(self):
        with patch(
            "features.ssl_feature.socket.create_connection",
            side_effect=TimeoutError("timed out"),
        ):
            self.assertEqual(ssl_feature("https://example.com"), 0)

    def test_phishing_when_destination_is_private(self):
        with patch(
            "features.ssl_feature.resolve_public_destination",
            side_effect=UnsafeDestinationError("private destination"),
        ):
            self.assertEqual(ssl_feature("https://127.0.0.1"), -1)

    def test_connects_to_validated_ip_and_keeps_hostname_for_sni(self):
        cert = {"notAfter": "Jan 01 00:00:00 2999 GMT"}
        context = FakeSslContext(cert)
        destination = ResolvedDestination(
            url="https://example.com",
            hostname="example.com",
            port=443,
            addresses=(ipaddress.ip_address("93.184.216.34"),),
        )
        with patch(
            "features.ssl_feature.resolve_public_destination",
            return_value=destination,
        ):
            with patch(
            "features.ssl_feature.socket.create_connection",
                return_value=FakeSocket(),
            ) as mock_connect:
                with patch(
                    "features.ssl_feature.ssl.create_default_context",
                    return_value=context,
                ):
                    self.assertEqual(ssl_feature("https://example.com"), 1)

        mock_connect.assert_called_once_with(
            ("93.184.216.34", 443),
            timeout=5,
        )
        self.assertEqual(context.server_hostname, "example.com")


if __name__ == "__main__":
    unittest.main()
