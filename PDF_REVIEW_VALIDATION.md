# PDF 중심 UI 개편 및 검증

## 화면 구성

사이드바는 220px이며 문서 업로드, PDF 검토, 청구항 분석, 근거 비교와 설정/도움말을 제공합니다.
분석 성공 후 PDF 검토를 자동으로 엽니다. 중앙 PDF와 오른쪽 Review Panel은 약 60:40으로 배치하며,
컴포넌트 폭이 880px 이하이면 패널을 아래로 내립니다. 1366×768 데스크톱을 기준으로 확인합니다.

뷰어에는 Patent/OA 문서 선택, 파일명, 이전/다음, 현재/전체 페이지, 확대/축소,
너비/페이지 맞춤, 문서 내 검색 및 원본 PDF 다운로드가 있습니다.
하단의 색상 범례와 전체/직접 지적/종속 영향/citation 필터는 PDF 스크롤 영역 밖에 유지됩니다.
오른쪽에는 요약 필터, rejection 범위 선택, 거절 사유 바로가기, 클릭 가능한 검토 카드가 있습니다.
카드는 기존 설명·법조항·원문 근거·인용문헌·종속 관계·체크리스트와 명시적 명세서/도면 링크를 표시합니다.

## PDF 렌더링 및 annotation

- `frontend/pdf_adapter.py`가 이미 설치된 pypdfium2를 사용해 요청한 페이지를 PNG로 렌더링합니다.
  원본 bytes를 변경하거나 PDF에 주석을 저장하지 않습니다. 다운로드도 업로드 원본과 동일합니다.
- 페이지 이미지는 요청 시 생성하고 현재 세션에 최대 12쪽 캐시합니다. PDFium의 native 호출은
  전역 RLock으로 직렬화해 Streamlit 동시 세션에서 겹치지 않도록 합니다.
- annotation은 `frontend/review_model.py`에서 기존 분석 응답을 표시용 모델로 변환한 결과입니다.
  `id/page/type/claim_number/statute/bbox/evidence_text/linked_rejection_id` 및 `document_id`,
  여러 줄의 `boxes`, 페이지 내부 `start/end`, `location_method`, `match_coverage`를 포함합니다.
- 여러 거절에 연결된 Claim은 `linked_rejection_ids`에 모든 ID를 보존하고 `statute`에 적용 법조항을 표시합니다.
  `linked_rejection_id` 단일 값은 연결된 거절이 하나일 때만 지정합니다.
- bbox는 원본 페이지 **좌상단 기준 0~1 비율**입니다. PDFium의 page-to-device 변환으로
  CropBox와 회전을 반영하고, 화면 확대 시 같은 비율의 overlay를 배치합니다.
- Evidence가 지정한 페이지·범위만 사용합니다. NFKC/대소문자/공백 차이는 좌표를 맞출 때만
  비교용으로 정규화하고 원문/분석 텍스트는 수정하지 않습니다.
- 우선 완전하고 유일하게 일치하는 텍스트 구간을 찾고, 그 외에는 페이지 전체의 문자 정렬을 사용합니다.
  문자 위치 일치율이 85% 미만이면 임의의 bbox를 만들지 않고 `page_only`로 표시합니다.
  이는 좌표 매칭 기준이며 법률적 확신도나 OCR 정확도 점수가 아닙니다.
- adapter의 원문 줄 좌표는 유지합니다. 표시할 때는 같은 Claim의 좌표를 페이지·열별 바깥 테두리로
  합칩니다. 두 열을 잇는 여백을 가로지르지 않으며 여러 거절이 같은 Claim을 지적해도 중복 테두리를 만들지 않습니다.
  인용문헌·명세서의 짧은 근거에는 줄 단위의 연한 강조를 유지합니다.
  변경 방식과 실제 Claim 1·14·18 검증은 [CLAIM_BORDER_VALIDATION.md](CLAIM_BORDER_VALIDATION.md)에 기록합니다.

## 양방향 선택과 색상

검토 카드 선택 → 문서/페이지 전환 → annotation 스크롤 및 일시 강조.
PDF annotation 선택 → 같은 Claim/문헌/근거 카드 활성화.
다른 annotation은 투명도를 낮춥니다. 기존 그래프는 청구항 분석 화면에서 유지하고,
선택한 Claim을 PDF로 다시 여는 버튼을 제공합니다.

색상은 기존 `impacts`를 그대로 사용합니다. 전체 보기에서 다른 rejection이라도 직접 지적되면 빨강입니다.
사용자가 제시한 R2는 Claims 1–19를 모두 직접 지적하므로 **전체 보기: 빨강 19, 노랑 0**입니다.
R1만 선택하면 직접 지적 15개와 종속 영향 **Claim 2, 5, 8, 11**의 노랑 4개가 보입니다.
별도 합성 사례에서 Claim 1 빨강, Claim 3 노랑도 검증합니다. 색상을 보여주기 위해 분석 결과를 바꾸지 않습니다.

Citation 클릭은 **Office Action에서 인용된 위치**를 엽니다. 인용 특허나 논문 원문 자체를
자동 다운로드한 것처럼 표시하지 않습니다. Paragraph [0018]/Figure 1 등은 OA 원문에서 명시된
참조가 Patent 텍스트에 확인될 때만 연결합니다. 명세서 support의 충분/불충분 판단을 새로 생성하지 않습니다.

## OCR과 backend 변경 범위

기존 `image_to_string` 호출과 분석용 텍스트·정규화·`ocr_raw_text`를 유지합니다.
같은 이미지/eng/PSM 3/DPI로 `image_to_data`를 추가 호출하고 단어·block·line·confidence·bbox를
`documents[].metadata.ocr_words`에 저장합니다. bbox가 있는 스캔은 같은 overlay 경로로 표시합니다.
추가 호출 때문에 OCR 페이지당 처리 시간이 늘어나며 worker timeout도 두 호출을 수용하도록 조정했습니다.
좌표만 실패하면 경고 및 페이지 근거를 제공하고, 실제 텍스트 OCR 실패를 성공으로 숨기지 않습니다.

