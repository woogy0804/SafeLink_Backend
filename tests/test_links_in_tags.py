import unittest
from unittest.mock import patch

from features.links_in_tags_feature import links_in_tags_feature


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class TestLinksInTagsFeature(unittest.TestCase):
    def setUp(self):
        destination_patcher = patch(
            "features.safe_http.resolve_public_destination",
            side_effect=lambda url: url,
        )
        destination_patcher.start()
        self.addCleanup(destination_patcher.stop)

    def test_legitimate_when_external_ratio_is_under_17(self):
        html = """
        <script src="/a.js"></script>
        <script src="https://static.example.com/b.js"></script>
        <link href="/a.css" rel="stylesheet">
        <link href="/b.css" rel="stylesheet">
        <link href="/c.css" rel="stylesheet">
        <link href="/d.css" rel="stylesheet">
        <script src="https://cdn.example.net/x.js"></script>
        """
        with patch("features.safe_http._request_pinned_destination", return_value=FakeResponse(html)):
            self.assertEqual(links_in_tags_feature("https://example.com"), 1)

    def test_suspicious_when_external_ratio_is_between_17_and_81(self):
        html = """
        <script src="/a.js"></script>
        <script src="https://cdn.example.net/b.js"></script>
        """
        with patch("features.safe_http._request_pinned_destination", return_value=FakeResponse(html)):
            self.assertEqual(links_in_tags_feature("https://example.com"), 0)

    def test_phishing_when_external_ratio_is_over_81(self):
        html = """
        <script src="https://cdn1.example.net/a.js"></script>
        <link href="https://cdn2.example.net/a.css" rel="stylesheet">
        """
        with patch("features.safe_http._request_pinned_destination", return_value=FakeResponse(html)):
            self.assertEqual(links_in_tags_feature("https://example.com"), -1)

    def test_meta_refresh_url_is_counted(self):
        html = '<meta http-equiv="refresh" content="0; url=https://evil.example.net">'
        with patch("features.safe_http._request_pinned_destination", return_value=FakeResponse(html)):
            self.assertEqual(links_in_tags_feature("https://example.com"), -1)

    def test_suspicious_when_page_is_empty_spa_shell(self):
        html = '<html><body><div id="root"></div><script src="/app.js"></script></body></html>'
        with patch("features.safe_http._request_pinned_destination", return_value=FakeResponse(html)):
            self.assertEqual(links_in_tags_feature("https://example.com"), 0)


if __name__ == "__main__":
    unittest.main()
