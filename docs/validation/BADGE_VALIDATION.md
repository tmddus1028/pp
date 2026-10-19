# Claim 번호 badge 일관성 수정

정책은 **표시 중인 모든 Claim annotation에 badge 표시**입니다.
여백 부족을 이유로 개별 badge를 숨기던 조건을 제거했습니다. 좌표가 없어 annotation 자체가 없는 구간은
기존처럼 페이지·원문 근거로 표시하며, 위치를 새로 추정하지 않습니다.

## 위치와 표시

- 같은 페이지의 badge는 동일한 크기를 사용합니다. 두 자리 번호는 16×12px, 9px 굵은 흰색 글자입니다.
  더 긴 번호가 있으면 그 페이지의 모든 badge 폭을 함께 늘립니다.
- 기본 anchor는 각 Claim bbox의 왼쪽 바깥·상단입니다. 왼쪽/오른쪽 column 모두 같은 함수를 사용합니다.
- 같은 높이의 원문 좌표를 확인해 인접 column과 겹치면 필요한 만큼만 오른쪽으로 조정합니다.
  실제 41쪽의 기본 너비 맞춤에서는 번호 1–19 모두 원문을 가리지 않고 표시됩니다.
- 축소 또는 페이지 가장자리에서 공간이 부족하면 bbox 왼쪽 안쪽 상단으로 옮깁니다.
  이 경우에도 숨기지 않습니다. 매우 작은 축척에서는 작은 badge가 모서리의 원문 일부와 겹칠 수 있습니다.
- 위치는 PDF 페이지 안쪽 1px 안전 영역으로 제한합니다.
- badge를 개별 annotation의 자식에서 별도 `claim-badge-layer`로 이동했습니다.
  이 레이어는 같은 page overlay 안에 있고 z-index 10으로 테두리·검색 표시보다 위에 있습니다.
- 배경은 직접 지적 red, 종속 영향 amber이며 Claim bbox의 배경·테두리·클릭 영역은 변경하지 않습니다.
  badge는 pointer-events를 받지 않아 기존 Claim 클릭을 가로막지 않습니다.

## 확대와 스크롤

원래 normalized bbox에서 현재 page image의 픽셀 좌표를 계산합니다.
기존 `resizePaper()` 경로에서 확대/축소, 너비/페이지 맞춤, 창 크기 변경, 이미지 로드 시 다시 배치합니다.
스크롤은 같은 page container 안에서 이미지·테두리·badge를 함께 이동하므로 별도 좌표 보정이 필요 없습니다.
원본 PDF, backend, OCR, parser, Evidence 좌표, Claim bbox 병합은 변경하지 않습니다.

## 실제 브라우저 검사

실제 공개 US 2015/0283132 A1 전체 41쪽 PDF와 기존 재현 OA PDF를 업로드합니다.
OA 원본 자체를 검증한 것은 아닙니다.

`scripts/browser_badge_flow.py`를 기존 `scripts/browser_pdf_review.py`에서 실행하여 다음을 확인합니다.

- 41쪽 Claim 1–19: badge **19개**, 누락/숨김/중복 없음, 같은 크기와 페이지 내부 위치.
- 오른쪽 Claim 13–19를 포함한 두 column 모두 표시.
- 기본 너비 맞춤에서 원문 좌표와 겹침 없음.
- 확대 2회, 축소, 페이지 맞춤, 너비 맞춤, 최소 축소에서도 19개 유지.
- 스크롤 전후 badge의 페이지 상대좌표 동일.
- Claim 14/19 클릭과 Review Panel 연동, 원본 annotation 객체 불변.
- 기존 관계 지도·PDF 왕복·필터·citation·원본 다운로드·실제 OCR 흐름 유지.

캡처: [41쪽 전체 badge](data/outputs/pdf-review-badges-page41.png).
최종 실행 결과: [VALIDATION.md](VALIDATION.md).

## 수정 파일

- `frontend/pdf_review_component/review.js` — 전부 표시, 안전 위치 계산, 별도 badge 레이어.
- `frontend/pdf_review_component/review.css` — badge 크기/색상/레이어 스타일.
- `scripts/browser_badge_flow.py` — 추가, 실제 41쪽 badge 회귀.
- `scripts/browser_pdf_review.py` — badge 회귀 연결.
- `CLAIM_BORDER_VALIDATION.md`, `VALIDATION.md`, 이 문서 — 정책·검증 기록.
