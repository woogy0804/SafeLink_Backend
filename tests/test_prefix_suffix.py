import unittest

from features.prefix_suffix_feature import prefix_suffix_feature


class TestPrefixSuffixFeature(unittest.TestCase):
    def test_phishing_when_registered_domain_has_hyphen(self):
        self.assertEqual(prefix_suffix_feature("https://secure-login.com"), -1)

    def test_legitimate_when_registered_domain_has_no_hyphen(self):
        self.assertEqual(prefix_suffix_feature("https://example.com/login"), 1)

    def test_phishing_when_country_domain_registered_label_has_hyphen(self):
        self.assertEqual(prefix_suffix_feature("https://secure-login.co.kr"), -1)

    def test_invalid_url_returns_phishing(self):
        self.assertEqual(prefix_suffix_feature("not-a-url"), -1)


if __name__ == "__main__":
    unittest.main()
