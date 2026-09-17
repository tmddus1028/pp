# 검토용 청구항 개선 방안 — 구현 및 회귀 검증

검증일: 2026-09-17. Windows / Python 3.11 / 실제 API·Streamlit / Edge headless.
기존 분석 결과에 별도 검토 결과를 추가했다. 청구항·문서·심사관 원문을 변경하거나 제출하지 않는다.
실제 외부 LLM은 호출하지 않았다. 아래 실문서 결과는 **local 검토 항목**이며 생성형 AI의 품질 평가가 아니다.

## 1. 추가 모듈과 API

- `backend/improvements/context.py`: 기존 관계에서 선택 청구항·전체 상위/중간 청구항·거절·원문 근거만 구성.
- `models.py`: 요청, 구조화된 결과, 근거 및 응답 schema.
- `prompts.py`: 공통 근거 규칙과 US/KR 지침.
- `service.py`: local 검토 항목, 기존 OpenAI/Azure 연결 재사용, 결과 검증.
- `POST /improvements`: `analysis`, `claim_number`, 선택 `rejection_id` 입력.
  입력/근거 오류는 422, provider/출력 검증 실패는 502이며 기존 분석 응답은 변경하지 않는다.
- `frontend/improvements.py`: 공통 HTML 표시, 명시적 요청, 세션 캐시 및 독립 오류 상태.

## 2. Structured Output

`ClaimImprovementSuggestion`은 `claim_number`, `jurisdiction`, `issue_summary`,
`rejection_basis`, `element_comparison`, `strategies`, `optional_example`,
`missing_evidence`, `cautions`를 포함한다.
전략에는 action type, 대상 원문 요소, evidence IDs, 정확한 인용문, 기대 효과, tradeoff가 필요하다.
지원 action은 clarify/narrow/add_limitation/remove_unsupported_scope/dependency_rewrite/argument_only/other다.
문제 설명, 수정 방향, 수정 없이 검토할 반박 논점을 분리한다.
OpenAI SDK `responses.parse(text_format=ClaimImprovementSuggestion, store=False)`를 사용한다.

## 3. 관할별 처리

- US §103: 심사관의 구성 대응·문헌 조합 설명을 대상으로 조건부 비교 항목을 생성한다.
  선행문헌 본문이 없으면 실제 기술적 차이를 확인했다고 표시하지 않는다.
- US §112: OA에 명시된 written description, enablement, indefiniteness/antecedent basis를 구분한다.
  법조항 번호만 있는 경우 세부 유형 미확인으로 표시한다.
- KR 제29조제2항: 청구항·인용발명·의견제출통지서·명세서 용어와 진보성 검토 지침을 사용한다.
- 조건부 독립항 재작성: 기존 상태 플래그와 실제 심사관의
  `would be allowable if rewritten in independent form` 문구, 전체 상위 청구항 근거가 함께 있어야 한다.
  줄바꿈된 문구도 인식한다. 다른 청구항에 일괄 적용하지 않는다.

## 4. 근거 검증과 제한

1. 원본 문서의 Evidence start/end 및 페이지와 인용 텍스트가 일치하는지 확인한다.
2. 명세서 연결은 기존 `explicit_support` 정책을 그대로 재사용한다. 임의 검색으로 연결을 추가하지 않는다.
   그림 caption은 기술적 보정 근거로 사용하지 않는다.
3. 제공하지 않은 evidence ID, 다른 청구항/관할/거절/법조항, 원문에 없는 인용문·대상 요소는 거부한다.
4. 기술적 수정에는 실제 명세서 근거와 정확한 인용문이 필요하다. 예시 문안에도 명세서·청구항·OA 근거가 필요하다.
5. 근거 부족 시 수정 제안을 제한하거나 `strategies=[]`, `status=abstained`를 반환한다.
6. 관련 context JSON은 48,000자까지다. 넘으면 오류를 표시하고 거절 사유를 좁히도록 안내한다.
   외부 출력 상한은 6,000 tokens다. 입력 문자 제한은 비용/토큰 상한을 의미하지 않는다.

ID·문자 일치는 제안의 의미상 타당성이나 신규사항 부재를 인증하지 않는다.
명시적인 허용 보장 문구 일부를 차단하지만 모든 법률적 확정 표현을 자동 검증하는 기능은 아니다.

## 5–6. UI 위치와 기존 화면 보호

- PDF 검토: **펼친 청구항 카드 하단**, 기존 PDF/근거 비교 링크 다음에 `개선 방안 보기` 버튼과 결과 accordion.
- 청구항 분석: **청구항 상세 보기 내부 하단**, 기존 상세 내용 다음에 같은 버튼과 결과 accordion.
- 두 경로는 같은 `improvement_html`을 사용한다. 기존 readable text 스타일과 accordion을 재사용한다.
- 새 페이지·sidebar·CSS·색상·summary·filter·카드 배치는 추가/변경하지 않았다.
- PDF는 현재 거절 scope를 우선하고, 전체 scope에서는 현재 확인 중인 연결 거절이 있으면 그 사유를 사용한다.
  청구항 분석은 연결된 전체 거절을 대상으로 한다. 생성 요청이 선택 Claim, PDF 위치, scope를 바꾸지 않는다.
