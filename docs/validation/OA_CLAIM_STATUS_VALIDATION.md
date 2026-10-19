# OA 청구항 상태 분리 검증 · 2026-09-15

## 먼저 확인된 원문과 정답표의 불일치

제공된 `pp_vd3.pdf`의 실제 출원번호는 **17/708,932**입니다.
PDF를 렌더링하여 첫 거절 및 Allowable Subject Matter 페이지를 직접 확인했습니다.
출원 18/731,426의 정답표를 이 PDF의 실제 결과로 덮어쓰지 않았습니다.

| 항목 | 제공된 PDF 원문 | 사용자 정답표 재현 TXT |
|---|---|---|
| 출원번호 | 17/708,932 | 18/731,426으로 표기한 합성 입력 |
| 직접 거절 | 1~14, 17~19: **17개** | 1, 2, 3, 8: **4개** |
| Objection | 15, 16: **2개** | 4~7, 9~10: **6개** |
| 허용 | **0개** | 11~20: **10개** |
| 취소 | 20: **1개** | 없음 |
| 실제 §103 거절 블록 | **5개 유지** | **1개** |
| Wu·Ando | 이 원문에 없음 | 거절에 연결된 문헌 **2개** |

PDF 3페이지에는 Claim 20 취소 및 첫 거절이, 10페이지에는 Claim 15·16 objection과
독립항으로 재작성할 경우 허용 가능하다는 조건이 명시되어 있습니다.
R6는 별도의 §103 거절이 아니라 objection입니다.
특허 공개 문서에는 Claim 20이 있지만 OA에는 취소되어 있어, 두 입력의 버전이 완전히 같다고 주장하지 않습니다.

원본 사본·해시·페이지별 근거: [fixture 설명](tests/fixtures/oa_status/README.md).
검증에 사용한 PDF는 원본의 바이트 사본이며 원본 PDF를 수정·재저장하지 않았습니다.

## 오류 원인과 수정

1. 기존 parser는 이미 `rejection`과 `objection`을 구별했지만,
   impact 계산이 두 유형 모두의 `claims`를 `direct_claims`에 넣었습니다.
   따라서 실제 거절 17개에 objection 2개가 합산되어 UI에서 19개가 빨강으로 표시됐습니다.
2. OA의 취소·허용·심사 대상 제외 상태를 별도로 기록하지 않아 공개 청구항 목록의 Claim 20을
   종속 영향으로 계산했습니다.
3. Word-per-line PDF의 `Allowable\nSubject\nMatter` 같은 제목은 기존 공백 고정 패턴으로
   끊지 못했고, objection에는 법조항이 없으므로 `unknown`이 UI에 노출됐습니다.
4. Citation 추출이 거절 구간의 모든 특허 번호를 수집했습니다.
   LLM 근거 검증에도 명시적 action 대신 단순 Claim 언급으로 보완하는 경로가 있었습니다.

수정 후 동작:

- `claim_statuses`에 `rejected/objected/allowed/withdrawn/canceled/pending/unknown`,
  원문 Evidence 및 `conditional_allowance`를 기록합니다. Patent Claim의 기존 active/canceled 필드는 보존합니다.
- `direct_claims`는 명시적인 rejection에만 사용하며 objection 대상은 `objected_claims`로 분리합니다.
  OA에서 allowed/withdrawn/canceled로 확인된 Claim은 직접 거절·종속 영향 집계에서 제외합니다.
- `claim_summary`는 직접 거절·objection·허용·취소 등 번호 집합을 반환합니다.
  PDF 및 Claim 목록은 이 상태와 impact를 이용해 색상/집계를 일치시킵니다.
- Objection과 실제 종속 영향의 합집합을 amber로 표시하며 중복 집계하지 않습니다.
  허용 Claim은 별도 상태·필터로 표시합니다. R6 라벨은 `Objection`이며 `unknown`이 아닙니다.
- 명시적 상태 문장과 여러 줄 섹션 제목에서 거절 evidence를 종료합니다.
  Allowable Subject Matter/Reasons for Allowance 구간의 번호 언급은 새 거절로 만들지 않습니다.
