def format_detection_response(url: str, risk: str, score: float, features: dict) -> dict:
    messages = {
        "safe": "안전한 URL로 판단됩니다.",
        "suspicious": "의심스러운 URL입니다.",
        "phishing": "피싱 위험이 높은 URL입니다.",
    }

    return {
        "url": url,
        "risk": risk,
        "score": round(score, 2),
        "message": messages.get(risk, "분석 결과를 확인할 수 없습니다."),
        "features": features,
    }
