# 검증 기록 · 2026-09-15

환경: Windows, CPython 3.11.16, `uv.lock` 의존성.

**최신 변경: 인용문헌 고유 목록 및 거절별 역할·원문 연결.**

전체 **244 passed**, backend coverage **93%**, Ruff check/format 통과입니다.
실제 pp_ex3/pp_vd3 업로드에서 고유 거절 문헌 7개, 보조 Wei 1개, 기록 Oda·Biyikli 2개를 확인했습니다.
Liu 카드 1개에 R1~R5를 연결하며, R2 인용 원문 선택 시 PDF 5페이지로 이동합니다.
18개 회귀 테스트와 실제 Edge 업로드·카드 개수·문헌별 Claim·역할 필터·원문 이동을 검증했습니다.
문헌 catalog와 연결을 분리하고 기존 API 참조 목록은 동일 canonical ID를 사용합니다.
자세한 내용: [CITATION_REGISTRY_VALIDATION.md](CITATION_REGISTRY_VALIDATION.md).

**이전 변경: OA 상태 분리 및 objection 직접 거절 집계 오류 수정.**

전체 **226 passed**, backend coverage **92%**, Ruff check/format 통과입니다.
제공된 pp_vd3.pdf는 **17/708,932**이며, 직접 거절 17 / objection 2 / 허용 0 / 취소 1(Claim 20)을 확인했습니다.
사용자 정답표의 18/731,426 사례는 별도 합성 TXT로 4 / 6 / 10 및 Wu·Ando 2개를 검증했습니다.
실제 OA와 재현 TXT를 혼동하여 결과를 덮어쓰지 않았습니다.
실제 API HTTP 200 및 Edge 업로드·Claim 15 amber·OA p.10 이동·Claim 20 취소·재현 Claim 15 허용을 확인했습니다.
자세한 원인·변경 파일·결과: [OA_CLAIM_STATUS_VALIDATION.md](OA_CLAIM_STATUS_VALIDATION.md).

**이전 변경: 제목 없는 청구항 구간 fallback 및 pp_ex3 원본 회귀.**

| 최종 실행 명령 | 결과 |
|---|---|
| `uv run pytest -q` | **205 passed**, 84.88초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | **205 passed**, backend **92%**, 152.79초 |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **102 files already formatted** |

사용자 제공 US20220325409A1 (`pp_ex3.pdf`) 18페이지에서 OCR 없이 Claim 1~20을 모두 추출했습니다.
기존 heading 탐지를 유지하고, 문서 후반의 연속 번호·청구항 문장·종속 표현을 확인하는 fallback을 추가했습니다.
같은 줄에 이어진 Claim 19·20도 구분하며, 모든 Evidence 문자 위치·페이지 일치를 검사했습니다.
실제 API 및 Edge 업로드, Claim 1 → p.17 / Claim 19·20 → p.18 이동을 확인했습니다.
함께 입력한 OA는 경로 검증용 합성 TXT입니다. 실제 대응 OA 쌍 검증은 아닙니다.
상세: [CLAIM_SECTION_FALLBACK_VALIDATION.md](CLAIM_SECTION_FALLBACK_VALIDATION.md).

**이전 변경: native PDF 열기 fallback 및 pp_ex2/pp_vd2 원본 회귀.**

| 최종 실행 명령 | 결과 |
|---|---|
| `uv run pytest -q` | **183 passed**, 80.10초 |
| `uv run pytest --cov=backend --cov-report=term-missing` | **183 passed**, backend **91%**, 135.62초 |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **99 files already formatted** |

PyMuPDF → PDFium → pypdf 순서로 PDF를 열고, pypdf의 페이지 트리 오류만으로 문서를 거부하지 않습니다.
사용자 원본 pp_ex2.pdf 47쪽 / pp_vd2.pdf 13쪽, Claim 1~20, §103(a) 거절 3개, 고유 citation 5개를
서비스·multipart API·CLI·실제 Edge 업로드에서 확인했습니다. 파일은 재저장하지 않았고 fixture 해시를 검증합니다.
검증 PC에서는 PyMuPDF DLL ImportError 이후 PDFium을 사용했습니다. 기존 OCR 및 정상 PDF 추출 회귀도 통과했습니다.
상세 원인·추가 형식 지원·수정 파일: [PDF_OPEN_FALLBACK_VALIDATION.md](PDF_OPEN_FALLBACK_VALIDATION.md).

