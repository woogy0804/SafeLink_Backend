"""Train and evaluate phishing classifiers from the 12 production features."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from features.feature_extractor import FEATURE_NAMES


DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / "phishing_websites.csv"
)
DEFAULT_MODEL = (
    Path(__file__).resolve().parents[1] / "models" / "phishing_model_v1.joblib"
)
PHISHING_SOURCE_LABEL = -1
LEGITIMATE_SOURCE_LABEL = 1
RANDOM_SEED = 42


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """Load and validate source rows without guessing URL identity.

    The source has no URL column. Feature-identical rows may therefore belong
    to different URLs and are retained. A known repeated file block must be
    removed explicitly with ``scripts.clean_training_dataset`` before training.
    Evaluation leakage is prevented separately by grouping identical production
    12-feature vectors into the same split.
    """

    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("Training CSV has no header")
        required = set(FEATURE_NAMES) | {"Result"}
        missing = sorted(required.difference(reader.fieldnames))
        if missing:
            raise ValueError(f"Training CSV is missing columns: {', '.join(missing)}")

        raw_rows = 0
        features = []
        labels = []
        label_counts = Counter()

        for row_number, row in enumerate(reader, start=2):
            raw_rows += 1
            try:
                values = [int(row[name]) for name in FEATURE_NAMES]
                source_label = int(row["Result"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid integer at CSV row {row_number}") from error
            if any(value not in {-1, 0, 1} for value in values):
                raise ValueError(f"Invalid feature value at CSV row {row_number}")
            if source_label not in {PHISHING_SOURCE_LABEL, LEGITIMATE_SOURCE_LABEL}:
                raise ValueError(f"Invalid Result label at CSV row {row_number}")

            # Internal ML label: 1=phishing, 0=legitimate.
            model_label = 1 if source_label == PHISHING_SOURCE_LABEL else 0
            features.append(values)
            labels.append(model_label)
            label_counts[model_label] += 1

    if len(features) < 100:
        raise ValueError("Training CSV contains fewer than 100 unique records")

    x = np.asarray(features, dtype=np.int8)
    y = np.asarray(labels, dtype=np.int8)
    metadata = {
        "raw_rows": raw_rows,
        "training_rows": len(features),
        "unique_12_feature_vectors": len({tuple(row) for row in features}),
        "class_counts": {
            "legitimate": label_counts[0],
            "phishing": label_counts[1],
        },
    }
    return x, y, metadata


def split_dataset(x: np.ndarray, y: np.ndarray):
    """Create 70/15/15 splits without sharing a feature vector across splits."""

    groups = np.asarray([hash(tuple(map(int, row))) for row in x], dtype=np.int64)
    outer = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=RANDOM_SEED)
    train_index, holdout_index = next(outer.split(x, y, groups))

    holdout_groups = groups[holdout_index]
    inner = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=RANDOM_SEED + 1)
    validation_relative, test_relative = next(
        inner.split(x[holdout_index], y[holdout_index], holdout_groups)
    )
    validation_index = holdout_index[validation_relative]
    test_index = holdout_index[test_relative]

    split_groups = [set(groups[index]) for index in (train_index, validation_index, test_index)]
    if split_groups[0] & split_groups[1] or split_groups[0] & split_groups[2] or split_groups[1] & split_groups[2]:
        raise RuntimeError("Feature-vector group leakage detected")
    return train_index, validation_index, test_index, groups


def _metrics(model, x: np.ndarray, y: np.ndarray) -> dict:
    probabilities = model.predict_proba(x)[:, 1]
    predictions = (probabilities >= 0.5).astype(np.int8)
    return {
        "accuracy": float(accuracy_score(y, predictions)),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "average_precision": float(average_precision_score(y, probabilities)),
        "confusion_matrix": confusion_matrix(y, predictions, labels=[0, 1]).tolist(),
    }


def _candidate_models() -> dict:
    return {
        "logistic_regression": LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            random_state=RANDOM_SEED,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_SEED,
        ),
    }


def _write_split(path: Path, x: np.ndarray, y: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow([*FEATURE_NAMES, "label"])
        for values, label in zip(x, y):
            writer.writerow([*map(int, values), int(label)])


def train(input_path: Path, model_path: Path) -> dict:
    x, y, source_metadata = load_dataset(input_path)
    train_index, validation_index, test_index, groups = split_dataset(x, y)

    validation_results = {}
    candidates = _candidate_models()
    for name, candidate in candidates.items():
        candidate.fit(x[train_index], y[train_index])
        validation_results[name] = _metrics(candidate, x[validation_index], y[validation_index])

    selected_name = max(
        validation_results,
        key=lambda name: (
            validation_results[name]["f1"],
            validation_results[name]["average_precision"],
        ),
    )
    selected_model = _candidate_models()[selected_name]
    fit_index = np.concatenate((train_index, validation_index))
    selected_model.fit(x[fit_index], y[fit_index])
    test_metrics = _metrics(selected_model, x[test_index], y[test_index])

    trained_at = datetime.now(timezone.utc).isoformat()
    artifact = {
        "estimator": selected_model,
        "feature_names": list(FEATURE_NAMES),
        "model_name": selected_name,
        "model_version": "v1",
        "phishing_threshold": 0.5,
        "gray_zone": [0.4, 0.6],
        "label_mapping": {"0": "legitimate", "1": "phishing"},
        "trained_at": trained_at,
        "sklearn_version": sklearn.__version__,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path, compress=3)

    processed_dir = input_path.parents[1] / "processed"
    _write_split(processed_dir / "train_v1.csv", x[train_index], y[train_index])
    _write_split(processed_dir / "validation_v1.csv", x[validation_index], y[validation_index])
    _write_split(processed_dir / "test_v1.csv", x[test_index], y[test_index])

    report = {
        "model_name": selected_name,
        "model_version": "v1",
        "trained_at": trained_at,
        "input_file": str(input_path.name),
        "input_sha256": _file_sha256(input_path),
        "feature_names": list(FEATURE_NAMES),
        "source": source_metadata,
        "split": {
            "strategy": "grouped_by_identical_12_feature_vector",
            "train_rows": len(train_index),
            "validation_rows": len(validation_index),
            "test_rows": len(test_index),
            "train_groups": len(set(groups[train_index])),
            "validation_groups": len(set(groups[validation_index])),
            "test_groups": len(set(groups[test_index])),
        },
        "validation_candidates": validation_results,
        "test": test_metrics,
    }
    metrics_path = model_path.with_suffix(".metrics.json")
    metrics_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    return parser


def main() -> None:
    arguments = _build_parser().parse_args()
    report = train(arguments.input, arguments.model)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
