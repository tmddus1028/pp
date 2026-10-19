# Patent Review 전체 기능 회귀 감사

검증일: 2026-09-16. Windows / Python 3.11 / local provider / 실제 로컬 API·Streamlit 서버 및 Chromium 브라우저에서 실행했다.

## 검사 범위와 집계

사용자 체크리스트에 더해 전체 소스를 먼저 조사하고, API, ingestion, parser, 분석, provider, CLI/도구, 다섯 화면, 공통 컴포넌트, state/navigation을 목록화했다. CSV adapter, 문서 다운로드, 오류 화면, 설정/도움말, 공개 자료 다운로드 도구, 평가 CLI, 기존 graph component, Windows 시작/종료도 포함했다.

| 항목 | 수 |
|---|---:|
| 구현 기능 inventory | **141** |
| 검사 완료 기능 | **139** |
| PASS | **139** |
| FAIL — 최종 실행 기준 | **0** |
| 테스트하지 못한 기능 | **2** |

기능 수는 독립적으로 확인할 수 있는 동작 단위다. 함수·테스트 케이스 수와 다르다. 각 기능의 소스, 실행 근거, 미검사 이유는 [전체 inventory](AUDIT_INVENTORY.md)에 기록했다. 최초 110개, 최종 115개 소스·테스트·도구 파일의 함수/클래스/상태 참조는 [최종 소스 인덱스](data/outputs/audit-20260916/source-inventory-final.json)에 있다. 설정 파일 `pyproject.toml`, `uv.lock`, `.env.example`, `.streamlit/config.toml`도 검토했다. 실제 `.env` 비밀값은 보고서나 백업에 포함하지 않았다.

**미검사 2건:** 실제 OpenAI 응답 품질(LLM-09), 실제 Azure OpenAI 응답 품질(LLM-10). 두 provider의 사용 가능한 키가 설정되어 있지 않았다. SDK 전송 계약, 거절/refusal, 연결 오류, 근거 검증은 mock으로 실행했으며 실제 API 품질 검증과 구분했다. 따라서 **“전체 기능 이상 없음”으로 결론내리지 않는다.**

PASS는 기록한 입력과 실행 경로에서 해당 동작을 확인했다는 뜻이다. 모든 입력 조합, 모든 코드 분기, 모든 브라우저와 OS를 검증했다는 뜻이 아니다. PyMuPDF/PDFium/기존 parser의 실패 분기는 mock 검사와 실제 PDF fallback 검사를 병행했다.

## 1. 발견한 실제 버그와 2. 원인

| 재현된 문제 | 원인 | 최소 수정 및 확인 |
|---|---|---|
| 실제 pp_vd1의 인용문헌이 5개 대신 3개 | OCR의 `W02013/119950 A2`를 WO 특허로 인식하지 못해 Hout 이후 NPL 연결도 끊김 | 연도/번호 형식이 뒤따르는 `W0`만 publication pattern에서 허용. canonical 식별자만 WO로 정규화하고 원문·Evidence는 유지. 실제 전체 PDF에서 5개 확인 |
| 청구항 상세·근거 비교·관계 지도에 보조 문헌이 노출 | 일부 화면이 `cited_references`/graph의 모든 관계를 그대로 렌더링 | 공통 `relied_references`와 map의 표시 조건으로 실제 거절 문헌만 표시. backend의 Wei/Oda/Biyikli 및 관계는 그대로 보존 |
| 평가 지표에서 Objection까지 직접 거절로 집계 | evaluator가 action type과 citation role을 구분하지 않음 | rejection 및 relied-upon 기준으로 평가 집합 생성. parser 결과는 변경하지 않음 |
| 같은 파일 재분석 후 이전 검색/비교 상태가 남음 | content 기반 analysis ID가 같아 초기화 조건을 통과하지 않음 | 새 업로드 성공 시 Claim/Comparison 초기화 식별자도 함께 해제 |
| 명시적 화면 이동 후 늦게 온 지도 이벤트가 상태를 덮음 | map 이벤트에 navigation 세대 검사가 없음 | 이벤트에 navigation 값을 넣고 현재 세대와 일치할 때만 수용 |
| Claim 선택 직후 사이드바로 이동하면 이전 Claim이 열림 | component의 마지막 값이 도착한 rerun에서 출발 화면을 다시 실행하지 않음 | 목적지 context 계산 전에 이미 도착한 선택을 검증·반영. PDF/지도 양쪽 재현 테스트 추가 |
| 인용문헌의 개별 OA 근거 보기에서 Summary scope/type filter가 바뀜 | 원문 이동 핸들러가 rejection scope와 목록 필터까지 재설정 | 문서·페이지·근거·active rejection만 변경하고 검토 범위/목록 필터 유지 |
| 원문 accordion이 이미지 로딩·resize·rerun 때 다시 접힘 | PDF 검토 목록 DOM을 다시 만들 때 nested `details.open`을 잃음 | 카드와 근거 제목별 열림 상태 보존. 명시적으로 이동한 active 근거의 자동 펼침 우선; 새 분석/진입 때 초기화 |

