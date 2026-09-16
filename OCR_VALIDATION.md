# 스캔 PDF OCR 구현·검증 기록

검증일: 2026-09-14. Windows, CPython 3.11.16, `uv.lock` 환경.

## 실행 결과

| 요청한 명령 | 최종 결과 |
|---|---|
| `uv run pytest -q` | **107 passed**, 2 warnings, 14.06초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | **107 passed**, backend **92%**, 26.43초 |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **58 files already formatted** |

실제 Tesseract 통합 테스트 3개도 실행했으며 skip하지 않았습니다. 두 경고는 기존 Starlette/httpx/AnyIO deprecation입니다.
OCR worker는 별도 프로세스로 실행하므로 위 기본 커버리지 명령은 자식 프로세스의 실행 줄을 집계하지 않습니다.
현재 수치를 이전의 95%와 동일하다고 표시하지 않습니다.

실행 중인 API/Streamlit 서버도 새 코드로 재시작했습니다.
실제 `http://127.0.0.1:8000/analyze/files`에 스캔 fixture를 multipart 업로드하여 **HTTP 200**,
`ocr_pages=[1,2]`, CLI와 같은 결과를 확인했습니다. Streamlit health도 200입니다.
Streamlit 자동 테스트는 OCR 안내·페이지 목록·OCR 원문 표시와 메타데이터가 없는 이전 응답의 표시를 확인합니다.

검증 산출물: [분석 JSON](data/validation/ocr/analysis.json), [실행 환경·입력 해시·실서버 결과](data/validation/ocr/checks.json).

## OCR 처리 흐름

1. 기존 pypdf 추출과 기존 중복 OCR 레이어 처리를 수행합니다.
2. 페이지의 문자/숫자가 기본 20자 이상이면 기존 텍스트를 그대로 사용합니다. OCR 엔진 탐색·렌더링도 하지 않습니다.
3. 텍스트가 부족한 페이지만 OCR 대상으로 모읍니다. 실제로 빈 페이지는 빈 위치와 페이지 번호를 보존합니다.
4. 별도 로컬 프로세스에서 대상 페이지만 300 DPI RGB 이미지로 렌더링하고, `pytesseract` → Tesseract `eng`로 읽습니다.
5. 페이지 순서대로 OCR 텍스트를 해당 위치에 넣고, 정규화 전 결과는 `metadata.ocr_raw_text`에 보존합니다.
6. 기존 정규화·문자 위치 계산을 거쳐 기존 Claim/OA parser와 graph/evaluation 경로로 전달합니다.

외부 API/LLM 호출, OCR 문구 교정, 특허번호 추정, § 기호 치환은 하지 않습니다.
LLM 설정을 켜더라도 OCR은 로컬에서 처리하며, 이후 OA 분석의 기존 공급자 선택만 적용됩니다.
이번 검증에서는 `provider=local`을 명시했습니다.

PyMuPDF는 우선 렌더러입니다. 이 PC에서는 PyMuPDF DLL 로딩/Windows 애플리케이션 제어 문제로
실제 렌더링이 실행되지 않아, **PDFium 5.13.0 + Tesseract 5.4.0.20240606**으로 실제 OCR을 검증했습니다.
PyMuPDF 1.28.2 우선 선택과 300 DPI 호출 계약, strict 모드 실패는 모의 테스트로 검증했습니다.
이 환경에서 PyMuPDF의 실제 렌더링까지 통과했다고 주장하지 않습니다.
`OCR_RENDERER=auto`의 전환은 경고와 `ocr_renderer=pdfium`으로 공개하며,
`OCR_RENDERER=pymupdf`는 PyMuPDF 미사용 시 오류를 반환합니다. Windows 보안 설정을 변경하지 않았습니다.

## 특허 표현·downstream 검사

`14/623,904` 형식을 본뜬 **가상 문서**로 텍스트 PDF, 이미지 전용 스캔 PDF, 혼합 PDF를 만들었습니다.
[fixture 구성과 정답 문구](tests/fixtures/ocr/README.md)를 참고하세요. 실제 사건의 거절 사실을 재현한 문서가 아닙니다.

| 검사 | 결과 |
|---|---|
| 텍스트 PDF | OCR 호출 0회, 잘못된 Tesseract 경로로도 텍스트 처리 성공 |
| 스캔 PDF | pypdf 추출 텍스트가 실제로 비어 있음; OCR 페이지 `[1,2]` |
| 혼합 PDF | 1쪽 텍스트 유지, OCR 페이지 `[2]` |
| 페이지 번호만 있는 스캔 | 숫자 한 개를 충분한 본문으로 간주하지 않고 OCR |
| 특허 표현 | `Claim 1`, `Claims 1-19`, `35 U.S.C.`, `§ 112`, `§ 103`, `14/623,904` 보존 |
| 공개/등록번호 | `US 2010/0123456 A1`, `8,765,432 B2` 보존 |
| 인용 성명 | `Smith`, `Johnson` 보존 |
| OA parser | §112(b), §103 모두 청구항 1–19에 연결 |
| citation parser | Smith → `US20100123456A1`, Johnson → `US8765432B2` |
| Evidence | OCR 정규화 전/후 대응, 페이지 순서, 원문 `start/end` 일치 검사 |
| 실패 경로 | 손상 PDF, 엔진 미설치/경로 오류/영어 데이터 누락/시간 초과/빈 인식 결과 구분 |
| API 실패 | `422` 후 health 정상; 혼합 PDF의 일부 인식 실패를 부분 성공으로 반환하지 않음 |

