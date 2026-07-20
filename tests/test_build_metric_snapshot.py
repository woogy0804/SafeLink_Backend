import sqlite3
import tempfile
import unittest
from pathlib import Path

from features.metric_database import (
    query_backlink_count,
    query_tranco_rank,
)
from scripts.build_metric_snapshot import (
    build_backlink_database,
    build_tranco_database,
)


class TestBuildMetricSnapshot(unittest.TestCase):
    def test_builds_tranco_database_and_keeps_best_duplicate_rank(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = directory / "tranco.csv"
            output_path = directory / "tranco.sqlite3"
            source_path.write_text(
                "rank,domain\n20,www.example.com\n10,example.com\n",
                encoding="utf-8",
            )

            row_count = build_tranco_database(
                source_path,
                output_path,
                snapshot_id="TEST1",
            )
            result = query_tranco_rank(output_path, "example.com")

        self.assertEqual(row_count, 1)
        self.assertTrue(result.available)
        self.assertEqual(result.value, 10)

    def test_builds_backlink_database_with_explicit_zero(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = directory / "backlinks.csv"
            output_path = directory / "backlinks.sqlite3"
            source_path.write_text(
                "domain,count\nexample.com,0\nother.com,3\n",
                encoding="utf-8",
            )

            row_count = build_backlink_database(
                source_path,
                output_path,
                source="test-provider",
                observed_at="2026-07-20T00:00:00Z",
            )
            zero_result = query_backlink_count(output_path, "example.com")
            missing_result = query_backlink_count(output_path, "missing.com")

        self.assertEqual(row_count, 2)
        self.assertEqual(zero_result.value, 0)
        self.assertTrue(missing_result.available)
        self.assertIsNone(missing_result.value)

    def test_failed_build_does_not_replace_existing_database(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = directory / "empty.csv"
            output_path = directory / "tranco.sqlite3"
            source_path.write_text("rank,domain\n", encoding="utf-8")
            output_path.write_bytes(b"existing-data")

            with self.assertRaises(ValueError):
                build_tranco_database(
                    source_path,
                    output_path,
                    minimum_rows=1,
                )

            self.assertEqual(output_path.read_bytes(), b"existing-data")

    def test_metadata_is_recorded_in_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_path = directory / "tranco.csv"
            output_path = directory / "tranco.sqlite3"
            source_path.write_text("1,example.com\n", encoding="utf-8")
            build_tranco_database(
                source_path,
                output_path,
                source="unit-test",
                snapshot_id="TEST2",
            )

            connection = sqlite3.connect(output_path)
            try:
                metadata = dict(
                    connection.execute(
                        "SELECT key, value FROM snapshot_metadata"
                    ).fetchall()
                )
            finally:
                connection.close()

        self.assertEqual(metadata["source"], "unit-test")
        self.assertEqual(metadata["snapshot_id"], "TEST2")
        self.assertEqual(metadata["row_count"], "1")


if __name__ == "__main__":
    unittest.main()
