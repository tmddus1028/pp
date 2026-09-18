# 공통 정렬·간격 검증

2026-09-18. 현재 테마와 기존 동작을 유지하면서 표시 구조와 CSS만 수정했다.

## 발견한 문제와 원인

| 영역 | 확인한 문제 | 조치 |
|---|---|---|
| 업로드 | 숫자의 장식선까지 포함한 flex 중심과 제목 baseline이 다름 | 공통 3열·2행 grid의 첫 baseline에 숫자/제목 배치 |
| 업로드 설명문 | 별도 caption과 `margin-top: -4px`, Streamlit caption/Markdown의 음수 여백이 겹침 | 제목 아래 동일한 grid 행으로 배치, 여백을 공통 토큰으로 지정 |
| 아이콘/구분선 | 아이콘의 자동 좌측 margin, 제목 블록의 높이에 의존한 구분선 | 고정 icon slot과 최소 120px header, header 하단 border |
| 카드 높이 | 선택 인용발명 accordion이 있는 오른쪽 카드만 길어짐 | 부모 column과 wrapper를 stretch하여 두 카드가 함께 늘어나도록 수정 |
| 국가/입력 방식 | 가상 label과 native label의 높이·아래 여백이 다름 | 24px label 높이, 8px 간격으로 통일 |
| 사이드바 | 설정/도움말 버튼의 내부 flex가 가운데 정렬, 로고·caption의 서로 다른 여백 | 공통 inset, 고정 메뉴 icon 폭, 버튼 내부 좌측 정렬 |
| PDF 검토 | 카드 번호의 padding-top, 도구모음 버튼/입력의 서로 다른 높이 | 번호 flex 중앙 정렬, toolbar control 최소 32px 높이 |
| 청구항 분석 | 카드/summary의 제각각 padding, badge의 inline 기준선 | 공통 card padding과 badge 가운데 정렬 |
| 관계 지도 | toolbar/detail heading·caption 간격과 패널 여백이 다름 | 공통 heading line-height와 16px 패널 padding |
| 근거 비교 | 의미색 상단 border 3px와 일반 border 1px 차이, 제목 margin, 높이 전달이 안 되는 wrapper | 상단 border 두께·48px heading·간격 통일, 같은 행의 카드 높이 stretch |

## 공통 규칙

- spacing: `--space-1`~`--space-8` = **4 / 8 / 12 / 16 / 24 / 32 / 40 / 48px**.
- 페이지 gutter 32px, 작은 화면 24/16px. 검토 카드 padding 16px,
  업로드 카드 padding 32px, 작은 화면 24/16px.
- 업로드 header: **72px / minmax(0, 1fr) / 56px** 공통 grid.
  1280px 이하에서는 **48px / minmax(0, 1fr) / 32px**.
- 숫자/제목은 첫 baseline 공유. 설명문은 다음 행, 행 간격 8px.
  아이콘은 공통 slot의 중앙에 위치하며 두 카드의 좌표가 동일하다.
- heading line-height 1.25, subtitle 1.5, 숫자 1. 원문 본문 기존 1.6은 유지.
- 긴 내용이나 펼친 accordion은 카드 높이를 자연스럽게 늘린다. 고정 높이로
  내용을 자르지 않는다. 기존 responsive stack도 유지한다.

## 제거한 임시 보정

- 업로드 caption의 `margin-top: -4px`.
- 숨겨진 native 제목의 `position: absolute`, `margin: -1px`, 1px 폭.
- 숫자 아래 장식선 때문에 발생하던 추가 높이와 아이콘의 `margin-left: auto`.
- 좁은 화면에서 로고에만 별도로 적용하던 5px inset.

접근성 및 기존 native heading/caption 계약을 유지하기 위한 중복 요소만
일반 흐름의 높이 0 영역에 시각적으로 숨긴다. 실제 보이는 제목/설명문은
숨김·absolute·음수 margin을 사용하지 않는다. 장식 SVG의 absolute 배치는 유지했다.

## 수정 파일

