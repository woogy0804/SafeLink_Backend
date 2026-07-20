import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from features.web_traffic_feature import (
    clear_web_traffic_cache,
    web_traffic_feature,
)


class TestWebTrafficFeature(unittest.TestCase):
    def setUp(self):
        clear_web_traffic_cache()
        self.addCleanup(clear_web_traffic_cache)
        environment_patcher = patch.dict(
            os.environ,
            {"SAFELINK_TRANCO_FILE": "test-tranco.csv"},
        )
        environment_patcher.start()
        self.addCleanup(environment_patcher.stop)

    @patch("features.web_traffic_feature._load_domain_ranks", return_value={"example.com": 10})
    def test_legitimate_when_rank_is_within_top_100000(self, mock_load):
        self.assertEqual(web_traffic_feature("https://www.example.com"), 1)

    @patch("features.web_traffic_feature._load_domain_ranks", return_value={"example.com": 200000})
    def test_suspicious_when_rank_is_below_top_100000(self, mock_load):
        self.assertEqual(web_traffic_feature("https://example.com"), 0)

    @patch("features.web_traffic_feature._load_domain_ranks", return_value={})
    def test_phishing_when_domain_has_no_rank(self, mock_load):
        self.assertEqual(web_traffic_feature("https://example.com"), -1)

    @patch("features.web_traffic_feature._load_domain_ranks", return_value=None)
    def test_suspicious_when_rank_data_is_unavailable(self, mock_load):
        self.assertEqual(web_traffic_feature("https://example.com"), 0)

    def test_loads_real_tranco_csv_with_header_and_subdomain(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            rank_file = Path(temporary_directory) / "tranco.csv"
            rank_file.write_text(
                "rank,domain\n10,www.example.com\n200000,other.example\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"SAFELINK_TRANCO_FILE": str(rank_file)},
            ):
                self.assertEqual(web_traffic_feature("https://example.com"), 1)

    def test_reloads_rank_file_after_atomic_style_replacement(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            rank_file = Path(temporary_directory) / "tranco.csv"
            rank_file.write_text("10,example.com\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"SAFELINK_TRANCO_FILE": str(rank_file)},
            ):
                self.assertEqual(web_traffic_feature("https://example.com"), 1)
                replacement = rank_file.with_suffix(".new")
                replacement.write_text("200000,example.com\n", encoding="utf-8")
                replacement.replace(rank_file)
                self.assertEqual(web_traffic_feature("https://example.com"), 0)

    def test_malformed_rank_file_is_treated_as_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            rank_file = Path(temporary_directory) / "tranco.csv"
            rank_file.write_text("rank,domain\ninvalid,row\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"SAFELINK_TRANCO_FILE": str(rank_file)},
            ):
                self.assertEqual(web_traffic_feature("https://example.com"), 0)

    def test_queries_sqlite_snapshot_without_loading_full_list(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "tranco.sqlite3"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute(
                    "CREATE TABLE tranco_ranks "
                    "(domain TEXT PRIMARY KEY, rank INTEGER NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO tranco_ranks VALUES (?, ?)",
                    ("example.com", 100000),
                )
                connection.commit()
            finally:
                connection.close()

            with patch.dict(
                os.environ,
                {"SAFELINK_TRANCO_FILE": str(database_path)},
            ):
                self.assertEqual(web_traffic_feature("https://example.com"), 1)


if __name__ == "__main__":
    unittest.main()
