"""Train the second-stage Random Forest model."""

import argparse
import json
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier

from ml.model_utils import MODELS_DIR, PROCESSED_DIR, load_processed_dataset, save_artifact


def train(input_path: Path, output_path: Path) -> dict:
    features, labels = load_processed_dataset(input_path)
    estimator = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    estimator.fit(features, labels)
    metadata = save_artifact(estimator, "random_forest", output_path)
    return {**metadata, "training_rows": len(labels), "output": str(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROCESSED_DIR / "train_v1.csv")
    parser.add_argument("--output", type=Path, default=MODELS_DIR / "random_forest_model.pkl")
    args = parser.parse_args()
    print(json.dumps(train(args.input, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
