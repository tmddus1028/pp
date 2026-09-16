# PDF 열기 fallback · pp_ex2 / pp_vd2

## 원인

기존 ingestion은 `PdfReader` 생성과 `pdf.pages` 순회를 먼저 수행했다.
`pp_vd2.pdf`의 `/Pages` 객체를 pypdf가 해석하지 못하면 `PdfReadError: Invalid object in /Pages`가 발생했고,
바깥 예외 처리에서 즉시 ‘PDF를 열 수 없습니다’ 오류로 바뀌었다. API는 이를 422로 반환했다.
OCR과 다른 renderer는 이 초기 열기 단계 뒤에 있어 실행할 기회가 없었다.
pypdf의 기본 strict 설정이 엄격 모드인지와 관계없이 발생하는 parser별 호환성 문제였다.

## 변경 흐름

1. 별도 로컬 프로세스에서 PyMuPDF로 문서와 페이지를 연다.
2. import/DLL/open/page-tree 오류가 있으면 PDFium으로 재시도한다.
3. 두 native parser가 실패하면 기존 pypdf로 연다.
4. 성공한 parser가 있으면 전체 페이지 수와 페이지 순서를 유지해 진행한다.
5. 기존 정상 문서의 텍스트 읽기 순서와 중복 OCR 레이어 처리를 유지하기 위해, pypdf 텍스트 추출을
   계속 사용할 수 있으면 재사용한다. 페이지 트리 오류 또는 페이지 수 불일치 시 성공한 native parser의 텍스트로 처리한다.
6. 텍스트가 부족하거나 추출에 실패한 페이지만 기존 Tesseract OCR을 수행한다.
7. 선택적인 margin cleaner도 pypdf 오류로 유효한 문서를 다시 거부하지 않도록 처리한다.

OCR renderer의 auto 모드도 PyMuPDF import뿐 아니라 PDF open 실패 시 PDFium으로 이어진다.
암호화·페이지 제한·모든 parser 실패·실제 OCR 실패는 기존과 같이 오류로 표시한다.
파일은 byte-for-byte 임시 복사만 하며 `save`/repair/rewrite로 새 PDF를 만들지 않는다.

현재 개발 PC는 PyMuPDF DLL 로드에 실패한다. 두 사용자 파일의 **실제 open 경로는 PDFium**이다.
PyMuPDF 우선과 open 실패 후 PDFium 전환 분기는 별도 mock 회귀로 확인한다. 이 PC에서 실제 PyMuPDF open을 성공했다고 주장하지 않는다.

## 요청된 분석 검증을 위한 형식 보완

- `pp_ex2.pdf`의 마지막 두 페이지는 내장 OCR 텍스트가 좌우 단과 줄을 섞어 Claim 제목·번호를 한 줄로 반환한다.
  inline Claims 제목이 감지된 구간에 한해 실제 글자의 baseline 원점과 x 좌표로 줄·단 순서를 정렬한다.
  제목 위의 전체 너비 구간은 유지하고, 두 단 모두 Claim 시작이 확인될 때만 단을 나누어 읽는다.
  이 페이지들은 `metadata.pdf_layout_pages`에 기록한다. Claim parser 자체는 변경하지 않았다.
  원문 글자 수/종류 불변 검사를 포함하며 철자, 줄 번호, 화학·생물학 용어를 추정 교정하지 않는다.
- OA의 `Claims ... is/are rejected under ...`를 지원한다. 법조항 없는 Summary 체크박스 문장을 별도 거절로 세지 않는다.
- `US PG PUB ... A 1`, 대괄호 특허 번호, `저자 [학술지, volume, 연도, pages]`를 인식한다.
- 후속 거절의 `as applied ... claims ... above`가 명시된 경우에만 유일하게 일치하는 기존 저자명/문헌 정의와 연결한다.
  다른 문헌이 같은 저자명을 쓰면 병합하지 않는다. 현재 언급 위치는 기존 `evidence`에,
  최초 서지정보 위치는 선택 필드 `definition_evidence`에 보존한다.

