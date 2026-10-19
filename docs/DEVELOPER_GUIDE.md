# PinPoint 개발자 가이드

처음 코드를 보는 팀원용 지도입니다. "무엇이 어디 있고, 무엇을 고치려면 어디를 보면 되는지"만 정리했습니다.
실행 방법은 [README](../README.md), 수치와 실험 기록은 [PRECEDENT_VALIDATION](validation/PRECEDENT_VALIDATION.md),
발표 숫자 설명·재계산은 [PRESENTATION_NUMBERS](PRESENTATION_NUMBERS.md)(`uv run python scripts/report_numbers.py`)를 보세요.

## 1. 한 장 요약

사용자가 **공개특허 PDF + 거절 통지서(의견제출통지서)** 를 올리면:

```
업로드 ─▶ ① 문서 읽기 ─▶ ② 거절 종류 분류 ─▶ ③ 설명서 근거 찾기 ─▶ ④ 체크리스트 + 대응 사례 ─▶ ⑤ AI 방어 전략(버튼)
frontend   jurisdictions/     precedents/          improvements/          analysis/checklist_      improvements/
app.py     korean.py          taxonomy.py          retrieval.py           generator.py             service.py
                                                                          + precedents/             + providers.py
                                                                            repository.py
```

- ①~④는 규칙 기반이라 몇 초 안에 끝나고 LLM을 쓰지 않습니다.
- ⑤만 LLM(Claude 또는 로컬 Ollama)을 부르고, 결과는 **원문 인용이 맞는지 기계로 검증**한 뒤에만 보여줍니다.

## 2. 폴더 지도

| 위치 | 하는 일 | 주로 보는 사람 |
| --- | --- | --- |
| `backend/main.py` | FastAPI 앱. `/analyze/*`, `/improvements`, `/precedents/*`, `/cases/*` | 김경훈 |
| `backend/jurisdictions/korean.py` | 한국 문서 분석 진입점 (`korean_prototype/kr_review` 추출기를 연결) | 김승제 |
| `backend/analysis/checklist_generator.py` | 체크리스트 문구 + `[대응 사례]` 항목 생성 | 김승제 |
| `backend/precedents/` | **대응 사례 DB** (아래 3장) | 김승제·김채희 |
| `backend/improvements/` | AI 방어 전략: 근거 모으기 → LLM 호출 → 검증 (아래 4장) | 변유민 |
| `backend/schemas.py` | 분석 결과 데이터 모양(Pydantic). `ReviewItem.precedent`가 대응 사례 근거 | 전원 |
| `frontend/app.py` | Streamlit 화면 뼈대, 위쪽 메뉴(문서 업로드 / 검토) | 이승연 |
| `frontend/pdf_review_component/` | 검토 화면(HTML/JS/CSS). 왼쪽 PDF, 오른쪽 섹션 5개 | 이승연 |
| `scripts/` | 데이터 만들기·실험 스크립트 (아래 5장). `start.ps1`/`stop.ps1`은 앱 실행 | 전원 |
| `data/precedents/` | 앱이 읽는 대응 사례 완성본(JSONL) | - |
| `data/eval/kr/` | LLM 채점표 (사건별 JSON + 입력 PDF) | 김경훈 |
| `data/research/` | 수동 자료(의견서 PDF), `OPINION_DOWNLOAD_TODO.md` | 김채희 |
| `web/` | Next.js 화면 (해커톤 후 이식 예정) | 김승제·이승연 |
| `tests/` | pytest. `uv run pytest -q` 로 전체 실행 (약 8분) | 전원 |

Git에 올리지 않는 것: `.env`(API 키), `data/kipris_cache/`(KIPRIS 응답 캐시), `data/datasets/`(PatRe 원본), `data/outputs/`(실행 결과).

## 3. 대응 사례 DB (`backend/precedents/`)

사례 1건 = **거절 이유 1개**에 대해 "① 거절 이유 → ② 무엇을 고쳤나 → ③ 왜 다르다고 주장했나 → ④ 결과".

| 파일 | 역할 |
| --- | --- |
| `taxonomy.py` | 한·미 조문을 공통 종류로 묶음. `categorize("특허법 제29조제2항")` → `"inventive_step"`(진보성). 대응 방식 분류 정규식도 여기 |
| `repository.py` | JSONL 읽기. `stats(category, path)` = 해소율 통계, `find(category, query, path=...)` = 대표 사례 |
| `kipris.py` | KIPRIS Plus API 클라이언트. 모든 응답을 `data/kipris_cache/`에 캐시, 서비스별 월 950회에서 멈춤, 연결 끊김 3회 재시도 |
| `api.py` | `GET /precedents/stats`, `/precedents`, `/precedents/{case_id}`, `/precedents/categories` |

해소 라벨 규칙 (재설계안 기준):
- 다음 조치가 **등록** → 해소
- **거절결정** → 결정서의 "해소되지 않은 부분" 표에 있으면 미해소, 없으면 해소
- **다시 통지** → 같은 종류가 또 나오면 미해소
- 제외: 무대응, 재심사·RCE 경유, 결정서에 표가 없는 경우

## 4. AI 방어 전략 (`backend/improvements/`)

