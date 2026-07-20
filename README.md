# SafeLink Backend

## 📢 최근 변경사항

### 2026-07-20 (B 담당 Feature 작업)

- RDAP 생성일/만료일 1회 조회 및 프로세스 로컬 TTL 캐시 적용
  - 정상 응답 24시간
  - 일시적 실패 5분
- Public Suffix List 및 IDNA 2008/UTS #46 기반 도메인 정규화 적용
- 정수형·16진수·8진수·축약형·전각문자 IP 우회 탐지 추가
- SSL 검사 시 검증한 공인 IP로 연결하고 원래 호스트명을 SNI에 유지
- 공식 Tranco 최신 목록을 SQLite로 변환하는 갱신 도구 추가
- 대용량 외부 지표를 메모리에 전부 적재하지 않는 SQLite 단건 조회 추가
- 백링크의 `0개 관측`과 `미수집`을 구분
- Feature 및 관련 API 회귀 테스트 165개 통과
- SSL·HTML·RDAP 네트워크 작업 병렬 실행 및 async용 추출 래퍼 추가

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
- Random Forest 중요도 기준 Top 12 Feature로 모델 입력 목록 변경
- `web_traffic`, `having_Sub_Domain`, `Links_in_tags`,
  `Links_pointing_to_page`, `Domain_registeration_length` 구현
- Anchor, SFH, Links in tags, Request URL이 단일 HTML 요청과 파싱 결과 공유
- Feature HTML 요청에 redirect별 SSRF 검사, 최대 5회 redirect,
  최대 2MB 응답 및 HTML Content-Type 제한 적용
- `/detect` 처리 과정에 URL 검증 단계 추가
- API 응답 형식을 다음과 같이 확장

```text
기존: url, risk, score, message, features
변경: url, risk, score, model_used, gray_zone, message, features
```

#### 🗑️ 삭제
기존 feature_service.py의 임시 5개 Feature 추출 로직
README의 완료된 작업 목록Feature Extractor 연결
URL 검증
API 에러 처리

#### ⚠️ 참고
현재 score는 머신러닝 모델의 confidence가 아닌 임시 점수
model_used는 현재 temporary_rule
gray_zone은 모델 연결 전까지 false

## 🚧 현재 진행 단계

- 🚧 Level 1: 12개 Feature Extractor 핵심 로직 완료, 운영 준비 약 93%
- ✅ Level 2: `/detect` API 구현 완료
- ⏸️ Level 3: 머신러닝 모델 학습·연동은 현재 보류

## Top 12 Feature 순서

모델 학습 데이터와 서버 입력은 반드시 다음 순서를 함께 사용해야 합니다.

1. `SSLfinal_State`
2. `URL_of_Anchor`
3. `web_traffic`
4. `Prefix_Suffix`
5. `having_Sub_Domain`
6. `Links_in_tags`
7. `Links_pointing_to_page`
8. `Request_URL`
9. `SFH`
10. `age_of_domain`
11. `Domain_registeration_length`
12. `having_IP_Address`

등록 도메인과 서브도메인 경계는 `tldextract`의 내장 Public Suffix List로
계산합니다. 실행 중 PSL을 다운로드하지 않으며, `github.io` 같은 private
suffix도 포함해 서로 다른 서비스 사용자의 도메인이 같은 사이트로 합쳐지는
문제를 방지합니다. 국제화 도메인(IDN)은 Punycode로 정규화합니다.

`having_IP_Address`는 일반 IPv4/IPv6뿐 아니라 정수형 IPv4, 16진수·8진수
표현 및 `127.1` 같은 축약 표현도 IP 직접 사용으로 판정합니다.

`SSLfinal_State`는 시스템 신뢰 저장소를 이용해 인증서 체인과 호스트명을
검증합니다. 유효하고 신뢰되는 HTTPS는 `1`, 신뢰 검증 실패나 통신 장애는
`0`, HTTP·만료·아직 유효하지 않은 인증서는 `-1`입니다. 잔여기간 1년 기준은
현행 공개 TLS 인증서 최대 유효기간보다 길어 정상 사이트를 오탐하므로
적용하지 않습니다.

`web_traffic`은 Tranco 형식의 `rank,domain` CSV 또는 SQLite 스냅샷을
사용합니다. 기본적으로 `features/tranco_ranks.sqlite3`가 있으면 이를 먼저
사용하고, 없으면 `features/tranco_top_domains.csv`를 찾습니다.

