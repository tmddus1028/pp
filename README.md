# Patent Review · AI 기반 특허 검토 지원

특허 청구항과 USPTO Office Action 사이의 관계를 원문 근거와 함께 구조화하는 로컬 MVP입니다.
구현 계획은 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)를 참고하세요.

## 실행

Python 3.11 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다. 아래 명령은 프로젝트 루트에서 실행합니다.

```powershell
uv sync --python 3.11
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

- 웹 화면: http://127.0.0.1:8501
- API 문서: http://127.0.0.1:8000/docs
- 화면의 **예제 분석 · 가상 문서** 버튼으로 API 키 없이 바로 확인할 수 있습니다.
- 종료: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1`

Windows 실행 명령은 해당 PowerShell 프로세스에서만 스크립트를 허용하며 시스템 정책을 변경하지 않습니다.
서버는 localhost에만 바인딩됩니다. 실행 로그는 `data/outputs/`에 저장합니다.
다른 OS 또는 두 터미널에서 직접 실행하려면 다음 명령을 각각 실행합니다.

```sh
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
uv run streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

uv 없이도 `python -m venv .venv` 및 `python -m pip install -r requirements.txt`로 설치할 수 있습니다.
재현 가능한 버전은 `uv.lock`을 사용합니다.

### 재부팅 후 다시 시작하기 (Windows)

컴퓨터를 재부팅하면 로컬 서버도 종료되므로, 웹 화면에 접속하기 전에 다시 실행해야 합니다.
VS Code 터미널 또는 PowerShell에서 아래 명령을 실행하세요. 프로젝트를 다른 위치로 옮겼다면 경로를 바꾸세요.

```powershell
cd "C:\Users\dltmddus\Desktop\pp"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

위 명령은 API 서버와 웹 화면을 함께 실행합니다. 서버가 시작될 때까지 잠시 기다린 뒤
브라우저에서 **http://127.0.0.1:8501** 을 여세요.
http://127.0.0.1:8000/docs 는 웹 검토 화면이 아니라 개발용 API 문서입니다.
이미 설치를 완료했다면 재부팅할 때마다 `uv sync`를 실행할 필요는 없습니다.

