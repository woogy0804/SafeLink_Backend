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
    score = 0.0

    if features["url_length"] == 1:
        score += 0.25

    if features["has_at_symbol"] == 1:
        score += 0.30

    if features["has_dash"] == 1:
        score += 0.15

    if features["uses_https"] == 0:
        score += 0.20

    if features["has_ip_address"] == 1:
        score += 0.30

    return min(score, 1.0)


def classify_risk(score: float) -> str:
    if score >= 0.7:
        return "phishing"

    if score >= 0.3:
        return "suspicious"

    return "safe"
