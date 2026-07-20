import unittest
from unittest.mock import patch

from features.sfh_feature import sfh_feature


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class TestSfhFeature(unittest.TestCase):
    def setUp(self):
        destination_patcher = patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        )
        destination_patcher.start()
        self.addCleanup(destination_patcher.stop)

    def test_legitimate_when_action_is_same_domain(self):
        html = '<form action="https://example.com/login"></form>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), 1)

    def test_legitimate_when_action_is_relative_path(self):
        html = '<form action="/login"></form>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), 1)

    def test_suspicious_when_action_uses_different_subdomain(self):
        html = '<form action="https://auth.example.com/login"></form>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://www.example.com"), 0)

    def test_phishing_when_action_is_external_domain(self):
        html = '<form action="https://evil.example.net/login"></form>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), -1)

    def test_phishing_when_action_is_empty(self):
        html = '<form action=""></form>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), -1)

    def test_phishing_when_action_is_about_blank(self):
        html = '<form action="about:blank"></form>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), -1)

    def test_legitimate_when_no_forms_exist(self):
        html = "<html><body>No forms</body></html>"

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), 1)

    def test_suspicious_when_page_is_empty_spa_shell(self):
        html = '<html><body><div id="app"></div><script src="/app.js"></script></body></html>'

        with patch("features.sfh_feature.requests.get", return_value=FakeResponse(html)):
            self.assertEqual(sfh_feature("https://example.com"), 0)

    def test_phishing_when_request_fails(self):
        with patch("features.sfh_feature.requests.get", side_effect=Exception("network error")):
            self.assertEqual(sfh_feature("https://example.com"), -1)


if __name__ == "__main__":
    unittest.main()
