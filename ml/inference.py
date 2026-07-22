"""Stable B-to-A inference interface for the two-stage phishing models."""

import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from features.feature_extractor import FEATURE_NAMES
from ml.model_utils import MODELS_DIR, load_artifact


LOGISTIC_MODEL_ENV = "SAFELINK_LOGISTIC_MODEL_FILE"
RANDOM_FOREST_MODEL_ENV = "SAFELINK_RANDOM_FOREST_MODEL_FILE"
DEFAULT_GRAY_ZONE = (0.30, 0.70)


@dataclass(frozen=True)
class CascadePrediction:
    risk: str
    phishing_probability: float
    first_stage_probability: float
    model_used: str
    gray_zone: bool

    def as_dict(self) -> dict:
        return asdict(self)


def _configured_path(environment_name: str, default_name: str) -> Path:
    configured = os.getenv(environment_name)
    return Path(configured) if configured else MODELS_DIR / default_name


@lru_cache(maxsize=4)
def _load_models(logistic_path: Path, forest_path: Path) -> tuple[dict, dict]:
    return load_artifact(logistic_path), load_artifact(forest_path)


def clear_model_cache() -> None:
    _load_models.cache_clear()


def _probability(artifact: dict, values: list[int]) -> float:
    estimator = artifact["estimator"]
    phishing_index = list(estimator.classes_).index(1)
    return float(estimator.predict_proba([values])[0][phishing_index])


def predict_feature_dict(
    features: dict[str, int],
    *,
    gray_zone: tuple[float, float] = DEFAULT_GRAY_ZONE,
) -> CascadePrediction:
    """Predict from the exact production 12-feature dictionary.

    Internal label/probability convention is 0=legitimate and 1=phishing.
    Random Forest runs only when Logistic Regression falls inside the open
    Gray Zone interval.
    """

    if set(features) != set(FEATURE_NAMES):
        missing = sorted(set(FEATURE_NAMES).difference(features))
        extra = sorted(set(features).difference(FEATURE_NAMES))
        raise ValueError(f"Feature keys mismatch; missing={missing}, extra={extra}")

    values = [features[name] for name in FEATURE_NAMES]
    if any(type(value) is not int or value not in {-1, 0, 1} for value in values):
        raise ValueError("Every feature value must be one of -1, 0, 1")

    lower, upper = gray_zone
    if not 0 <= lower < upper <= 1:
        raise ValueError("Gray Zone must satisfy 0 <= lower < upper <= 1")

    logistic_path = _configured_path(LOGISTIC_MODEL_ENV, "logistic_model.pkl")
    forest_path = _configured_path(RANDOM_FOREST_MODEL_ENV, "random_forest_model.pkl")
    logistic, forest = _load_models(logistic_path, forest_path)
    first_probability = _probability(logistic, values)
    uses_second_stage = lower < first_probability < upper

    if uses_second_stage:
        final_probability = _probability(forest, values)
        model_used = "logistic_regression_v1+random_forest_v1"
    else:
        final_probability = first_probability
        model_used = "logistic_regression_v1"

    return CascadePrediction(
        risk="phishing" if final_probability >= 0.5 else "safe",
        phishing_probability=final_probability,
        first_stage_probability=first_probability,
        model_used=model_used,
        gray_zone=uses_second_stage,
    )
