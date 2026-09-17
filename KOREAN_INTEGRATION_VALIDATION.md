# 미국 / 한국 모드 통합 검증

검증일: 2026-09-17. 기존 8000 API / 8501 Streamlit 앱에 한국 모드를 추가했다.

## 변경 범위

- `frontend/app.py`: 업로드 화면에 미국/한국 선택 하나를 추가했다. 미국이 기본값이다.
  한국 선택 시 기존 업로드 위젯이 PDF/TXT + XML을 받으며 기존 버튼으로 분석한다.
  입력 위젯 키를 관할별로 구분하고 모드 변경 시 이전 결과·PDF를 해제한다.
  분석 성공 시 기존 초기화 경로를 그대로 사용한다.
- `backend/main.py`: 기존 두 분석 endpoint에 선택적 query `jurisdiction=US|KR`을 추가했다.
  생략 시 기존 미국 경로다. 한국 오류는 기존 형태의 422 응답으로 반환한다.
- `backend/jurisdictions/__init__.py`, `backend/jurisdictions/korean.py`: 기존 한국 시제품의
  추출 결과를 기존 `AnalysisResult`에 매핑한다. 한국어를 영어 parser에 넣지 않는다.
  공통 종속 영향·체크리스트·그래프·요약 생성 함수를 그대로 재사용한다.
- `data/raw/kr_demo_patent.txt`, `data/raw/kr_demo_office_action.xml`: 기존 가상 예제 버튼용
  한국 합성 문서다. 실제 심사 문서가 아님을 본문에도 명시한다.
- `tests/test_korean_integration.py`: 통합 회귀 테스트 9개.
- `scripts/browser_jurisdiction.py`: 미국 화면 전후 비교 및 한국 실제 문서 브라우저 검증.
- `README.md`, `korean_prototype/README.md`, 이 문서: 공통 앱 진입점·범위·검증 안내.

기존 `backend/schemas.py`, 미국 parser/OCR/분석 모듈과 한국 시제품의 parser는 수정하지 않았다.
기존 PDF 검토·청구항 분석·관계 지도·근거 비교 컴포넌트 및 모든 CSS/JS/HTML도 수정하지 않았다.
한국 전용 페이지·사이드바는 만들지 않았다. 기존 독립 시제품 파일은 보존한다.

## 데이터 및 API 확인

실제 출원 `10-2019-0000844`의 공개공보와 의견제출통지서 XML을 사용했다.
테스트에서 기존 manifest의 5개 문서 해시를 먼저 검사한다.

| 항목 | 결과 |
|---|---|
| 청구항 / 직접 지적 / 종속 영향 | 1 / 1 / 0 |
| 거절 사유 | 특허법 제29조제2항 1개 |
| 인용발명 / 그래프 citation 노드 | 3 / 3 |
| 청구항 PDF 근거 | 실제 3쪽, 좌표와 하이라이트 확인 |
| 문서·청구항·거절 설명 | 기존 한국 추출 결과와 동일한 텍스트 |
| Evidence start/end | 해당 문서 텍스트 slice와 일치 |
| 미국 API 기본값 / 명시적 US | TXT JSON 요청 및 multipart 응답 완전 동일 |
| 합성 한국 종속항 | 청구항 1 직접 지적, 청구항 2 종속 영향 |
| 잘못된 XML·DTD·지원하지 않는 관할·문자수 제한 | 오류 응답 확인 |

OA XML에는 실제 PDF 페이지 정보가 없다. 기존 TXT 입력과 같은 논리 페이지 1개를 사용하고
기존 텍스트 뷰어에서 근거를 강조한다. 이는 실제 OA PDF의 p.1을 뜻하지 않는다.
원문을 PDF로 재작성하지 않으며 이 구분은 문서 warnings 및 README에 기록했다.
XML 원본의 요소 경로는 독립 시제품에 남아 있고 공통 모델에서는 문서 ID·문자 위치로 연결한다.

## 브라우저 검증

Microsoft Edge, 1440 × 1000에서 통합 전후 동일 미국 가상 예제를 캡처했다.

