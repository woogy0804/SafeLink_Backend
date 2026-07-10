import unittest
from unittest.mock import patch

from features.request_url_feature import request_url_feature


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class TestRequestUrlFeature(unittest.TestCase):
    def test_legitimate_when_external_ratio_under_22(self):
        html = """
        <img src="/a.png">
        <img src="https://example.com/b.png">
        <video src="/c.mp4"></video>
        <audio src="/d.mp3"></audio>
        <img src="https://cdn.example.net/e.png">
        """

        with patch("features.request_url_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(request_url_feature("https://example.com"), 1)

    def test_suspicious_when_external_ratio_between_22_and_61(self):
        html = """
        <img src="/a.png">
        <img src="https://cdn.example.net/b.png">
        <video src="/c.mp4"></video>
        <audio src="https://media.example.net/d.mp3"></audio>
        <img src="/e.png">
        """

        with patch("features.request_url_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(request_url_feature("https://example.com"), 0)

    def test_phishing_when_external_ratio_over_61(self):
        html = """
        <img src="https://cdn1.example.net/a.png">
        <img src="https://cdn2.example.net/b.png">
        <video src="https://cdn3.example.net/c.mp4"></video>
        <audio src="https://cdn4.example.net/d.mp3"></audio>
        <img src="/e.png">
        """

        with patch("features.request_url_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(request_url_feature("https://example.com"), -1)

    def test_legitimate_when_no_media_resources(self):
        html = "<html><body>No media</body></html>"

        with patch("features.request_url_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(request_url_feature("https://example.com"), 1)

    def test_phishing_when_request_fails(self):
        with patch("features.request_url_feature.requests.get", side_effect=Exception("network error")):
            self.assertEqual(request_url_feature("https://example.com"), -1)


if __name__ == "__main__":
    unittest.main()
