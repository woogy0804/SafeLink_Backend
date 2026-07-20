import unittest

from features.subdomain_feature import subdomain_feature


class TestSubdomainFeature(unittest.TestCase):
    def test_legitimate_when_no_subdomain_exists(self):
        self.assertEqual(subdomain_feature("https://example.com"), 1)

    def test_www_is_not_counted_as_subdomain(self):
        self.assertEqual(subdomain_feature("https://www.example.com"), 1)

    def test_suspicious_when_one_subdomain_exists(self):
        self.assertEqual(subdomain_feature("https://login.example.com"), 0)

    def test_phishing_when_multiple_subdomains_exist(self):
        self.assertEqual(subdomain_feature("https://bank.login.example.com"), -1)

    def test_country_code_registered_domain_is_handled(self):
        self.assertEqual(subdomain_feature("https://login.example.co.kr"), 0)


if __name__ == "__main__":
    unittest.main()
