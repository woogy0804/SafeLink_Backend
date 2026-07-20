import unittest
from unittest.mock import patch

from features.anchor_feature import anchor_feature


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class TestAnchorFeature(unittest.TestCase):
    def setUp(self):
        destination_patcher = patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        )
        destination_patcher.start()
        self.addCleanup(destination_patcher.stop)

    def test_legitimate_when_unsafe_ratio_under_31(self):
        html = """
        <a href="/home">home</a>
        <a href="https://example.com/about">about</a>
        <a href="/contact">contact</a>
        <a href="https://external.example.net">external</a>
        """

        with patch("features.anchor_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(anchor_feature("https://example.com"), 1)

    def test_suspicious_when_unsafe_ratio_between_31_and_67(self):
        html = """
        <a href="/home">home</a>
        <a href="https://external1.example.net">external</a>
        <a href="/contact">contact</a>
        <a href="#">invalid</a>
        """

        with patch("features.anchor_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(anchor_feature("https://example.com"), 0)

    def test_phishing_when_unsafe_ratio_over_67(self):
        html = """
        <a href="#">invalid</a>
        <a href="javascript:void(0)">invalid</a>
        <a href="https://external.example.net">external</a>
        <a href="/safe">safe</a>
        """

        with patch("features.anchor_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(anchor_feature("https://example.com"), -1)

    def test_legitimate_when_no_anchors_exist(self):
        html = "<html><body>No anchors</body></html>"

        with patch("features.anchor_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(anchor_feature("https://example.com"), 1)

    def test_suspicious_when_page_is_empty_spa_shell(self):
        html = '<html><body><div id="root"></div><script src="/app.js"></script></body></html>'

        with patch("features.anchor_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(anchor_feature("https://example.com"), 0)

    def test_subdomain_of_same_registered_domain_is_safe(self):
        html = '<a href="https://help.example.com/faq">help</a>'

        with patch("features.anchor_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(anchor_feature("https://www.example.com"), 1)

    def test_phishing_when_request_fails(self):
        with patch("features.anchor_feature.requests.get", side_effect=Exception("network error")):
            self.assertEqual(anchor_feature("https://example.com"), -1)


if __name__ == "__main__":
    unittest.main()