- 기존 미국 4개 화면의 기본 진입 화면 픽셀·구조와 CSS/annotation geometry 해시 비교가 통과했다.
  추가 버튼이 보이는 펼친 상세 카드까지 이전 화면과 동일하다는 뜻은 아니다.

## 7. Provider 호출과 캐시

페이지 진입/Claim 선택은 호출하지 않으며 사용자가 버튼을 눌렀을 때만 `/improvements`를 요청한다.
`IMPROVEMENT_PROVIDER=inherit`가 기본이고 local/openai/azure를 별도로 지정할 수 있다.
`LLM_PROVIDER=local`, `IMPROVEMENT_PROVIDER=azure`이면 기존 추출은 로컬로 유지하고 개선 검토만 Azure를 사용한다.
KR은 기존 `korean_prototype/.env` 또는 환경변수의 `KR_AZURE_OPENAI_*` 설정을 우선한다.
`IMPROVEMENT_PROVIDER=local`이면 KR 설정이 있어도 외부 호출하지 않는다. 실제 키는 변경하지 않았다.

세션은 analysis ID + 전체 분석 내용 해시로 구분하며 청구항/거절별 성공 결과를 캐시한다.
응답에 관련 evidence hash도 보존한다. 문서 내용 또는 관할이 바뀌면 초기화한다.
실패는 별도 오류 상태에 저장하고 재시도할 수 있다. 기존 분석 데이터는 덮어쓰지 않는다.

## 8–9. 실제 미국·한국 문서 결과

미국은 `pp_ex1/pp_vd1`, `pp_ex2/pp_vd2`, `pp_ex3/pp_vd3` **전체 원본 PDF**를
실제 multipart API에 다시 입력했다. SHA-256, 기대값 및 Evidence 검사는
[golden-checks.json](data/outputs/improvements/golden/golden-checks.json)에 보존했다.

| 사례 | 기존 분석 유지 | 새 검토 결과 |
|---|---|---|
| 14/623,904 | 19항, 거절 2, 인용 5; R1 직접 15/종속 4, R2 직접 19/종속 0 | Claim 1 R1 §112와 R2 §103 분리; 서로 다른 context hash와 검토 항목 |
| 15/914,356 | 20항, 거절 3, 인용 5; PDF 47/13쪽 | Claim 1 R1 제한된 근거 기반 검토 |
| 17/708,932 | 직접 17, Objection 2, 허용 0, relied 7; Wei/Oda/Biyikli 내부 보존 | Claim 15·16/R6만 명시적 조건부 재작성; Claim 1/R1에는 붙이지 않음 |
| 10-2019-0000844 | 실제 PDF/XML 재입력: 1항, 직접 1, 종속 0, 제29조제2항, 인용발명 3 | 한국 용어로 표시; 명세서 자동 연결 및 선행문헌 본문 부재를 명시하고 구체적 한정 제안 제한 |

7개 요청 모두 PASS. [요청별 결과](data/outputs/improvements/improvement-checks.json),
[브라우저 기록](data/outputs/improvements/browser.json),
[미국 화면](data/outputs/improvements/us-improvement.png),
[한국 화면](data/outputs/improvements/kr-improvement.png).
개선 버튼 브라우저 검사에는 미국 특허 40–41쪽과 재구성 OA fixture를 사용했다.
전체 미국 OA 원본 검증은 위 별도 multipart 검사로 수행했으며 두 검사를 혼동하지 않는다.

## 10. 추가 테스트와 기존 회귀 실행

`tests/test_improvements.py`의 25개 테스트: §103/§112/KR29(2), 종속 chain과 조건부 문구,
명세서/인용 원문 부족, 잘못된 ID·quote·요소·법조항·scope·새 기술 내용 차단,
명시적 실행/캐시/문서 전환, provider 실패/거절/중단 응답, API 오류와 원본 보존,
안전한 HTML 표시, 근거를 갖춘 mock 보정안 및 abstention을 검사했다.

| 명령 | 최종 결과 |
|---|---|
| `uv run python -m pytest -q` | **300 passed**, 2 deprecation warnings, 87.42초 |
| `uv run python -m pytest --cov=backend --cov-report=term-missing` | **300 passed**, backend **93%**, 170.92초 |
| `uv run python -m ruff check .` | PASS |
| `uv run python -m ruff format --check .` | PASS, 175 files |
| `uv run --project korean_prototype python -m pytest korean_prototype/tests -q` | **56 passed**, 2 deprecation warnings |