수정 전 실패는 [parser/표시/평가 재현](data/outputs/audit-20260916/reproduced-bugs.log), [상태 재현](data/outputs/audit-20260916/reproduced-state-bugs.log), [사이드바 재현](data/outputs/audit-20260916/reproduced-sidebar-bug.log)에 보존했다. 원래 테스트 247개는 통과했지만 위 경계 상황을 잡지 못했다. 기존 브라우저 검사 중 과거의 카드 개수·label·자동 선택을 기대하던 항목도 현재 요구사항에 맞게 수정했다. 이것은 제품 버그 수정과 구분한다.

## 3. 수정한 파일

제품 코드:

- [backend/analysis/citation_analyzer.py](backend/analysis/citation_analyzer.py): 제한된 W0 publication 인식.
- [backend/evaluation/evaluator.py](backend/evaluation/evaluator.py): rejection/relied-only 평가 지표.
- [frontend/app.py](frontend/app.py): 재분석 초기화, 화면 전환 직전 선택 반영.
- [frontend/review_model.py](frontend/review_model.py): 표시용 relied-only 공통 helper.
- [frontend/claim_analysis.py](frontend/claim_analysis.py), [frontend/evidence_comparison.py](frontend/evidence_comparison.py): helper 적용.
- [frontend/relationship_map.py](frontend/relationship_map.py), [map.js](frontend/relationship_map_component/map.js): 오래된 이벤트 차단, 표시용 문헌 제한.
- [review.js](frontend/pdf_review_component/review.js): citation 근거 이동 시 scope 유지, 원문 accordion 상태 보존.

검증 코드:

- 추가: `tests/test_audit_regressions.py`, `tests/test_audit_utilities.py`.
- 추가: `scripts/audit_golden_pairs.py`, `scripts/browser_audit_state.py`, `scripts/browser_audit_utilities.py`.
- 추가: 실제 OCR 문단 fixture와 [출처 설명](tests/fixtures/citations/office_action_14623904_ocr_excerpt.README.md).
- 수정: `tests/test_evidence_comparison.py`, `tests/test_relationship_map.py` — navigation 세대 포함.
- 수정: `scripts/browser_accordion_flow.py`, `browser_citation_registry.py`, `browser_claim_analysis_flow.py`, `browser_pdf_review.py` — 현재 요구사항과 일치하는 검증 및 공유 체크리스트 상태 처리.
- 보고서: 이 파일과 `AUDIT_INVENTORY.md`, `data/outputs/audit-20260916/`의 실행 결과.

기존 사용자 변경과 구분하기 위해 git diff 전체가 아니라 시작 당시 파일 해시와 비교한 [수정 소스 목록](data/outputs/audit-20260916/changed-source-files.json)을 남겼다.

## 4. 수정하지 않은 영역

Claim parser, OA 상태/거절 parser, OCR 엔진과 PDF open fallback, 종속관계 계산, citation role 분류·deduplication, Evidence 위치 계산, API/Pydantic 계약, backend graph 데이터 생성, LLM provider 구현은 변경하지 않았다. 인용문헌 parser의 변경은 위 W0 패턴에 한정된다. 원본 PDF를 재저장하거나 수정하지 않았다. 실제 PDF 입력의 해시와 모든 Evidence 문자 범위/페이지를 검사했다.

일반 UI에서 보조 문헌 카드·chip을 숨겨도 원문 인용문 안의 이름을 삭제하거나 분석 JSON에서 문헌을 제거하지 않는다. 새로운 법률 판단이나 LLM 원문 교정도 추가하지 않았다.

수정 전 [소스 백업](data/outputs/audit-20260916/before-source.zip), git 상태와 작업 diff를 보존했다. Windows start/stop 스크립트는 실제 종료·재시작하여 검증했고 수정하지 않았다. 종료 시 8000/8501의 listener가 모두 사라졌으며, 재시작 후 API와 UI health가 정상이다. 이 환경에서는 README의 `powershell -ExecutionPolicy Bypass -File ...` 방식으로 실행했다.

## 5. 추가한 테스트 및 실행 결과

