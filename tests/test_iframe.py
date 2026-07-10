import unittest
from unittest.mock import patch

from features.iframe_feature import iframe_feature


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class TestIframeFeature(unittest.TestCase):
    def test_legitimate_when_iframe_does_not_exist(self):
        html = "<html><body>No iframe</body></html>"

        with patch("features.iframe_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(iframe_feature("https://example.com"), 1)

    def test_phishing_when_iframe_exists(self):
        html = '<iframe src="https://external.example.net"></iframe>'

        with patch("features.iframe_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(iframe_feature("https://example.com"), -1)

    def test_phishing_when_frame_exists(self):
        html = '<frame src="https://external.example.net">'

        with patch("features.iframe_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(iframe_feature("https://example.com"), -1)

    def test_phishing_when_request_fails(self):
        with patch("features.iframe_feature.requests.get", side_effect=Exception("network error")):
            self.assertEqual(iframe_feature("https://example.com"), -1)


if __name__ == "__main__":
    unittest.main()