기존 section chunking은 다음 페이지의 머리말까지 근거에 포함할 수 있습니다.
fixture의 §112 근거 페이지는 `[1,2]`, §103은 `[2]`이며 실제 문자 구간과 일치합니다.
이를 단일 페이지로 임의 축소하거나 parser를 다시 작성하지 않았습니다.

깨끗한 인쇄체 fixture 결과를 저화질·회전·손글씨·다단 문서 전체의 인식 정확도로 일반화하지 않습니다.
OCR 결과가 비어 있지 않아도 오인식은 가능하며, 원문 대조가 필요합니다. 자동 문맥 수정은 없습니다.

## Windows 준비 및 실제 파일 테스트

현재 PC에는 Tesseract와 영어 데이터가 `%LOCALAPPDATA%\Programs\Tesseract-OCR`에 설치되어 자동 탐색됩니다.
다른 PC에서는 Tesseract Windows 설치와 `uv sync`가 필요합니다. 자세한 링크·경로 설정은 [README](README.md#스캔-pdf-자동-ocr)에 있습니다.

```dotenv
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_DPI=300
OCR_RENDERER=auto
```

PyMuPDF DLL 오류에는 Microsoft Visual C++ x64 런타임 설치/복구가 필요할 수 있습니다.
실제 설치 경로가 다르면 `TESSERACT_CMD`를 수정하고 backend를 재시작하세요.

현재 [Streamlit 화면](http://127.0.0.1:8501)에서 당시 버전의 Claims와 스캔 OA를 올린 뒤 “분석 시작”을 누르면 자동 처리됩니다.
OCR 안내 쪽수, “원문 및 JSON”의 페이지별 문구와 정규화 전 OCR 원문을 대조할 수 있습니다.

```powershell
uv run python -m backend.cli --patent 'C:\Documents\claims.pdf' --office-action 'C:\Documents\office-action-scan.pdf' --provider local --output data/outputs/my-scan-analysis.json
```

기본 자동 판정은 텍스트 양에 따른 휴리스틱입니다. 스캔 위에 이미 긴 머리말 텍스트가 있는 경우
필요에 따라 `OCR_MIN_TEXT_CHARS`를 조정할 수 있습니다. 충분한 텍스트를 가진 페이지의 OCR 오타까지 자동 재판독하지 않습니다.

## 수정·추가 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `backend/ingestion/pdf_reader.py` | 페이지별 fallback, 빈 페이지·추출 실패 처리; 기존 `read_pdf()` 2값 반환 유지 |
| `backend/ingestion/ocr.py` **추가** | 실행 파일 탐색, 격리 worker 호출·시간 제한·응답 검증 |
| `backend/ingestion/ocr_worker.py` **추가** | PyMuPDF/PDFium 렌더링, 실제 pytesseract 실행·실패 처리 |
| `backend/ingestion/adapters.py` | OCR metadata를 기존 Document 정규화 경로에 연결 |
| `backend/config.py` | OCR 및 Tesseract 환경 설정 |
| `backend/errors.py` | OCRDependencyError/OCRProcessingError; 기존 DocumentError 하위 타입 |
| `backend/schemas.py` | 기본값이 있는 `Document.metadata` 및 OCRMetadata |
| `frontend/app.py` | 자동 OCR 안내, 페이지 번호·OCR 원문 표시 |
| `pyproject.toml`, `uv.lock`, `requirements.txt` | PyMuPDF/pytesseract/Pillow/PDFium 의존성 및 테스트 marker |
| `.env.example` | Windows 경로와 OCR 설정 예시 |
| `tests/test_ocr.py` **추가** | 선택적 OCR, 실제 엔진, 특허 표현, parser 연결, 오류/API 회귀 25개 |
| `tests/test_frontend.py` | OCR 안내 및 기존 응답 호환 테스트 추가 |
| `tests/test_cli_and_public.py` | 기존 127쪽 PDF의 Claims 누락 검사에 모의 OCR 연결; 실제 OCR은 별도 fixture에서 검증 |
| `scripts/make_ocr_fixtures.py` **추가** | 재현 가능한 가상 스캔 fixture 생성 |
| `tests/fixtures/ocr/office_action_text.pdf` **추가** | 텍스트 입력 비교용 |
| `tests/fixtures/ocr/office_action_scan.pdf` **추가** | 텍스트 레이어 없는 2쪽 스캔 |
| `tests/fixtures/ocr/office_action_mixed.pdf` **추가** | 혼합 문서 |
| `tests/fixtures/ocr/expected_pages.json`, `claims.txt`, `README.md` **추가** | 정답 문구·Claims·출처 성격 |
| `README.md`, `VALIDATION.md`, `DEVELOPMENT_PLAN.md` | 설치·실행·현재 검증 범위 갱신 |
| `OCR_VALIDATION.md` **추가** | 이 보고서 |
| `data/validation/ocr/analysis.json`, `checks.json` **추가** | CLI·실서버 결과와 환경·해시 |

## 기존 기능에 대한 영향

Claim parser, OA parser, graph, evaluation, LLM prompt/전송 경로는 수정하지 않았습니다.
PDF/TXT/JSON 요청 형식과 API endpoint, 기존 응답 필드를 유지하고 `documents[].metadata`만 추가했습니다.
기존 저장 JSON에 metadata가 없어도 기본값으로 읽으며 UI도 해당 필드 없이 동작합니다.
`documents[].text`는 기존 정규화 후 문자 위치를 사용하고, OCR 원문은 별도 보존하므로 Evidence 기준은 바뀌지 않습니다.
OCR 오류는 기존 `DocumentError` 처리 경로로 전달되어 API 계약을 유지합니다.
DB/agent framework를 추가하지 않았습니다.