사용을 마친 뒤 서버를 종료하려면 같은 프로젝트 폴더에서 실행하세요.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1
```

## 구현 범위

Phase 1~4 분석 파이프라인, PDF 검토 중심 Streamlit UI, 평가 기반을 구현했습니다.

| 모듈 | 기능 |
|---|---|
| `backend/ingestion` | PDF/TXT/JSON 입력, 페이지별 텍스트, 정규화·문자 위치, CSV adapter |
| `backend/patent` | Claims/번호/범위 파싱, 복수 종속관계, 중복·누락·순환 검증 |
| `backend/office_action` | 거절 단위 chunking, 표준 문장의 Claim/법조항/인용문헌 추출 |
| `backend/llm` | local/OpenAI/Azure 분리, Pydantic 출력, 원문 근거 검증 |
| `backend/analysis` | 상위 Claim·종속 영향 계산, citation ID, 검토 체크리스트 |
| `backend/graph` | OA → 지적 사유 → Claim, 부모 → 종속 Claim, 인용문헌 그래프 |
| `backend/evaluation` | Precision/Recall/F1, 일치율, 정렬된 법조항 label의 분류 지표 |
| `frontend` | 원본 PDF 렌더링, 좌표 overlay, 양방향 Claim/근거 선택, 필터·검색, 보조 그래프, JSON 다운로드 |

DB, agent framework, 자동 대응문/청구항 수정, 등록 가능성 예측은 포함하지 않습니다.
프론트엔드는 분석을 기존 FastAPI에 요청하고, 표시용 adapter에서 원문 좌표를 계산합니다.
PDF는 로컬 PDFium, overlay와 보조 그래프는 로컬 component로 렌더링하며 외부 CDN을 사용하지 않습니다.

## PDF 검토 화면

분석이 끝나면 **PDF 검토**가 자동으로 열립니다. 220px 사이드바, 중앙 원본 PDF,
오른쪽 검토 패널로 구성되며 좁은 화면에서는 검토 패널을 아래로 배치합니다.

- 문서 업로드: 기존 PDF/TXT/JSON 및 텍스트 입력을 유지합니다. PDF 원본 bytes는 현재 Streamlit 세션에 보관합니다.
- PDF 검토: Patent/OA 전환, 페이지 이동, 확대/축소, 너비/페이지 맞춤, 검색, 원본 다운로드를 제공합니다.
- 검토 카드와 PDF 하이라이트를 클릭하면 서로 연결된 Claim·거절·문헌·근거 위치로 이동합니다.
- PDF 검토에 처음 또는 일반 메뉴로 다시 들어오면 모든 검토 카드가 접혀 있고 선택 Claim이 없습니다.
  Claim 카드를 클릭하면 해당 카드만 열리며, 다시 클릭하면 접힙니다. PDF 이동과 bbox 강조는 유지합니다.
  PDF annotation 클릭 또는 다른 화면의 명시적인 ‘PDF에서 보기’는 해당 항목만 선택하고 펼칩니다.
  펼침 상태와 PDF 선택 상태를 분리하여 카드가 접혀도 현재 강조 위치는 유지할 수 있습니다.
- Claim 상세의 Office Action 원문 근거를 보면 해당 Claim 선택·펼침과 목록을 유지한 채
  PDF만 근거 페이지로 이동합니다. R1/R2 카드를 목록에 추가하지 않고, Claim 내부에 현재 근거와
  OA 페이지를 표시합니다. ‘청구항 원문 보기’로 돌아오거나 다른 지적 근거로 전환할 수 있습니다.
- 빨강은 직접 지적, 노랑은 종속 영향, 초록은 인용 문헌, 청록은 거절 사유와 명시적으로 연결된 명세서/도면입니다.
  전체 보기에서 직접 지적이 우선하며, 거절 사유별 필터에서는 해당 사유의 영향을 표시합니다.
- 청구항 분석: 전체 청구항·거절/지적 사유·직접 지적·추가 검토 수를 간결하게 표시하고,
  Claim 번호순 목록에서 상태·법조항·상위 Claim·직접 종속 Claim 수를 확인합니다.
  전체/직접 지적/추가 검토/§112/§103 필터와 정확한 번호 검색을 지원합니다.
  원문·OA 근거·citation·명세서·체크리스트는 각 Claim의 접힌 상세에 있습니다.
  ‘PDF에서 보기’로 해당 원문 위치를 선택하며, 돌아와도 선택과 필터를 유지합니다.
  OCR·provider·renderer·warning 및 JSON 다운로드는 ‘문서 처리 정보 보기’에 모았습니다.
  전체 관계 구조는 별도 ‘관계 지도’에서 확인합니다.
- 관계 지도: Office Action → 거절 사유 → 주요 Claim/인용문헌을 계층형으로 표시합니다.
  Claim 목록은 펼칠 수 있고, 선택한 Claim의 상위·직접 종속항만 연결합니다.
  유형/거절 범위/직접 지적/종속관계/인용문헌 필터와 hover·선택 경로 강조를 제공합니다.
- PDF 하단의 ‘전체 관계 지도 보기’와 지도의 ‘PDF에서 보기’/‘Office Action 근거 보기’로
  선택 항목과 거절 범위를 유지하며 이동합니다. 원본 파일·OCR·분석을 다시 실행하지 않습니다.
- 근거 비교: 선택 Claim의 청구항 원문·심사관 지적·명세서 근거·인용 선행기술을 2×2 카드로 비교합니다.
  좁은 화면에서는 세로로 쌓이며 큰 PDF Viewer는 표시하지 않습니다. Claim/지적 사유 selector로
  비교 범위를 바꾸고, §112는 Claim·명세서·OA, §103은 Claim·OA·선행기술을 중심으로 봅니다.
  기존 OA의 명시적 문단/도면 연결만 재사용하고, 연결이 없으면 ‘현재 자동 연결된 명세서 근거가 없습니다.’로 표시합니다.
  Patent/NPL 인용문헌은 펼쳐 원문 인용·사용된 지적 사유·동일 사유의 Claim을 확인할 수 있습니다.
  PDF 검토와 관계 지도의 Claim 상세에서 ‘근거 비교’로 이동하면 Claim과 거절 범위를 유지합니다.
  각 근거의 PDF 버튼은 원문 페이지를 선택합니다. 근거 비교에서는 추가 분석/LLM 호출을 하지 않습니다.

PDF 파일 자체는 수정하지 않습니다. 좌표는 페이지 좌상단을 원점으로 하는 0~1 비율이며,
기존 Evidence의 문서·페이지·문자 범위를 PDF 텍스트 레이어 또는 `metadata.ocr_words`와 연결합니다.
확실한 좌표가 없으면 페이지와 원문 근거를 보여주고 임의의 하이라이트를 만들지 않습니다.
TXT/JSON은 PDF로 위장하지 않고 텍스트 원문으로 표시합니다.

스캔 PDF는 기존 OCR 본문 출력과 `ocr_raw_text`를 유지하면서 Tesseract의 표시용 단어 좌표를
`metadata.ocr_words`에 추가합니다. 좌표 추출은 추가 로컬 OCR 호출이어서 스캔 페이지 처리 시간이 늘어납니다.
표시용 좌표만 실패하면 이를 경고하고 페이지 근거로 표시하며, 기존 텍스트 OCR 실패 처리는 그대로입니다.
OCR 좌표가 없는 과거 결과는 다시 분석해야 스캔 하이라이트를 사용할 수 있습니다.
추가 설치·DB·로그인·외부 OCR API는 없습니다.

화면 및 검증 상세는 [PDF_REVIEW_VALIDATION.md](PDF_REVIEW_VALIDATION.md)를 참고하세요.
관계 지도와 실제 Claim 1·14·15 연결 검사는 [RELATIONSHIP_MAP_VALIDATION.md](RELATIONSHIP_MAP_VALIDATION.md)에 기록합니다.

```powershell
# 합성 회귀 PDF 재생성
uv run python scripts/make_review_fixtures.py
# 실행 중인 localhost 서버를 대상으로 실제 Edge에서 UI 확인
uv run --no-project --with playwright --python 3.11 python -X utf8 -u scripts/browser_pdf_review.py
```

## 입력과 결과

두 파일을 PDF/TXT/JSON으로 업로드하거나 두 텍스트를 입력합니다. 파일별 기본 제한은 20 MB,
PDF 150페이지, 문서 텍스트 500,000자입니다. TXT는 UTF-8이며 `\f`로 페이지를 나눌 수 있습니다.
JSON adapter 형식은 다음과 같습니다. 페이지 번호와 문자 위치는 서버가 계산합니다.

```json
{"pages": [{"text": "Claims\n1. A sensor system...\n2. The system of claim 1..."}]}
```

분석 예제는 Claim 9개, 거절 3개를 포함합니다. R1이 Claim 1~3을 직접 지적하면
Claim 4~5는 종속관계에 따른 추가 검토 대상으로 계산됩니다.
직접 지적은 각 rejection마다 보존되며 다른 rejection에서 직접 지적된 Claim이 동시에 종속 영향도 받을 수 있습니다.
UI의 전체 지표는 직접 지적을 우선 표시하여 중복 계산하지 않습니다.

모든 Evidence의 `start`/`end`는 **정규화된 `documents[].text`의 0-based Python 문자 위치**입니다.
`end`는 포함하지 않습니다. `text[start:end] == evidence.text`로 검증할 수 있습니다.
PDF의 페이지는 1부터 시작하는 실제 파일 페이지이며, TXT/JSON은 해당 입력의 논리 페이지입니다.
원본 PDF byte offset 또는 인쇄된 페이지 라벨과는 다릅니다.

`dependency_impacted_claims`는 자동 거절 판정이 아니라 추가 검토 범위입니다.
`unaddressed` 상태도 등록 가능/허용 판정이 아닙니다. 입력에 없는 Claim은 삭제하거나 만들어내지 않고
`missing_claims`와 그래프의 missing 노드로 표시합니다.

```powershell
uv run python -m backend.cli --patent data/raw/demo_patent.txt --office-action data/raw/demo_office_action.txt --provider local --output data/outputs/demo.json
uv run python -m backend.evaluation.evaluator data/outputs/demo.json data/raw/demo_ground_truth.json --output data/outputs/demo_metrics.json
```

API: `GET /health`, `POST /analyze/text` (`patent_text`, `office_action_text`),
`POST /analyze/files` (multipart `patent`, `office_action`). 잘못된 문서는 422, 크기 초과는 413,
provider 연결 실패/거절은 502로 반환합니다. API는 업로드 문서나 결과를 자동 저장하지 않습니다.
CLI는 지정된 경로에 JSON을 저장하며 UI는 다운로드를 제공합니다.

## 스캔 PDF 자동 OCR

PDF 열기는 **PyMuPDF → PDFium → pypdf** 순서로 시도합니다. 한 parser가 `/Pages` 같은 객체를
읽지 못해도 다른 parser에서 페이지를 열 수 있으면 계속 처리합니다. 원본 PDF를 복구 저장하거나 재작성하지 않습니다.
열기 검증 후 기존 pypdf 텍스트 추출·중복 OCR 레이어 처리가 가능한 문서는 그 결과를 유지하고,
pypdf가 실패하거나 페이지 수가 다르면 성공한 native parser의 텍스트를 사용합니다.
native 열기·텍스트 추출도 별도 로컬 프로세스에서 실행합니다. `metadata.pdf_parser`와
`pdf_text_extractors`에서 실제 사용 경로를 확인할 수 있습니다.

OCR은 **완전 로컬 처리**입니다. 외부 OCR API나 LLM으로 이미지/문구를 보내거나 OCR 결과를 보정하지 않습니다.
기존 pypdf 텍스트 추출과 중복 OCR 레이어 처리를 먼저 수행하고, 페이지별 영숫자 등 문자 수가
`OCR_MIN_TEXT_CHARS`(기본 20자) 미만일 때만 OCR합니다. 충분한 텍스트가 있는 페이지는 다시 렌더링하지 않습니다.
빈 페이지는 순서를 유지하며 생략하고, 읽을 내용이 있는 페이지의 OCR 실패는 문서 분석 전체를 중단합니다.

대상 페이지만 기본 **300 DPI**로 렌더링하고 `pytesseract`를 통해 Tesseract의 **영어 `eng`** 엔진으로 읽습니다.
PyMuPDF를 우선 사용합니다. Windows DLL 문제 등으로 PyMuPDF를 불러오지 못하면 로컬 PDFium으로 전환하고
경고 및 `ocr_renderer`를 기록합니다. `OCR_RENDERER=pymupdf`로 지정하면 대체하지 않고 명확한 오류를 반환합니다.
PDF 손상이나 실제 OCR 인식 실패를 대체 렌더러로 숨기지는 않습니다.

Windows 설치:

```powershell
uv sync --python 3.11
winget install --id UB-Mannheim.TesseractOCR --exact --source winget
```

또는 [Tesseract 설치 안내](https://tesseract-ocr.github.io/tessdoc/Installation.html)에서 연결하는
[UB Mannheim Windows 설치 파일](https://github.com/UB-Mannheim/tesseract/wiki)을 사용하고 영어 데이터를 포함하세요.
Python 패키지 `pytesseract`만 설치하는 것으로는 Tesseract 실행 파일이 설치되지 않습니다.
PyMuPDF DLL 오류가 있으면 [Microsoft Visual C++ x64 런타임](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)을
설치/복구하세요. 관련 원인은 [PyMuPDF 설치 문서](https://pymupdf.readthedocs.io/en/latest/installation.html)에 설명되어 있습니다.

필요하면 `.env`에 실행 파일 경로를 지정합니다. 경로는 따옴표 없이 입력하거나 **작은따옴표**로 감싸세요.

```dotenv
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_DPI=300
OCR_MIN_TEXT_CHARS=20
OCR_TIMEOUT_SECONDS=60
OCR_MAX_PIXELS=40000000
OCR_RENDERER=auto
```

`TESSERACT_CMD`가 비어 있으면 PATH, `%LOCALAPPDATA%\Programs\Tesseract-OCR`,
`%LOCALAPPDATA%\Tesseract-OCR`, `%ProgramFiles%\Tesseract-OCR`를 찾습니다.
현재 개발 PC에는 사용자별 경로 `%LOCALAPPDATA%\Programs\Tesseract-OCR`에 설치했습니다.
설정 변경 후 backend를 재시작합니다. 실행 확인:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
```

