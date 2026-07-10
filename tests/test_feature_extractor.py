import unittest
from unittest.mock import patch

from features import feature_extractor


class TestFeatureExtractor(unittest.TestCase):
    def test_feature_names_are_fixed_in_expected_order(self):
        self.assertEqual(
            feature_extractor.FEATURE_NAMES,
            [
                "having_ip",
                "url_length",
                "shortener",
                "prefix_suffix",
                "ssl",
                "domain_age",
                "dns",
                "request_url",
                "anchor",
                "sfh",
                "forwarding",
                "iframe",
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


if __name__ == "__main__":
    unittest.main()
