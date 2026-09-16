# Claim 전체 영역 테두리 표시

이번 변경은 PDF component의 표시용 geometry와 스타일에 한정합니다.
Backend, OCR, parser, Evidence start/end 및 기존 좌표 adapter는 변경하지 않습니다.

## 병합 방식

1. annotation을 문서 ID·페이지·Claim 번호로 묶고 동일 좌표를 중복 제거합니다.
2. 해당 페이지의 Claim 줄 좌표를 x축에 투영합니다. x 범위가 겹치는 줄들을 같은 열로 묶고,
   열 사이의 비어 있는 구간은 연결하지 않습니다. 화면 필터와 관계없이 전체 Claim 좌표를 사용합니다.
3. 각 열에서 **해당 Claim에 속한 좌표만** `min(x1), min(y1), max(x2), max(y2)`로 합칩니다.
   다른 Claim의 위치는 열을 식별하는 데만 쓰며 Claim 테두리 크기에 포함하지 않습니다.
4. 원문 글자와 테두리가 닿지 않도록 화면상의 3px 여유를 둡니다.
   페이지 또는 열을 넘어가는 Claim은 페이지·열마다 테두리 하나씩 표시합니다.
5. 원본 annotation/boxes는 변경하지 않습니다. 클릭 대상의 item ID와 기존 Review Panel 연결을 유지합니다.
   긴 카드도 선택 시 오른쪽 패널 안에서 제목부터 보이도록 스크롤 위치를 맞춥니다.

직접 지적은 2px의 부드러운 빨간 테두리, 선택 시 3px `#D94343`와
`rgba(217,67,67,0.05)` 배경입니다. 종속 영향도 영역 전체의 amber 테두리를 사용합니다.
인용문헌은 green, 명세서 근거는 teal 테두리와 약한 배경으로 표시합니다.
기존의 진한 fill, multiply blend, 선택 시 줄마다 생기던 테두리를 제거했습니다.
번호 배지는 후속 수정에서 모든 Claim annotation에 표시하도록 통일했습니다.
여백이 좁으면 위치를 조정하고, 필요한 경우 안쪽 상단으로 옮깁니다.
개별 badge를 숨기지 않으며 상세 정책은 [BADGE_VALIDATION.md](BADGE_VALIDATION.md)에 기록했습니다.

## 브라우저 검증

`scripts/browser_pdf_review.py`는 실제 공개 US 2015/0283132 A1 **전체 41쪽**을 업로드합니다.
Office Action은 이전과 동일한 재현 fixture이며 실제 14/623,904 OA 원본을 검증한 것은 아닙니다.

- Claim 1: 40쪽 17개 좌표와 41쪽 5개 좌표를 각각 하나의 테두리로 표시.
- Claim 14: 41쪽의 12개 좌표를 오른쪽 열의 테두리 하나로 표시.
- Claim 18: 41쪽의 12개 좌표를 오른쪽 열의 테두리 하나로 표시.
- 테두리 범위가 해당 Claim의 원래 좌표 최솟값/최댓값과 일치하고 다른 열까지 늘어나지 않는지 확인.
- 동일 annotation을 두 번 전달해도 테두리 중복이 없고 입력 모델이 변하지 않는지 확인.
- 두 열에 걸친 Claim, 좁은 열 간격, 한 단의 긴 줄, 일부 짧은 줄, 좌표 없음의 geometry 회귀 확인.
- 카드 → PDF 및 PDF → 카드, 일반 2px/선택 3px 스타일과 연한 배경, 여러 법조항 표시 확인.
- 기존 페이지/확대/검색/다운로드, 다섯 citation, R1의 종속 영향, 보조 그래프,
  명세서/도면 연결, 좁은 화면 및 실제 OCR 흐름도 실행.

```powershell
uv run --no-project --with playwright --python 3.11 python -X utf8 -u scripts/browser_pdf_review.py
```

화면 캡처: `data/outputs/pdf-review-claim-1-border.png`,
`pdf-review-claim-14-border.png`, `pdf-review-claim-18-border.png`.
최종 실행 결과는 [VALIDATION.md](VALIDATION.md)에 기록합니다.

## 변경 파일

- `frontend/pdf_review_component/annotation_geometry.js` — 추가, 열별 Claim 영역 병합과 중복 제거.
- `frontend/pdf_review_component/index.html` — 로컬 geometry 스크립트 로드.
- `frontend/pdf_review_component/review.js` — 영역 테두리 렌더링과 번호 배지.
- `frontend/pdf_review_component/review.css` — 유형별 테두리, 일반/선택 상태 및 연한 배경.
- `scripts/browser_pdf_review.py` — 실제 Claim 1·14·18 및 geometry/중복/원문 불변 회귀.
- `PDF_REVIEW_VALIDATION.md`, `VALIDATION.md`, 이 문서 — 변경·검증 기록.

복잡한 레이아웃에서 열을 확실히 합칠 수 없으면 별도 영역을 유지합니다.
좌표가 없는 구간은 기존처럼 페이지와 텍스트 근거로 표시하며 테두리를 임의로 생성하지 않습니다.
