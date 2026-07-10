import ssl
import unittest
from unittest.mock import patch

from features.ssl_feature import ssl_feature


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

    def wrap_socket(self, sock, server_hostname):
        if self.error:
            raise self.error
        return FakeSslSocket(self.cert)


class TestSslFeature(unittest.TestCase):
    def test_legitimate_when_https_certificate_is_valid(self):
        cert = {"notAfter": "Jan 01 00:00:00 2999 GMT"}

        with patch("features.ssl_feature.socket.create_connection", return_value=FakeSocket()):
            with patch("features.ssl_feature.ssl.create_default_context", return_value=FakeSslContext(cert)):
                self.assertEqual(ssl_feature("https://example.com"), 1)

    def test_phishing_when_url_is_not_https(self):
        self.assertEqual(ssl_feature("http://example.com"), -1)

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


if __name__ == "__main__":
    unittest.main()