사용자별 설치인 경우 위 경로를 해당 설치 위치로 바꾸고, 언어 목록에 `eng`가 있는지 확인하세요.
Linux는 `sudo apt install tesseract-ocr tesseract-ocr-eng`, macOS는 `brew install tesseract` 후 `uv sync`로 준비할 수 있습니다.

각 `documents[]`에 기본값이 있는 `metadata` 필드를 추가했습니다. TXT/JSON과 텍스트 PDF도 읽을 수 있고,
기존 필드·입력 형식·Evidence 계산 방식은 유지합니다. 예:

```json
{
  "ocr_used": true,
  "ocr_pages": [2, 4],
  "ocr_engine": "tesseract",
  "ocr_renderer": "pymupdf",
  "ocr_dpi": 300,
  "ocr_language": "eng",
  "ocr_raw_text": {"2": "Claims 1-19 ...\n", "4": "35 U.S.C. § 103 ...\n"}
}
```

`ocr_raw_text`는 정규화 전 Tesseract 출력을 그대로 보관합니다. `documents[].text`와 `pages[].text`는
기존 NFKC/공백 정규화를 적용한 뒤 문자 위치를 계산하므로 `text[start:end] == evidence.text`가 유지됩니다.
OCR 문구, § 기호, 출원/특허번호를 자동 추정·교정하지 않습니다. UI는 문서별 OCR 쪽수와 페이지 번호를 표시하고,
청구항 분석의 “문서 처리 정보 보기”에서 정규화된 텍스트와 OCR 원문을 모두 볼 수 있습니다.

