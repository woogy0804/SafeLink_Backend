import csv
import tempfile
import unittest
from pathlib import Path

from scripts.clean_training_dataset import remove_repeated_half


class TestCleanTrainingDataset(unittest.TestCase):
    def test_removes_second_half_when_only_index_differs(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            output_path = Path(directory) / "output.csv"
            input_path.write_text(
                "index,feature,Result\n"
                "0,1,-1\n1,-1,1\n"
                "2,1,-1\n3,-1,1\n",
                encoding="utf-8",
            )

            count = remove_repeated_half(input_path, output_path)
            with output_path.open(encoding="utf-8", newline="") as output:
                rows = list(csv.DictReader(output))

        self.assertEqual(count, 2)
        self.assertEqual([row["index"] for row in rows], ["0", "1"])

    def test_rejects_nonmatching_halves(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            output_path = Path(directory) / "output.csv"
            input_path.write_text(
                "index,feature,Result\n0,1,-1\n1,-1,1\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                remove_repeated_half(input_path, output_path)


if __name__ == "__main__":
    unittest.main()
