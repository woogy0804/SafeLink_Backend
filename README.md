# SafeLink Backend

## 📢 최근 변경사항

### 2026-07-12

#### 🆕 추가

- `/detect` URL 입력 검증
- `http`, `https` 프로토콜 검사
- localhost 및 사설 IP 차단
- 공통 JSON 오류 응답
- `model_used`, `gray_zone` 응답 필드
- `requirements.txt`
- `/detect` API 및 URL 검증 테스트

#### 🔄 변경

- `feature_service.py`를 B 담당의 12개 Feature 추출기와 연결
- 기존 5개 임시 Feature를 실제 12개 Feature로 변경
- `/detect` 처리 과정에 URL 검증 단계 추가
- API 응답 형식을 다음과 같이 확장

```text
기존: url, risk, score, message, features
변경: url, risk, score, model_used, gray_zone, message, features

#### 🗑️ 삭제
기존 feature_service.py의 임시 5개 Feature 추출 로직
README의 완료된 작업 목록Feature Extractor 연결
URL 검증
API 에러 처리

####⚠️ 참고
현재 score는 머신러닝 모델의 confidence가 아닌 임시 점수
model_used는 현재 temporary_rule
gray_zone은 모델 연결 전까지 false

## 🚧 현재 진행 단계

- ✅ Level 1: 12개 Feature Extractor 구현 완료
- ✅ Level 2: `/detect` API 구현 완료
- 🚧 Level 3: 머신러닝 모델 연동 예정

## detect API 설명

1. main.py가 서버를 실행 중
2. routes/detect_routes.py가 POST /detect 요청을 받음
3. DetectRequest가 url 값이 있는지 검사함
4. detect_url(url)을 호출함
5. detection_service.py가 extract_features(url)을 호출함
6. feature_service.py가 features/feature_extractor.py의 12개 feature를 호출함
7. detection_service.py가 1 / 0 / -1 feature 값을 기준으로 임시 점수를 계산함
8. 점수 기준으로 safe/suspicious/phishing 중 하나를 고름
9. response_formatter.py가 최종 JSON을 만듦
10. FastAPI가 사용자에게 JSON 응답을 보냄

# feature_service.py는 B 담당 feature_extractor와 연결 완료
# detection_service.py의 점수 계산은 모델 연결 전까지 사용하는 임시 로직

## 🚩 다음으로 해야 할 일

### B 담당

- Logistic Regression 학습
- Random Forest 학습
- 모델 파일 생성
- Gray Zone 기준 실험
- 모델 성능 평가

### A 담당

- Logistic Regression 모델 연결
- Gray Zone 처리
- Random Forest 2차 검사 연결
- 실제 confidence 반환
- `/benchmark` API 구현
- CORS 설정

등등...
