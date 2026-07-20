import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from features.feature_extractor import FEATURE_NAMES
from scripts.train_phishing_model import load_dataset, split_dataset


class TestTrainPhishingModel(unittest.TestCase):
    def test_loader_retains_feature_identical_rows_and_maps_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.csv"
            fieldnames = ["index", *FEATURE_NAMES, "extra", "Result"]
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for index in range(120):
                    row = {
                        "index": index,
                        **{name: (-1 if index % 2 else 1) for name in FEATURE_NAMES},
                        "extra": index,
                        "Result": -1 if index % 2 else 1,
                    }
                    writer.writerow(row)
                    duplicate = dict(row)
                    duplicate["index"] = index + 1000
                    writer.writerow(duplicate)

            x, y, metadata = load_dataset(path)

        self.assertEqual(len(x), 240)
        self.assertEqual(metadata["training_rows"], 240)
        self.assertEqual(set(y), {0, 1})

    def test_split_keeps_identical_feature_vectors_in_one_partition(self):
        rng = np.random.default_rng(42)
        unique = rng.integers(-1, 2, size=(200, len(FEATURE_NAMES)), dtype=np.int8)
        x = np.repeat(unique, 2, axis=0)
        y = np.tile(np.asarray([0, 1], dtype=np.int8), 200)

        train_index, validation_index, test_index, groups = split_dataset(x, y)
        group_sets = [set(groups[index]) for index in (train_index, validation_index, test_index)]

        self.assertFalse(group_sets[0] & group_sets[1])
        self.assertFalse(group_sets[0] & group_sets[2])
        self.assertFalse(group_sets[1] & group_sets[2])


if __name__ == "__main__":
    unittest.main()