Backend 변경은 `schemas.py`, `ingestion/ocr.py`, `ingestion/ocr_worker.py`, `ingestion/pdf_reader.py`의
**선택적 좌표 metadata 전달**에 한정합니다. API endpoint와 기존 필드는 유지합니다.
Claim parsing, header cleaning, rejection/§112/§103/citation 추출, dependency/graph/evaluation,
local/OpenAI/Azure provider 로직은 변경하지 않았습니다.

## 자료 및 검증 범위

실제 공개 [US 2015/0283132 A1 41쪽 PDF](https://patentimages.storage.googleapis.com/09/b0/9c/a46e422b185a1c/US20150283132A1.pdf)를 사용했습니다.
실제 Application 14/623,904 OA 파일은 아직 제공되지 않았으므로, 해당 OA에 대한 결과는
사용자가 제공한 범위·문헌 정보로 만든 **재현 PDF**의 UI 결과입니다.
실제 동일 시점 청구항 + 전체 OA 쌍을 새로 검증했다고 주장하지 않습니다.
기존 출원 14/455,526 실제 쌍의 회귀 테스트는 그대로 실행합니다.

`scripts/browser_pdf_review.py`는 다음을 확인합니다.

1. 실제 41쪽 Patent PDF + 재현 OA PDF 업로드와 PDF 검토 자동 진입.
2. Claim 1의 40·41쪽 위치, 빨강 overlay, 카드 ↔ PDF 선택.
3. 페이지 이동, 확대/맞춤, 검색 위치, 원본 다운로드 bytes 동일성.
4. WO 3개/NPL 2개, Greco 클릭과 OA 초록 overlay·정확한 원문.
5. R1 필터와 노랑 4개, 체크리스트 상태 유지, 보조 그래프와 PDF 복귀.
6. 합성 Patent/OA의 명시적 Paragraph [0018]/Figure 1 연결, 좁은 화면 배치.
7. 이미지 전용 Patent + OA의 실제 Tesseract 실행 및 빨강/노랑 overlay.

추가로 1366×768에서 사이드바 하단 설정/도움말의 가시성과 두 dialog 열기/닫기를 확인했습니다.

화면 캡처는 `data/outputs/pdf-review-desktop.png`, `pdf-review-dependency.png`,
`pdf-review-narrow.png`, `pdf-review-ocr.png`에 저장합니다.
하단 메뉴 배치까지 반영한 합성 예제 화면은 `data/outputs/pdf-review-demo.png`입니다.
최종 실행 결과는 [VALIDATION.md](VALIDATION.md)의 최신 검사 기록을 참고하세요.

## 남은 제한

- 복잡한/손상된 텍스트 레이어, OCR 오인식, 중복 문구에서 정확한 위치를 결정하지 못하면
  페이지와 원문 근거로 표시합니다. 하이라이트만으로 검토를 끝내지 않도록 원문을 함께 제공합니다.
- 문자 좌표 기반 annotation이며 자유로운 PDF 주석 편집·주석 저장·색칠된 PDF 내보내기는 구현하지 않습니다.
- 도면 이미지의 의미 해석이나 명세서 support 자동 판단은 없습니다. 명시적 paragraph/figure 텍스트 연결만 지원합니다.
- 검색은 정규화된 추출 텍스트를 사용하고 검색에 일치하는 페이지를 순회합니다. 현재 페이지의 처음 25개 일치를 표시합니다.
- 원본 파일·검토 선택·체크 상태는 Streamlit 세션에 있습니다. 영구 프로젝트 저장·로그인은 추가하지 않았습니다.
- TXT/JSON 및 원본 PDF bytes가 없는 과거 결과는 텍스트 원문 모드입니다. OCR 좌표가 없는 과거 결과는 재분석이 필요합니다.
- 추가 OCR 좌표 추출로 스캔 문서 처리 시간이 늘어납니다. 첫 검토 화면은 기존 분석이 끝난 뒤 열립니다.
- 실제 인증 키를 사용한 LLM 호출과 실제 14/623,904 OA 원본 대조는 이번 브라우저 검증에 포함되지 않습니다.

## 변경 파일

- UI: `frontend/app.py`, `frontend/styles.css` (추가), `frontend/legacy_views.py` (기존 보조 화면 이동),
  `frontend/pdf_review.py`, `frontend/pdf_adapter.py`, `frontend/review_model.py` (추가).
- 로컬 component: `frontend/pdf_review_component/index.html`, `review.css`, `review.js` (추가).
- OCR metadata: `backend/schemas.py`, `backend/ingestion/ocr.py`, `backend/ingestion/ocr_worker.py`,
  `backend/ingestion/pdf_reader.py`.
- 테스트: `tests/test_pdf_review.py` (추가), `tests/test_frontend.py` (새 기본 화면과 기존 보조 화면 확인).
- 재현 스크립트: `scripts/make_review_fixtures.py`, `scripts/browser_pdf_review.py` (추가),
  `scripts/browser_smoke.py`, `scripts/browser_citation_smoke.py` (보조 그래프 메뉴 경로 반영).
- 합성 fixture: `tests/fixtures/pdf_review/`의 PDF 5개와 README.
- 문서: `README.md`, `VALIDATION.md`, 이 문서.

구현 참고: [PDFium API와 threading 제약](https://pypdfium2.readthedocs.io/en/stable/python_api.html),
[Streamlit custom components](https://docs.streamlit.io/develop/concepts/custom-components/components-v1/intro).
