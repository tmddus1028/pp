# 관계 지도와 PDF 검토 연결

## 화면 및 기존 그래프와의 차이

메인 진입은 계속 PDF 검토입니다. 사이드바에 ‘관계 지도’를 추가했고, 이 메뉴에서만
전체 구조를 중심으로 한 화면을 엽니다. 왼쪽은 계층형 SVG 지도, 오른쪽은 선택 노드의 상세정보입니다.
기존 dense graph도 삭제하지 않고 청구항 분석의 ‘기존 그래프 보기’ expander 안에 보관했습니다.

초기 지도에는 Office Action, 거절 사유, backend가 이미 계산한 `primary_claims`, 인용문헌만 표시합니다.
거절별 ‘청구항 N개 펼치기’와 Claim 찾기로 나머지 Claim을 볼 수 있습니다.
같은 Claim/문헌을 여러 거절이 가리켜도 기존 graph node ID를 기준으로 한 번만 표시합니다.
노드가 많으면 지도 안에서 스크롤합니다. 880px 이하에서는 상세 패널이 아래로 이동합니다.

## 기존 결과를 사용하는 방식

`frontend/relationship_map.py`가 기존 graph의 node/edge를 표시용으로 복사하고
기존 review model의 원문·법조항·문헌·Claim 정보와 ID로 연결합니다.
Backend, OCR, PDF 좌표 adapter, Claim bbox 병합, parser, provider, evaluation, API는 변경하지 않습니다.
원본 결과 객체를 수정하거나 관계 지도 이동 때문에 재분석하지 않습니다.

Dependency는 기존 `depends_on` 간선의 방향 **상위 Claim → 종속 Claim**을 사용합니다.
Claim을 선택하면 그 Claim과 직접 연결된 부모·자식만 표시하며 전체 종속 간선을 펼치지 않습니다.
선택된 Claim에서 종속관계 표시를 끌 수도 있습니다.

Citation은 기존 `cites` 간선 **거절 사유 → 문헌**을 사용합니다.
특허/NPL/유형 미확인을 원래 metadata대로 구분하고 문헌명·번호·publication/year,
연결된 거절·법조항·관련 Claim·OA 원문을 표시합니다.
문헌의 관련 Claim은 **동일 거절 사유에 연결된 Claim**이며, 문헌이 각 구성을 개시한다는
별도 분석이나 문헌→Claim 직접 간선을 생성하지 않습니다.

## PDF와의 왕복 이동

- PDF Claim 상세의 상위·종속 Claim chip을 누르면 해당 Claim의 페이지·테두리·카드로 이동합니다.
- 관련 인용문헌 chip은 citation 상세와 Office Action 인용 위치를 엽니다.
- PDF 하단은 현재 Claim의 상위 → 선택 Claim → 직접 종속 Claim 관계를 짧게 표시합니다.
  ‘전체 관계 지도 보기’를 누르면 현재 Claim/문헌을 선택한 지도로 이동합니다.
- 지도에서 ‘PDF에서 보기’ 또는 ‘Office Action 근거 보기’를 누르면 기존 PDF component로 돌아가
  같은 항목의 첫 근거 페이지와 annotation을 엽니다. 선택한 거절 범위도 양방향으로 유지합니다.
- 이벤트 nonce를 처리한 뒤 기록하여 이전 이동 이벤트를 재실행하지 않습니다.
  체크리스트·확대 상태·원본 PDF bytes는 기존 Streamlit 세션에 유지합니다.
- 원문이 없는 missing Claim은 지도에는 표시하되 PDF 링크를 만들지 않습니다.

## 필터와 강조

전체 / 거절 사유 / Claim / 종속 관계 / 인용 문헌 필터, 거절 범위 선택과
직접 지적만 / 종속관계 표시 / 인용문헌 표시 toggle을 제공합니다.
기본 보기는 주요 직접 지적 Claim과 citation 중심이며 종속 간선은 숨깁니다.
Claim 선택 시 그 Claim의 직접 부모·자식 연결을 표시합니다.

