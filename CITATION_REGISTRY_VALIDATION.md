# 인용문헌 고유 목록·거절별 역할 검증 · 2026-09-15

## 실제 파일 결과

실제 `pp_ex3.pdf` / `pp_vd3.pdf`를 다시 multipart 업로드하여 검사했습니다.
OA는 출원 **17/708,932**이며, 이전 상태 검증의 실제 PDF fixture를 그대로 사용했습니다.
원본 PDF를 수정하거나 합성 OA로 대체하지 않았습니다.

| 문헌 역할 | 고유 문헌 | 개수 |
|---|---|---:|
| relied_upon | Liu, Donmez, Bakke, Huang, Yao, Nakayama, Motamedi | **7** |
| supporting_evidence | Wei | **1** |
| not_relied_upon | Oda, Biyikli | **2** |

UI의 **인용 문헌 = 7**, **보조 증거 = 1**, **기록 문헌 = 2**입니다.
전체 문헌 레지스트리는 10개지만 거절 인용문헌 숫자에 Wei·Oda·Biyikli를 포함하지 않습니다.
거절용 7개 중 Nakayama는 특허문헌, 나머지 6개는 NPL입니다.
원문에 없는 DOI, kind code, 공동저자 전체 명단을 추정해 채우지 않았습니다.

| 거절/지적 | 대상 Claim | relied_upon | supporting_evidence |
|---|---|---|---|
| R1 · §103 | 1~4, 6, 8, 17~19 | Liu, Donmez | 없음 |
| R2 · §103 | 5, 6 | Liu, Donmez, Bakke | 없음 |
| R3 · §103 | 7, 9 | Liu, Donmez, Huang | 없음 |
| R4 · §103 | 10, 11 | Liu, Donmez, Yao, Nakayama | Wei |
| R5 · §103 | 12~14 | Liu, Donmez, Yao, Nakayama, Motamedi | Wei |
| R6 · Objection | 15, 16 | 없음 | 없음 |

Liu 카드/문헌은 **1개**이며 R1~R5를 연결합니다.
문헌별 Claim은 연결된 거절의 대상 번호 합집합입니다. Bakke → 5·6, Huang → 7·9,
Motamedi → 12·13·14입니다. 동일 번호를 중복 표시하지 않습니다.

## 중복·누락 원인

- 서지정보가 부족한 문헌의 기존 ID는 OA 거절 구간의 시작 위치를 포함했습니다.
  따라서 제목을 얻지 못한 Liu가 R1~R5에서 각각 다른 ID로 생성됐습니다.
- NPL 추출은 일부 표기·대문자·길이에 의존했습니다. Liu의 제목은 PDF 페이지를 넘고
  중간에 페이지 머리말이 있어 정상적인 서지정보로 인식하지 못했습니다.
- `(Liu)`, `(Donmez)` 같은 재인용을 완전한 서지정보와 연결하지 못했고,
  자유형 NPL 패턴이 다음 저자의 제목/연도를 끌어오는 경우도 있었습니다.
- 뒤따르는 `and Bakke`, `Yao`, `Nakayama`, 단일 저자 `Motamedi`와 보조 문헌 `Wei`를
  온전히 추출할 수 없어 이름 기반 UI 중복 제거만으로는 해결할 수 없었습니다.

## 추출·identity·관계 구조

`bibliography.py`는 공백을 한 칸으로 보는 검색용 문자열과 원문 문자 위치 매핑을 만듭니다.
괄호 깊이를 추적하여 `(Invited)`나 화학식처럼 내부 괄호가 있는 서지정보도 처리합니다.
각 Evidence는 변형되지 않은 `documents[].text`의 연속된 구간과 페이지를 사용합니다.
제목 정규화에서만 명확한 Application/Control Number·Page·Art Unit 머리말을 제외합니다.
원문 Evidence에는 머리말과 OCR 표기, `Motadeni` 등의 원래 철자가 그대로 남습니다.

canonical key의 우선순위:

1. `publication:` + 정규화된 공개/특허 번호.
   공백·구두점 차이와 kind code 생략은 같은 문헌으로 연결합니다.
   예: `US 2004/0188693`, `US20040188693`, `US 2004/0188693 A1` → `publication:US20040188693`.
   동일 번호의 A1과 A2가 **둘 다 명시**되면 서로 다른 문헌으로 보존하고, 생략된 kind를 임의 추정하지 않습니다.
2. `doi:` + 소문자 정규화된 DOI. URL prefix와 끝 구두점 차이를 정리합니다.
3. `title:` + 정규화된 선두 저자 표기 + 제목.
4. `bibliography:` + 정규화된 저자 + publication/year/서지 locator.
5. 식별 정보가 부족하면 원문 위치를 포함한 unresolved key를 유지합니다.
   같은 저자라는 이유만으로 다른 문헌을 합치지 않습니다.

저자 key는 `et al.`, 쉼표·마침표·공백·대소문자 차이를 정리합니다.
`Liu et al.`, `Liu et al`, `LIU ET AL.`, `Liu, et al.`은 동일한 저자 key입니다.
`(Liu)` 같은 명시적 alias는 **이 OA에서 해당 저자의 완전한 서지가 하나일 때만** 연결합니다.
동명이인의 문헌이 2개면 alias를 어느 쪽으로도 강제 연결하지 않습니다.

