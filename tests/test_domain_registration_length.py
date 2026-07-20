import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from features.domain_context import DomainAnalysisContext
from features.domain_registration_length_feature import (
    domain_registration_length_feature,
)


class TestDomainRegistrationLengthFeature(unittest.TestCase):
    def test_legitimate_when_more_than_one_year_remains(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=None,
            expiration_date=datetime(2999, 1, 1, tzinfo=timezone.utc),
            lookup_failed=False,
        )
        with patch(
            "features.domain_registration_length_feature.fetch_domain_context",
            return_value=context,
        ):
            self.assertEqual(domain_registration_length_feature("https://example.com"), 1)

    def test_phishing_when_domain_is_already_expired(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=None,
            expiration_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
            lookup_failed=False,
        )
        with patch(
            "features.domain_registration_length_feature.fetch_domain_context",
            return_value=context,
        ):
            self.assertEqual(domain_registration_length_feature("https://example.com"), -1)

    def test_suspicious_when_rdap_lookup_fails(self):
        context = DomainAnalysisContext(
            registered_domain="example.com",
            creation_date=None,
            expiration_date=None,
            lookup_failed=True,
        )
        with patch(
            "features.domain_registration_length_feature.fetch_domain_context",
            return_value=context,
        ):
            self.assertEqual(domain_registration_length_feature("https://example.com"), 0)


if __name__ == "__main__":
    unittest.main()
