# 한국 모드 표시 용어 검토 — 2026-09-17

기존 공통 앱의 한국 모드에만 적용한 표시 변경이다. 별도 화면이나 CSS를 만들지 않았다.
`kr-` 분석 식별자는 기존 한국 adapter의 식별 규칙을 사용하며 API schema를 추가하지 않았다.
업로드 전에는 기존 관할 선택값을 사용한다.

## 용어와 적용 범위

| 기존 표시 | 한국 모드 표시 |
|---|---|
| Patent / Claims | 명세서·청구범위 |
| Patent PDF / Patent 원문 | 명세서 PDF / 명세서 원문 |
| Office Action / OA | 의견제출통지서 |
| Claim / Claims | 청구항 |
| 거절 사유 / 지적 사유 / 심사관 지적 | 거절이유 |
| Patent / NPL (문헌 유형) | 특허문헌 / 비특허문헌 |
| specification / drawing / Paragraph / Figure | 명세서 / 도면 / 문단 / 도면 |
| Publication number / Publication・journal / Year | 문헌 번호 / 간행물·학술지 / 발행 연도 |
| 허용 / 취소됨 / 계류 중 (청구항 상태) | 특허 가능 / 삭제됨 / 심사 중 |
| Objection | 추가 지적 |

`특허 가능`을 `특허결정`이나 `등록`으로 표시하지 않는다. `Objection` 표시를 한국 법률상
이의신청이나 거절결정으로 변환하지 않는다. 한국 parser의 지원 상태도 추가하지 않았다.
원문의 인용발명 이름·공개번호는 그대로 표시하며 비특허문헌을 인용발명으로 일괄 변경하지 않는다.

검토 기준: [공식 특허 안내](https://www.kipo.go.kr/ko/kpoContentView.do?menuCd=SCD0200111),
[공식 심사기준의 의견제출통지서 용어](https://www.kipo.go.kr/upload/mobile/exammanual/pdf/exammanual_05_1.pdf).

적용: 문서 업로드(파일/텍스트), 도움말, PDF 검토의 요약·카드·필터·문서 선택·원문 이동,
청구항 분석의 상태 필터·검색·상세·체크리스트, 관계 지도의 노드·검색·범례·상세,
근거 비교의 선택창·원문 카드·문헌 유형·비교 요약. 접근성 이름도 같은 용어를 사용한다.
사용 중인 5개 화면을 조사했으며 호출되지 않는 구형 `graph_component`와 독립 시제품은 수정하지 않았다.

## 데이터와 상태 보호

- `frontend/terminology.py`와 `terminology.js`가 동일한 표시 용어 사전을 사용한다.
- UI가 생성한 라벨만 명시적으로 변환한다. 원문 DOM을 순회해 일괄 번역하지 않는다.
- 원문·OCR·근거·거절 설명·문헌명·파일명·법조항·문헌 번호는 변환하지 않는다.
- 체크리스트는 알려진 생성 문구만 변환하고 삽입된 법조항과 문헌명은 보존한다.
- 필터 내부 값(`허용`, `all`, `citation` 등), 선택 ID, navigation, API 응답은 유지한다.
- 브랜드 Patent Review, 기술 식별자 PDF/XML/OCR, 원문·진단 데이터 안의 영문은 유지한다.
- 이번 작업은 지원 문서 종류를 늘리지 않는다. 한국 OA PDF/OCR 및 미지원 XML은 그대로 미지원이다.

## 검증

`uv run --project korean_prototype python -X utf8 scripts/browser_jurisdiction.py`

- Edge headless, 1440×1000. 실제 출원 10-2019-0000844의 PDF/XML 업로드 통과.
- 청구항 1개, 직접 지적 1개, 종속 영향 0개, 특허 가능 0개, 인용문헌 3개 유지.
- 청구항 PDF 3쪽, XML 근거 이동, 원문 문자열 일치, 선택 유지, 3개 인용문헌 클릭 통과.
- 한국어 라벨·접근성 이름·체크리스트·관계 지도·근거 비교 및 미국→한국→미국 전환 통과.
- 미국 PDF 검토/청구항 분석/관계 지도/근거 비교 4개 화면은 기존 baseline과 구조 및 픽셀 동일.
- 기존 CSS와 annotation geometry 파일 해시 동일. 캡처: `data/outputs/jurisdiction/`.

자동 검증:

- `uv run python -m pytest -q`: **275 passed**, 기존 의존성 deprecation warning 2건.
- 최종 용어 사전 보완 후 `tests/test_terminology.py`: **3 passed**.
- `uv run python -m ruff check .`: 통과.
- `uv run python -m ruff format --check .`: **165 files already formatted**.
- `git diff --check`: 통과.

Azure 실제 호출이나 한국 parser 미지원 문서에 대한 지원 확대는 이번 검증 범위가 아니다.

## 이번 변경 파일

- `frontend/terminology.py`, `frontend/terminology.js` (신규 공통 표시 용어)
- `frontend/app.py`, `frontend/claim_analysis.py`, `frontend/evidence_comparison.py`
- `frontend/pdf_review.py`, `frontend/pdf_review_component/review.js`, `frontend/pdf_review_component/index.html`
- `frontend/relationship_map.py`, `frontend/relationship_map_component/map.js`, `frontend/relationship_map_component/index.html`
- `tests/test_terminology.py`, `tests/test_korean_integration.py`
- `scripts/browser_jurisdiction.py`, `scripts/browser_korean_downloads.py` (한국 표시명에 맞춘 검증)
- `korean_prototype/README.md`, 이 문서

작업 시작 전 존재하던 backend/통합/다운로드 변경은 이번 용어 작업에서 수정하지 않았다.
