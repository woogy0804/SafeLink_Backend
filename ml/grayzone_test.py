"""Compare Logistic-to-Random-Forest Gray Zone boundaries."""

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


DEFAULT_ZONES = ((0.45, 0.55), (0.40, 0.60), (0.35, 0.65), (0.30, 0.70))


def evaluate_zones(dataset_path: Path, logistic_path: Path, forest_path: Path) -> dict:
    features, labels = load_processed_dataset(dataset_path)
    logistic = load_artifact(logistic_path)
    forest = load_artifact(forest_path)
    logistic_scores = phishing_probabilities(logistic, features)
    forest_scores = phishing_probabilities(forest, features)
    results = []

    for lower, upper in DEFAULT_ZONES:
        gray_mask = (logistic_scores > lower) & (logistic_scores < upper)
        cascade_scores = logistic_scores.copy()
        cascade_scores[gray_mask] = forest_scores[gray_mask]
        metrics = classification_metrics(labels, cascade_scores)
        results.append(
            {
                "lower": lower,
                "upper": upper,
                "second_stage_rows": int(gray_mask.sum()),
                "second_stage_rate": float(gray_mask.mean()),
                **metrics,
            }
        )

    recommended = max(
        results,
        key=lambda item: (item["f1"], item["recall"], -item["second_stage_rate"]),
    )
    return {
        "dataset": str(dataset_path),
        "rows": len(labels),
        "selection_rule": "highest F1, then recall, then lower second-stage rate",
        "recommended_gray_zone": [recommended["lower"], recommended["upper"]],
        "candidates": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROCESSED_DIR / "validation_v1.csv")
    parser.add_argument("--logistic", type=Path, default=MODELS_DIR / "logistic_model.pkl")
    parser.add_argument("--forest", type=Path, default=MODELS_DIR / "random_forest_model.pkl")
    parser.add_argument("--output", type=Path, default=MODELS_DIR / "grayzone_report.json")
    args = parser.parse_args()
    report = evaluate_zones(args.dataset, args.logistic, args.forest)
    write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
