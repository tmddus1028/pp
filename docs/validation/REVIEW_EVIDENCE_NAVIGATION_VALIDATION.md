# Claim 선택을 유지하는 Office Action 근거 이동

## 원인과 수정

기존 `selectItem('rejection-R1')`은 `selected`와 `expanded`를 rejection으로 덮어썼다.
`drawPanel()`은 선택된 rejection을 `points.unshift(selected)`로 목록 맨 앞에 삽입했다.
이 때문에 Claim 1에서 OA 근거를 볼 때 R1이 별도의 최상위 카드로 나타났다.

이제 PDF에서 보는 근거를 Claim 카드 선택과 분리한다.

| UI state | 역할 |
|---|---|
| `selected` | 검토 카드 선택. Claim 근거 이동 시 `claim-1` 등을 유지 |
| `expanded` | 펼친 카드. 근거 이동으로 변경하지 않음 |
| `document`, `page` | PDF 문서와 현재 페이지 |
| `viewer_evidence` | PDF에서 강조·스크롤할 기존 item ID (`rejection-R1` 등) |
| `active_rejection` | Claim 상세에서 현재 확인 중인 rejection ID (`R1` 등) |

기존 카드 ID와 원문 근거 ID를 재사용하며 분석/API schema에 필드를 추가하지 않았다.
rejection을 임시 최상위 카드로 넣는 렌더링 조건은 제거했다.
기존 Claim·citation·specification 목록과 필터는 유지하며, 근거 이동으로 필터를 변경하지 않는다.
직접 지적 필터 상태에서도 선택된 OA 근거는 PDF에서 표시하고 강조한다.

Claim 내부에 ‘현재 보고 있는 근거’, R1/R2·법조항·OA 페이지를 표시한다.
현재 근거의 원문 details를 열고, 다른 근거 이동과 청구항 원문 복귀 버튼을 제공한다.
다른 Claim을 명시적으로 선택하면 Claim 선택과 PDF 위치를 함께 변경하고 현재 rejection을 비운다.
일반 메뉴 재진입은 기존대로 모든 카드와 근거 선택을 초기화한다.

근거 비교 화면에서 OA로 이동할 때도 기존 선택 Claim을 전달한다.
Claim 맥락이 없는 단독 rejection 이동에서는 임의의 Claim을 선택하거나 펼치지 않는다.

## 검증 범위

- AppTest: OA 이동 상태의 서버 저장·재실행 유지, 메뉴 재진입 초기화, 단독 rejection 이동,
  근거 비교 → OA/PDF 이동 시 Claim 14 유지.
- Edge: Claim 1 선택 → R1 → R2 → OA 영역 재클릭 → 확대 → 청구항 원문 복귀 → Claim 3 선택.
- 직접 지적 필터에서는 Claim 1~19 목록 그대로, 전체 필터에서는 기존 전체 목록 그대로 유지.
- 근거 이동 전후 목록 ID·순서 일치, rejection 카드 없음, PDF 페이지·강조와 Claim accordion 유지.
- 표시용 model과 annotation 원본의 불변성 확인.

별도 브라우저 검사는 실제 공개 특허의 40~41쪽 발췌 PDF와 **재현 OA**를 사용한다.
재현 OA 앞에 빈 표지 두 쪽을 추가하여 R1 p.3 / R2 p.4 이동을 검사한다.
사용자 원본 Office Action 자체를 검증한 것은 아니다.

```powershell
uv run --no-project --with playwright --with pypdf --python 3.11 python -X utf8 scripts/browser_claim_evidence_flow.py
```

전체 PDF 회귀에도 같은 검사를 연결했다. 이 경우 실제 특허 전체 41쪽과 기존 재현 OA p.1/p.2를 사용한다.

```powershell
uv run --no-project --with playwright --python 3.11 python -X utf8 -u scripts/browser_pdf_review.py
```

## 실행 결과 · 2026-09-15

| 검사 | 결과 |
|---|---|
| `uv run pytest -q` | 163 passed, 2 dependency deprecation warnings, 43.96초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | 163 passed, backend 92%, 88.41초 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 92 files already formatted |
| 별도 Edge 근거 이동 검사 | 통과, R1 p.3 / R2 p.4 |
| 전체 41쪽 PDF Edge 회귀 | 통과, accordion·Claim 1/14/18 bbox·badge 19개·지도·비교·OCR 포함 |

[Claim 1을 유지한 OA 근거 화면](data/outputs/claim1-oa-evidence.png).
전체 회귀가 마지막으로 저장한 캡처는 기존 재현 OA의 R2 p.2를 표시한다.

## 수정 파일

- `frontend/pdf_review_component/review.js`: Claim/근거 상태 분리, 임시 rejection 카드 제거, 내부 근거 표시.
- `frontend/pdf_review_component/review.css`: Claim 내부 현재 근거 표시 스타일.
- `frontend/pdf_review.py`: 근거 선택 상태 저장·초기화, 외부 OA 이동 시 Claim 맥락 유지.
- `tests/test_review_accordion.py`: 상태 지속 및 초기화 회귀.
- `tests/test_evidence_comparison.py`: Claim 선택과 PDF 근거 선택을 별도로 검증.
- `scripts/browser_claim_evidence_flow.py`: 추가, 실제 Edge의 근거 이동 회귀.
- `scripts/browser_pdf_review.py`: 기존 전체 PDF 회귀에 새 검사 연결.
- `README.md`, `VALIDATION.md`, 이 문서: 동작 및 검증 기록.

분석·OCR·parser·Evidence 계산·좌표 aggregation·graph·provider/API는 변경하지 않았다.
UI 서버만 재시작했으며 `data/outputs/server-processes.json`의 실행 PID를 갱신했다.
