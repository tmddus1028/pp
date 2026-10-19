# AI 개선안 생성 + 사용자 수정본 재검증

2026-09-17 / Windows / Python 3.11 / Edge. 기존 분석 결과·원문·CSS를 변경하지 않고
개선 방안 accordion 안에 명시적 생성 및 수정본 검증 workflow를 추가했다.

**실제 Ollama 모델 추론은 미검증이다.** 이 PC에서 Ollama 실행 파일과 설정된 로컬 모델이
확인되지 않았다. 모델을 임의로 고르거나 다운로드하지 않았다. 아래 LLM 성공 응답은
mock 기반 계약/통합 테스트이며 실제 모델의 기술적·법률적 판단 품질을 뜻하지 않는다.

## 1. 무료 로컬 provider와 2. 설치·실행

`local_ollama`는 loopback의 Ollama-compatible `/api/chat`에 `stream=false`,
Pydantic JSON schema를 `format`으로 전달한다. 모델 이름은 `LOCAL_LLM_MODEL` 설정값만 사용한다.
OpenAI/Azure는 기존 연결 클래스를 재사용한다. 세 provider 모두
`generate_improvement()` / `review_revision()` 경계를 사용한다.
`local` 규칙 모드와 `local_ollama`는 구분한다. UI의 AI 버튼은 규칙 템플릿으로 대체하지 않는다.
기존 `/improvements`의 명시적 legacy local API 호출만 하위 호환을 위해 유지한다.