| 실행 | 최종 결과 |
|---|---|
| `uv run pytest -q` | **263 passed**, 2 warnings; 83.44초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | **263 passed**, backend **93%**; 160.32초 |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS — 130 files already formatted |

테스트 케이스는 247개에서 263개로 16개 늘었다. 실제 OCR 문헌 누락, 역할별 UI 표시/데이터 보존, 평가 기준, 같은 문서 재분석, 늦은 지도 이벤트, 두 출발 화면의 사이드바 상태 경쟁을 추가했다. API 문서·JSON 업로드·문자 제한·파일 close, 오류 시 기존 분석 보존, provider 오류, fixture 생성 도구, 평가 CLI도 실행했다.

로그: [pytest](data/outputs/audit-20260916/final-tests.log), [coverage](data/outputs/audit-20260916/coverage.log), [Ruff](data/outputs/audit-20260916/ruff-check-final.log), [format](data/outputs/audit-20260916/ruff-format-final.log). 두 warning은 의존 라이브러리의 deprecation 안내다. Coverage의 실행되지 않은 125문장은 남아 있으며 기능 PASS 수와 혼동하지 않는다.

### 페이지별 브라우저 결과

| 페이지 | 결과 | 실제 실행한 주요 동작 |
|---|---|---|
| Document Upload | PASS | 무분석 진입, PDF/TXT/JSON·텍스트·데모 입력, 오류 표시, 동일 세션의 새 문서 초기화, 설정/도움말, JSON 다운로드 |
| PDF Review | PASS | 실제 페이지 렌더링, 원본 다운로드, 검색/줌/fit, Claim 1/14/18 박스와 양 column badge, accordion, scope Summary, 목록 필터, OA/citation 이동, 체크리스트 |
| Claim Analysis | PASS | 4개 상태 필터·번호 검색, § 버튼 없음, 법조항·원문 유지, 처리 정보 접힘, 체크리스트 공유, PDF 연결 |
| Relationship Map | PASS | node/edge·선택·scope/type 필터·확장·강조, Claim 7의 R1/R3와 Liu/Donmez/Huang, source 표시, PDF/비교 왕복, 늦은 이벤트 차단 |
| Evidence Comparison | PASS | Claim/거절 선택, 원문·기존 명세서/도면 근거·문헌·요약, 근거 없는 상태, PDF 왕복, overflow일 때만 더 보기/접기, 버튼 간격 |

최종 통합 실행: [PDF→Claim→지도→비교→OCR](data/outputs/audit-20260916/pdf-browser-complete.log). 추가 실행: [scope 회귀](data/outputs/audit-20260916/scope-browser-final.log), [실제 문헌 registry](data/outputs/audit-20260916/citation-browser.log), [같은 세션 재분석/선택 전달](data/outputs/audit-20260916/browser_audit_state-final.log), [텍스트/JSON/기존 graph](data/outputs/audit-20260916/utilities-browser.log), [OA 상태](data/outputs/audit-20260916/browser_oa_status-final.log).

1920/1440/1280/1024px에서 PDF 원문·문헌, 지도 원문·문헌, 청구항 상세, 근거 비교의 6개 표시 위치를 검사했다. **24개 조합 PASS**, 측정한 원문 최소 폭 302px, 지정 회귀 문장은 1~3줄로 표시됐다. 데이터와 선택 상태 불변도 확인했다. [측정 로그](data/outputs/audit-20260916/readable-browser-final.log). [더 보기 검사](data/outputs/audit-20260916/browser_readable_toggle.log)는 짧은 원문에서 토글 숨김, 긴 원문 확장/접기, resize 반영, 다음 버튼과 간격을 확인했다. 기존 공통 CSS는 이 검사에 통과하여 불필요하게 다시 수정하지 않았다.

브라우저의 일부 UI 시나리오는 공개 실제 특허+재현용 OA 또는 합성 fixture로 실행했다. 아래 golden 검증은 그것과 별도로 **사용자가 제공한 원본 PDF 6개를 실제 multipart API에 직접 입력**했다. 합성 OA를 실제 전체 OA 검증으로 표현하지 않는다.

## 6. Fixture 1 — application 14/623,904

`pp_ex1.pdf` 41쪽 / `pp_vd1.pdf` 10쪽. 전체 PDF에서 Claims 1~19 추출.

