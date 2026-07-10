import unittest

from features.having_ip_feature import having_ip_feature


class TestHavingIpFeature(unittest.TestCase):
    def test_phishing_when_hostname_is_ipv4(self):
        self.assertEqual(having_ip_feature("http://192.168.0.1"), -1)

    def test_phishing_when_hostname_is_ipv6(self):
        self.assertEqual(having_ip_feature("http://[2001:4860:4860::8888]"), -1)

    def test_legitimate_when_hostname_is_domain(self):
        self.assertEqual(having_ip_feature("https://google.com"), 1)

    def test_phishing_when_url_has_no_hostname(self):
        self.assertEqual(having_ip_feature("invalid-url"), -1)


if __name__ == "__main__":
    unittest.main()