**이전 변경: OA 근거 이동 시 Claim 선택·펼침·목록 유지.**

Claim 카드 선택과 PDF 근거 선택을 분리하고, 선택된 rejection을 목록 앞에 추가하던 조건을 제거했습니다.
Claim 내부에서 현재 R1/R2 근거와 OA 페이지를 확인하고 다른 근거 또는 청구항 원문으로 이동합니다.
별도 Edge 검사에서 실제 특허 40~41쪽 발췌와 재현 OA R1 p.3/R2 p.4로 이동·강조·목록 유지가 통과했습니다.
실제 특허 전체 41쪽과 기존 재현 OA로도 같은 흐름 및 기존 accordion·bbox·badge·지도·비교·OCR 검사가 통과했습니다.
사용자 원본 OA 자체를 검증한 것은 아닙니다.
수정 파일과 상세: [REVIEW_EVIDENCE_NAVIGATION_VALIDATION.md](REVIEW_EVIDENCE_NAVIGATION_VALIDATION.md).

**이전 변경: 근거 비교를 Evidence Comparison 전용 화면으로 분리.**

Claim/OA/명세서/선행기술의 2×2 비교 화면, Claim·지적 사유 선택, §112/§103 비교 강조를 추가했습니다.
기존 Evidence와 명시적 연결만 재사용하고, 문헌 전문·법적 support·문장별 대응을 새로 생성하지 않습니다.
실제 41쪽 특허 PDF와 재현 OA의 Claim 14로 두 OA 원문·citation 5개·상세 펼침·PDF/지도 왕복,
Claim 변경·종속 영향·900px 스택·명세서 빈 상태 및 기존 명시적 문단/도면 연결을 확인했습니다.
기존 accordion·Claim 1/14/18 bbox·badge 19개·관계 지도·OCR을 포함한 전체 Edge 검사도 통과했습니다.
설명과 수정 파일: [EVIDENCE_COMPARISON_VALIDATION.md](EVIDENCE_COMPARISON_VALIDATION.md).
[Claim 14 비교 화면](data/outputs/evidence-comparison-claim14.png).

**이전 변경: PDF 검토 카드 기본 접힘 및 단일 accordion.**

PDF 검토에 처음 또는 일반 메뉴로 재진입하면 선택·펼침이 모두 비어 있습니다.
카드 하나만 펼치고 재클릭하면 접으며, PDF annotation 클릭과 명시적 PDF 이동은 해당 카드만 엽니다.
이전 화면의 늦은 이벤트가 초기화한 카드를 다시 열지 않도록 내부 navigation 번호를 확인합니다.
초기 상태·재진입·PDF 링크·선택 없는 관계 지도 이동 회귀 4개를 추가했습니다.
실제 41쪽 특허 PDF와 재현 OA의 전체 Edge 검사에서 Claim 7→14→재클릭 접힘,
PDF 41쪽 이동·키보드·일반 재진입 접힘 및 기존 bbox/badge/관계 지도/citation/OCR 흐름이 통과했습니다.
설명과 수정 파일: [REVIEW_ACCORDION_VALIDATION.md](REVIEW_ACCORDION_VALIDATION.md).
[처음 진입 화면](data/outputs/review-accordion-initial.png).

**이전 변경: 청구항 분석을 간결한 Claim별 상태 목록으로 개편.**

