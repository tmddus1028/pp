# 제목 없는 청구항 구간 탐지 검증 · 2026-09-15

## 원인과 수정 범위

사용자가 제공한 `pp_ex3.pdf`는 US20220325409A1의 18페이지 텍스트 PDF입니다.
기존 ingestion은 OCR 없이 텍스트를 추출했으나, Claim parser는 제목이 없고 첫 청구항 번호가
본문 시작 1,000자 뒤에 있으면 구간을 식별하지 못했다는 오류를 반환했습니다.
또한 PDF 텍스트에서 Claim 18·19·20이 한 줄로 추출되어 줄 시작 번호만 찾으면 19·20을 놓칩니다.

`backend/patent/claim_parser.py`에만 분석 동작 변경을 적용했습니다.
기존 제목 기반 경로와 제목 없이 청구항만 입력하는 경로를 유지했습니다.
`What is claimed:`도 명시적 제목으로 지원합니다.
OCR, ingestion, 종속관계 계산, OA 분석, API schema, PDF viewer는 변경하지 않았습니다.

## Fallback 확정 조건

기존 제목/청구항 전용 입력으로 구간을 인식하지 못했을 때 다음 조건을 모두 확인합니다.

1. 정규화된 문서 텍스트의 후반 50%에서 시작하는 Claim 1 후보.
2. Claim 1부터 최소 3개 이상, 중복·누락 없이 연속하는 번호.
3. 번호 뒤 `A`, `An`, `The`로 시작하는 문장, 최소 6단어와 문장 마침표.
4. 각 항의 `comprising`, `wherein`, `configured to` 등의 청구항 표현 또는 종속 표현.
5. 적어도 한 항이 `of claim 1`, `according to claim 2` 등으로 앞 번호를 참조.
6. 후보 구간이 하나일 때만 확정. 다음 Abstract/Description/References/Appendix 등 제목에서 종료.

Fallback 번호 경계는 줄 시작뿐 아니라 마침표·세미콜론과 공백 뒤의 번호도 인식합니다.
따라서 `... sapphire. 19. The method ... 20. A thin film ...`을 분리합니다.
원문을 다시 쓰거나 줄바꿈을 삽입하지 않고 원래 문자열의 구간을 잘라 Evidence를 생성합니다.
기존 정규화 텍스트, 페이지 정보와 Evidence `start/end` 계약은 유지됩니다.

## 실제 파일 및 회귀 결과

- 원본의 바이트 사본: [pp_ex3.pdf](tests/fixtures/claim_sections/pp_ex3.pdf).
- SHA-256: `e8d5120002a99f6a36c9835b2cb7e932e2304fe110e1ae1ac681d64964003cf9`.
- 18페이지, OCR 사용 없음, 명시적 Claim 제목 없음.
- **Claim 1~20 모두 추출, 총 20개.** Claim 1은 PDF 17페이지, Claim 16~20은 18페이지.
- Claim 19 → Claim 18, Claim 20 → Claim 1의 기존 종속 파싱 확인.
- 모든 Claim Evidence의 원문 문자열·문자 위치·페이지 일치 확인.
- 기존 제목 5종의 우선 적용, 청구항 전용 TXT, 페이지 경계, 같은 줄 번호, 참고문헌 배제 검증.
- 단일 번호, 두 항만 존재, 번호 누락/중복, 종속 표현 없음, 일반 목록, 문서 전반부 후보,
  둘 이상의 모호한 구간은 fallback으로 확정하지 않음.
- 실제 FastAPI multipart 업로드 성공.
- 실제 Edge에서 원본 사본 업로드 성공, 20개 Claim 카드 확인.
  Claim 1 → PDF 17페이지, Claim 19·20 → PDF 18페이지 이동 및 선택 카드 확인.
- [브라우저 화면](data/outputs/claim-section-pp-ex3.png).

API·브라우저 테스트의 OA는 전송 및 분석 경로 확인용 합성 TXT입니다.
실제 같은 사건의 특허/OA 쌍이나 법률적 분석 정확도를 검증한 것이 아닙니다.
이번 변경은 구간 탐지입니다. 추출 원문에 남은 화학식·공백·하이픈·페이지 머리말을 교정하지 않습니다.
모든 독립항만 있거나 번호가 누락된 제목 없는 문서는 보수적 확정 조건 때문에 여전히 확인이 필요합니다.

## 실행 결과

| 명령 | 결과 |
|---|---|
| `uv run pytest -q` | 205 passed, 84.88초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | 205 passed, backend 92%, 152.79초 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 102 files already formatted |
| `uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_claim_section.py` | PASS |

pytest의 기존 Starlette/httpx·anyio deprecation 경고 2개가 남습니다.
검증 후 수정 코드로 API 서버를 실행 중이며 새 분석부터 적용됩니다.

## 변경 파일

- `backend/patent/claim_parser.py`
- `tests/test_claim_sections.py` — 회귀 테스트 22개
- `tests/fixtures/claim_sections/pp_ex3.pdf`, `README.md`
- `scripts/browser_claim_section.py`
- `README.md`, `VALIDATION.md`, 이 검증 문서

실행 산출물: `data/outputs/claim-section-pp-ex3.png`, 진단용 `pp_ex3_text.txt`, API 로그 및 서버 PID 기록.
