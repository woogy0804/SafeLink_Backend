# Backend 구조

1. main.py가 서버를 실행 중
2. routes/detect_routes.py가 POST /detect 요청을 받음
3. DetectRequest가 url 값이 있는지 검사함
4. detect_url(url)을 호출함
5. detection_service.py가 extract_features(url)을 호출함
6. feature_service.py가 URL 특징 5개를 뽑음
7. detection_service.py가 임시 점수를 계산함
8. 점수 기준으로 safe/suspicious/phishing 중 하나를 고름
9. response_formatter.py가 최종 JSON을 만듦
10. FastAPI가 사용자에게 JSON 응답을 보냄

# 현재 detection_service.py랑 feature_service.py는 임시로 채워놓은 상태임

# 테스트용 json
{
  "url": "http://test-login-example.com@fake-site.com"
}

# 다음으로 해야 할 일
1. services/detection_service.py
   → 실제 모델 연결, gray zone 처리

2. services/feature_service.py
   → feature_extractor 연결

3. utils/response_formatter.py
   → 모델명, confidence, gray zone 여부 추가

4. routes/detect_routes.py
   → URL 검증, 에러 처리 추가

5. main.py
   → CORS, /benchmark 라우터 추가
