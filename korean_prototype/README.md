# Patent Review · 한국어 프로토타입

현재 권장 진입점은 **기존 앱 http://127.0.0.1:8501 → 문서 업로드 → 한국 특허**입니다.
기존 미국 UI를 그대로 재사용하며 한국 추출 결과만 backend adapter로 변환합니다.
실행·입력 방법은 [루트 README](../README.md#같은-앱에서-미국--한국-모드-선택)를 참고하세요.
아래 문서는 별도로 보존한 독립 시제품의 실행·검증 안내입니다. 공통 앱을 사용할 때
이 별도 웹/API 서버를 함께 켤 필요는 없습니다.

공통 앱의 한국 모드에서는 `Claim → 청구항`, `Office Action → 의견제출통지서`,
`Patent / Claims → 명세서·청구범위`, `지적 사유 → 거절이유`로 표시합니다.
문헌 유형은 특허문헌/비특허문헌으로 구분합니다. 미국 모드 문구, 원문·법조항,
API 데이터와 화면 배치는 유지합니다. [용어 변경·검증 기록](../KOREAN_TERMINOLOGY_VALIDATION.md).

**2026-09-17 추가 실문서 검증:** 공식 공개 샘플의 OA PDF/XML 5건과 대응 공개특허를
새로 내려받아 현재 앱에 입력했습니다. 결과는 통과 1건, 부분 실패 1건, 미지원 3건입니다.
원본·검사 결과·브라우저 캡처는 [배포용 자료 설명](../data/downloads/Patent_Review_KR_Data_20260917/README.md)에
있으며 ZIP은 `C:\Users\dltmddus\Desktop\Patent_Review_KR_Data_20260917.zip`에 저장했습니다.
추가 2015년 OA XML 178건도 받았으나 현 parser에서는 모두 미지원입니다.
이번 자료 검사에서는 UI나 분석 로직을 수정하지 않았습니다.

기존 미국 버전과 **독립된 추가 버전**이다. 기존 `backend/`, `frontend/`, API,
실행 환경과 데이터는 변경하지 않으며 이 폴더 밖의 프로그램을 import하지 않는다.
이 폴더만 복사해 별도로 설치·실행할 수 있다.

현재 범위는 **한국 공개특허 PDF/TXT + KIPRIS 의견제출통지서 XML + 인용발명 PDF**다.
실제 출원 `10-2019-0000844`의 문서 5개를 포함하여 API 키 없이 시작할 수 있다.

## 재부팅 후 웹 화면 실행

PowerShell에서:

```powershell
cd C:\Users\dltmddus\Desktop\pp\korean_prototype
uv sync
uv run python -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1
```

접속: **http://127.0.0.1:8502** → 왼쪽 **한국 사례 분석** 버튼.
웹 화면은 자체 분석 모듈을 사용하므로 API 서버를 별도로 켤 필요가 없다.
서버 터미널은 실행 중 열어 두며 종료는 `Ctrl+C`다.
`.python-version`으로 Python 3.11을 선택하고 자체 `.venv`와 `uv.lock`을 사용한다.
Windows 실행 파일 래퍼 호환성을 위해 `python -m` 명령으로 안내한다.

| 버전 | 웹 화면 | API 문서 |
|---|---|---|
| 기존 미국 버전 | http://127.0.0.1:8501 | http://127.0.0.1:8000/docs |
| 추가 한국어 버전 | http://127.0.0.1:8502 | http://127.0.0.1:8001/docs |

한국 API도 사용하려면 **별도 터미널**에서:

```powershell
cd C:\Users\dltmddus\Desktop\pp\korean_prototype
uv run python -m uvicorn kr_review.api:app --host 127.0.0.1 --port 8001
```

## 현재 사용할 수 있는 기능

- **한국 사례 분석**: 해시를 확인한 실제 문서로 바로 분석.
- **직접 문서 업로드**: 특허·청구항 PDF/TXT, 의견제출통지서 XML, 선택 인용발명 PDF.
- **청구항 검토**: 한국 청구항 번호·본문·독립/종속관계, 직접 지적 및 종속 영향,
  거절표에 명시된 한국 법조항, 거절에 연결된 인용발명.
- **원문 확인**: 특허·인용발명의 PDF 페이지 미리보기와 원본 다운로드,
  XML의 원문·요소 경로. 근거 이동이 선택한 청구항이나 요약을 바꾸지 않음.
- **Azure 검토**: 선택 청구항과 관련 원문 발췌로 구성 비교 및 대응 검토안을 요청.
  클릭하기 전에는 외부 LLM을 호출하지 않음. 결과에 사용한 근거를 별도로 표시.

분석 흐름:

```text
한국 특허 PDF/TXT + 의견제출통지서 XML + 인용발명 PDF
→ 출원번호 확인 및 문서별 원문·위치 보존
→ 한국 청구항 / 거절이유 표 / 한국 법조항 / 인용발명 추출
→ 직접 지적·종속 영향·인용문헌 원문 연결
→ 청구항 검토 및 원문 확인
→ 사용자가 요청하면 관련 문단 검색 → Azure 검토 초안 + 근거
```

명세서와 OA의 출원번호가 다르거나, 지적 청구항이 명세서에 없거나,
모호한 거절 본문을 여러 거절에 구분 없이 붙여야 하는 경우에는 오류로 알린다.
원문을 LLM으로 고쳐 쓰거나 문헌·근거 위치를 임의로 생성하지 않는다.

## 포함한 실제 자료

[데이터 출처·버전 검토](data/kr_1020190000844/README.md) 및
[다운로드 주소·해시](data/kr_1020190000844/manifest.json).

| 자료 | 파일 |
|---|---|
| 공개 명세서·청구항, 17쪽 | `KR20190025857A.pdf` |
| 2019-04-09 의견제출통지서 | `office_action_20190409.xml` |
| 인용발명 1, 13쪽 | `KR20150096573A.pdf` |
| 인용발명 2, 19쪽 | `KR20150090348A.pdf` |
| 인용발명 3, 25쪽 | `KR20150093093A.pdf` |

이 사례의 기대 결과: **청구항 1개 / 직접 지적 1개 / 종속 영향 0개 /
특허법 제29조제2항 거절 1개 / 인용발명 3개**.
청구항 근거는 PDF 3쪽이다. 등록 후 바뀐 청구항은 포함하지 않았다.
공개공보·인용발명 PDF 확보에 구매비가 들지 않았으며 OA는 제공받은 샘플이다.

공개 PDF를 다시 내려받거나 기존 파일의 해시를 확인하려면:

```powershell
uv run python scripts/download_publications.py
```

이 명령은 수정된 파일을 덮어쓰지 않는다. 제공받은 OA XML은 공개 PDF 다운로드와
별개이며, 원본 샘플이 필요하다. 대량 수급·상업적 이용 조건은 별도 확인해야 한다.

## Azure 연결

**`korean_prototype/.env`**에 아래 값을 넣는다. 기존 미국 버전의 `.env`는 읽지 않는다.
환경변수를 사용하는 경우에도 `KR_` 접두사를 사용해 두 버전을 구분한다.

```dotenv
KR_AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com
KR_AZURE_OPENAI_API_KEY=YOUR-KEY
KR_AZURE_OPENAI_DEPLOYMENT=YOUR-DEPLOYMENT-NAME
```

청구항을 선택하고 **Azure 검토 → Azure로 검토**를 누른다.
배포는 Responses API와 구조화된 출력을 지원해야 한다.
선택 청구항·연결된 OA와 명세서·인용발명의 관련 발췌를 최대 36,000자로 제한해 보낸다.
현재 실제 사례의 로컬 문맥 구성은 17개 발췌, 8,008자다.
이 제한은 토큰 수 또는 비용 상한과 동일하지 않다.

결과의 근거 ID가 제공한 원문에 존재하는지 검사한다. 이는 내용의 법적·기술적 타당성을
자동 인증하는 검사가 아니다. 검토안은 원문과 함께 사용자가 확인해야 한다.
연결 실패·응답 형식 오류·없는 근거 ID는 성공한 결과로 표시하지 않는다.
설정이 없으면 명확한 오류를 보여주며 로컬 분석은 계속 사용할 수 있다.

실제 Azure 서비스 호출은 아직 검증하지 않았다. SDK 요청 형식·오류 처리·근거 검사는
네트워크 요청을 대체한 테스트로 확인했다.
구현 참고: [OpenAI 공식 구조화된 출력 문서](https://developers.openai.com/api/docs/guides/structured-outputs).

## API

| 메서드·경로 | 기능 |
|---|---|
| `GET /health` | 한국 버전 상태 확인 |
| `POST /demo/analyze` | 포함한 실제 한국 문서 분석 |
| `POST /analyze` | multipart `patent`, `office_action`, 선택 `references` 파일 목록 |
| `POST /review` | JSON `analysis`, `claim_number`로 명시적 Azure 검토 요청 |

입력 파일당 20 MB, 인용발명 최대 10개. XML은 UTF-8, 최대 5 MB이며 DTD·외부 엔터티는 거부한다.
로컬 연구용 API이며 인증·다중 사용자 저장·배포 기능은 포함하지 않는다.

## 검증

한국어 버전 폴더에서:

```powershell
uv run python -m pytest -q
uv run python -m pytest --cov=kr_review --cov-report=term-missing
uv run python -m ruff check .
uv run python -m ruff format --check .
```

웹 서버 실행 후 Microsoft Edge 브라우저 검증:

```powershell
uv run python scripts/browser_smoke.py
```

실제 PDF/XML 분석, API multipart 요청, 원문 위치 일치, 종속관계, 입력 오류,
XML 엔터티 차단, Azure 근거 검증, UI 선택 상태를 검사한다.
실행 결과와 검증하지 않은 항목은 [VALIDATION.md](VALIDATION.md)에 기록한다.

## 현재 지원 범위의 한계

- 한국어 OA PDF 입력, 한국어 스캔 OCR은 아직 지원하지 않는다. 기존 미국 OCR과 별도다.
- OA는 확인한 KIPRIS `PatentOpinionSubmission` 계열 XML의 거절표와 본문 구조를 대상으로 한다.
  모든 시기의 XML 변형·모든 종류의 심사 문서를 지원한다고 주장하지 않는다.
- 여러 법조항·거절 범위가 한 본문에 혼재해 대응이 모호하면 잘못 연결하는 대신 오류를 낸다.
- 현재 한국 청구항 parser는 `청구범위` 및 `청구항 N` 제목이 필요하다.
  여러 페이지의 반복 머리말, 복잡한 종속 표현 등은 추가 사례 검증이 필요하다.
- XML에 PDF 페이지 정보가 없으므로 OA PDF 하이라이트를 만들지 않는다.
- 동일 출원번호만으로 심사 당시 청구항 버전까지 자동 판정하지 않는다.
- 허용·철회·보정 전후 비교, 기존 미국 화면의 전체 관계 지도·근거 비교 기능 복제는
  이 첫 한국어 프로토타입에 포함하지 않았다.
- 검증한 실제 한국 사례는 1쌍이다. Azure 실제 출력 품질과 대응안의 적절성은 미검증이다.