공식 [Windows 설치 안내](https://docs.ollama.com/windows)에 따라 설치 후:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
ollama serve
```

서버가 이미 실행 중이면 중복 실행하지 않는다. 별도 터미널:

```powershell
$reviewModel = "사용할-로컬-모델명"
ollama pull $reviewModel
ollama list
```

루트 `.env`:

```dotenv
LLM_PROVIDER=local
IMPROVEMENT_PROVIDER=local_ollama
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=사용할-로컬-모델명
LOCAL_LLM_TIMEOUT_SECONDS=180
LOCAL_LLM_CONTEXT_TOKENS=32768
LOCAL_EMBEDDING_MODEL=
```

기존 API를 재시작한 후 8501 공통 앱에서 사용한다. 기존 분석은 local로 유지한다.
local_ollama 선택은 KR Azure 설정보다 우선한다. base URL은 localhost/127.0.0.1/::1만 허용하고
환경 proxy·redirect를 사용하지 않으며 cloud 모델명은 거부한다. 키가 필요한 유료 API는 필수가 아니다.
참고: [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs),
[embedding API](https://docs.ollama.com/api/embed).

## 3. 개선안 생성 구조

`개선 방안 보기` → 영역만 열기 → `AI 개선안 생성` → 선택 청구항 및 기존 종속 chain,
현재 거절/OA/relied citation 언급 + 명세서 검색 후보 → provider structured output → 근거 검사 → 표시.

기존 `ClaimImprovementSuggestion` schema와 amendment/argument 구분을 유지한다.
prompt는 현재 요소와 심사관 주장의 대응, 명세서 지지, 권리범위 tradeoff를 구체적으로 요구한다.
US103/112와 KR29(2) 지침을 유지한다. 없음/불확실한 근거에서 예시 보정을 강제로 생성하지 않는다.
`POST /improvements`에 UI는 `require_llm=true`를 보낸다. 모델 미설정은 오류로 알리며
규칙 응답을 AI 생성 성공으로 표시하지 않는다.

## 4. 수정본 검증 구조

`POST /improvements/revisions`: 기존 analysis, claim_number, rejection_id,
revised_text, 선택 parent_revision_id를 입력한다.

```text
사용자 수정본
→ 코드 기반 diff 및 요소 구간 분해
→ 요소별 원 명세서 Top-K 검색
→ 원 청구항·상위항·변경점·관련 OA·검색 후보를 LLM에 전달
→ 요소별 support 및 거절별 대응 가능성 structured output
→ 근거 ID/인용/수치/범위 검사
→ 변경점 + 근거 + 제한사항 + 별도 유사도 표시
```

`ClaimRevision`은 frozen 객체다. 원문·AnalysisResult는 수정하지 않는다.
revision_id, text_hash, parent_revision_id, created_at을 기록한다.
브라우저 세션에 최근 3개 결과와 순서를 보관하며 파일 저장·제출·원본 PDF 수정 기능은 없다.
동일 사건/청구항/거절/수정문/근거 조합은 세션 결과를 재사용한다. 서버 응답에는 근거 해시와
전체 cache key가 포함된다. 문서 해시/analysis ID/관할 변경 및 새 업로드 시 캐시를 초기화한다.

## 5. Claim diff

`difflib.SequenceMatcher(autojunk=False)`로 whitespace를 포함한 토큰을 비교한다.
각 변경은 added/removed/changed/unchanged, 원문·수정문 부분 문자열과 양쪽 시작/끝 위치를 가진다.
원문 부분과 수정문 부분을 각각 합치면 정확히 입력 문자열을 복원할 수 있다.

요소는 세미콜론/줄바꿈 기준으로 나눈 결정적 구간이다. 각 구간에 정확한 위치와 변경 유형을 붙인다.
이것은 완전한 법률적 청구항 구성요소 parser가 아니다. PDF 줄바꿈을 독립 구간으로 볼 수 있다.
최대 수정문 12,000자, 요소 32개, diff 토큰 6,000개를 넘으면 오류로 알린다.

## 6. 명세서 support

기존 청구항 Evidence 영역을 먼저 제외하고 원 patent document에서 문단/최대 1,200자 chunk를 만든다.
원문 위치와 페이지를 보존하고 요소별 상위 3개, 전체 최대 12개 후보를 선택한다.
검색용 cosine은 순위 선택에만 쓰며 SUPPORTED 판정 threshold가 아니다.

LLM은 모든 요소 ID에 대해 정확히 한 번씩 SUPPORTED/PARTIALLY_SUPPORTED/NOT_FOUND/UNCERTAIN을
반환해야 한다. 지지 판정에는 해당 요소에 제공된 명세서 ID와 정확한 인용문이 필요하다.
NOT_FOUND는 제공된 검색 후보에서 찾지 못했다는 뜻이며 원 명세서 전체에 없다는 단정이 아니다.
추가/변경 요소가 충분히 지지되지 않으면 서버가
`신규사항 가능성 — 추가 확인 필요` 안내를 추가한다.

한국 기존 사례도 원 명세서 검색 후보를 구성한다. 이전 기능에서 자동 연결이 없던 상태와 구분한다.
현재 문서가 출원 당시 원 명세서인지, 보정 이력에서 동일 버전인지까지 자동 인증하지 않는다.

## 7. 유사도

- `LOCAL_EMBEDDING_MODEL` 설정: Ollama `/api/embed`, `truncate=false`, 벡터 cosine.
  모델 다운로드를 자동 수행하지 않는다.
- 미설정: 단어 빈도 cosine. UI에 **의미 유사도 아님**을 명시한다.
- embedding 실패/잘못된 벡터: 실패 안내와 함께 단어 빈도 지표를 표시한다.
- 원문↔수정문 및 요소↔검색 후보의 최고 유사도를 별도로 반환한다.
- 어떤 점수도 LLM support status 또는 거절 대응 status를 결정하지 않는다.

## 8. OA 대응과 9. 근거 오류 차단

거절별로 POTENTIALLY_ADDRESSES / PARTIALLY_ADDRESSES / DOES_NOT_ADDRESS /
INSUFFICIENT_EVIDENCE를 반환한다. UI는 한국어 검토 문구로 표시한다.
해당 거절의 OA 근거 ID와 정확한 인용이 필요하며 다른 R 범위가 섞이면 실패한다.

현재 공통 모델에 실제 인용문헌 본문은 없다. OA의 인용 언급을 선행문헌 본문으로 취급하지 않는다.
prior_art_assessment는 OA_ONLY 또는 INSUFFICIENT_EVIDENCE다. 명세서 지원이 확인되더라도
그것만으로 §103 또는 한국 진보성 지적에 대응했다고 결론내리지 않도록 prompt에서 구분한다.

존재하지 않는 ID·문단 번호, 다른 요소/거절 범위, 원문에 없는 quote, 근거 없는 수치·범위 및
일부 확정 표현을 검사한다. 예시 보정문도 동일한 수치·근거 검사를 적용한다.
실패한 응답을 검증된 결과로 표시하지 않는다.

**이 검사는 의미적 hallucination의 완전한 차단을 뜻하지 않는다.** 실제 문장을 인용해도
추론이 틀릴 수 있고, 문단 간 결합·범위·관계의 적절성 및 신규사항은 전문가 검토가 필요하다.
수치 검사는 제한적인 표기 pattern이며 모든 과학적 표기/단위 변환을 해석하지 않는다.

## 10. UI 변경 위치

기존 PDF 검토/청구항 분석의 청구항 상세 → 기존 `개선 방안` accordion 내부에만:

1. AI 개선안 생성 버튼과 결과
2. 수정 Claim textarea
3. 수정본 검증 버튼
4. 최근 revision 결과

추가했다. Sidebar, 기본 카드 배치, 색상/CSS, Summary, 필터, PDF/지도/근거 비교의 navigation을
변경하지 않았다. 긴 결과는 기존 공통 readable text renderer를 사용한다.
모델 연결/응답 실패는 이 accordion의 오류로 표시하고 기존 분석 및 이전 수정본 검토 결과를 유지한다.

## 11. 회귀 검증

자동 테스트 결과와 브라우저 결과는 아래 실행 범위만 의미하며 전체 입력/모델 품질의 보증이 아니다.

| 검사 | 결과 |
|---|---|
| 기존+신규 pytest | **327 passed**, 2 deprecation warnings, 89.01초; `data/outputs/revisions/pytest.log` |
| backend coverage | **327 passed / 94%**, 165.33초; `data/outputs/revisions/coverage.log` |
| Ruff check / format | PASS / 184 files already formatted |
| Ollama mock success/error, diff, 지원/미지원, 허위 ID/quote/문단/수치, US103/112/KR29(2), embedding 실패, session/cache/immutable | PASS, `tests/test_revisions.py` |
| 실제 미국 원본 PDF 3쌍 multipart 분석 | PASS, 기존 기대값 유지 |
| 실제 한국 PDF/XML 분석 및 네 화면 | PASS, 1항/직접1/종속0/인용3 유지 |
| `browser_jurisdiction.py` | PASS, 미국 기본 4개 화면 픽셀·구조/CSS·geometry 유지, KR 및 모드 전환 |
| `browser_pdf_review.py` | PASS, OCR·badge·accordion·원문 이동·청구항/지도/비교·명세서/도면 링크 |
| `browser_audit_state.py` | PASS, 새 문서 초기화/17·2·0·7/역할별 표시/다운로드/원본 불변 |
| `browser_review_scope.py` | PASS, ALL19/0, R1 15/4, R2 19/0 및 목록 필터 분리 |
| `browser_revisions.py` | PASS, **HTTP Ollama mock** 기반 US/KR 통합 workflow |

미국 실제 자료:

- 14/623,904: 19항, 거절2, 인용5; R1 종속2·5·8·11 유지.
- 15/914,356: 20항, 거절3, 인용5; 47/13페이지 유지.
- 17/708,932: 직접17, Objection2, 허용0, relied7; 보조/기록 문헌 내부 보존.

[원본 해시·기대값 비교](data/outputs/revisions/golden/golden-checks.json),
[브라우저 mock 검증](data/outputs/revisions/browser.json),
[mock 화면](data/outputs/revisions/mock-revision.png).
미국 개선 workflow 화면은 실제 특허 40–41쪽+재구성 OA fixture를 사용한다.
전체 미국 원본 검증은 별도의 golden multipart 실행이다.

Ollama 모의 서버 검사는 실제 HTTP JSON schema 계약을 거쳐 API와 Streamlit을 연결한다.
분석/Claim 선택/accordion 열기에서 호출 0회, 생성 버튼에서 1회, 수정본 3종에서 3회,
동일 입력 재검증 추가 호출 0회, scope 분리, 문서 변경 초기화, 서버 중단 오류를 확인했다.
1920/1440/1280/1024px에서 결과 본문 너비도 검사했다.

## 12. 실제 모델 호출 여부와 13. 남은 한계

| 항목 | 상태 / 이유 |
|---|---|
| 실제 Ollama 추론·판단 품질 | 미검증: 로컬 서버·사용할 모델 미설치/미설정 |
| 실제 로컬 embedding 결과 | 미검증: embedding 모델 미설정; mock 계약/오류만 검사 |
| 실제 OpenAI/Azure 검토 응답 | 미검증: 이 작업에서 외부 서비스를 호출하지 않음 |
| 모델별 문맥 길이·속도·메모리 | 미검증: 설치 모델/실제 하드웨어 추론 시험 필요 |
| 실제 인용발명 본문 대비 | 미지원: 현재 공통 분석 모델에 본문 없음; OA 설명으로 제한 |
| 전문 법률/기술적 적절성 | 미검증: 전문가 평가 및 더 많은 실제 보정 사례 필요 |

관련 context JSON은 최대 48,000자다. 초과하면 자르지 않고 오류로 알린다.
이는 실제 tokenizer의 토큰 상한과 같지 않으며 모델이 설정한 context를 지원해야 한다.
검색 후보 누락, 요소 분할 오차, 복잡한 기술 표현은 남을 수 있다.
작은 모델도 JSON schema를 출력할 수 있다는 사실만으로 전문 검토 성능을 보장하지 않는다.
따라서 **실제 LLM까지 전체 정상 동작한다고 결론내리지 않는다.**

## 수정 파일과 재현

추가 backend: `providers.py`, `retrieval.py`, `revision.py`, `revision_models.py`, `grounding.py`
(`backend/improvements/` 내부).
수정 backend: `config.py`, `main.py`, `improvements/models.py`, `improvements/service.py`.
수정 frontend: `app.py`, `improvements.py`, `pdf_review.py`, `pdf_review_component/review.js`.
추가 테스트: `tests/test_revisions.py`, `scripts/revision_mock_server.py`, `scripts/browser_revisions.py`.
기존 테스트 조정: API 경로 목록에 새 endpoint 추가, 개선 영역 열기와 AI 실행 분리 반영.
`browser_improvements.py`는 새 isolated workflow 검사 진입점으로 연결했다.
문서: `.env.example`, 루트/한국 README, 이 파일. 기존 분석 parser·Evidence schema·CSS는 변경하지 않았다.

```powershell
uv run python -m pytest -q
uv run python -m pytest --cov=backend --cov-report=term-missing
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run --project korean_prototype python -X utf8 scripts/browser_revisions.py
```

마지막 스크립트는 11435/18000/18501에서 테스트 전용 서버를 만들고 끝나면 종료한다.
8501 사용 환경의 설정을 바꾸지 않으며 실제 Ollama를 설치하거나 호출하지 않는다.