| 항목 | Expected | Actual | 결과 |
|---|---|---|---|
| ALL 직접 / 종속 | 19 / 0 | 19 / 0 | PASS |
| R1 §112 직접 / 종속 | 15 / 4 | 15 / 4 | PASS |
| R1 종속 Claim | 2,5,8,11 | 2,5,8,11 | PASS |
| R2 §103(a) 직접 / 종속 | 19 / 0 | 19 / 0 | PASS |
| 거절 / relied 문헌 | 2 / 5 | 2 / 5 | PASS |
| Evidence 위치 불일치 | 0 | 0 | PASS |

문헌: Lombardi, Bendiera, Hout, Greco, Lipska. 세 특허와 두 NPL을 유지한다. R1에서 종속 목록을 선택해도 Summary 15/4, R2에서 19/0과 빈 종속 목록을 브라우저로 확인했다.

## 7. Fixture 2 — application 15/914,356

| 항목 | Expected | Actual | 결과 |
|---|---|---|---|
| Patent / OA 페이지 | 47 / 13 | 47 / 13 | PASS |
| Claim 번호 | 1~20 | 1~20 | PASS |
| ALL 직접 / 종속 | 20 / 0 | 20 / 0 | PASS |
| §103 거절 / relied 문헌 | 3 / 5 | 3 / 5 | PASS |
| R1 직접 Claim | 1~12,20 | 1~12,20 | PASS |
| R2 직접 Claim | 13,17,18,19 | 13,17,18,19 | PASS |
| R3 직접 Claim | 14,15,16 | 14,15,16 | PASS |
| Evidence 위치 불일치 | 0 | 0 | PASS |

문헌: Han, Lin, Vogelstein, Empedocles, Newton. malformed Pages 때문에 strict parser가 실패해도 기존 fallback으로 분석이 시작되는 것을 API와 브라우저에서 확인했다.

## 8. Fixture 3 — application 17/708,932

`pp_ex3.pdf` 18쪽 / `pp_vd3.pdf` 11쪽. Claim 20은 취소 청구항으로 원문 목록에 남는다.

| 항목 | Expected | Actual | 결과 |
|---|---|---|---|
| Claim 번호 | 1~20 | 1~20 | PASS |
| 직접 거절 | 1~14,17~19 (17개) | 동일 | PASS |
| Objection / 종속 | 15,16 (2개) | 동일 | PASS |
| 허용 / 취소 | 0 / Claim 20 | 동일 | PASS |
| 실제 rejection / objection | 5 / 1 | 5 / 1 | PASS |
| relied 문헌 | 7 | 7 | PASS |
| supporting | Wei 1 | Wei 1 | PASS |
| not relied | Oda, Biyikli 2 | 동일 | PASS |
| Evidence 위치 불일치 | 0 | 0 | PASS |

relied 문헌은 Liu, Donmez, Bakke, Huang, Yao, Nakayama, Motamedi다. UI 문헌 카드에 이 7개만 노출하며 숨긴 3문헌은 분석 JSON과 내부 관계에 유지됨을 검사했다. `R6`의 내부 statute `unknown`은 Objection의 값이고, 여섯 번째 §103 rejection으로 세지 않는다.

세 fixture의 expected/actual 전체 배열, 원본 해시, API 결과는 [golden-checks.json](data/outputs/audit-20260916/final-golden/golden-checks.json) 및 같은 폴더 `pair-1.json`~`pair-3.json`에 있다.

## 9. 남아 있는 위험 및 검사 한계

- Live OpenAI/Azure 응답 품질은 미검사다. 현재 local 동작을 외부 LLM 성능 검증으로 해석하면 안 된다.
- OCR 철자와 원문 판독 정확도 전부를 보증하지 않는다. 이번 W0 보완은 번호 문맥으로 제한했고 raw text는 수정하지 않았다.
- 세 실제 pair와 기존 테스트는 개발·회귀 자료다. 새로운 사건에 대한 일반화 성능이나 법률 판단 타당성을 입증하지 않는다.
- 브라우저는 Windows Chromium과 명시한 viewport에서 검사했다. 다른 브라우저/OS, 1024px보다 작은 모든 화면의 동작은 이번 전수 결과에 포함하지 않는다. 일부 별도 900px stack 검사는 통과했다.
- 함수 목록 전체를 조사했지만 코드 coverage는 93%다. 무한한 입력·상태 조합에 대한 완전 검증을 주장하지 않는다.
- 재현 실패 로그와 중간 브라우저 실패 기록을 삭제하지 않았다. `browser-runs.json`, `browser-final-runs.json`은 중간 시도이며 최종 판정은 이 보고서가 연결한 최종 로그를 기준으로 한다.

검사한 139개 동작은 최종 통과했으며, 테스트하지 못한 2개 기능은 위와 같이 남겨 두었다.