다음 브라우저 스크립트도 실제 Edge에서 통과했다.

- `browser_improvements.py`: 명시적 실행, scope별 캐시, 문서/관할 초기화, 원본/선택 상태 불변, 한국 근거 부족.
- `browser_jurisdiction.py`: 기존 미국 4개 화면 비교, 실제 한국 문서/원문 이동, 모드 전환.
- `browser_pdf_review.py`: PDF 렌더링·OCR, Claim 1/14/18 영역·badge, accordion, Claim/지도/비교 왕복 및 명세서/도면 링크.
- `browser_audit_state.py`, `browser_audit_utilities.py`: 새 문서 초기화, 역할별 표시, TXT/JSON, 설정/도움말, 다운로드, 기존 graph.
- `browser_review_scope.py`: 전체 19/0, R1 15/4(2·5·8·11), R2 19/0, 목록 필터/원문 이동과 Summary 분리.
- `browser_citation_registry.py`: 17/2/0/7, relied 7개 표시, Wei/Oda/Biyikli 내부 보존, 선택·원문 이동.
- `browser_readable_text.py`: 4개 화면의 1920/1440/1280/1024px 원문 폭·자연스러운 줄바꿈.
- `browser_readable_toggle.py`: 실제 overflow일 때만 펼치기, 숨겨진 accordion/resize 반영, 버튼 겹침 없음.

최초 검사에서 기존 OpenAPI 경로 목록 테스트가 새 endpoint를 허용하지 않아 실패했다.
기대 목록에 추가 endpoint를 반영했다. 브라우저 검사에서는 짧은 원문의 숨겨진 toggle까지
클릭하던 선택자를 Streamlit accordion으로 한정했고, 임시 DOM 텍스트 주입 전에
지도 선택의 rerender를 기다리도록 했다. 제품 텍스트/지도 로직은 변경하지 않았다.

## 11–12. 실제 외부 호출 및 남은 한계

- **실제 OpenAI/Azure 호출 없음.** SDK 요청 형식·Structured Output·근거 검증·실패 처리는
  mock으로 검증했다. 배포 모델별 호환성, 실제 응답 품질/지연/비용은 미검증이다.
- local 결과는 결정적 검토 질문이며 구체적 보정안을 생성하는 LLM 추론과 다르다.
- 현재 공통 AnalysisResult에는 실제 인용문헌 PDF 원문이 없어 모든 인용은 OA의 언급 근거다.
  한국 시제품 폴더에 있는 인용발명 PDF도 이 요청에 자동 첨부하지 않는다.
- 한국 실제 사례에는 자동 연결된 명세서 발췌가 없다. 명세서가 존재한다는 이유만으로 임의의
  문단을 보정 근거로 연결하지 않으며 구체적 수정 제안은 제한된다.
- 증거 인용의 의미적 적절성, 신규사항, 권리범위·법률 판단은 자동 인증하지 않는다.
  실제 문서/출원 이력과 전문가 확인이 필요하다. 모든 문서에 개선안이 나온다고 보장하지 않는다.
- 한국어 조건부 재작성 문구의 추가 parser 지원, 인용발명 본문 편입, 대응안의 전문 평가 등은 후속 범위다.
- 이전 전체 audit의 기능 수를 이번 검사 완료 수로 그대로 재사용하지 않았다.
  위 실행 범위에서 회귀를 확인했으며 **모든 기능·모든 실제 LLM 결과에 이상이 없다고 결론내리지 않는다.**

## 이번 작업 파일

추가: `backend/improvements/{__init__,context,models,prompts,service}.py`,
`frontend/improvements.py`, `tests/test_improvements.py`,
`scripts/browser_improvements.py`, `scripts/validate_improvements.py`, 이 검증 문서.

수정: `backend/config.py`, `backend/main.py`, `frontend/app.py`,
`frontend/claim_analysis.py`, `frontend/pdf_review.py`,
`frontend/pdf_review_component/review.js`, `tests/test_audit_utilities.py`,
`scripts/browser_readable_text.py`, `scripts/browser_readable_toggle.py`, `.env.example`, `README.md`.

기존 KR 통합·용어 변경 등 이전 작업의 미커밋 파일을 이번 변경으로 집계하지 않는다.
parser, OCR, citation deduplication/classification, dependency, 기존 AnalysisResult 및 graph 생성은 변경하지 않았다.

재현: API/UI를 실행한 상태에서 아래 명령을 사용한다. 개선안 golden 스크립트는 local 설정에서만 실행한다.

```powershell
uv run python -X utf8 scripts/audit_golden_pairs.py --input C:\Users\dltmddus\Desktop\dltmddus\pp --output data/outputs/improvements/golden
uv run python -X utf8 scripts/validate_improvements.py
uv run --project korean_prototype python -X utf8 scripts/browser_improvements.py
```
