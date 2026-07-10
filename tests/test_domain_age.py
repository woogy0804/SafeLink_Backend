import subprocess
import unittest
from unittest.mock import patch

from features.domain_age_feature import domain_age_feature


class TestDomainAgeFeature(unittest.TestCase):
    def test_legitimate_when_domain_is_older_than_six_months(self):
        result = subprocess.CompletedProcess(
            args=["whois", "example.com"],
            returncode=0,
            stdout="Creation Date: 2020-01-01T00:00:00Z\n",
            stderr="",
        )

        with patch("features.domain_age_feature.subprocess.run", return_value=result):
            self.assertEqual(domain_age_feature("https://example.com"), 1)

    def test_phishing_when_domain_is_younger_than_six_months(self):
        result = subprocess.CompletedProcess(
            args=["whois", "example.com"],
            returncode=0,
            stdout="Creation Date: 2999-01-01T00:00:00Z\n",
            stderr="",
        )

        with patch("features.domain_age_feature.subprocess.run", return_value=result):
            self.assertEqual(domain_age_feature("https://example.com"), -1)

    def test_phishing_when_whois_fails(self):
        result = subprocess.CompletedProcess(
            args=["whois", "example.com"],
            returncode=1,
            stdout="",
            stderr="error",
        )

        with patch("features.domain_age_feature.subprocess.run", return_value=result):
            self.assertEqual(domain_age_feature("https://example.com"), -1)


if __name__ == "__main__":
    unittest.main()