```
service.generate_improvement()
  ├─ context.build_context()      선택 청구항·거절 이유·인용 위치·대응 사례 통계를 모음
  ├─ retrieval.retrieved_context() 명세서 근거 후보 검색 (IMPROVEMENT_SPEC_MODE)
  ├─ providers.get_provider()      anthropic / local_ollama / qwen / openai / azure
  ├─ service.validate_suggestion() 근거 ID·원문 인용·법조항이 실제와 맞는지 검사 (틀리면 버림)
  └─ (실패 시) 실패 이유를 알려주고 1회 재요청
```

- 프롬프트: `prompts.py` (`COMMON`, `KR`, 실험용 `KR_V2`)
- 근거 검증에 실패한 제안은 **절대 화면에 나오지 않습니다.** `IMPROVEMENT_PRUNE_INVALID=true`면 통과한 항목만 보여줍니다.

## 5. 스크립트 (자주 쓰는 순서)

| 하고 싶은 일 | 명령 |
| --- | --- |
| 앱 실행 / 종료 | `.\scripts\start.ps1` / `.\scripts\stop.ps1` → http://127.0.0.1:8501 |
| 미국 대응 사례 다시 만들기 | `uv run python scripts/build_precedents.py --download` |
| 한국 대응 사례 늘리기 (KIPRIS 키 필요) | `uv run python scripts/build_kr_precedents.py --oa-2015 --limit 50 --from-dates --per-date 5` |
| PostgreSQL에 사례 넣기 | `docker compose up -d` 후 `uv run python scripts/load_precedents_pg.py` |
| 채점표 자동 초안 만들기 | `uv run python scripts/build_gold_cases.py <출원번호> ...` |
| AI 방어 전략 실행 기록 | `uv run python scripts/run_kr_llm_cases.py --eval --label <이름>` |
| 실행 결과 채점 | `uv run python scripts/grade_llm_runs.py --repeats 3 <이름> ...` |

KIPRIS 키는 월 한도가 있어 팀원별로 받는 게 좋습니다. 받은 응답은 캐시되므로 같은 명령을 다시 돌려도 한도를 다시 쓰지 않습니다.

## 6. 설정 (`.env`)

`.env.example`을 복사해서 씁니다. 자주 바꾸는 것만:

| 이름 | 뜻 | 기본값 |
| --- | --- | --- |
| `IMPROVEMENT_PROVIDER` | AI 방어 전략에 쓸 공급자 | `anthropic` 또는 `local_ollama` |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Claude 키 / 모델 | `claude-sonnet-5-5` (품질 우선은 `claude-opus-5-5`) |
| `IMPROVEMENT_SPEC_MODE` | 명세서 근거 공급 방식: `retrieve`(예전) / `elements`(구성요소별) / `full`(전체) | `elements` |
| `IMPROVEMENT_PROMPT` | `v1`(예전) / `v2`(구체적 한정 유도) | `v2` |
| `LOCAL_LLM_MODEL` | Ollama 모델명 | `qwen3:14b` |
| `KIPRIS_ACCESS_KEY` | KIPRIS Plus REST 키 (`REST_AccessKey`도 읽음) | - |
| `SHOW_US_MODE` | 업로드 화면에 미국/한국 선택 표시 | `false` |

## 7. 자주 하는 작업

- **체크리스트 문구 바꾸기** → `backend/analysis/checklist_generator.py`
- **검토 화면 섹션 추가/수정** → `frontend/pdf_review_component/index.html`(틀), `review.js`(`drawPrecedents`, `drawAI` 등), `review.css`
- **새 거절 종류 매핑** → `backend/precedents/taxonomy.py`의 `CATEGORIES`와 `categorize()`, 테스트는 `tests/test_precedents.py`
- **LLM 공급자 추가** → `backend/improvements/providers.py`에 `complete()`를 가진 클래스 추가 후 `get_provider()`에 연결
- **채점표 추가** → `scripts/build_gold_cases.py`로 초안 → 사람이 `rubric` 검토 → `data/eval/kr/README.md` 표 갱신

## 8. 용어 사전

| 화면·발표 (쉬운 말) | 법률 용어 | 코드 이름 |
| --- | --- | --- |
| 거절 통지서 | 의견제출통지서 | `office_action` |
| 거절 이유 | 거절사유 / 법조항 | `rejection`, `statute` |
| 권리 문장 | 청구항 | `claim` |
| 특허 설명서 | 명세서 | `specification`, `SPEC-*` 근거 ID |
| 심사관이 비교한 기존 특허 | 인용발명 / 선행기술 | `citation`, `reference` |
| "쉽게 만들 수 있다"는 거절 | 진보성 (제29조제2항, §103) | `inventive_step` |
| 이미 있는 발명 | 신규성 (제29조제1항, §102) | `novelty` |
| 설명이 부족함 | 기재불비 (제42조, §112) | `description` |
| 특허 문장 수정 | 보정 | `amendment` |
| 거절이 풀림 / 안 풀림 | 해소 / 미해소 | `resolved` / `unresolved` |
| 최종 거절 / 등록 | 거절결정 / 등록결정 | `RE` / `RG` (KIPRIS 서비스) |
| 한미 거절 이름 맞추기 | 거절 유형 공통 분류 | `taxonomy.py`의 `CATEGORIES`, `categorize()` |
| 대응 사례 카드 | - | `data/precedents/*.jsonl`의 한 줄 |
| 채점표 | 평가셋 | `data/eval/kr/*.json` |