로컬 OCR은 별도 프로세스에서 페이지 순서대로 실행하여 FastAPI 스레드 사이의 네이티브 라이브러리 충돌과
Tesseract 경로 설정 공유를 피합니다. 작업용 PDF와 이미지 임시 파일은 처리 후 정리합니다.
페이지별 OCR 시간 및 렌더링 픽셀 수를 제한하며, 미설치/실행 실패/시간 초과는 API에서 이해 가능한 `422` 오류를 반환합니다.
엔진이 읽지 못한 페이지를 빈 텍스트로 성공 처리하지 않습니다.

사용자 원본 `pp_ex2.pdf`(47쪽)와 `pp_vd2.pdf`(13쪽)의 parser fallback·Claim 1~20·§103 거절 3개·
인용문헌 5개 회귀는 [PDF_OPEN_FALLBACK_VALIDATION.md](PDF_OPEN_FALLBACK_VALIDATION.md)에 기록합니다.
원본 fixture 해시와 출처·문서 버전 범위는 [fixture 설명](tests/fixtures/pdf_fallback/README.md)을 참고하세요.

```powershell
uv run python -m scripts.validate_pdf_fallback
```

실제 스캔 PDF는 기존 화면에서 Claims와 OA를 업로드하고 **분석 시작**을 누르면 됩니다. 별도 OCR 버튼은 없습니다.
CLI에서도 같은 경로로 처리합니다.

