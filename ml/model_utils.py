"""Shared, leakage-safe helpers for model training and evaluation."""

import csv
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from features.feature_extractor import FEATURE_NAMES


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"


def load_processed_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = set(FEATURE_NAMES) | {"label"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

        rows: list[list[int]] = []
        labels: list[int] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                values = [int(row[name]) for name in FEATURE_NAMES]
                label = int(row["label"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid integer at row {row_number}") from error
            if any(value not in {-1, 0, 1} for value in values):
                raise ValueError(f"Invalid feature value at row {row_number}")
            if label not in {0, 1}:
                raise ValueError(f"Invalid label at row {row_number}")
            rows.append(values)
            labels.append(label)

    if not rows:
        raise ValueError(f"Dataset is empty: {path}")
    return np.asarray(rows, dtype=np.int8), np.asarray(labels, dtype=np.int8)


def save_artifact(estimator, model_name: str, output_path: Path) -> dict:
    metadata = {
        "feature_names": list(FEATURE_NAMES),
        "model_name": model_name,
        "model_version": "v1",
        "label_mapping": {"0": "legitimate", "1": "phishing"},
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    artifact = {"estimator": estimator, **metadata}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path, compress=3)
    return metadata


def load_artifact(path: Path) -> dict:
    # These repository-owned artifacts are validated immediately below and
    # have an explicit adapter for the one incompatible estimator attribute.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InconsistentVersionWarning)
        artifact = joblib.load(path)
    if not isinstance(artifact, dict):
        raise ValueError(f"Invalid model artifact: {path}")
    if artifact.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError(f"Feature order mismatch: {path}")
    estimator = artifact.get("estimator")
    if not callable(getattr(estimator, "predict_proba", None)):
        raise ValueError(f"Estimator does not support predict_proba: {path}")
    # Models committed by B were serialized by a newer scikit-learn release.
    # scikit-learn 1.6 still reads their fitted coefficients, but expects this
    # constructor attribute to exist when predict_proba() is called.
    if isinstance(estimator, LogisticRegression) and not hasattr(
        estimator, "multi_class"
    ):
        estimator.multi_class = "auto"
    return artifact


def classification_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict:
    predictions = (probabilities >= 0.5).astype(np.int8)
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
    }


def phishing_probabilities(artifact: dict, features: np.ndarray) -> np.ndarray:
    estimator = artifact["estimator"]
    phishing_index = list(estimator.classes_).index(1)
    return estimator.predict_proba(features)[:, phishing_index]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
