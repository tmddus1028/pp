# 박스형 원문 주석 복구

2026-09-18. 실행 코드 변경은 `frontend/pdf_review_component/review.css` 한 파일이다.

## 원인과 수정

실제 PDF는 기존 `button.annotation.region` 사각 오버레이를 사용하고 있었다.
텍스트 대체 화면은 같은 원문의 구간을 `mark.text-highlight`로 표시하며,
`border:0`과 상태별 배경색 때문에 형광펜 스트립처럼 보였다.
취소 등 별도 배경 규칙이 없는 상태에는 브라우저 기본 mark 배경도 적용됐다.

텍스트 원문의 배경 채움을 제거하고 구간별 2px 사각 테두리, 5px 모서리,
10px/12px 안쪽 여백을 적용했다. 선택 시 같은 상태색으로 안쪽 테두리만 강조한다.
직접 지적 빨강, 종속 영향 노랑, 인용 녹색, 관련 근거 청록, 기타 상태 회색을 사용한다.
원문 구간 경계와 내용, DOM 생성, 클릭/키보드 핸들러는 그대로 유지한다.
PDF의 기존 옅은 배경과 명확한 사각 경계도 그대로다.
기존 전체 화면 테마·업로드 장식·카드 배치는 유지했다.

## 유지 여부

- [x] 실제 PDF의 사각 오버레이 및 원본 좌표 유지
- [x] 텍스트 원문의 형광펜 채움 제거, 박스 경계 적용
- [x] 직접 지적/종속 영향/취소 상태의 색 구분
- [x] 원문 textContent 및 분석 model 불변
- [x] 클릭, Enter, Space 선택 및 카드 동기화
- [x] 한국 PDF↔XML 원문 이동 시 청구항 선택 유지
- [x] 미국/한국 전환 및 기존 네 화면 이동
- [x] review.js, annotation_geometry.js, backend, parser 변경 없음

## 실행 검증

- `uv run python -m pytest tests/test_pdf_review.py tests/test_pdf_margins.py tests/test_pdf_fallback.py tests/test_review_accordion.py tests/test_korean_integration.py -q`: **51 passed**.
- `uv run --project korean_prototype python -X utf8 scripts/browser_annotation_boxes.py`: **PASS**.
  1920/1440/1280/1024px에서 미국 텍스트 예제와 실제 한국 명세서 PDF/통지서 XML을 검사했다.
  텍스트 보존, 박스 폭/테두리/배경, 키보드/마우스 선택, 네 화면 이동을 포함한다.
- 새 브라우저 검사 스크립트 Ruff lint/format: **PASS**.
- `scripts/browser_pdf_review.py`: **부분 통과 후 FAIL**.
  실제 미국 41쪽 PDF의 Claim 1/14/18 사각 영역, 열 경계, 중복 방지,
  accordion, 근거 이동과 선택 유지 검사는 통과했다.
  이후 1366px 화면의 Claim 14/16 번호 배지가 박스 안쪽으로 배치되어
  기존 `check_claim_badges`의 외부 배치 조건에서 중단됐다. 뒤의 검사는 실행되지 않았다.
  수정 전 CSS로 브라우저에서 비교해도 같은 배지 배치가 발생한다.
  기존 CSS와 수정 CSS의 PDF 영역 좌표/인라인 스타일/번호 배지 위치는 모두 일치한다.
  이 기존 배지 배치 문제는 이번 요청에서 변경을 금지한 좌표/배치 로직을 수정하지 않고 남겼다.

전체 기능 무결함을 주장하지 않는다. 이번 변경의 박스 표시 및 관련 동작 검증 결과다.

## 증거

- [화면별 검사 결과](data/outputs/annotation_boxes/checks.json)
- [수정 전후 PDF 좌표·배지 비교](data/outputs/annotation_boxes/pdf_before_after.json)
- [소스 해시 비교](data/outputs/annotation_boxes/functional_diff.json): 기존 파일 133개 불변, review.css만 변경
- [미국 원문 박스](data/outputs/annotation_boxes/text-1440.png)
- [한국 실제 PDF 박스](data/outputs/annotation_boxes/kr-pdf-1440.png)
- [한국 XML 원문 박스](data/outputs/annotation_boxes/kr-xml-1440.png)

변경 파일: `frontend/pdf_review_component/review.css`,
`scripts/browser_annotation_boxes.py`, `ANNOTATION_BOX_VALIDATION.md`.