OCR·시스템 안내를 접힌 처리 정보로 모으고, 작은 요약 카드와 번호순 Claim 목록을 표시합니다.
상태/법조항 필터·정확한 Claim 번호 검색·접힌 상세·PDF 이동 및 선택/체크리스트 유지 회귀가 통과했습니다.
실제 41쪽 전체 특허 PDF와 재현 OA를 사용한 Edge 브라우저 검사에서 Claim 14의 PDF 41쪽 이동,
처리 정보 숨김/펼침, 기존 bbox·badge 19개·관계 지도·citation·다운로드 및 실제 스캔 OCR 흐름도 통과했습니다.
1366px/900px에서 목록 간격과 PDF 버튼의 전체 문구를 확인했습니다.
자세한 변경과 파일 목록: [CLAIM_ANALYSIS_VALIDATION.md](CLAIM_ANALYSIS_VALIDATION.md).
[청구항 분석 화면](data/outputs/claim-analysis-desktop.png).

**이전 변경: 모든 Claim annotation의 번호 badge 표시 통일.**

실제 Edge에서 US 2015/0283132 A1 전체 PDF를 업로드해 41쪽 Claim 1–19의
badge **19개가 모두 표시**되는 것을 확인했습니다. 왼쪽·오른쪽 column 모두 같은 크기와 위치 규칙을 사용하며,
기본 너비 맞춤에서 원문과 겹치지 않습니다. 확대/축소·페이지 맞춤·너비 맞춤·최소 축소·스크롤 뒤에도
누락이나 숨김이 없고 페이지 내부에 유지됩니다. Claim 14/19 클릭 및 Review Panel 연결,
기존 annotation 좌표 객체의 불변도 검사했습니다.
기존 관계 지도·citation·검색/다운로드·bbox·명세서/도면·실제 OCR 브라우저 흐름도 통과했습니다.
Backend/OCR/parser/Evidence/bbox 병합은 변경하지 않았습니다.
자세한 정책·파일 목록: [BADGE_VALIDATION.md](BADGE_VALIDATION.md).
[41쪽 badge 화면](data/outputs/pdf-review-badges-page41.png).

**이전 변경: 보조 관계 지도와 PDF 검토 양방향 연결.**

새 회귀 5개로 기존 graph/분석 결과 불변, 실제 Claim 14의 dependency와 5개 citation,
missing Claim, 선택 항목·거절 범위의 왕복 전달과 이전 이벤트 재실행 방지를 확인했습니다.
실제 Edge 1366×768에서 US 2015/0283132 A1 전체 41쪽을 업로드하여 다음 흐름이 통과했습니다.

- PDF Claim 14 → 상위 Claim 1 → 종속 Claim 15, Lombardi Patent/번호/관련 Claim/OA 근거.
- PDF → 관계 지도: 기본 9개 노드, citation 5개, 접힌 Claim 목록.
- Claim 14 선택: 실제 Claim 1 → 14 → 15, R1/R2와 관련 문헌 경로.
- Hover의 직접 연결 강조, 선택 유지, PDF Claim 14의 빨간 테두리로 복귀.
- Greco NPL/2010/publication/관련 Claims 1–19와 OA 초록 annotation 복귀.
- 모든 유형/표시 toggle, Claim 19개 펼치기/접기, R1 Claim 2 amber와 PDF 범위 유지.
- 기존 Claim bbox, 검색/원본 다운로드/체크리스트, 접힌 이전 그래프, 명세서/도면, 실제 OCR.

추가로 900px 브라우저에서 관계 지도 상세 패널이 아래로 배치되는 것을 확인했습니다.
Backend/parser/OCR/API와 기존 Claim 좌표/병합은 변경하지 않았습니다.
OA는 실제 14/623,904 원본이 아닌 기존 **재현 PDF**를 사용했습니다.
전체 구현·파일·제한: [RELATIONSHIP_MAP_VALIDATION.md](RELATIONSHIP_MAP_VALIDATION.md).
캡처: [Claim 14 관계 지도](data/outputs/relationship-map-claim14.png),
[Greco citation](data/outputs/relationship-map-citation.png), [좁은 화면](data/outputs/relationship-map-narrow.png).

**이전 변경: Claim 전체 영역 테두리와 열별 bbox 병합.**