- PDF 검토, 청구항 분석, 관계 지도, 근거 비교 **4개 화면의 이미지 픽셀 차이 없음**.
- 사이드바·제목·버튼·요약·비교 카드 위치/크기 동일.
- `frontend/app.py` 이외 기존 frontend 컴포넌트와 CSS/JS/HTML 해시 동일.
- 한국 실제 PDF/XML 업로드 후 기존 네 화면 모두 렌더링.
- 최초 Claim 접힘 → 선택 → 실제 PDF 3쪽 강조 → XML 거절 근거 이동.
- 근거 이동 중 Claim 유지 및 R1 최상위 카드 미생성 확인.
- 인용문헌 필터 3개, citation 클릭 시 XML 원문 이동, 요약 수치 유지.
- 청구항 분석 → PDF, 관계 지도 → 근거 비교, 근거 비교 → OA 이동 확인.
- 미국 → 한국 → 미국 전환 시 이전 데이터 미노출 및 새 분석 선택 상태 초기화.
- 브라우저 pageerror 없음.

추가로 기존 `scripts/browser_evidence_comparison.py`를 그대로 실행했다.
US20150283132A1의 청구항 40–41쪽 추출본과 재구성 OA fixture에서 Claim 14,
두 거절 근거, 특허/NPL 5개, R1 종속 영향, PDF/OA 이동, 관계 지도 연동,
좁은 화면 배치 및 기존 annotation 유지가 통과했다. 별도 합성 fixture의 명세서 문단·도면
명시적 연결도 통과했다. 이 브라우저 검사는 전체 실제 OA 검증으로 표현하지 않는다.

캡처·비교 기준: `data/outputs/jurisdiction/baseline.json`, `us-before-*.png`,
`us-after-*.png`, `kr-*.png`. 이 경로는 기존 정책에 따라 Git 추적 대상이 아니다.

## 실행 결과

| 검사 | 결과 |
|---|---|
| `uv run python -m pytest -q` | 272 passed |
| `uv run python -m pytest --cov=backend --cov-report=term-missing` | 272 passed, backend 93% |
| 한국 시제품 폴더의 `uv run python -m pytest -q` | 56 passed |
| `uv run python -m ruff check .` | PASS |
| `uv run python -m ruff format --check .` | PASS |
| `git diff --check` | PASS |
| 새 통합 브라우저 검사 / 기존 근거 비교 브라우저 검사 | PASS / PASS |

pytest에는 FastAPI/Starlette 의존성의 기존 deprecation warning 2개가 있다.
coverage는 줄 실행률이며 모든 분기·기능의 완전한 검증을 의미하지 않는다.

브라우저 재현(기존 앱 8000/8501 실행 필요):

```powershell
uv run --project korean_prototype python scripts/browser_jurisdiction.py
uv run --project korean_prototype python scripts/browser_evidence_comparison.py
```

브라우저 스크립트는 한국 시제품 개발 환경에 설치된 Playwright/Edge를 사용한다.
전후 비교의 `--baseline`은 통합 전 코드에서 이미 실행했다. 수정 후 baseline을 재생성해
과거 화면 비교라고 주장하지 않는다. 캡처 파일을 보관해야 전후 비교를 재현할 수 있다.

## 범위 밖 / 미검증

- 통합 한국 모드는 로컬 추출이다. 독립 시제품 Azure 검토 호출 UI를 새로 추가하지 않았다.
  실제 Azure 서비스 호출·응답 품질은 이번 작업에서 검증하지 않았다.
- 한국 OA PDF·한국어 스캔 OCR·새로운 XML 구조는 이번 통합의 지원 범위 밖이다.
- 인용문헌은 기존 화면 정책대로 OA의 인용 위치로 이동한다. 별도 인용발명 PDF 입력 UI는 없다.
- 한국 실제 사례는 1쌍이다. 다른 한국 사건에 대한 일반화 성능을 주장하지 않는다.
- 픽셀 비교는 명시한 환경·예제의 네 화면이다. 모든 viewport·브라우저의 동일성을 주장하지 않는다.
