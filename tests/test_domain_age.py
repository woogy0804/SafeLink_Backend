import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from features.domain_age_feature import domain_age_feature
from features.domain_context import DomainAnalysisContext


class TestDomainAgeFeature(unittest.TestCase):
    def test_legitimate_when_domain_is_older_than_six_months(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            expiration_date=None,
            lookup_failed=False,
        )
        with patch(
            "features.domain_age_feature.fetch_domain_context",
            return_value=context,
        ):
            self.assertEqual(domain_age_feature("https://example.com"), 1)

    def test_phishing_when_domain_is_younger_than_six_months(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=datetime(2999, 1, 1, tzinfo=timezone.utc),
            expiration_date=None,
            lookup_failed=False,
        )
        with patch(
            "features.domain_age_feature.fetch_domain_context",
            return_value=context,
        ):
            self.assertEqual(domain_age_feature("https://example.com"), -1)

    def test_suspicious_when_rdap_lookup_fails(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=None,
            expiration_date=None,
            lookup_failed=True,
        )
        with patch(
            "features.domain_age_feature.fetch_domain_context",
            return_value=context,
        ):
            self.assertEqual(domain_age_feature("https://example.com"), 0)


if __name__ == "__main__":
    unittest.main()