실제 Edge에서 US 2015/0283132 A1 전체 PDF를 업로드해 다음을 확인했습니다.
41쪽 Claim 14·18의 **각 12개 줄/조각 좌표 → Claim별 테두리 1개**,
Claim 1의 **40쪽 17개 → 1개 / 41쪽 5개 → 1개**.
두 열을 가로지르지 않는 병합, 중복 annotation 제거, 입력 모델 불변,
일반 2px/선택 3px 빨간 테두리와 연한 배경, 카드 ↔ PDF 선택을 검사했습니다.
기존 PDF 검토 브라우저 전체 흐름과 실제 OCR도 통과했습니다.
이번 변경은 frontend 렌더링에 한정하며 backend/OCR/parser/Evidence 좌표 계산은 변경하지 않았습니다.
상세 알고리즘·변경 파일·검증 범위: [CLAIM_BORDER_VALIDATION.md](CLAIM_BORDER_VALIDATION.md).
캡처: [Claim 1](data/outputs/pdf-review-claim-1-border.png),
[Claim 14](data/outputs/pdf-review-claim-14-border.png), [Claim 18](data/outputs/pdf-review-claim-18-border.png).

**이전 변경: PDF 중심 검토 UI, 원문 좌표 adapter, OCR overlay metadata.**

이번 변경으로 회귀 11개를 추가했습니다. 기존 Claim dependency, §112/§103 rejection,
여백 정리, WO/NPL 인용, 실제 출원 14/455,526 PDF 쌍, 실제 Tesseract OCR 검사가 모두 통과했습니다.
Starlette httpx/AnyIO 의존성 deprecation warning 2개는 기존과 동일합니다.

Microsoft Edge 1366×768에서 `scripts/browser_pdf_review.py`를 실행하여 다음을 확인했습니다.

- 실제 US 2015/0283132 A1 **전체 41쪽** 업로드와 PDF 검토 자동 진입.
- Claim 1 빨강, 40→41쪽 위치 연결, 카드 ↔ 하이라이트 선택, 페이지/확대/맞춤/검색.
- 다운로드 PDF와 업로드 원본의 bytes 일치, 보조 그래프 Claim 4 선택 후 PDF 복귀.
- 재현 OA의 WO 3개/NPL 2개, Greco 원문과 초록 하이라이트, 체크리스트 상태 유지.
- 전체 거절 범위의 직접 지적 19개와 R1 한정 종속 영향 4개(Claim 2, 5, 8, 11).
- 합성 사례의 Paragraph [0018]/Figure 1 원문 연결, 900px 화면에서 패널을 아래로 배치.
- 이미지 전용 합성 Patent/OA의 실제 Tesseract 실행, OCR 좌표로 Claim 1 빨강·Claim 3 노랑 표시.
- 1366×768에서 사이드바 하단 설정/도움말 표시 및 dialog 열기/닫기.

실제 Application 14/623,904 OA 원본은 제공되지 않아 사용자 제공 범위·문헌으로 만든
**재현용 OA PDF**를 사용했습니다. 이 출원의 동일 시점 청구항·전체 OA 원본 쌍을 검증한 결과는 아닙니다.
명세서/도면 링크는 원문의 명시적 참조만 연결하며 support 판단을 새로 생성하지 않습니다.
자료·구현·제한·전체 변경 파일: [PDF_REVIEW_VALIDATION.md](PDF_REVIEW_VALIDATION.md).
스크린샷: [데스크톱](data/outputs/pdf-review-desktop.png),
[종속 영향](data/outputs/pdf-review-dependency.png), [좁은 화면](data/outputs/pdf-review-narrow.png),
[OCR](data/outputs/pdf-review-ocr.png).

**이전 변경: Patent PDF 여백 정리와 WO/NPL 인용문헌 완전성 수정.**
당시 127 tests passed, backend coverage 92%, Ruff lint/format 통과.

