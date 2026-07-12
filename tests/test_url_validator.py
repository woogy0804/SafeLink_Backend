import socket
import unittest
from unittest.mock import patch

from utils.url_validator import validate_public_url


class TestUrlValidator(unittest.TestCase):
    def test_accepts_public_http_url(self):
        address_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

        with patch("utils.url_validator.socket.getaddrinfo", return_value=address_info):
            self.assertEqual(
                validate_public_url(" https://example.com/path "),
                "https://example.com/path",
            )

    def test_rejects_private_ip(self):
        with self.assertRaisesRegex(ValueError, "내부 네트워크"):
            validate_public_url("http://192.168.0.10/admin")

    def test_rejects_domain_resolving_to_loopback(self):
        address_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]

        with patch("utils.url_validator.socket.getaddrinfo", return_value=address_info):
            with self.assertRaisesRegex(ValueError, "내부 네트워크"):
                validate_public_url("http://example.com")

    def test_allows_unresolved_domain_for_dns_feature(self):
        with patch("utils.url_validator.socket.getaddrinfo", side_effect=socket.gaierror):
            self.assertEqual(
                validate_public_url("https://unknown.example"),
                "https://unknown.example",
            )


if __name__ == "__main__":
    unittest.main()
