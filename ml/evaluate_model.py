"""Evaluate the two independently trained models on a held-out dataset."""

import argparse
import json
from pathlib import Path

from ml.model_utils import (
    MODELS_DIR,
    PROCESSED_DIR,
    classification_metrics,
    load_artifact,
    load_processed_dataset,
    phishing_probabilities,
    write_json,
)


def evaluate(
    dataset_path: Path,
    logistic_path: Path,
    forest_path: Path,
    gray_lower: float = 0.30,
    gray_upper: float = 0.70,
) -> dict:
    features, labels = load_processed_dataset(dataset_path)
    logistic = load_artifact(logistic_path)
    forest = load_artifact(forest_path)
    logistic_scores = phishing_probabilities(logistic, features)
    forest_scores = phishing_probabilities(forest, features)
    gray_mask = (logistic_scores > gray_lower) & (logistic_scores < gray_upper)
    cascade_scores = logistic_scores.copy()
    cascade_scores[gray_mask] = forest_scores[gray_mask]
    return {
        "dataset": str(dataset_path),
        "rows": len(labels),
        "logistic_regression": classification_metrics(
            labels, logistic_scores
        ),
        "random_forest": classification_metrics(
            labels, forest_scores
        ),
        "cascade": {
            "gray_zone": [gray_lower, gray_upper],
            "second_stage_rows": int(gray_mask.sum()),
            "second_stage_rate": float(gray_mask.mean()),
            **classification_metrics(labels, cascade_scores),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROCESSED_DIR / "test_v1.csv")
    parser.add_argument("--logistic", type=Path, default=MODELS_DIR / "logistic_model.pkl")
    parser.add_argument("--forest", type=Path, default=MODELS_DIR / "random_forest_model.pkl")
    parser.add_argument("--gray-lower", type=float, default=0.30)
    parser.add_argument("--gray-upper", type=float, default=0.70)
    parser.add_argument("--output", type=Path, default=MODELS_DIR / "model_evaluation.json")
    args = parser.parse_args()
    if not 0 <= args.gray_lower < args.gray_upper <= 1:
        parser.error("Gray Zone must satisfy 0 <= lower < upper <= 1")
    report = evaluate(
        args.dataset,
        args.logistic,
        args.forest,
        args.gray_lower,
        args.gray_upper,
    )
    write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