```powershell
uv run python -m backend.cli --patent 'C:\Documents\claims.pdf' --office-action 'C:\Documents\office-action-scan.pdf' --provider local --output data/outputs/my-scan-analysis.json
```

동일 버전 Claims 파일을 사용하세요. 이 명령은 OCR과 후속 분석을 모두 로컬에서 실행합니다.
회귀 fixture 및 실제 Tesseract 테스트:

```powershell
uv run python -m backend.cli --patent tests/fixtures/ocr/claims.txt --office-action tests/fixtures/ocr/office_action_scan.pdf --provider local --output data/outputs/ocr-analysis.json
uv run pytest -q -m ocr_integration
```

fixture는 요청에 나온 출원번호 `14/623,904`, Claims 1–19, §112/§103 형식을 본떠 **새로 만든 가상 문서**입니다.
실제 사건의 심사 내용을 재현한다고 주장하지 않습니다. 자세한 구성은 [fixture 설명](tests/fixtures/ocr/README.md),
검증 결과와 수정 파일은 [OCR_VALIDATION.md](OCR_VALIDATION.md)에 있습니다.

## LLM 설정

`.env.example`을 `.env`로 복사한 뒤 설정합니다. 기본 `LLM_PROVIDER=local`은 외부 호출을 하지 않습니다.
local은 정규식 기반 기준선이며 AI 문맥 분석을 수행하지 않습니다.

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-structured-output-model
```

또는:

```dotenv
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=your-deployment
```

설정 변경 후 backend를 재시작합니다. 모델/배포명은 계정에서 접근 가능한 Structured Outputs 지원 모델을 명시합니다.
[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)와
[Azure Structured Outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)의
`responses.parse(text_format=...)`를 사용합니다. Azure endpoint에는 `/openai/v1/`를 붙이며 이미 있으면 중복하지 않습니다.

LLM은 OA chunk에서 구조화된 지적 사유·설명·인용문헌과 원문 발췌를 반환합니다.
코드는 정확히 일치하는 근거를 찾아 문자 위치/페이지를 계산하고 Claim 번호·법조항·인용문헌을 검증합니다.
검증 실패를 로컬 결과로 숨겨 대체하지 않습니다. 체크리스트는 근거에 연결된 결정적 검토 템플릿입니다.
원문 내 지시문은 문서 데이터로 취급하도록 prompt를 구성합니다. 이 검증은 의미적 오류를 전부 탐지하는 보장은 아닙니다.

외부 모드는 OA 텍스트를 설정된 공급자로 전송하고 `store=False`를 사용합니다.
공급자의 데이터 보관 정책 자체를 변경하는 설정은 아닙니다. 이 구현에서는 특허 원문을 LLM으로 보내지 않습니다.
추출 결과의 구조 검증은 SDK mock transport로 시험했으며, 실제 인증 키를 사용한 호출은 검증하지 않았습니다.

## 공개 데이터 및 한계

[공개 자료 설명](data/raw/uspto/README.md)에 원본·발췌·출처·버전 차이를 기록했습니다.
`data/raw/demo_*`는 직접 만든 가상 문서이며 공개 USPTO 데이터로 표시하지 않습니다.
출원 **14/455,526**의 **2016-06-17 전체 OA 16쪽 + 2016-07-05 미수정 청구항 3쪽**으로
PDF → 로컬 분석 → API/CLI 검증을 완료했습니다. 미수정 선언과 제출 이력으로 OA 당시 청구항 버전과 대조했습니다.
당시 제출 파일 자체와 직접 비교한 것은 아니며, 답변서 표지의 날짜 불일치도 기록했습니다.
[실제 쌍의 출처·버전 근거](data/raw/uspto_14455526_20160617/README.md)와 [검증 결과](VALIDATION.md)를 참고하세요.

- 영어 스캔 페이지의 로컬 OCR을 지원합니다. 복잡한 다단 편집 복원, 변경 표시/취소 범위 병합은 후속 범위입니다.
  명시적인 중복 OCR 레이어 일부는 내용 유사도를 확인해 한 레이어를 사용하고 경고합니다. OCR 철자 보정은 하지 않습니다.
- PDF 일부 페이지의 텍스트가 부족하면 자동 OCR하며, OCR 또는 Claims 식별이 불가능하면 오류를 반환합니다.
- OCR은 인식 정확도를 보장하지 않습니다. 특히 작은 글자, 기울어진 스캔, 손글씨, 도면, §/숫자/슬래시는 원본과 대조하세요.
  이미지 위에 이미 충분한 텍스트가 있는 페이지나 기존 OCR 철자 오류를 자동으로 재판독하지는 않습니다.
- local 모드는 명시적인 `Claims 1-3 are rejected ...` 등의 표현을 처리합니다. 비표준 문장,
  과거 지적의 인용/철회 문맥, 문서 전역의 인용문헌 별칭, 길게 분할된 설명은 누락·오인할 수 있습니다.
- 기본 chunk 크기를 넘는 구간은 overlap으로 분할하며, continuation만 있는 구간의 연결 한계를 경고합니다.
- 법조항은 §101/102/103/112 및 괄호 하위항을 정규화합니다. 근거가 불명확하거나 지원 범위 밖이면 `unknown`입니다.
- 인용문헌은 명시적 US/WO 번호와 `저자 et al., 학술지 (연도), 권호/페이지` 형태의 NPL을 로컬에서 추출합니다.
  특허는 공개번호, NPL은 저자·학술지·연도·권호/페이지로 식별하며 이름 유사도로 서로 다른 문헌을 합치지 않습니다.
  이름만 있는 문헌은 지적 구간 내 ID를 부여합니다. 서지정보가 생략된 별칭이나 다른 서지 형식은 누락될 수 있습니다.
- 종속관계는 명시적 Claim 참조를 사용합니다. `any preceding claim` 같은 번호 없는 표현은 지원하지 않습니다.
- 로그인/운영 보안/문서 저장 정책/작업 큐 없이 로컬 사용을 전제로 합니다. 여러 명의 운영 서비스 배포는 후속 범위입니다.

다운로드한 USPTO CSV에는 release에 따라 다른 열 이름이 있으므로 `claims_from_csv`에 ID/번호/본문 열을 명시합니다.
OA 연구 데이터의 문서 수준 라벨을 청구항별 정답으로 간주하지 않습니다.

## 검증

2026-09-15 인용문헌 중복·역할 분리: [CITATION_REGISTRY_VALIDATION.md](CITATION_REGISTRY_VALIDATION.md).
실제 17/708,932 OA에서 거절 인용 **7개**, 보조 증거 **Wei 1개**, 거절에 사용하지 않은 기록 **Oda·Biyikli 2개**를 확인했습니다.
Liu 카드는 하나이며 R1~R5와 연결합니다. `citations`는 고유 문헌, `rejection_citations`는 역할·근거를 가진 연결입니다.
기존 `rejections[].cited_references`도 같은 canonical ID를 참조하도록 유지했습니다.
최신 전체 검사: **244 tests passed**, backend coverage **93%**, Ruff lint/format 통과입니다.

2026-09-15 OA 상태 분리 검증: [OA_CLAIM_STATUS_VALIDATION.md](OA_CLAIM_STATUS_VALIDATION.md).
OA의 rejected/objected/allowed/withdrawn/canceled/pending/unknown을 별도로 기록하고,
objection은 직접 거절로 세지 않으며 허용·취소·심사 대상 제외 항은 종속 영향에서 제외합니다.
제공된 pp_vd3.pdf의 실제 결과는 **17/708,932: 직접 거절 17, objection 2, 취소 1**입니다.
사용자 정답표의 4/6/10 및 Wu·Ando는 다른 사건을 표현하는 별도 합성 TXT로 검증했습니다.
최신 전체 검사: **226 tests passed**, backend coverage **92%**, Ruff lint/format 통과입니다.

2026-09-15 제목 없는 청구항 탐지 회귀는 [CLAIM_SECTION_FALLBACK_VALIDATION.md](CLAIM_SECTION_FALLBACK_VALIDATION.md)에 기록했습니다.
기존 제목 기반 탐지를 유지하며, 제목이 없는 전체 문서는 후반부의 Claim 1부터 최소 3개 연속 번호,
청구항 문장 형태와 앞 청구항 참조를 함께 확인합니다. 같은 줄로 추출된 다음 청구항 번호도 구분합니다.
사용자 제공 `pp_ex3.pdf`(US20220325409A1)에서 **Claim 1~20 모두 추출**, 실제 API·Edge 업로드를 확인했습니다.
최신 전체 검사: **205 tests passed**, backend coverage **92%**, Ruff lint/format 통과입니다.
재현: `uv run pytest -q tests/test_claim_sections.py`.

2026-09-14 PDF 검토 UI·좌표 adapter·OCR overlay 검증은 [PDF_REVIEW_VALIDATION.md](PDF_REVIEW_VALIDATION.md)에 기록했습니다.
최종 결과는 **143 tests passed**, backend coverage **92%**, Ruff lint/format 통과입니다.
관계 지도 추가 후 실제 Claim 1·14·15와 citation 5개, 모든 필터 및 PDF 왕복 연결 검증은
[RELATIONSHIP_MAP_VALIDATION.md](RELATIONSHIP_MAP_VALIDATION.md)에 기록했습니다.
실제 Edge에서 PDF 업로드, 양방향 선택, 검색/다운로드, 5개 citation, 실제 OCR 및 좁은 화면 배치를 확인했습니다.
실제 공개 특허 41쪽을 사용했으며, Application 14/623,904 OA는 원본 미제공으로 재현용 PDF를 사용했습니다.
이전 헤더/푸터·WO/NPL 인용 회귀 검증은 [HEADER_CITATION_VALIDATION.md](HEADER_CITATION_VALIDATION.md)에 기록했습니다.
OCR 추가 당시 검증 결과는 **107 tests passed**, backend coverage **92%**였습니다.
실제 Tesseract 스캔·혼합 PDF 및 특허 표현 보존 검증은 [OCR_VALIDATION.md](OCR_VALIDATION.md)에 기록했습니다.
실제 PDF 1쌍에서 거절 2개, 법조항–청구항 연결 8개, 인용 특허 4개, 종속관계 3개가 원문 기준 라벨과 일치했습니다.
이 사례를 보며 코드를 보완한 개발·회귀 검증이며 일반 성능이나 LLM 성능 수치가 아닙니다.
2026-09-11에는 실제 Edge 브라우저에서 가상 예제 실행, 그래프 Claim 클릭, 상세 전환, 체크리스트 체크, JSON 다운로드를 확인했습니다.

```powershell
uv run pytest -q
uv run pytest --cov=backend --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run python -m scripts.validate_real_pair
```

테스트는 범위/복수 종속/순환/취소항, PDF/JSON/CSV, 서로 다른 거절 사유,
근거 위조와 인용문헌 검증, SDK 요청 계약, API 업로드·오류, UI 예제와 Claim 선택을 다룹니다.
CLI 예제의 평가 수치는 가상 fixture에 대한 회귀 검증이며 실제 특허 문서의 성능 수치가 아닙니다.
`classification_metrics`는 같은 항목 순서로 정렬된 label을 받아 Accuracy/Macro-F1을 계산합니다.
평가 CLI의 statute/claim 집합 점수는 rejection grouping이나 자연어 설명의 정확도를 측정하지 않습니다.

선택적 브라우저 검증은 서버 실행 후 설치된 Microsoft Edge에서 수행합니다.

```powershell
uv run --no-project --with playwright --python 3.11 python scripts/browser_smoke.py
```

This system is an AI-assisted patent document analysis tool.
It does not provide legal advice or replace professional patent counsel.

## PDF 헤더/푸터와 인용문헌 근거

Patent PDF는 텍스트/OCR 추출 후 정규화 전에 여백을 정리합니다. 실제 PDF 좌표, 본문과의 간격,
공개번호·발행일·페이지 번호 패턴과 여러 페이지의 반복을 함께 확인합니다. 본문 안의 동일한 번호나
날짜는 유지하며, 식별이 불확실한 회전/복잡한 좌표나 중복 텍스트 레이어는 정리를 생략합니다.
좌표가 없는 OCR 결과는 반복 공개번호를 포함하는 연속된 페이지 시작/끝 구간만 보수적으로 정리합니다.
제거한 내용은 `documents[].metadata.removed_margins`의 `page_number/text/position/reason`으로 확인합니다.
OCR 엔진 원문은 기존 `ocr_raw_text`에 그대로 남으며, 화학명 하이픈이나 OCR 철자를 LLM으로 고치지 않습니다.

`documents[].text`와 Claim/Evidence는 정리 후 정규화된 동일 텍스트를 사용합니다. 페이지 수·순서를 유지하고
`start/end`를 다시 계산합니다. 기존 JSON 입력·API endpoint·graph node/edge 구조는 유지합니다.
인용 응답에는 기본값이 있는 `type` (`patent/npl/unknown`), `raw_text`, `publication`, `year` 필드만 추가했습니다.
그래프의 인용 노드는 저자와 공개번호 또는 NPL을 두 줄로 표시하며, 클릭하면 해당 OA 원문·페이지·문자 위치를 보여줍니다.
외부 LLM 모드도 기존 근거 검증 후 같은 rejection chunk의 명시적 인용을 로컬 규칙으로 보완합니다.

추가 설치는 필요하지 않습니다. 기존 Windows Tesseract 설정과 로컬 OCR 처리 방식은 그대로입니다.
새 분석부터 적용되므로 이미 저장된 결과는 문서를 다시 분석하세요.

```powershell
# 실제 공개 특허 41쪽 + 사용자 제공 문헌 목록을 재현한 가상 OA
uv run python scripts/validate_header_citations.py
# 실제 OA 파일로 대조 (OCR 오류/번호 차이는 검증 실패로 표시)
uv run python scripts/validate_header_citations.py --office-action "C:\path\office_action.pdf"
# 서버 실행 후 실제 Edge 브라우저에서 PDF 업로드, 5개 노드와 클릭 근거 확인
uv run --no-project --with playwright --python 3.11 python scripts/browser_citation_smoke.py
```