새 회귀 20개를 추가했습니다. 기존 Claim dependency, §112/§103 rejection,
실제 출원 14/455,526 PDF 쌍, 실제 Tesseract OCR 회귀가 모두 통과했습니다.
Starlette httpx/AnyIO 의존성 deprecation warning 2개는 기존과 동일합니다.
실제 US 2015/0283132 A1 전체 41쪽에서 Claim 1의 40→41쪽 연결 및 19개 청구항을 확인했고,
여백 요소 68개가 제거된 뒤 모든 Claim/인용 Evidence의 위치·페이지 검사가 통과했습니다.
사용자 제공 다섯 문헌으로 재현한 가상 OA에서는 R2 아래 patent 3개와 NPL 2개가 중복 없이 연결됩니다.
Edge 브라우저에서 실제 특허 발췌 PDF 업로드, 5개 citation node, Greco 근거 클릭,
기존 Claim 4 클릭을 확인했습니다. `scripts/browser_citation_smoke.py`로 재현할 수 있습니다.
실제 Application 14/623,904 OA 파일과 동일 시점 청구항 쌍은 이번에 검증하지 못했습니다.
자료·알고리즘·변경 파일의 상세 기록: [HEADER_CITATION_VALIDATION.md](HEADER_CITATION_VALIDATION.md).

**이전 변경: 스캔 페이지 자동 OCR 추가.** 당시 107 tests passed,
backend coverage 92%, Ruff lint/format 통과. 실제 Tesseract 스캔/혼합 PDF와 특허 표현 보존,
실서버 업로드 검증 및 Windows 렌더러 제약은 [OCR_VALIDATION.md](OCR_VALIDATION.md)에 기록했습니다.
아래 실제 문서 1쌍의 결과는 OCR 추가 전 확보한 원본·기준 라벨 검증 기록이며 회귀 테스트에도 유지합니다.

**실제 청구항·전체 Office Action 1쌍의 PDF → 분석 → API/CLI 검증을 완료했습니다.**
출원 **14/455,526**, **2016-06-17 최종 OA 16쪽**과 **2016-07-05 미수정 청구항 목록 3쪽**을 사용했습니다.
공개 법원 부록의 원본 페이지를 보존했으며 발췌 텍스트나 합성 입력으로 대체하지 않았습니다.

## 청구항 버전과 원본

청구항 목록의 `Previously presented`, 같은 제출물의 **“No claims are amended”**, 인증된 제출 이력,
OA의 **5/6/2016 제출물에 대한 응답** 표시를 대조해 **OA 당시와 실질적으로 같은 청구항 버전**임을 확인했습니다.
5월 6일 제출 청구항 원본 파일 자체와 직접 비교한 것은 아닙니다.

7월 답변서 표지에는 OA 날짜가 5월 31일로 적혀 있으나, 실제 OA 표지와 인증 이력은 6월 17일입니다.
이 불일치를 숨기거나 입력에서 수정하지 않았고, 동일 버전 판정은 미수정 선언과 제출 이력에 근거합니다.
근거 페이지와 문서 전체 여부, 판정의 한계는 [원본·버전 검토 기록](data/raw/uspto_14455526_20160617/README.md)에 있습니다.

- [전체 OA PDF](data/raw/uspto_14455526_20160617/office_action.pdf), [전체 청구항 PDF](data/raw/uspto_14455526_20160617/claims.pdf)
- [버전 확인 근거 PDF](data/raw/uspto_14455526_20160617/version_evidence.pdf), [출처·SHA-256·페이지 매핑](data/raw/uspto_14455526_20160617/manifest.json)
- [기준 라벨](data/raw/uspto_14455526_20160617/ground_truth.json), [분석 결과](data/validation/uspto_14455526_20160617/analysis.json)
- [평가 수치](data/validation/uspto_14455526_20160617/metrics.json), [검사 결과](data/validation/uspto_14455526_20160617/checks.json)

## 실제 1쌍의 결과

`provider=local`, 실제 PDF 직접 입력. 기준 라벨은 원문 페이지를 대조해 작성했습니다.

