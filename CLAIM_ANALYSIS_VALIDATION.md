# 청구항 분석 화면 · 가독성 개선

## 화면 구성

- 상단에는 `✓ 문서 분석 완료 · OCR 사용됨` 한 줄만 표시합니다. OCR을 사용하지 않았으면 해당 문구를 생략합니다.
- `문서 처리 정보 보기`는 기본적으로 접혀 있습니다. provider, OCR 엔진·페이지·renderer,
  PDF 화면 renderer, warning/debug, 추출 원문·보정하지 않은 OCR 출력과 JSON 다운로드를 모았습니다.
- 작은 요약 카드 4개: 전체 청구항, 거절/지적 사유, 직접 지적 Claim, 추가 검토 Claim.
- 번호순 Claim 목록: 상태, 법조항, 상위 Claim, **직접 종속 Claim 수**, PDF 이동 버튼.
  전체 하위 항목 수와 혼동하지 않도록 직접 종속 관계임을 표시합니다.
- 각 Claim 상세는 접혀 있으며, Claim 원문·OA 근거·citation·명세서/도면·체크리스트를 포함합니다.
- 직접 지적은 red, 종속 영향은 amber의 badge와 왼쪽 테두리로 구분합니다.
  상세의 citation은 green, 명세서/근거는 teal 표시를 사용하고 원문 글자 색은 유지합니다.
- 복잡한 그래프는 이 화면에서 제거했습니다. 전체 구조는 기존 `관계 지도`, 원문 위치는 `PDF 검토`에서 봅니다.

## 상태와 연결

기존 `build_review_model`의 직접 지적·종속 영향·상하위 관계를 그대로 사용합니다.
직접 지적이 있으면 해당 사유의 법조항을 카드에 표시하고, 다른 종속 영향은 상세에 남깁니다.
직접 지적이 없으면 종속 영향의 법조항을 표시합니다. §112/§103 필터도 **카드에 표시된 법조항**을 기준으로 합니다.
예를 들어 재현 OA의 Claim 2는 직접 지적 103(a)로 표시되고, 112 종속 영향은 상세에서 확인할 수 있습니다.

숫자 검색은 정확히 일치하는 번호만 표시합니다. `1`은 Claim 10–19와 일치하지 않습니다.
필터와 검색은 함께 적용되며, 결과가 없으면 빈 상태를 안내합니다.

`PDF에서 보기`는 기존 `review_jump` 경로로 Claim의 첫 근거 페이지를 선택합니다.
PDF의 검색·거절 사유 필터는 전체로 전환하여 선택 Claim이 가려지지 않게 합니다.
청구항 분석으로 돌아오면 선택 Claim과 목록 필터·검색을 유지합니다.
체크리스트는 기존 item ID로 PDF 화면과 상태를 공유하며, 해당 Claim에 연결된 항목만 보여줍니다.
인용문헌은 지적 사유에 연결된 문헌으로 설명하고 새로운 Claim별 개시 판단을 만들지 않습니다.

## 검증

- `uv run pytest -q`: **148 passed**, 29.00초.
- `uv run pytest --cov=backend --cov-report=term-missing`: **148 passed**, backend **92%**, 52.59초.
- `uv run ruff check .`: **All checks passed**.
- `uv run ruff format --check .`: **83 files already formatted**.
- Streamlit 회귀: 필터·정확한 번호 검색·빈 상태, 접힌 처리 정보·상세, PDF 왕복 선택,
  공유 체크리스트, 인용 원문, 이전 metadata 응답 호환성, local/openai/azure 표시를 검사했습니다.
  provider 표시 테스트는 기존 응답을 사용하며 외부 LLM을 호출하지 않습니다.
- 실제 공개 특허의 40–41쪽 fixture와 **재현 OA**로 Edge에서 19개 목록, 5개 인용문헌,
  필터·검색·상세·JSON 다운로드·체크리스트·PDF 이동·900px 화면을 확인했습니다.
- 가상 TXT 문서로 추가 검토 amber 표시, 체크리스트, PDF 검토의 텍스트 원문 이동도 확인했습니다.
- `scripts/browser_pdf_review.py`: 실제 **41쪽 전체 특허 PDF** 업로드로도 모두 통과했습니다.
  OCR 완료 한 줄/접힌 엔진·renderer 정보, Claim 14 → PDF 41쪽 자동 이동,
  기존 Claim 1/14/18 테두리·19개 badge·관계 지도·인용·체크리스트·원본 다운로드를 검사했습니다.
  별도 이미지 전용 Patent/OA fixture의 실제 Tesseract OCR과 직접 지적/종속 영향 표시도 통과했습니다.
- 1366×768 및 900×900 화면 캡처를 확인했습니다. Claim 관계 정보와 상세 버튼이 겹치지 않고,
  좁은 화면에서도 `PDF에서 보기` 버튼에 최소 폭을 확보해 문구를 온전히 표시합니다.

원본 OA 자체를 검증한 것은 아닙니다. OCR·Claim/rejection parser·dependency 계산·citation extraction·
PDF viewer 및 annotation geometry·provider·API 구조는 변경하지 않았습니다.

## 수정 파일

- `frontend/claim_analysis.py` — 추가, 기존 `frontend/legacy_views.py`의 화면 구성을 대체.
- `frontend/app.py` — 새 Claim 목록 화면 연결, 중복 상단 안내/이동 버튼 제거.
- `frontend/styles.css` — 분석 화면에 한정한 간격, 작은 카드·필터·상태 스타일.
- `tests/test_frontend.py` — 기존 화면 테스트를 새 정보 구조와 상태 유지 회귀로 갱신.
- `scripts/browser_claim_analysis_flow.py` — 추가, 실제 Claim 목록 브라우저 회귀.
- `scripts/browser_pdf_review.py`, `scripts/browser_citation_smoke.py`, `scripts/browser_smoke.py` — 새 UI 흐름으로 연결.
- `README.md`, `VALIDATION.md`, 이 문서 — 사용 방법·검증 기록.

화면: [데스크톱](data/outputs/claim-analysis-desktop.png), [900px 화면](data/outputs/claim-analysis-narrow.png).
