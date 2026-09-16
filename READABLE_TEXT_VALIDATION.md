# 공통 원문 렌더링 검증

2026-09-16. application 17/708,932, 실제 pp_ex3/pp_vd3 fixture 사용.

## 원인과 수정

- `white-space: pre-wrap`이 OCR/추출 원문의 단어별 개행을 그대로 표시했다.
- Streamlit `st.text(width="content")`의 fit-content 래퍼는 일부 본문 폭을 좁혔다.
- 메인 화면과 두 iframe의 CSS가 분리되어 화면별 수정이 다른 화면에 전달되지 않았다.
- `frontend/readable_text.css`가 원문 타이포그래피와 Streamlit 부모 래퍼를 공통 관리한다.
  메인 화면에는 직접 삽입하고 PDF/지도 iframe에는 동일 파일 내용을 컴포넌트 인자로 전달한다.
- `.readable-text`, `.readable-panel`, `.readable-text-content`, `.readable-toggle`를 사용한다.
  `width/max-width:100%`, `min-width:0`, `white-space:normal`, `word-break:normal`,
  `overflow-wrap:break-word`, `line-height:1.6`을 한 파일에서 정의한다.
- `readable_text()` / `text_html()`은 원문을 HTML 이스케이프하며 개행도 문자 참조로 보존한다.
  Markdown이 빈 줄을 문단 태그로 재해석하지 않게 할 뿐 원문 문자를 고치지 않는다.
  선택적으로 5줄 미리보기와 더 보기/접기를 제공한다.
- 개별 CSS에는 색상·패딩·패널 크기 등 화면 디자인만 유지한다. 텍스트 박스 내부 스크롤을 제거했다.
  PDF 이미지와 annotation/evidence 좌표, 분석 모델은 변경하지 않았다.
- 처리 정보의 raw/debug `st.code` 출력은 원시 문서 검사용으로 유지한다.

## 적용 범위

PDF 검토의 Claim/OA/citation evidence, 설명 문단, TXT 대체 뷰;
청구항 분석의 Claim/OA/인용문헌/명세서 근거;
관계 지도의 Claim/OA/문헌 상세;
근거 비교의 Claim/OA/명세서/문헌 원문 및 비교 요약.

## 브라우저 검증

`scripts/browser_readable_text.py`에서 1920, 1440, 1280, 1024px 각각 검사했다.
6개 표시 범주 × 4개 viewport = 24개 조합에서 실제 표시 요소들을 측정했다.
사용자가 지정한 Claims 1-4 ... Donmez et al. 문장과 모든 공백을 개행으로 바꾼
회귀용 문자열을 동일 스타일로 렌더링했다. 분석 모델에는 테스트 문장을 넣지 않았다.

- 모든 원문: normal 줄바꿈, break-word, 1.6 줄 간격, 부모 폭의 80% 이상, 가로 넘침 없음.
- 회귀 문장 표시: 1~3줄. 최소 측정 본문 폭 302px.
- 전체 evidence 문자열(개행 포함)과 기존 모델의 원문을 정확히 비교했다.
- 네 화면을 오간 뒤 PDF 검토 모델 JSON이 처음과 동일한지 비교했다.
- 기존 요약 수치 20 Claims / 6 사유 / 17 직접 지적 / 2 추가 검토 / 0 허용 유지.
- 지도 Claim 7의 R1/R3 및 Liu/Donmez/Huang 연결, Claim/OA PDF 이동, 선택 유지 검증 통과.
- 심사관 지적의 미리보기/펼치기/접기, 다른 비교 카드 유지, 원문 문자 동일성 검증 통과.

세부 측정: [readable-text-validation.json](data/outputs/readable-text-validation.json).

## 자동 검증

- `uv run pytest -q`: **247 passed**, 기존 라이브러리 deprecation warning 2개.
- 새 회귀 테스트는 원문 문장, OCR 개행·법조항·특허번호, HTML/Markdown 특수문자의 보존을 검사한다.
- Ruff 검사와 포맷 검사 통과.

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_readable_text.py
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_map_detail.py
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_oa_snippets.py
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_citation_registry.py
```

## 변경 파일

- 공통: `frontend/readable_text.css`, `frontend/readable_text.py` (신규)
- 연결: `frontend/app.py`, `frontend/pdf_review.py`, `frontend/relationship_map.py`
- Streamlit 원문: `frontend/claim_analysis.py`, `frontend/evidence_comparison.py`, `frontend/styles.css`
- PDF iframe: `frontend/pdf_review_component/index.html`, `review.js`, `review.css`
- 지도 iframe: `frontend/relationship_map_component/map.js`, `map.css`
- 테스트: `tests/test_readable_text.py` (신규), `tests/test_frontend.py`
- 브라우저: `scripts/browser_readable_text.py` (신규), `scripts/browser_oa_snippets.py`,
  `scripts/browser_claim_analysis_flow.py`, `scripts/browser_evidence_comparison.py`
- 문서: `READABLE_TEXT_VALIDATION.md` (신규)

backend, parsing, API 데이터 구조, citation 분류/중복 제거, 관계 계산은 수정하지 않았다.
