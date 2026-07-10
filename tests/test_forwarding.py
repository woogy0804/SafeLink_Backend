import unittest
from unittest.mock import patch

from features.forwarding_feature import forwarding_feature


class FakeResponse:
    def __init__(self, redirect_count: int):
        self.history = [object()] * redirect_count

    def raise_for_status(self):
        return None


class TestForwardingFeature(unittest.TestCase):
    def test_legitimate_when_redirect_count_is_one_or_less(self):
        with patch("features.forwarding_feature.requests.get", return_value=FakeResponse(1)):
            self.assertEqual(forwarding_feature("https://example.com"), 1)

    def test_suspicious_when_redirect_count_is_between_two_and_four(self):
        with patch("features.forwarding_feature.requests.get", return_value=FakeResponse(3)):
            self.assertEqual(forwarding_feature("https://example.com"), 0)

    def test_phishing_when_redirect_count_is_five_or_more(self):
        with patch("features.forwarding_feature.requests.get", return_value=FakeResponse(5)):
            self.assertEqual(forwarding_feature("https://example.com"), -1)

    def test_phishing_when_request_fails(self):
        with patch("features.forwarding_feature.requests.get", side_effect=Exception("network error")):
            self.assertEqual(forwarding_feature("https://example.com"), -1)


if __name__ == "__main__":
    unittest.main()
