from typing import Optional


def format_detection_response(
    url: str,
    risk: str,
    score: float,
    features: dict,
    *,
    model_used: str = "temporary_rule",
    gray_zone: bool = False,
    rule_score: Optional[float] = None,
) -> dict:
    messages = {
        "safe": "안전한 URL로 판단됩니다.",
        "suspicious": "의심스러운 URL입니다.",
        "phishing": "피싱 위험이 높은 URL입니다.",
    }

    response = {
        "url": url,
        "risk": risk,
        "score": round(score, 2),
        "model_used": model_used,
        "gray_zone": gray_zone,
        "message": messages.get(risk, "분석 결과를 확인할 수 없습니다."),
        "features": features,
    }
    if rule_score is not None:
        response["rule_score"] = round(rule_score, 2)
    return response


def format_error_response(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
