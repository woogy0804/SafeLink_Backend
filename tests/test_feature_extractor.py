import unittest
from threading import Barrier
from datetime import datetime, timezone
from unittest.mock import patch

from features import feature_extractor
from features.domain_context import DomainAnalysisContext


class FakeResponse:
    def __init__(self, text: str, url: str):
        self.text = text
        self.url = url

    def raise_for_status(self):
        return None


class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        destination_patcher = patch(
            "features.safe_http.resolve_public_destination",
            side_effect=lambda url: url,
        )
        destination_patcher.start()
        self.addCleanup(destination_patcher.stop)

    def test_feature_names_are_fixed_in_expected_order(self):
        self.assertEqual(
            feature_extractor.FEATURE_NAMES,
            [
                "SSLfinal_State",
                "URL_of_Anchor",
                "web_traffic",
                "Prefix_Suffix",
                "having_Sub_Domain",
                "Links_in_tags",
                "Links_pointing_to_page",
                "Request_URL",
                "SFH",
                "age_of_domain",
                "Domain_registeration_length",
                "having_IP_Address",
            ],
        )

    def test_extract_features_returns_values_in_function_order(self):
        feature_functions = (
            ("first", lambda url: 1),
            ("second", lambda url: 0),
            ("third", lambda url: -1),
        )

        with patch.object(feature_extractor, "FEATURE_FUNCTIONS", feature_functions):
            self.assertEqual(feature_extractor.extract_features("https://example.com"), [1, 0, -1])

    def test_extract_features_converts_invalid_values_to_phishing(self):
        feature_functions = (
            ("valid", lambda url: 1),
            ("invalid", lambda url: 99),
        )

        with patch.object(feature_extractor, "FEATURE_FUNCTIONS", feature_functions):
            self.assertEqual(feature_extractor.extract_features("https://example.com"), [1, -1])

    def test_extract_features_converts_feature_exception_to_phishing(self):
        def broken_feature(url):
            raise RuntimeError("feature failed")

        feature_functions = (
            ("valid", lambda url: 1),
            ("broken", broken_feature),
        )

        with patch.object(feature_extractor, "FEATURE_FUNCTIONS", feature_functions):
            self.assertEqual(feature_extractor.extract_features("https://example.com"), [1, -1])

    def test_extract_feature_dict_maps_names_to_values(self):
        with patch.object(feature_extractor, "FEATURE_NAMES", ["first", "second"]):
            with patch.object(feature_extractor, "extract_features", return_value=[1, -1]):
                self.assertEqual(
                    feature_extractor.extract_feature_dict("https://example.com"),
                    {"first": 1, "second": -1},
                )

    def test_html_features_share_one_http_request(self):
        url = "https://example.com"
        html = """
        <html>
          <head>
            <script src="/app.js"></script>
            <link href="/style.css" rel="stylesheet">
          </head>
          <body>
            <a href="/home">home</a>
            <form action="/login"></form>
            <img src="/logo.png">
          </body>
        </html>
        """
        html_features = (
            ("anchor", feature_extractor.anchor_feature),
            ("links_in_tags", feature_extractor.links_in_tags_feature),
            ("request_url", feature_extractor.request_url_feature),
            ("sfh", feature_extractor.sfh_feature),
        )

        with patch.object(feature_extractor, "FEATURE_FUNCTIONS", html_features):
            with patch(
                "features.safe_http._request_pinned_destination",
                return_value=FakeResponse(html, url),
            ) as mock_get:
                self.assertEqual(
                    feature_extractor.extract_features(url),
                    [1, 1, 1, 1],
                )

        self.assertEqual(mock_get.call_count, 1)

    def test_domain_features_share_one_rdap_lookup(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            expiration_date=datetime(2999, 1, 1, tzinfo=timezone.utc),
            lookup_failed=False,
        )
        domain_features = (
            ("domain_age", feature_extractor.domain_age_feature),
            (
                "domain_registration_length",
                feature_extractor.domain_registration_length_feature,
            ),
        )

        with patch.object(feature_extractor, "FEATURE_FUNCTIONS", domain_features):
            with patch.object(
                feature_extractor,
                "fetch_domain_context",
                return_value=context,
            ) as mock_fetch:
                self.assertEqual(
                    feature_extractor.extract_features("https://example.com"),
                    [1, 1],
                )

        mock_fetch.assert_called_once_with("https://example.com")

    def test_network_groups_start_concurrently(self):
        barrier = Barrier(3, timeout=2)

        def concurrent_ssl(url):
            barrier.wait()
            return 1

        def concurrent_html_context(url):
            barrier.wait()
            return "html-context"

        def concurrent_domain_context(url):
            barrier.wait()
            return "domain-context"

        def html_feature(url, html_context):
            return 1 if html_context == "html-context" else -1

        def domain_feature(url, domain_context):
            return 1 if domain_context == "domain-context" else -1

        feature_functions = (
            ("ssl", concurrent_ssl),
            ("html", html_feature),
            ("domain", domain_feature),
        )

        with patch.object(feature_extractor, "ssl_feature", concurrent_ssl):
            with patch.object(
                feature_extractor,
                "FEATURE_FUNCTIONS",
                feature_functions,
            ):
                with patch.object(
                    feature_extractor,
                    "HTML_FEATURE_FUNCTIONS",
                    frozenset({html_feature}),
                ):
                    with patch.object(
                        feature_extractor,
                        "DOMAIN_FEATURE_FUNCTIONS",
                        frozenset({domain_feature}),
                    ):
                        with patch.object(
                            feature_extractor,
                            "fetch_html_context",
                            concurrent_html_context,
                        ):
                            with patch.object(
                                feature_extractor,
                                "fetch_domain_context",
                                concurrent_domain_context,
                            ):
                                result = feature_extractor.extract_features(
                                    "https://example.com"
                                )

        self.assertEqual(result, [1, 1, 1])


class TestAsyncFeatureExtractor(unittest.IsolatedAsyncioTestCase):
    async def test_async_extractor_returns_sync_result(self):
        with patch.object(
            feature_extractor,
            "extract_features",
            return_value=[1, 0, -1],
        ) as mock_extract:
            result = await feature_extractor.extract_features_async(
                "https://example.com"
            )

        self.assertEqual(result, [1, 0, -1])
        mock_extract.assert_called_once_with("https://example.com")

    async def test_async_dict_keeps_feature_names(self):
        with patch.object(
            feature_extractor,
            "FEATURE_NAMES",
            ["first", "second"],
        ):
            with patch.object(
                feature_extractor,
                "extract_features_async",
                return_value=[1, -1],
            ):
                result = await feature_extractor.extract_feature_dict_async(
                    "https://example.com"
                )

        self.assertEqual(result, {"first": 1, "second": -1})


if __name__ == "__main__":
    unittest.main()
