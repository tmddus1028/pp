# Evidence Comparison 전용 화면

## 정보 구조

Claim selector와 지적 사유 selector 아래에 상태·법조항·명세서 연결 수·인용문헌 수를 간결하게 표시합니다.
본문은 데스크톱에서 2×2 카드, 1000px 이하에서 세로 스택입니다.

1. **청구항 원문**: 전체 Evidence 텍스트, 독립/종속항, 상위 Claim, 직접 종속 Claim, PDF 이동.
2. **심사관 지적**: 연결된 rejection의 법조항/ID, 직접 지적 또는 종속 영향, OA 원문, 페이지, OA PDF 이동.
3. **명세서 근거**: 기존에 명시적으로 연결된 문단/도면의 제목·페이지·원문·연결 이유.
4. **인용 선행기술**: Patent/NPL 이름·번호/학술지·연도. 펼치면 원문 인용, 사용된 rejection, 같은 사유의 Claim과 인용 위치 이동.

긴 원문은 텍스트 영역 안에서 스크롤하며 전체 내용을 유지합니다.
§112 선택 시 Claim–명세서–OA, §103 선택 시 Claim–OA–선행기술의 비교 안내와 카드 테두리를 강조합니다.
직접 지적은 red, 종속 영향은 amber, 명세서는 teal, 인용문헌은 green을 사용하며 본문 전체를 진하게 칠하지 않습니다.
하단 ‘비교 요약’은 기존 `reason_summary`와 상태/관계 정보만 표시합니다.

## 데이터와 연결

`build_review_model`의 기존 Claim/direct/indirect/rejection_ids/depends_on/children/support_ids를 재사용합니다.
rejection ID로 해당 OA Evidence를 찾고, 각 rejection의 citation을 모아 동일 citation ID만 합칩니다.
이름이 비슷하다는 이유로 다른 문헌을 합치지 않습니다. Patent/NPL 구분은 기존 `type`을 사용합니다.
각 citation에는 해당 비교 범위의 등장 위치와 관련 rejection, 같은 rejection에 포함된 Claim 목록을 함께 표시합니다.
이를 Claim 구성요소별 개시 판단으로 표현하지 않습니다.

원문 텍스트·document ID·page·start/end는 변경하지 않습니다. UI에 법조항 구두점만 읽기 쉽게 표시합니다.
Backend 분석, OCR, ingestion, parser, dependency 계산, citation extraction, graph edges, provider 및 API schema는 그대로입니다.
Claim/범위를 바꾸어도 API 분석이나 LLM 호출을 하지 않습니다.

## 명세서와 미자동화 범위

현재 데이터에는 일반적인 Claim → specification support 판단이 없습니다.
기존 PDF 검토가 사용하는 **OA의 명시적인 paragraph/figure 언급**이 있는 경우에만 그 연결을 재사용하고,
OA에서 언급된 위치임을 설명합니다. 법적 뒷받침 여부나 관련도 점수를 생성하지 않습니다.
Claim 14의 재현 OA에는 명시적인 명세서 연결이 없어
‘현재 자동 연결된 명세서 근거가 없습니다.’로 표시합니다.
단순히 같은 단어가 나온다는 이유로 문단을 매칭하지 않는 회귀를 추가했습니다.

아직 자동화하지 않는 부분:

- 새 Claim–명세서 support 매칭과 법적 충분성 판단.
- 인용 선행기술/논문의 전문 수집 및 Claim 구성요소별 대응 비교.
- 기존 Evidence 범위보다 세밀한 Claim phrase–OA 문장 대응 생성.

따라서 화면은 기존 OA 근거 구간을 그대로 보여주며, 없는 문장 위치나 highlight를 만들지 않습니다.
인용문헌 카드의 원문은 **OA에서 인용된 근거**이며 문헌 전문을 가져온 것이 아닙니다.

## 페이지 이동

