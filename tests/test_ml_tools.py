import csv
import tempfile
import unittest
from pathlib import Path

from features.feature_extractor import FEATURE_NAMES
from ml.model_utils import load_artifact, load_processed_dataset
from ml.prepare_dataset import prepare


class TestMlTools(unittest.TestCase):
    def test_generated_artifacts_use_production_feature_order(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ("logistic_model.pkl", "random_forest_model.pkl"):
            artifact = load_artifact(root / "models" / filename)
            self.assertEqual(artifact["feature_names"], list(FEATURE_NAMES))
            self.assertEqual(list(artifact["estimator"].classes_), [0, 1])

    def test_processed_loader_rejects_out_of_range_feature(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=[*FEATURE_NAMES, "label"])
                writer.writeheader()
                row = {name: 1 for name in FEATURE_NAMES}
                row[FEATURE_NAMES[0]] = 2
                writer.writerow({**row, "label": 0})

            with self.assertRaisesRegex(ValueError, "Invalid feature value"):
                load_processed_dataset(path)

    def test_prepare_dataset_maps_source_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "raw.csv"
            output_path = Path(directory) / "feature_dataset.csv"
            fieldnames = [*FEATURE_NAMES, "Result"]
            with source_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for index in range(100):
                    writer.writerow(
                        {
                            **{name: 1 if index % 2 else -1 for name in FEATURE_NAMES},
                            "Result": 1 if index % 2 else -1,
                        }
                    )

            self.assertEqual(prepare(source_path, output_path), 100)
            features, labels = load_processed_dataset(output_path)
            self.assertEqual(len(features), 100)
            self.assertEqual(set(labels), {0, 1})


if __name__ == "__main__":
    unittest.main()
