# B 모델 연동 계약

## 호출 인터페이스

A 담당 코드는 Feature 추출 결과를 아래 함수에 전달하면 된다.

```python
from ml.inference import predict_feature_dict

prediction = predict_feature_dict(features)
result = prediction.as_dict()
```

`features`는 `features.feature_extractor.FEATURE_NAMES`의 12개 키를 정확히
포함해야 하며 각 값은 `-1`, `0`, `1` 중 하나여야 한다. 키 순서는 함수가 모델
학습 순서로 다시 정렬하므로 호출자가 보장할 필요가 없다.

## 반환값

```json
{
  "risk": "safe",
  "phishing_probability": 0.08,
  "first_stage_probability": 0.08,
  "model_used": "logistic_regression_v1",
  "gray_zone": false
}
```

- `phishing_probability`: 최종 판정에 사용한 확률
- `first_stage_probability`: Logistic Regression의 원래 확률
- `gray_zone`: Random Forest 2차 검사가 실행됐는지 여부
- `risk`: `safe` 또는 `phishing`

LR 확률이 `0.3` 초과, `0.7` 미만일 때만 RF를 실행한다. 경계값 `0.3`, `0.7`은
LR 결과를 그대로 사용한다.

## API 응답 연결

`POST /detect`의 `features`는 기존 추출 결과를 그대로 반환하고, 모델 관련 필드는
다음과 같이 매핑한다.

| 추론 결과 | `/detect` 응답 |
| --- | --- |
| `risk` | `risk` |
| `phishing_probability` | `score` |
| `model_used` | `model_used` |
| `gray_zone` | `gray_zone` |

프론트엔드는 모델 파일이나 Feature 순서를 알 필요 없이 `/detect`에 URL만 보낸다.

```json
{"url": "https://example.com"}
```

모델 경로를 변경해야 하는 배포 환경에서는 아래 환경변수를 사용한다.

- `SAFELINK_LOGISTIC_MODEL_FILE`
- `SAFELINK_RANDOM_FOREST_MODEL_FILE`
