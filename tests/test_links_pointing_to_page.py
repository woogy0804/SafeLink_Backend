import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from features.links_pointing_to_page_feature import (
    clear_backlink_cache,
    links_pointing_to_page_feature,
)


class TestLinksPointingToPageFeature(unittest.TestCase):
    def setUp(self):
        clear_backlink_cache()
        self.addCleanup(clear_backlink_cache)
        environment_patcher = patch.dict(
            os.environ,
            {"SAFELINK_BACKLINK_FILE": "test-backlinks.csv"},
        )
        environment_patcher.start()
        self.addCleanup(environment_patcher.stop)

    @patch(
        "features.links_pointing_to_page_feature._load_backlink_counts",
        return_value={"example.com": 3},
    )
    def test_legitimate_when_backlink_count_is_three_or_more(self, mock_load):
        self.assertEqual(links_pointing_to_page_feature("https://example.com"), 1)

    @patch(
        "features.links_pointing_to_page_feature._load_backlink_counts",
        return_value={"example.com": 2},
    )
    def test_suspicious_when_backlink_count_is_one_or_two(self, mock_load):
        self.assertEqual(links_pointing_to_page_feature("https://example.com"), 0)

    @patch(
        "features.links_pointing_to_page_feature._load_backlink_counts",
        return_value={"example.com": 0},
    )
    def test_phishing_when_no_backlink_exists(self, mock_load):
        self.assertEqual(links_pointing_to_page_feature("https://example.com"), -1)

    @patch(
        "features.links_pointing_to_page_feature._load_backlink_counts",
        return_value={},
    )
    def test_suspicious_when_domain_was_not_collected(self, mock_load):
        self.assertEqual(links_pointing_to_page_feature("https://example.com"), 0)

    @patch(
        "features.links_pointing_to_page_feature._load_backlink_counts",
        return_value=None,
    )
    def test_suspicious_when_backlink_data_is_unavailable(self, mock_load):
        self.assertEqual(links_pointing_to_page_feature("https://example.com"), 0)

    def test_loads_real_backlink_csv_and_normalizes_domain(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            backlink_file = Path(temporary_directory) / "backlinks.csv"
            backlink_file.write_text(
                "domain,count\nwww.example.com,3\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"SAFELINK_BACKLINK_FILE": str(backlink_file)},
            ):
                self.assertEqual(
                    links_pointing_to_page_feature("https://example.com"),
                    1,
                )

    def test_reloads_backlink_file_after_atomic_style_replacement(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            backlink_file = Path(temporary_directory) / "backlinks.csv"
            backlink_file.write_text("example.com,1\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"SAFELINK_BACKLINK_FILE": str(backlink_file)},
            ):
                self.assertEqual(
                    links_pointing_to_page_feature("https://example.com"),
                    0,
                )
                replacement = backlink_file.with_suffix(".new")
                replacement.write_text("example.com,3\n", encoding="utf-8")
                replacement.replace(backlink_file)
                self.assertEqual(
                    links_pointing_to_page_feature("https://example.com"),
                    1,
                )

    def test_malformed_backlink_file_is_treated_as_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            backlink_file = Path(temporary_directory) / "backlinks.csv"
            backlink_file.write_text("domain,count\ninvalid,row\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"SAFELINK_BACKLINK_FILE": str(backlink_file)},
            ):
                self.assertEqual(
                    links_pointing_to_page_feature("https://example.com"),
                    0,
                )

    def test_queries_sqlite_snapshot_without_loading_full_list(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "backlinks.sqlite3"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute(
                    "CREATE TABLE backlink_counts "
                    "(domain TEXT PRIMARY KEY, count INTEGER NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO backlink_counts VALUES (?, ?)",
                    ("example.com", 3),
                )
                connection.commit()
            finally:
                connection.close()

            with patch.dict(
                os.environ,
                {"SAFELINK_BACKLINK_FILE": str(database_path)},
            ):
                self.assertEqual(
                    links_pointing_to_page_feature("https://example.com"),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
