import socket
import unittest
from unittest.mock import patch

from features.dns_feature import dns_feature


class TestDnsFeature(unittest.TestCase):
    def test_legitimate_when_dns_lookup_succeeds(self):
        with patch("features.dns_feature.socket.gethostbyname", return_value="93.184.216.34"):
            self.assertEqual(dns_feature("https://example.com"), 1)

    def test_phishing_when_dns_lookup_fails(self):
        with patch(
            "features.dns_feature.socket.gethostbyname",
            side_effect=socket.gaierror("not found"),
        ):
            self.assertEqual(dns_feature("https://missing.example"), -1)

    def test_phishing_when_url_has_no_hostname(self):
        self.assertEqual(dns_feature("not-a-url"), -1)


if __name__ == "__main__":
    unittest.main()