| 검증 항목 | 결과 |
|---|---|
| 청구항 번호·상태 | **8/8 일치**: 활성 3, 4, 5, 8 / 취소 1, 2, 6, 7 |
| 거절 단위 및 소속 인용문헌 | **2/2 일치**: §101, §103 각각 3, 4, 5, 8을 지적 |
| 법조항–청구항 연결 | **8/8 일치**, Precision/Recall/F1 = 1.0 |
| 인용 특허 | **4/4 일치**, Precision/Recall/F1 = 1.0 |
| 종속관계 | **3/3 일치**, 8 → 3, 8 → 4, 8 → 5 |
| 주 청구항·추가 영향 | 두 거절의 주 청구항 8; 추가 종속 영향 0, 누락 청구항 0 |
| 근거 위치·페이지 | **37/37 Evidence 출현 위치 통과**, 그래프/체크리스트에 반복되는 근거 포함 |
| 그래프 | 노드 15개, 간선 17개; 종속관계 및 유형별 개수 일치 |
| 체크리스트 | 2개 거절에 총 6개 생성; 근거 연결 확인, 조언의 법적 타당성은 미평가 |
| 파일 업로드 API | FastAPI TestClient multipart **HTTP 200**, 서비스 결과와 동일 |
| CLI 별도 프로세스 | **종료 코드 0**, 서비스 결과와 동일 |

인용 특허는 Singhal **US20020062281**, Scipioni **US20120296821**,
Del Favero et al **US8073775**, Davis et al **US20090070263**입니다.
§102의 법조항 설명을 추가 거절로 오인하지 않았고, 이후 Advisory Action은 입력에 포함하지 않았습니다.

초기 실행은 PDF의 중복 OCR 레이어 때문에 Claim 1 중복 오류로 실패했습니다.
동일 내용을 가진 명시적 OCR 레이어의 중복 처리, `Listing of claims` 제목,
`USPAP`/`USPN` 번호 및 복합 성명·슬래시 연결 인용을 수정했습니다.
[수정 전 실패 기록](data/raw/uspto_14455526_20160617/baseline.json)을 보존했고 회귀 테스트를 추가했습니다.

재현 명령:

```powershell
uv run python -m scripts.validate_real_pair
```

이 사례를 보며 코드를 보완했으므로 **개발·회귀 검증 1쌍의 일치 결과**입니다. 독립된 평가셋의 정확도가 아닙니다.
새 OCR, 글자 단위 전사 정확도, 판례 추출, 자연어 설명의 완전성, 법률 판단은 검증 범위 밖입니다.
실제 LLM 인증 키 호출은 여전히 미검증이며, 이번 결과는 로컬 규칙 모드 결과입니다.
브라우저에서 이 실제 파일을 업로드하는 동작은 이번 검사에 포함하지 않았습니다.

## 전체 회귀 및 기존 실행 검증

| 검증 | 결과 |
|---|---|
| `pytest --cov=backend --cov-report=term-missing` | 관계 지도 추가 후 **143 passed**, backend **92% coverage** (PDF UI 개편 당시 138 passed, 여백·인용 보완 당시 127 passed, OCR 추가 당시 107 passed) |
| `ruff check .` | 통과 |
| `ruff format --check .` | 통과 |
| CLI 데모 분석 | 9 claims, 3 actions, JSON 저장 |
| 가상 fixture 평가 | rejected claims/statute-claim links/citations/dependency edges/impacts F1=1.0, 실제 성능 수치 아님 |
| FastAPI health / Streamlit health | localhost 8000 / 8501 정상 (2026-09-11 기록) |
| Edge 브라우저 smoke | 예제 → 그래프 Claim 4 클릭 → 상세 → 체크리스트 → JSON 다운로드 통과 (2026-09-11 기록) |
| OpenAI/Azure SDK transport | mock HTTP 요청/응답으로 Pydantic schema와 provider별 모델·endpoint 검증 |
| 기존 공개 PDF/실제 OA 발췌 | partial scan 및 버전 불일치 경고 확인; 이번 실제 쌍과는 별도 자료 |

PyMuPDF가 이 Windows 환경에서 DLL import에 실패하여 pypdf로 대체했습니다.
테스트에서 Starlette의 httpx/AnyIO 관련 dependency deprecation warning 2개가 발생했으며 테스트 실패는 아닙니다.
한 번의 UI 테스트에서 초기 실행 timeout이 있었고, 단독 재검증과 전체 재검증 및 실제 브라우저 검증이 통과했습니다.

화면 캡처: `data/outputs/app-preview.png`.