최신 공식 Tranco 목록을 내려받아 SQLite로 변환하는 명령:

```text
python -m scripts.update_tranco
```

생성 파일은 약 25MB이며 Git에는 포함하지 않습니다. 배포 환경마다 위 명령을
한 번 실행하거나, 생성된 DB를 별도 데이터 artifact로 배포해야 합니다.
`SAFELINK_TRANCO_FILE`로 CSV 또는 SQLite 경로를 직접 지정할 수도 있습니다.

`Links_pointing_to_page`는 출처가 명확한 `domain,count` 백링크 CSV가
필요합니다. 아래 명령으로 SQLite 스냅샷을 만들 수 있습니다.

```text
python -m scripts.build_metric_snapshot backlinks INPUT.csv --source PROVIDER_NAME --observed-at 2026-07-20T00:00:00Z
```

기본 파일은 `features/backlink_counts.sqlite3` 또는
`features/backlink_counts.csv`이며 `SAFELINK_BACKLINK_FILE`로 변경할 수
있습니다. 데이터에 도메인이 없으면 `0(미수집)`, 명시적으로 count가 0인
경우만 `-1(백링크 0개)`로 판정합니다. 현재 팀의 백링크 공급자는 미정입니다.

외부 데이터 파일이 없거나 손상되면 두 feature는 피싱으로 단정하지 않고
`0`(Suspicious/조회 불가)을 반환합니다.

`age_of_domain`과 `Domain_registeration_length`는 RDAP 조회 한 번에서
생성일과 만료일을 함께 사용합니다. 기본 RDAP 주소는 `https://rdap.org`이며
`SAFELINK_RDAP_BASE_URL` 환경 변수로 변경할 수 있습니다. RDAP 조회 또는
필요한 날짜 해석이 불가능하면 `0`을 반환합니다.

RDAP 결과는 현재 실행 중인 Python 프로세스 안에서 등록 도메인별로
캐싱합니다. 정상 응답(날짜가 없는 응답 포함)은 24시간, 네트워크·파싱 실패는
5분 동안 보관합니다. `SAFELINK_REDIS_URL`을 설정하면 같은 TTL로 Redis에도
저장하여 여러 서버 워커가 결과를 공유합니다. Redis가 없거나 일시 장애가
발생해도 요청은 중단하지 않고 프로세스 로컬 캐시로 자동 폴백합니다.

```text
SAFELINK_REDIS_URL=redis://localhost:6379/0
```

실제 네트워크 작업은 SSL, HTML, RDAP 세 그룹을 제한된 ThreadPool에서 동시에
실행합니다. 현재 `/detect`는 sync route라 FastAPI worker thread에서 안전하게
실행되며, 향후 async route에서는 `extract_feature_dict_async(url)`을 사용할 수
있습니다.

## detect API 설명

1. main.py가 서버를 실행 중
2. routes/detect_routes.py가 POST /detect 요청을 받음
3. DetectRequest가 url 값이 있는지 검사함
4. detect_url(url)을 호출함
5. detection_service.py가 extract_features(url)을 호출함
6. feature_service.py가 features/feature_extractor.py의 Top 12 feature를 호출함
7. detection_service.py가 1 / 0 / -1 feature 값을 기준으로 임시 점수를 계산함
8. 점수 기준으로 safe/suspicious/phishing 중 하나를 고름
9. response_formatter.py가 최종 JSON을 만듦
10. FastAPI가 사용자에게 JSON 응답을 보냄

# feature_service.py는 B 담당 feature_extractor와 연결 완료
# detection_service.py의 점수 계산은 모델 연결 전까지 사용하는 임시 로직

## 🚩 다음으로 해야 할 일

### B 담당

- 백링크 데이터 공급자와 count 정의 확정
- HTML/RDAP 요청의 DNS 검증-연결 간 재바인딩 방어(IP 고정 또는 egress 정책)
- Feature 추출 p50/p95 벤치마크
- 모델 학습·Gray Zone 실험은 현재 보류

### A 담당

- Logistic Regression 모델 연결
- Gray Zone 처리
- Random Forest 2차 검사 연결
- 실제 confidence 반환
- `/benchmark` API 구현
- CORS 설정

등등...