추가 출력:

- `citations[]`: 고유 `CitationDocument`. ID, canonical_key, 표시명, 저자 표기, 제목,
  publication number, DOI, journal/year, 문헌 유형, 역할 목록, 정의 원문 근거.
- `rejection_citations[]`: rejection ID, citation ID, **그 연결의 역할**, 원문 Evidence, 대상 Claim.
  not_relied_upon 기록은 rejection ID가 `null`이고 대상 Claim도 없습니다.
- 역할이 다른 거절에서 같은 문헌을 사용하는 경우 문헌은 하나이고 관계의 역할만 다릅니다.
- 기존 `rejections[].cited_references`는 API 호환용 참조 목록으로 유지합니다.
  각 목록은 동일한 canonical ID를 참조하며, 같은 거절·같은 역할의 중복은 제거합니다.
  이것을 별도 문헌 객체로 렌더링하지 않습니다. 원문 출현 위치들은 관계 목록에 보존합니다.

이 사례의 관계 레코드는 총 21개: relied_upon 17개, supporting_evidence 2개,
거절에 연결하지 않는 기록 문헌 원문 2개입니다.
관계 그래프는 거절 관련 문헌 노드 8개(7+1)와 역할이 있는 cites edge를 표시합니다.
Oda·Biyikli를 R6 또는 다른 거절 아래에 연결하지 않습니다.

`over`, `in view of`, 뒤따르는 문헌 목록은 relied_upon으로,
`is presented as evidence of`와 `as evidenced by`는 supporting_evidence로 분류합니다.
`not relied upon` 구간의 서지정보는 별도 기록 문헌으로 추출합니다.
일반 설명의 저자 이름만으로 문헌을 생성하지 않습니다.

## UI 및 브라우저 확인

- 고유 문헌당 top-level 카드 1개, 접힌 카드에도 R1~R5 badge 표시.
- 상세에는 제목·서지정보·역할·연결 거절·대상 Claim·각 거절에서의 인용 원문을 표시.
- Liu의 R2 인용 원문 보기 → **OA PDF 5페이지**로 이동, Liu 카드 선택·펼침 유지.
- 인용 문헌 필터 → 카드 **7개**, Liu **정확히 1개**.
- Motamedi → R5 badge 1개, Claims 12·13·14 확인.
- 보조 증거 필터 → Wei 1개, R4·R5 연결.
- 기록 문헌 필터 → Oda·Biyikli 2개.
- 직접 지적 17 / Objection 2 / 허용 0 집계와 기존 Claim/PDF 연결 유지.
- 최종 실행 중인 API 서버에서 실제 두 PDF 요청 **HTTP 200**.

산출물:

- [7개 문헌 목록](data/outputs/citation-registry-seven.png)
- [Liu R2 인용 원문 이동](data/outputs/citation-registry-liu-r2.png)
- [기록 문헌 2개](data/outputs/citation-registry-recorded.png)
- [실제 PDF 분석 JSON](data/validation/citation_registry/analysis.json)

## 추가 테스트

| 최종 실행 | 결과 |
|---|---|
| `uv run pytest -q` | **244 passed**, 76.00초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | **244 passed**, backend **93%**, 137.97초 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 113 files already formatted |
| 실제 Edge 원본 PDF 업로드 | PASS |

기존 Starlette/httpx·anyio deprecation 경고 2개가 남습니다.
기존 §112/§103, OA 상태, 실제 pp_ex2/pp_vd2 및 Fote 문서 쌍, Claim/OCR/좌표/의존관계 회귀도 통과했습니다.

`tests/test_citation_registry.py`에 회귀 18개를 추가했습니다.
실제 PDF의 7/1/2 문헌, R1~R5별 집합, R6 인용 없음, Claim 합집합,
문헌 정의·재인용 Evidence의 문자 위치와 페이지, UI 카드·그래프 고유성,
저자 표기 4종, 공개번호 3종, 서로 다른 kind 보존, DOI 우선순위,
동명 저자의 다른 논문, 모호한 alias, 반복 출현·서로 다른 역할을 검사합니다.
기존 관계 지도 테스트는 새 edge 역할 필드까지 원본과 같게 전달하는지 확인하도록 확장했습니다.

재현:

```powershell
uv run pytest -q tests/test_citation_registry.py
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_citation_registry.py
```

## 수정 파일

- 신규: `backend/analysis/bibliography.py`, `backend/analysis/citation_registry.py`.
- Backend: `analysis/citation_analyzer.py`, `office_action/rejection_extractor.py`,
  `schemas.py`, `service.py`, `graph/graph_builder.py`.
- Frontend: `review_model.py`, `claim_analysis.py`, `evidence_comparison.py`, `relationship_map.py`,
  `pdf_review_component/review.js`, `review.css`, `relationship_map_component/map.js`, `map.css`.
- 검증: `tests/test_citation_registry.py`, `tests/test_relationship_map.py`,
  `scripts/browser_citation_registry.py`, `README.md`, `VALIDATION.md`, 이 문서.

Claim 파싱, 거절 블록/법조항 추출, OCR, dependency 계산 및 PDF 좌표 계산은 변경하지 않았습니다.
외부 API로 문헌을 검색하거나 LLM으로 원문을 교정하지 않았습니다.