- PDF Review Panel 및 관계 지도에서 Claim의 ‘근거 비교’를 누르면 Claim 번호와 선택 rejection 범위를 전달합니다.
- 일반 메뉴 진입도 현재 선택한 Claim을 이어받을 수 있습니다.
- 비교 화면의 Claim/OA/명세서/citation 버튼은 기존 `review_jump` 경로로 해당 PDF 페이지와 annotation을 선택합니다.
- OA를 확인한 뒤 돌아와도 비교하던 Claim을 유지합니다. Claim을 변경하면 비교 범위는 전체로 초기화합니다.
- 이 페이지는 PDF viewer를 호출하거나 중복 렌더링하지 않습니다. 내용 비교와 PDF 위치 확인의 역할을 분리했습니다.

## 검증

실제 공개 US 2015/0283132 A1의 Claim 14와 **재현 OA**를 사용합니다. 사용자 원본 OA 자체를 검증한 것은 아닙니다.

Streamlit/presentation 회귀 9개:

- 실제 Claim 14의 두 지적 사유·5개 citation, 상위 Claim 1/직접 종속 Claim 15.
- Evidence가 원래 document text의 start/end 구간과 일치하고 분석 결과가 불변임을 확인.
- §112/§103 범위와 Claim 2의 종속 영향 분리.
- 없는 명세서 링크와 단어 겹침만 있는 경우를 비워 두고, 기존 명시적 문단만 표시.
- Claim/범위 변경, PDF/관계 지도 왕복, PDF 중복 렌더링 및 추가 API 호출 없음.

Edge 브라우저 흐름:

- Claim 14 선택 → 두 OA 원문과 5개 Patent/NPL 표시 → Greco 상세/학술지/연도/원문 펼침.
- §112/§103 비교 강조 및 citation 범위 변경.
- Claim PDF 및 OA PDF 이동, 선택 Claim/범위 유지.
- Claim 2로 변경 시 원문·관계·OA 직접 지적 여부·citation 갱신.
- 관계 지도에서 Claim 14와 §112 범위를 전달.
- 데스크톱 2×2와 900px 스택, 큰 PDF viewer 없음.
- 합성 문서의 명시적 [0018]/Figure 1 및 연결이 없는 Claim 4, 명세서 PDF 이동.

실행: `uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_evidence_comparison.py`
실제 전체 PDF는 `--full`로 실행하거나 `scripts/browser_pdf_review.py`의 전체 회귀를 사용합니다.
명령별 최종 결과: [VALIDATION.md](VALIDATION.md).
`uv run pytest -q`: **161 passed**. Coverage 실행: **161 passed**, backend **92%**.
Ruff check 및 format check도 통과했습니다.
`scripts/browser_pdf_review.py`의 **전체 41쪽 실제 특허 PDF** 검사도 통과했습니다.
기존 accordion·bbox·badge·관계 지도·목록·원본 다운로드·실제 Tesseract OCR 흐름을 함께 확인했습니다.
화면: [Claim 14 비교](data/outputs/evidence-comparison-claim14.png), [좁은 화면](data/outputs/evidence-comparison-narrow.png).

## 수정 파일

- `frontend/evidence_comparison.py` — 추가, 전용 비교 화면과 기존 근거를 묶는 표시 model.
- `frontend/app.py` — 전용 페이지 분기 및 선택 Claim 전달.
- `frontend/styles.css` — 비교 카드·상태·원문 영역·반응형 배치.
- `frontend/pdf_review.py`, `frontend/pdf_review_component/review.js` — PDF 상세에서 비교 이동.
- `frontend/relationship_map.py`, `frontend/relationship_map_component/map.js` — 지도에서 비교 이동.
- `tests/test_evidence_comparison.py` — 추가, 데이터/상태/이동 회귀 9개.
- `scripts/browser_evidence_comparison.py` — 추가, 실제 비교 브라우저 흐름.
- `scripts/browser_pdf_review.py` — 기존 전체 회귀에 비교 흐름 연결.
- `README.md`, `VALIDATION.md`, 이 문서 — 사용 방법과 검증 기록.

캐시된 Python 화면 연결을 반영하기 위해 UI 서버만 재시작했으며, `data/outputs/server-processes.json`도 갱신했습니다.
