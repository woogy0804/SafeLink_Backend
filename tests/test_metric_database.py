import sqlite3
import tempfile
import unittest
from pathlib import Path

from features.metric_database import (
    query_backlink_count,
    query_tranco_rank,
)


class TestMetricDatabase(unittest.TestCase):
    def test_queries_rank_and_backlink_values(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "metrics.sqlite3"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute(
                    "CREATE TABLE tranco_ranks "
                    "(domain TEXT PRIMARY KEY, rank INTEGER NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE backlink_counts "
                    "(domain TEXT PRIMARY KEY, count INTEGER NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO tranco_ranks VALUES (?, ?)",
                    ("example.com", 10),
                )
                connection.execute(
                    "INSERT INTO backlink_counts VALUES (?, ?)",
                    ("example.com", 3),
                )
                connection.commit()
            finally:
                connection.close()

            rank_result = query_tranco_rank(database_path, "example.com")
            backlink_result = query_backlink_count(
                database_path,
                "example.com",
            )

        self.assertTrue(rank_result.available)
        self.assertEqual(rank_result.value, 10)
        self.assertTrue(backlink_result.available)
        self.assertEqual(backlink_result.value, 3)

    def test_missing_row_is_different_from_unavailable_database(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "metrics.sqlite3"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute(
                    "CREATE TABLE tranco_ranks "
                    "(domain TEXT PRIMARY KEY, rank INTEGER NOT NULL)"
                )
                connection.commit()
            finally:
                connection.close()

            missing_row = query_tranco_rank(database_path, "example.com")
            unavailable = query_tranco_rank(
                Path(temporary_directory) / "missing.sqlite3",
                "example.com",
            )

        self.assertTrue(missing_row.available)
        self.assertIsNone(missing_row.value)
        self.assertFalse(unavailable.available)

    def test_invalid_database_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "invalid.sqlite3"
            database_path.write_text("not sqlite", encoding="utf-8")

            result = query_tranco_rank(database_path, "example.com")

        self.assertFalse(result.available)
        self.assertIsNone(result.value)


if __name__ == "__main__":
    unittest.main()
