import tempfile
import unittest
from pathlib import Path

from scripts.update_backlinks_dataforseo import (
    DataForSeoError,
    load_domains,
    parse_counts,
)


class TestUpdateBacklinksDataForSeo(unittest.TestCase):
    def test_load_domains_normalizes_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "domains.csv"
            path.write_text(
                "domain\nwww.Example.com\nexample.com\nsub.other.co.kr\n",
                encoding="utf-8",
            )
            domains = load_domains(path)

        self.assertEqual(domains, ["example.com", "other.co.kr"])

    def test_parse_counts_uses_referring_main_domains(self):
        payload = {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "target": "example.com",
                                    "referring_domains": 20,
                                    "referring_main_domains": 3,
                                }
                            ]
                        }
                    ],
                }
            ],
        }

        self.assertEqual(parse_counts(payload, {"example.com"}), {"example.com": 3})

    def test_missing_target_is_not_converted_to_explicit_zero(self):
        payload = {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
        }

        with self.assertRaises(DataForSeoError):
            parse_counts(payload, {"example.com"})


if __name__ == "__main__":
    unittest.main()
