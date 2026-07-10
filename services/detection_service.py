from services.feature_service import extract_features
from utils.response_formatter import format_detection_response


def detect_url(url: str) -> dict:
    features = extract_features(url)
    risk_score = calculate_temporary_score(features)
    risk = classify_risk(risk_score)

    return format_detection_response(
        url=url,
        risk=risk,
        score=risk_score,
        features=features,
    )


def calculate_temporary_score(features: dict) -> float:
    if not features:
        return 1.0

    feature_count = len(features)
    phishing_count = sum(1 for value in features.values() if value == -1)
    suspicious_count = sum(1 for value in features.values() if value == 0)

    score = (phishing_count + suspicious_count * 0.5) / feature_count
    return min(score, 1.0)


def classify_risk(score: float) -> str:
    if score >= 0.7:
        return "phishing"

    if score >= 0.3:
        return "suspicious"

    return "safe"