Hover는 해당 노드에 직접 닿은 간선만 강조합니다. 클릭은 선택 상태를 유지하고
관련 OA→거절→Claim/문헌 및 선택 Claim의 부모·자식 경로를 강조합니다. 나머지는 흐리게 표시합니다.
문헌 선택의 경로는 해당 문헌을 인용한 거절을 기준으로 표시합니다.

색은 직접 지적 red, 종속 영향 amber, citation green, 거절/근거 teal, OA dark green입니다.
PDF의 OA 거절 근거도 teal로 맞췄으며 Claim의 빨간 외곽 테두리는 유지합니다.
전체 범위에서 R2가 직접 지적한 Claim은 red이고, R1만 선택하면 Claim 2·5·8·11은 amber입니다.

## 검증 자료와 범위

실제 공개 US 2015/0283132 A1 **전체 41쪽 PDF**를 업로드하여 검사합니다.
Application 14/623,904 OA 원본은 없으므로 이전과 동일하게 사용자 제공 R1/R2/문헌 정보를
반영한 재현 OA PDF를 사용합니다. 실제 OA 원문 쌍 검증으로 해석하지 않습니다.
실제 특허에서 기존 parser가 추출한 **Claim 1 → Claim 14 → Claim 15** 관계를 그대로 확인합니다.

자동 검사는 기존 결과 불변/동일 graph 간선, 실제 특허의 dependency와 patent 3개/NPL 2개,
missing Claim, PDF↔지도 이동 및 거절 범위 유지, 이전 이벤트 재실행 방지를 포함합니다.

`scripts/browser_pdf_review.py`의 브라우저 흐름에는 다음이 포함됩니다.

1. 실제 PDF Claim 14 → 상위 Claim 1 → Claim 14 → 종속 Claim 15.
2. Lombardi chip → Patent/번호/R2/관련 Claims 1–19/OA 원문 → 관계 지도.
3. 기본 9개 노드와 5개 citation, Claim 14의 부모 1·자식 15와 두 dependency 간선.
4. Hover의 직접 연결만 강조, 클릭 후 관련 R1/R2/문헌 경로 강조, PDF Claim 14 복귀.
5. Citation 필터 → Greco NPL/2010/publication → OA 초록 annotation 복귀.
6. 모든 유형/toggle, R2 Claim 19개 펼치기/접기, R1의 Claim 2 amber → PDF 종속 영향 복귀.
7. 기존 Claim 1·14·18 bbox, 페이지/검색/다운로드, 체크리스트, 보조 그래프, 명세서/도면, 실제 OCR.

최종 명령 결과는 [VALIDATION.md](VALIDATION.md)에 기록합니다.
전체 브라우저 흐름이 통과했고, 자동 테스트 143개 및 backend coverage 92%, Ruff lint/format이 통과했습니다.
추가로 900px 폭 브라우저에서 상세 패널을 지도 아래에 배치하는 것을 확인했습니다.
캡처: `data/outputs/relationship-map-claim14.png`, `relationship-map-citation.png`.

## 변경 파일 및 제한

- 추가: `frontend/relationship_map.py`, `frontend/relationship_map_component/index.html`, `map.css`, `map.js`.
- 변경: `frontend/app.py`, `frontend/legacy_views.py`, `frontend/pdf_review.py`.
- PDF component 변경: `frontend/pdf_review_component/index.html`, `review.js`, `review.css`.
- 테스트 추가: `tests/test_relationship_map.py`, `scripts/browser_relationship_flow.py`.
- 브라우저 경로 변경: `scripts/browser_pdf_review.py`, `scripts/browser_smoke.py`, `scripts/browser_citation_smoke.py`.
- 문서: `README.md`, `VALIDATION.md`, 이 문서.

실제 14/623,904 OA 원문과 실제 LLM 인증 키 호출은 검증 대상에 포함되지 않습니다.
인용 문헌 자체의 PDF는 내려받지 않으며 OA에서 인용된 위치로 이동합니다.
레이아웃은 고정 계층 배치이며 자유 노드 드래그, 그래프 편집/저장, 대규모 문서 가상화는 제공하지 않습니다.
필터와 펼침 상태는 현재 세션에만 유지됩니다.
