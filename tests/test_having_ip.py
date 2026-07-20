import unittest

from features.having_ip_feature import having_ip_feature


class TestHavingIpFeature(unittest.TestCase):
    def test_phishing_when_hostname_is_ipv4(self):
        self.assertEqual(having_ip_feature("http://192.168.0.1"), -1)

    def test_phishing_when_hostname_is_ipv6(self):
        self.assertEqual(having_ip_feature("http://[2001:4860:4860::8888]"), -1)

    def test_phishing_when_hostname_is_decimal_ipv4_integer(self):
        self.assertEqual(having_ip_feature("http://2130706433"), -1)

    def test_phishing_when_hostname_is_hexadecimal_ipv4_integer(self):
        self.assertEqual(having_ip_feature("http://0x7f000001"), -1)

    def test_phishing_when_hostname_uses_hexadecimal_ipv4_components(self):
        self.assertEqual(having_ip_feature("http://0x7f.0x0.0x0.0x1"), -1)

    def test_phishing_when_hostname_uses_octal_ipv4(self):
        self.assertEqual(having_ip_feature("http://0177.0.0.1"), -1)

    def test_phishing_when_hostname_uses_short_ipv4_form(self):
        self.assertEqual(having_ip_feature("http://127.1"), -1)

    def test_phishing_when_hostname_uses_fullwidth_unicode_ipv4(self):
        self.assertEqual(having_ip_feature("http://１２７.０.０.１"), -1)

    def test_legitimate_when_hostname_is_domain(self):
        self.assertEqual(having_ip_feature("https://google.com"), 1)

    def test_numeric_registered_label_is_not_mistaken_for_ip(self):
        self.assertEqual(having_ip_feature("https://123.com"), 1)

    def test_phishing_when_url_has_no_hostname(self):
        self.assertEqual(having_ip_feature("invalid-url"), -1)


if __name__ == "__main__":
    unittest.main()