## 원문 기준 기대 결과

| 항목 | 기대 결과 |
|---|---|
| pp_ex2.pdf | 47쪽, Claim 1~20 |
| pp_vd2.pdf | 13쪽, 암호화 없음 |
| R1 | §103(a), Claims 1~12 및 20, PDF 5쪽 시작 |
| R2 | §103(a), Claims 13 및 17~19, PDF 8쪽 시작 |
| R3 | §103(a), Claims 14~16, PDF 10쪽 시작 |
| 고유 citation | Han, Lin, Vogelstein, Empedocles, Newton: 총 5개 |
| 문헌 종류 | 특허 3개, NPL 2개 |
| OCR | 특허 35쪽만 기존 OCR, OA는 native 텍스트 사용 |

파일 SHA-256 및 세부 기대값은 [manifest](tests/fixtures/pdf_fallback/manifest.json)에 고정한다.
등록특허와 OA 당시 청구항 버전이 동일하다는 검증은 포함하지 않는다.

## 재현 및 검증

```powershell
uv run python -m scripts.validate_pdf_fallback
uv run pytest -q tests/test_pdf_fallback.py
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_pdf_fallback.py
```

스크립트 결과는 `data/validation/pdf_fallback/analysis.json`과 `checks.json`에 저장한다.
단위·통합 검사는 parser fallback 순서, native 실패 후 pypdf, 모든 parser 실패, sparse-page OCR,
원본 해시·원문 Evidence 위치·글자 보존, 실제 multipart 업로드 및 문헌 약칭의 모호성을 포함한다.

## 수정 파일

최종 실행 결과 (2026-09-15):

| 검사 | 결과 |
|---|---|
| `uv run pytest -q` | 183 passed, 80.10초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | 183 passed, backend 91%, 135.62초 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 99 files already formatted |
| 새 fixture/실패 경로 회귀 | 20 passed |
| `scripts.validate_pdf_fallback` | 모든 check true, 원본 파일 해시 유지 |
| 실제 Edge 파일 업로드 | 47/13쪽, 20 Claims, 거절 3개, citation 5개, Claim 1 → OA p.5 통과 |

[분석 JSON](data/validation/pdf_fallback/analysis.json), [검사 결과](data/validation/pdf_fallback/checks.json),
[웹 화면 캡처](data/outputs/pdf-fallback-pp-pair.png).
pytest의 warning 2개는 기존 Starlette/httpx 및 anyio deprecation 안내이다.

수정 파일:

- `backend/ingestion/pdf_open.py`, `pdf_open_worker.py`: 격리된 native open/text fallback 추가.
- `backend/ingestion/pdf_reader.py`: 열기 결과와 기존 텍스트·OCR 흐름 연결.
- `backend/ingestion/ocr_worker.py`: auto renderer의 open 실패 fallback.
- `backend/ingestion/margin_cleaner.py`: 선택적 정리 단계의 parser 오류 처리.
- `backend/schemas.py`: parser/읽기 순서 metadata 및 선택적인 문헌 정의 근거.
- `backend/office_action/oa_parser.py`, `rejection_extractor.py`: 실제 지적 문장 형식 및 명시적 이전 문헌 참조.
- `backend/analysis/citation_analyzer.py`: 대괄호·PG PUB·volume-before-year 서지 형식.
- `tests/test_pdf_fallback.py`, `tests/fixtures/pdf_fallback/`: 원본 두 PDF·manifest·설명 및 회귀.
- `scripts/validate_pdf_fallback.py`, `scripts/browser_pdf_fallback.py`: 재현·실제 브라우저 업로드.
- `README.md`, `VALIDATION.md`, 이 문서: 동작과 검증 기록.

API endpoint와 기존 요청 형식은 유지한다. Claim dependency·graph·평가·LLM provider·PDF Viewer는 재작성하지 않았다.
