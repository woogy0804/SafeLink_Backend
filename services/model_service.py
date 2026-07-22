"""Fault-tolerant inference for the local phishing model artifact."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import joblib

from features.feature_extractor import FEATURE_NAMES, VALID_FEATURE_VALUES
from features.file_snapshot import FileSnapshot, get_file_snapshot
from ml.inference import clear_model_cache as clear_cascade_model_cache
from ml.inference import predict_feature_dict


DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "models" / "phishing_model_v1.joblib"
)
MODEL_FILE_ENVIRONMENT = "SAFELINK_MODEL_FILE"
MODEL_MODE_ENVIRONMENT = "SAFELINK_MODEL_MODE"


@dataclass(frozen=True)
class ModelPrediction:
    phishing_probability: float
    risk: str
    model_used: str
    gray_zone: bool


def _model_path() -> Path:
    configured_path = os.getenv(MODEL_FILE_ENVIRONMENT)
    return Path(configured_path) if configured_path else DEFAULT_MODEL_PATH


@lru_cache(maxsize=2)
def _load_model_snapshot(snapshot: FileSnapshot) -> Optional[dict]:
    try:
        artifact = joblib.load(snapshot.path)
    except Exception:
        return None
    if not isinstance(artifact, dict):
        return None
    if artifact.get("feature_names") != list(FEATURE_NAMES):
        return None
    estimator = artifact.get("estimator")
    if estimator is None or not callable(getattr(estimator, "predict_proba", None)):
        return None
    return artifact


def clear_model_cache() -> None:
    _load_model_snapshot.cache_clear()
    clear_cascade_model_cache()


def _predict_cascade(features: dict[str, int]) -> Optional[ModelPrediction]:
    try:
        prediction = predict_feature_dict(features)
    except Exception:
        # Model loading and inference must not prevent rule-based detection.
        return None
    return ModelPrediction(
        phishing_probability=prediction.phishing_probability,
        risk=prediction.risk,
        model_used=prediction.model_used,
        gray_zone=prediction.gray_zone,
    )


def predict_phishing(features: dict[str, int]) -> Optional[ModelPrediction]:
    """Prefer the two-stage model, then fall back to the legacy local model."""

    model_mode = os.getenv(MODEL_MODE_ENVIRONMENT, "auto").strip().lower()
    if model_mode == "rule":
        return None
    if set(features) != set(FEATURE_NAMES):
        return None
    values = [features[name] for name in FEATURE_NAMES]
    if any(value not in VALID_FEATURE_VALUES for value in values):
        return None

    if model_mode != "legacy":
        cascade_prediction = _predict_cascade(features)
        if cascade_prediction is not None:
            return cascade_prediction
        if model_mode == "cascade":
            return None

    snapshot = get_file_snapshot(_model_path())
    if snapshot is None:
        return None
    artifact = _load_model_snapshot(snapshot)
    if artifact is None:
        return None

    try:
        estimator = artifact["estimator"]
        phishing_index = list(estimator.classes_).index(1)
        probability = float(estimator.predict_proba([values])[0][phishing_index])
        gray_lower, gray_upper = artifact.get("gray_zone", [0.4, 0.6])
        gray_lower = float(gray_lower)
        gray_upper = float(gray_upper)
        gray_zone = gray_lower < probability < gray_upper
        if probability >= gray_upper:
            risk = "phishing"
        elif probability <= gray_lower:
            risk = "safe"
        else:
            risk = "suspicious"
        return ModelPrediction(
            phishing_probability=probability,
            risk=risk,
            model_used=(
                f"{artifact.get('model_name', 'unknown')}_"
                f"{artifact.get('model_version', 'unknown')}"
            ),
            gray_zone=gray_zone,
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None