- `frontend/styles/patent_theme.css`: 모든 공통 정렬·간격·반응형 규칙.
- `frontend/visual_theme.py`: 공통 `upload_header(label, subtitle)` markup.
- `frontend/app.py`: 기존 문구를 공통 header의 subtitle 인자로 전달.
- `scripts/browser_alignment.py` (신규): 브라우저 실제 좌표·baseline 검사.
- `ALIGNMENT_VALIDATION.md` (신규): 이 기록.

## 해상도별 검사

미국/한국 모드 각각 검사. 아래 항목은 카드 간 허용 오차 1px 기준이며,
최종 업로드 카드 쌍의 측정 차이는 모두 **0px**였다.

| 검사 | 1920×1080 | 1440×900 | 1280×800 | 1024×768 |
|---|---|---|---|---|
| 숫자 top 및 숫자↔제목 baseline | PASS | PASS | PASS | PASS |
| 제목/설명문 baseline | PASS | PASS | PASS | PASS |
| 아이콘 중심/구분선 | PASS | PASS | PASS | PASS |
| 업로드 top/높이/버튼/안내문 | PASS | PASS | PASS | PASS |
| 카드 top/bottom | PASS | PASS | PASS | PASS |
| radio/하단 버튼/페이지 좌측 기준선 | PASS | PASS | PASS | PASS |
| 사이드바 넘침/메뉴 텍스트 좌측 정렬 | PASS | PASS | PASS | PASS |
| PDF 도구모음 컨트롤 중심 | PASS | PASS | PASS | PASS |
| 청구항 summary 숫자 정렬 | PASS | PASS | PASS | PASS |
| 지도 toolbar 버튼 중심 | PASS | PASS | PASS | PASS |
| 근거 비교 header 및 카드 하단 | PASS | PASS | PASS | PASS |

600px stack 화면도 추가 검사했다. 업로드 header 제목·원문 영역의 가로 넘침 없음.
한국 인용발명 accordion을 펼친 상태에서도 두 카드 하단 일치.
최종 캡처는 업로드 8장, 검토 화면 16장, stack 1장으로 총 25장이다.

## 기능 회귀와 변경 범위 증거

- 루트 전체 테스트: **384 PASS**.
- 독립 한국 시제품 전체 테스트: **56 PASS**.
- Ruff check / format: 수정 Python 파일 및 신규 검사 스크립트 **PASS**.
- `browser_alignment.py`: **PASS**, 24개 viewport 검사 + stack.
- `browser_readable_text.py`: **PASS**, 4개 화면/4개 폭에서 원문 자연스러운 줄바꿈,
  원문·모델·선택 상태 유지.
- `browser_review_scope.py`: **PASS**, ALL 19/0, R1 15/4 (2·5·8·11), R2 19/0.
- `browser_kr_parity.py`: **PASS**, 실제 한국 PDF·인용발명 업로드, 거절 범위,
  선택, 원문 이동, 공통 화면 흐름.
- `browser_revisions.py`: 최종 **PASS**, 개선안 생성·수정본 검증 흐름.
  외부 AI 대신 HTTP 모의 응답을 사용했다. 실제 모델 출력 품질은 이 검사의 대상이 아니다.
  첫 실행의 폭 검사 1회 실패 후 같은 기대값으로 진단/재실행했고, 진단에서는 324px,
  최종 기존 스크립트 실행에서는 모두 통과했다.

작업 시작 시점의 128개 파일을 비교했다. 변경 파일은 위 frontend 3개뿐이며
나머지 **125개 파일 해시가 일치**한다. backend/parser/API/JS 이벤트 및 기존 테스트는
변경하지 않았다. app의 장식 Markdown 호출을 제외한 전체 AST가 동일하며,
**14개 interactive widget 호출의 인자/key/callback도 동일**하다.
기존 작업의 수정 사항은 그대로 보존했다.

## 결과 파일

- [정렬 측정 결과](data/outputs/alignment/browser.json)
- [기능 diff 검사](data/outputs/alignment/functional_diff.json)
- [변경 전 업로드](data/outputs/alignment/before-upload.png)
- [변경 후 한국 업로드 1440px](data/outputs/alignment/upload-kr-1440.png)
- [한국 업로드 1024px](data/outputs/alignment/upload-kr-1024.png)
- [근거 비교 1440px](data/outputs/alignment/근거%20비교-1440.png)

공통 앱 `http://127.0.0.1:8501`에 적용했다.
