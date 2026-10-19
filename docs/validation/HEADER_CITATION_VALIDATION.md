# PDF 여백 및 인용문헌 완전성 검증 — 2026-09-14

이번 변경은 Patent PDF의 여백 정리와 Office Action 인용문헌 추출·표시에 한정했습니다.
Claim parser/dependency parser, OCR 엔진, rejection 분류·법조항·직접 Claim 연결,
impact/evaluation 로직은 다시 작성하지 않았습니다.

## 실제 자료와 재현 자료의 구분

- 실제 특허: [US 2015/0283132 A1 공개 PDF](https://patentimages.storage.googleapis.com/09/b0/9c/a46e422b185a1c/US20150283132A1.pdf),
  출원 14/623,904, 41쪽. 로컬 사본: `data/raw/us20150283132a1/US20150283132A1.pdf`.
- 회귀 PDF: 원본의 40·41쪽을 페이지 객체 그대로 추출한
  `tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf`.
  [source.json](tests/fixtures/patent_headers/source.json)에 원본/발췌 SHA-256, URL, 페이지 대응을 기록했습니다.
- Office Action: 실제 사용자 파일은 제공되지 않았습니다.
  `tests/fixtures/citations/office_action_14623904_reconstructed.txt`는 사용자가 알려준
  출원번호, Claims 1–19, §112/§103(a), 다섯 인용문헌으로 만든 **가상 재현 fixture**입니다.
  심사관의 실제 문장이나 실제 거절 사유를 전사한 자료가 아닙니다.
- 따라서 이번 자료는 **동일 시점 실제 청구항 + 실제 전체 OA 한 쌍의 검증으로 간주하지 않습니다.**
  기존 출원 14/455,526 실제 쌍 검증은 별도 유지하며 전체 회귀에 포함했습니다.

## 여백 제거 방식과 확인 결과

`LocalAdapter`의 Patent PDF 입력에만 적용하며 TXT/JSON/OA 입력은 기존대로 처리합니다.
페이지 추출 후, `from_pages`의 정규화·페이지 오프셋 계산 전에 정리합니다.

1. pypdf visitor의 텍스트 행렬과 페이지 변환 행렬을 결합하여 실제 세로 위치를 구합니다.
   추출 문자열이 기존 추출 결과와 완전히 같은 경우에만 위치 정보를 사용합니다.
2. 상단 최대 96pt/12%, 하단 최대 64pt/8% 안의 한 줄짜리 요소를 후보로 봅니다.
   일반적인 반복 문구는 바깥쪽 32pt로 더 제한합니다.
3. 공개번호 헤더와 함께 있는 발행일·제목·페이지 번호 또는 두 페이지 이상 여백에서
   반복되는 요소를 확인하고, 유지할 본문과 최소 16pt 간격이 있는 경우에만 제거합니다.
   특정 공개번호나 저자·학술지명을 코드에 하드코딩하지 않습니다.
4. 본문 안의 동일한 공개번호, 날짜, 숫자와 Claim 문장은 유지합니다.
   불확실한 회전/복잡한 좌표, 여러 줄이 합쳐진 단위 등은 제거를 생략합니다.
5. 좌표 없는 OCR은 반복 공개번호가 있는 연속된 시작/끝 헤더 구간만 정리합니다.
   `ocr_raw_text`는 변경하지 않으며, 문자 보정·하이픈 제거·LLM 교정은 하지 않습니다.

실제 전체 특허에서 여백 요소 **68개**를 기록하고 **19개 청구항**을 추출했습니다.
Claim 1의 근거 페이지는 **40, 41**이며, 다음 경계에서 공개번호가 사라졌습니다.

```text
... 1H-indazol

3-yl)-2-((R)-2-methoxy-1-methyl-ethylamino)-4-(4-methyl
...
```

Claim 12 뒤의 `39` 및 `Oct. 8, 2015`도 Claim 본문에 남지 않습니다.
원래 텍스트 레이어의 철자·줄바꿈은 유지하며, `documents[].text[start:end] == Evidence.text`와
겹치는 페이지 번호를 검증했습니다. 정리 때문에 document ID와 문자 오프셋 값은 달라질 수 있으나
자료 구조와 오프셋의 기준은 유지합니다.

## 인용 추출·구분·중복 처리

- `patent`: US/WO 공개번호를 정규화하고 바로 앞 저자명을 연결합니다.
  기존 US 번호 저장 형식은 유지하며, WO 번호도 공백·슬래시 없는 정규형을 저장하고 화면에서 표시 형식을 복원합니다.
- `npl`: `저자 et al.` 뒤의 학술지·연도·권호/쪽수 표현을 인식합니다.
  `publication`, `year`를 별도로 기록하고 `raw_text`와 정확한 OA Evidence를 보존합니다.
  저자 이름만 나오거나 연도만 있는 일반 문장은 NPL 논문으로 만들지 않습니다.
- 특허는 정규화 번호, NPL은 저자·학술지·연도·권호/페이지를 이용해 식별합니다.
  동일 번호의 kind code 생략은 명시된 kind가 하나뿐인 경우만 연결하며, A1/A2를 서로 합치지 않습니다.
  NPL의 권/호 경계도 식별자에 남겨 `321(1)`과 `32(11)`을 구별합니다.
- 반복 인용은 같은 rejection에 노드/간선을 추가하지 않습니다.
  다른 rejection에서도 동일 문헌을 인용하면 공유 노드에 각 rejection의 근거 간선을 유지합니다.
- LLM 모드도 기존 환각/근거 검증을 먼저 수행한 뒤, 기존 action 경계로 나뉜 source chunk를
  로컬 규칙으로 보완합니다. LLM 설명 문장에서 인용을 만들어 내지 않습니다.

재현 fixture에서 R2 아래에 표시되는 결과:

| 저자 | 구분 | 문헌 |
|---|---|---|
| Lombardi et al | patent | WO2009/013126 A1 |
| Bendiera et al | patent | WO2008/074749 A1 |
| Hout et al | patent | WO2013/119950 A2 |
| Greco et al | npl | Molecular and Cellular Endocrinology, 2010, 321(1), 44–49 |
| Lipska et al | npl | BMC Cancer, 2009, 9:436, 1–9 |

노드 라벨은 저자 + 번호/NPL이고, 클릭하면 OA 인용 원문·페이지·문자 위치를 보여줍니다.
재현 JSON과 검사 결과는 각각 `data/outputs/header-citations-analysis.json`,
`data/outputs/header-citations-validation.json`에 저장합니다.

## 검증 범위

회귀에는 반복/중간 추출 헤더, 페이지 경계 화학명, 본문 속 동일한 번호/날짜 보존,
여백 근처 반복 본문 보존, OCR 원문 보존, 3개 WO/2개 NPL, 5개 노드와 중복 간선 방지,
동일 저자의 다른 논문 구분, 여러 페이지에 걸친 인용 Evidence,
LLM이 생략한 인용의 source chunk 보완, UI citation 선택을 포함했습니다.
기존 dependency/rejection/실제 PDF 쌍/OCR 테스트도 전체 실행에 포함합니다.

최종 명령 결과는 [VALIDATION.md](VALIDATION.md)의 최신 검사 표를 참고하세요.
브라우저 검사는 `scripts/browser_citation_smoke.py`로 실제 공개 특허 발췌 PDF 업로드와
가상 재현 OA를 분석하고, 다섯 노드와 Greco 원문 근거 클릭·기존 Claim 클릭을 확인합니다.

## 변경 파일

- Backend: `backend/ingestion/margin_cleaner.py` (추가), `backend/ingestion/adapters.py`,
  `backend/schemas.py`, `backend/analysis/citation_analyzer.py`,
  `backend/office_action/rejection_extractor.py` (문헌 Evidence에 Document 전달),
  `backend/llm/structured_extraction.py`, `backend/graph/graph_builder.py`.
- UI: `frontend/app.py`, `frontend/graph_component/index.html`.
- 테스트: `tests/test_pdf_margins.py`, `tests/test_citation_completeness.py` (추가),
  `tests/test_frontend.py`.
- 재현 스크립트: `scripts/validate_header_citations.py`, `scripts/browser_citation_smoke.py` (추가).
- Fixture: `tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf`,
  `tests/fixtures/patent_headers/source.json`,
  `tests/fixtures/citations/office_action_14623904_reconstructed.txt` (추가).
- 문서: `README.md`, `VALIDATION.md`, 이 문서 (추가).
- 내려받은 원본과 실행 결과: 위 `data/raw/us20150283132a1` 및 `data/outputs/header-citations-*`.

추가 패키지, DB, agent framework, 외부 OCR API는 도입하지 않았습니다.
문서 전역 별칭 해석, 서지 형식 전체 지원, 법적 판단이나 인식 정확도 보장은 이번 범위에 포함하지 않습니다.
