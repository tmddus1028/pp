# Patent Review · 한국어 프로토타입

현재 권장 진입점은 **기존 앱 http://127.0.0.1:8501 → 문서 업로드 → 한국 특허**입니다.
기존 미국 UI를 그대로 재사용하며 한국 추출 결과만 backend adapter로 변환합니다.
실행·입력 방법은 [루트 README](../README.md#같은-앱에서-미국--한국-모드-선택)를 참고하세요.
아래 문서는 별도로 보존한 독립 시제품의 실행·검증 안내입니다. 공통 앱을 사용할 때
이 별도 웹/API 서버를 함께 켤 필요는 없습니다.

**2026-09-18 지원 확대:** 한국 특허·의견제출통지서의 텍스트 PDF, 스캔/혼합 PDF OCR,
구형 XML, 법조항·상태·인용발명 원문 연결을 추가했습니다. 실제 5개 사건의 XML/PDF
10개 입력 조합을 정답과 비교했습니다. [전체 검증과 남은 한계](../KR_SUPPORT_VALIDATION.md).
공통 앱에서 **인용발명 원문 (선택)**으로 PDF를 함께 업로드하면 개선안·수정본 검토에도
실제 원문 발췌가 전달됩니다. 실제 LLM 품질은 아직 검증하지 않았습니다.

공통 앱에는 **개선 방안 보기 → AI 개선안 생성 → 수정 Claim 입력 → 수정본 검증** 흐름이
추가되어 있습니다. 무료 로컬 Ollama 또는 기존 Azure/OpenAI 설정을 사용할 수 있습니다.
공통 앱의 로컬 모델 설정은 루트 `.env`를 사용합니다. [설치·실행 안내](../README.md#api-비용-없는-로컬-llm-설정),
[수정본 검증 결과와 한계](../REVISION_VALIDATION.md)를 참고하세요. 아래 독립 시제품의 API와는 별도입니다.

공통 앱의 한국 모드에서는 `Claim → 청구항`, `Office Action → 의견제출통지서`,
`Patent / Claims → 명세서·청구범위`, `지적 사유 → 거절이유`로 표시합니다.
문헌 유형은 특허문헌/비특허문헌으로 구분합니다. 미국 모드 문구, 원문·법조항,
API 데이터와 화면 배치는 유지합니다. [용어 변경·검증 기록](../KOREAN_TERMINOLOGY_VALIDATION.md).

**2026-09-17 추가 실문서 검증:** 공식 공개 샘플의 OA PDF/XML 5건과 대응 공개특허를
새로 내려받아 현재 앱에 입력했습니다. 결과는 통과 1건, 부분 실패 1건, 미지원 3건입니다.
원본·검사 결과·브라우저 캡처는 [배포용 자료 설명](../data/downloads/Patent_Review_KR_Data_20260917/README.md)에
있으며 ZIP은 `C:\Users\dltmddus\Desktop\Patent_Review_KR_Data_20260917.zip`에 저장했습니다.
추가 2015년 OA XML 178건도 받았으나 현 parser에서는 모두 미지원입니다.
이는 9월 17일 당시 결과입니다. 이후 9월 18일 parser 개선 결과는 위 검증 보고서를 따릅니다.

이 폴더의 시제품은 폴더 밖의 프로그램을 import하지 않아 별도로 설치·실행할 수 있습니다.
현재 공통 앱은 이 폴더의 한국 분석 모듈을 backend adapter에서 재사용합니다.
미국 parser와 기존 화면 배치·CSS는 유지합니다.

현재 분석 모듈 범위는 **한국 공개특허 PDF/TXT + 의견제출통지서 XML/PDF/TXT + 인용발명 PDF**다.
실제 출원 `10-2019-0000844`의 문서 5개를 포함하여 API 키 없이 시작할 수 있다.
확장된 입력·원문 이동의 권장 화면은 공통 앱 8501입니다. 아래 독립 시제품 화면의
XML 중심 입력 구성은 별도로 개편하지 않았습니다.

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

- 한국어 OA PDF와 별도 Tesseract OCR pipeline을 지원합니다. 설치 명령은
  `uv run python scripts/install_korean_ocr.py`이며 Tesseract 실행 파일도 필요합니다.
  OCR 검증 자료는 공개 PDF를 300 dpi 이미지로 변환한 파생물입니다.
  실제 저해상도·기울어진 스캔에 대한 정확도는 검증하지 않았습니다.
- OA XML은 확인한 2019년 표 구조와 2015년 P 요소 구조를 처리합니다.
  추가 178건 중 165건은 추출되지만 수동 정답 검증이 없고, 13건은 명시적 오류입니다.
  모든 시기의 XML 변형·모든 종류의 심사 문서를 지원한다고 주장하지 않습니다.
- 여러 법조항·거절 범위가 한 본문에 혼재해 대응이 모호하면 잘못 연결하는 대신 오류를 낸다.
- 청구항 제목 변형, 페이지 머리말, 복수·선택 종속 표현과 제한된 heading fallback을 지원합니다.
  OCR 제목 후보는 경고하며 원문은 수정하지 않습니다. 더 다양한 문서 검증이 필요합니다.
- XML에 PDF 페이지 정보가 없으므로 OA PDF 하이라이트를 만들지 않는다.
- 공통 API의 제공 보정 이력·날짜·해시로 버전 후보를 연결하지만,
  실제 심사에 적용된 버전임을 자동 확정하지 않습니다. 보정 이력 UI는 추가하지 않았습니다.
- 허용·철회·삭제·보정 등 명시 상태를 원문과 함께 보존합니다. 이 상태 전부를 포함하는
  실제 사건별 검증은 아직 없으며 일부는 단위 테스트로만 검사했습니다.
- 공통 앱의 기존 관계 지도·근거 비교 화면을 재사용합니다. 독립 시제품에 복제하지 않습니다.
- 실제 한국 5쌍은 개발·회귀용입니다. 미지 사례 일반 정확도, 실제 LLM 출력 품질,
  대응안 적절성은 검증하지 않았습니다.
