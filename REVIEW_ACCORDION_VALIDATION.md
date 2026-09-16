# PDF Review Panel · 기본 접힘 및 단일 accordion

## 상태 관리

- 기존 `review_ui.selected`는 PDF에서 선택·강조할 항목입니다.
- 새 `review_ui.expanded`는 상세를 펼칠 항목 하나의 ID 또는 `None`입니다.
- 분석 결과 최초 진입과 일반 메뉴 재진입에서 둘 다 `None`으로 초기화합니다.
  Python의 `selected_claim`도 `None`으로 맞춥니다. 첫 Claim 위치가 있는 페이지는 표시하되 자동 선택하지 않습니다.
- 카드 헤더 클릭: 선택 항목의 PDF 위치로 이동하면서 닫혀 있던 카드는 열고, 열린 카드는 닫습니다.
  다른 카드는 자동으로 닫힙니다. 카드가 접혀도 PDF 선택·강조는 유지됩니다.
- PDF annotation 클릭: 해당 카드만 선택하고 펼칩니다. PDF에서 같은 Claim을 다시 클릭해도 열린 상태를 유지합니다.
- 필터 결과의 첫 항목을 자동으로 펼치지 않습니다. 기존 선택이 필터에서 제외되면 선택과 펼침을 해제합니다.
- 다른 화면에서 사용자가 `PDF에서 보기`를 명시적으로 누르면 그 항목 하나만 펼칩니다.
- 재진입 이전에 만들어진 늦은 이벤트가 카드를 다시 열지 않도록 frontend의 navigation 번호를 확인합니다.
- 체크리스트·문서·좌표 캐시는 재진입 시 유지하며, 펼침 때문에 OCR이나 분석을 다시 실행하지 않습니다.

## 상세 및 디자인

기존 상세 생성 함수를 재사용하여 분석 설명, Claim 원문, OA 원문 근거, 종속 관계,
관련 citation, 명시적 명세서·도면 근거, 체크리스트를 유지합니다.
Claim 번호·상태·법조항은 접힌 카드에도 보이고, 오른쪽 화살표와 `aria-expanded`로 펼침 여부를 표시합니다.
카드 번호는 필터 내 순번 대신 실제 Claim 번호를 사용합니다.
클릭과 Enter/Space를 지원하며, 상세 안의 `PDF에서 보기` 버튼으로 원문 위치를 다시 확인할 수 있습니다.
선택된 항목이 없는 상태에서도 `전체 관계 지도 보기`는 작동합니다.

## 검증

실제 공개 특허 US 2015/0283132 A1과 기존 **재현 OA**를 사용합니다. 사용자의 원본 OA를 검증한 것은 아닙니다.

- 최초 진입: `selected = null`, `expanded = null`, 열린 카드·선택 annotation 없음.
- Claim 7 클릭: 상세 한 개만 표시.
- Claim 14 클릭: Claim 7 닫힘, Claim 14만 열림, 해당 PDF 위치와 bbox 강조.
- Claim 14 재클릭: 상세 없음, 선택된 bbox는 유지.
- PDF에서 Claim 14 클릭: 해당 카드만 다시 열림.
- Enter/Space로 접기/펼치기, 체크리스트 값 유지.
- 필터 변경: 첫 카드를 자동으로 펼치지 않음.
- 청구항 분석 → PDF 검토 및 관계 지도 → PDF 검토 일반 메뉴 복귀: 다시 모두 접힘.
- 분석 model 및 원래 annotation geometry는 변경되지 않음.

자동화: `scripts/browser_accordion_flow.py`를 실제 PDF 브라우저 검사에 연결했습니다.
`scripts/browser_pdf_review.py`의 전체 Edge 검사가 통과했습니다. 실제 41쪽 PDF의 Claim 7/14,
기존 Claim 1/14/18 테두리, 19개 badge, 관계 지도, 5개 citation, 목록·체크리스트·다운로드,
명세서/도면 및 실제 Tesseract 스캔 PDF 흐름을 확인했습니다.
전체 pytest **152 passed**, backend coverage **92%**, Ruff 검사와 포맷 검사 모두 통과했습니다.
Streamlit 회귀 4개로 초기 상태, 재진입 및 늦은 이벤트 무시, 명시적 PDF 링크,
선택 없는 관계 지도 이동을 검사합니다. 최종 명령 결과는 [VALIDATION.md](VALIDATION.md)에 기록합니다.

화면: [처음 진입](data/outputs/review-accordion-initial.png), [Claim 14 상세](data/outputs/review-accordion-claim14.png).

## 수정 파일

- `frontend/pdf_review.py` — 초기화·명시적 이동·이벤트 상태 동기화.
- `frontend/app.py` — PDF 검토/근거 비교 재진입 감지.
- `frontend/pdf_review_component/review.js` — 단일 accordion 및 PDF 선택 연동.
- `frontend/pdf_review_component/review.css` — 작은 카드 헤더·화살표·키보드 포커스.
- `tests/test_review_accordion.py` — 추가, 상태 전환 회귀 4개.
- `tests/test_relationship_map.py` — 내부 UI 이벤트의 navigation 번호 반영.
- `scripts/browser_accordion_flow.py` — 추가, 실제 Claim 7/14 브라우저 검사.
- `scripts/browser_pdf_review.py`, `scripts/browser_citation_smoke.py` — 새 accordion 흐름 연결.
- `README.md`, `VALIDATION.md`, 이 문서 — 사용 방법과 검증 기록.

Backend, Claim/rejection parser, dependency 계산, citation extraction, OCR, provider,
API 응답과 PDF annotation bbox 계산은 변경하지 않았습니다.
실행 중이던 UI가 이전 Python 함수를 캐시하고 있어 UI 서버만 재시작했으며 서버 프로세스 기록을 갱신했습니다.
