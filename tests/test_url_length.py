import unittest

from features.url_length_feature import url_length_feature


class TestUrlLengthFeature(unittest.TestCase):
    def test_legitimate_when_length_is_under_54(self):
        self.assertEqual(url_length_feature("https://google.com"), 1)

    def test_suspicious_when_length_is_between_54_and_75(self):
        url = "https://example.com/" + ("a" * 40)
        self.assertEqual(len(url), 60)
        self.assertEqual(url_length_feature(url), 0)

    def test_phishing_when_length_is_over_75(self):
        url = "https://example.com/" + ("a" * 84)
        self.assertEqual(len(url), 104)
        self.assertEqual(url_length_feature(url), -1)


if __name__ == "__main__":
    unittest.main()