- `over`, `in view of`, `in further view of`, `as evidenced by` 등 reliance 표현과
  이어지는 문헌 목록을 연결합니다. 일반 배경 설명의 번호·not relied upon 문헌은 제외합니다.
  기존 특허/NPL identity 및 서로 다른 kind code의 분리는 유지합니다.
- LLM 응답도 같은 유형의 명시적 action 문장으로 Claim 번호를 검증합니다.
  단순 Regarding/objection 문장의 rejected라는 단어만으로 거절을 생성하면 실패합니다.
- 기존 API endpoint/입력, OCR, Claim parser, Claim 종속관계 파싱, PDF 좌표는 유지했습니다.
  출력에는 기본값이 있는 상태 필드만 추가했습니다. 상태/impact도 analysis_id에 반영해 이전 화면 캐시와 구분합니다.

## 검증 결과

| 실행 | 결과 |
|---|---|
| `uv run pytest -q` | **226 passed**, 88.35초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | **226 passed**, backend **92%**, 152.17초 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 107 files already formatted |
| 실제 실행 중인 FastAPI multipart 요청 | 실제 PDF·재현 TXT 모두 **HTTP 200** |
| 실제 Edge 업로드 | 두 경우 모두 통과 |

기존 Starlette/httpx·anyio deprecation 경고 2개는 남아 있습니다.
§112/§103, 기존 pp_ex2/pp_vd2의 20항·3거절·5문헌, 실제 Fote 문서 쌍,
Claim/Evidence/OCR 및 UI 선택 회귀가 모두 통과했습니다.

새 상태 회귀 21개는 실제 PDF 집합, 사용자 정답표 재현, 허용 항의 red 배제,
Regarding/종속 설명/조건부 허용의 오탐 방지, 취소/철회/계류,
LLM의 상태 오분류 차단, incidental citation 제외, API 결과 및 Evidence 위치를 검사합니다.
기존 citation identity 테스트 하나는 모든 문헌의 identity만 검증하도록 기본 citation extractor를 직접 호출합니다.
거절의 incidental reference 포함 여부는 새 전용 테스트로 검사합니다.
UI 기존 요약 테스트에는 새 허용 카드(예제에서 0)를 추가했습니다.

실제 PDF 브라우저 검사에서는 Claim 15가 amber이며 R6 클릭으로 OA PDF 10페이지로 이동하고,
Claim 15가 계속 펼쳐지는 것을 확인했습니다. Claim 20은 취소 상태와 원문 근거를 표시합니다.
재현 입력에서는 4/6/10·인용 2개, Claim 15 허용·red 없음 및 허용 근거를 확인했습니다.

- [실제 PDF 화면](data/outputs/oa-status-actual.png)
- [사용자 정답표 재현 화면](data/outputs/oa-status-reconstructed.png)
- [실제 PDF API 결과](data/validation/oa_status/actual.json)
- [재현 TXT API 결과](data/validation/oa_status/reconstructed.json)

재현 명령:

```powershell
uv run pytest -q tests/test_oa_status.py
# API 8000 / Streamlit 8501 실행 상태에서:
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_oa_status.py
```

## 수정 파일

- Backend: `schemas.py`, `service.py`, `office_action/claim_status.py`(신규),
  `office_action/oa_parser.py`, `office_action/rejection_extractor.py`,
  `analysis/impact_analyzer.py`, `analysis/citation_analyzer.py`,
  `llm/structured_extraction.py`, `graph/graph_builder.py`.
- Frontend: `review_model.py`, `claim_analysis.py`, `evidence_comparison.py`,
  `pdf_review_component/review.js`, `review.css`, `relationship_map_component/map.js`, `map.css`.
- Tests: `test_oa_status.py`(신규), `test_citation_completeness.py`, `test_frontend.py`,
  `fixtures/oa_status/`의 실제 PDF 사본·재현 TXT·README.
- 검증: `scripts/browser_oa_status.py`, `README.md`, `VALIDATION.md`, 이 문서 및 위 실행 산출물.

이번 검증은 두 입력의 상태 처리 회귀입니다. 출원 18/731,426의 실제 OA 원본 검증을 완료했다는 뜻은 아닙니다.
