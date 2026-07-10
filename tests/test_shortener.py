import unittest

from features.shortener_feature import shortener_feature


class TestShortenerFeature(unittest.TestCase):
    def test_phishing_when_url_uses_shortener_domain(self):
        self.assertEqual(shortener_feature("https://bit.ly/abc123"), -1)
        self.assertEqual(shortener_feature("https://tinyurl.com/test"), -1)
        self.assertEqual(shortener_feature("https://t.co/abcd"), -1)

    def test_legitimate_when_url_uses_normal_domain(self):
        self.assertEqual(shortener_feature("https://google.com"), 1)
        self.assertEqual(shortener_feature("https://github.com"), 1)

    def test_phishing_when_url_has_no_hostname(self):
        self.assertEqual(shortener_feature("invalid-url"), -1)


if __name__ == "__main__":
    unittest.main()
