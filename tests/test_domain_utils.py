import unittest

from features.domain_utils import (
    get_hostname,
    get_registered_domain,
    get_registered_domain_from_url,
    get_subdomain_labels,
    is_same_registered_domain,
)


class TestDomainUtils(unittest.TestCase):
    def test_extracts_multi_level_public_suffix(self):
        self.assertEqual(
            get_registered_domain("login.example.co.uk"),
            "example.co.uk",
        )

    def test_private_suffix_keeps_tenants_separate(self):
        self.assertEqual(
            get_registered_domain("assets.alice.github.io"),
            "alice.github.io",
        )
        self.assertFalse(
            is_same_registered_domain(
                "https://bob.github.io",
                "alice.github.io",
            )
        )

    def test_unicode_hostname_is_normalized_to_punycode(self):
        unicode_domain = get_registered_domain_from_url("https://www.bücher.de")
        ascii_domain = get_registered_domain_from_url(
            "https://www.xn--bcher-kva.de"
        )

        self.assertEqual(unicode_domain, "xn--bcher-kva.de")
        self.assertEqual(unicode_domain, ascii_domain)

    def test_idna_2008_does_not_merge_sharp_s_with_ss(self):
        sharp_s_domain = get_registered_domain_from_url("https://faß.de")
        ss_domain = get_registered_domain_from_url("https://fass.de")

        self.assertEqual(sharp_s_domain, "xn--fa-hia.de")
        self.assertEqual(ss_domain, "fass.de")
        self.assertNotEqual(sharp_s_domain, ss_domain)

    def test_ipv4_and_ipv6_are_preserved(self):
        self.assertEqual(get_registered_domain("192.0.2.1"), "192.0.2.1")
        self.assertEqual(get_registered_domain("2001:db8::1"), "2001:db8::1")

    def test_unknown_or_missing_public_suffix_returns_none(self):
        self.assertIsNone(get_registered_domain("localhost"))
        self.assertIsNone(get_registered_domain("example.invalid"))

    def test_subdomain_labels_use_public_suffix_result(self):
        self.assertEqual(
            get_subdomain_labels("www.login.example.co.kr"),
            ["login"],
        )
        self.assertEqual(
            get_subdomain_labels("cdn.alice.github.io"),
            ["cdn"],
        )

    def test_get_hostname_normalizes_case_trailing_dot_and_www(self):
        self.assertEqual(
            get_hostname("https://WWW.Example.COM./path", strip_www=True),
            "example.com",
        )


if __name__ == "__main__":
    unittest.main()
