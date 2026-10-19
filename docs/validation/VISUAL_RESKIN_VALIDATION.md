# Patent Review 시각 테마 변경 검증

2026-09-18. 이번 작업은 제공된 이미지의 navy / ivory / gold / teal 스타일을
기존 공통 앱에 적용한 presentation 변경이다. 새 기능, 새 메뉴, 외부 이미지·폰트
요청, 패키지 의존성을 추가하지 않았다.

## 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `frontend/app.py` | 로고·장식 SVG, 업로드 hero와 카드 wrapper, 기존 국가/입력 방식 radio의 가로 정렬 |
| `frontend/readable_text.py` | 기존 CSS 전달 경로에 공통 테마를 연결; Streamlit과 PDF/지도 iframe에 동일하게 적용 |
| `frontend/visual_theme.py` (신규) | 클릭·상태 없는 SVG 로고, 특허 도면 장식, 업로드 카드 제목 markup |
| `frontend/styles/patent_theme.css` (신규) | 공통 색상 변수, 사이드바, 제목, 카드, 업로드 영역, 버튼, iframe 외관, 반응형 스타일 |
| `scripts/validate_visual_reskin.py` (신규) | 작업 시작 시점과 파일 해시·위젯 인자·callback·key 비교 |
| `scripts/browser_visual_reskin.py` (신규) | 반응형 캡처, US/KR·입력 방식·화면 이동·설정/도움말 확인 |
| `VISUAL_RESKIN_VALIDATION.md` (신규) | 이 검증 기록 |

## 레퍼런스와 맞춘 부분

- 240px navy 사이드바, gold 기둥 로고와 메뉴 아이콘, teal 선택 메뉴.
- ivory 작업 영역, serif 제목, gold 단계 번호, 따뜻한 테두리의 paper 카드.
- 파일 업로더의 점선 테두리, 기존 버튼의 teal/paper 색상, 얇은 구분선.
- 외부 파일 없이 inline SVG로 특허 문서·도면을 표현. `aria-hidden` 및
  `pointer-events: none`으로 장식이 입력을 가로채지 않는다.
- PDF 검토, 청구항 분석, 관계 지도, 근거 비교에도 동일 테마 적용.
  PDF 배치·하이라이트 좌표, 그래프 노드/edge 배치, 비교 2×2 구조는 유지.
- 직접 지적 red, 종속 영향 yellow, 인용문헌 green 등 기존 의미 색상 유지.
- 1024px에서는 사이드바 220px와 카드 여백을 조정한다. 기존 작은 화면의
  PDF/지도 stacking과 긴 원문 공통 줄바꿈 규칙은 유지한다.

픽셀 단위 복제는 아니다. 본문·입력 위젯은 기존 글꼴과 동작을 유지하며 제목은
시스템 serif fallback을 사용하므로 설치된 글꼴에 따라 모양이 다를 수 있다.

## 기능 보호와 diff

작업 시작 시 이미 존재했던 수정 사항을 기준으로 비교했다. 기존 작업을
git HEAD로 되돌리지 않았다. 기준 해시는
`data/outputs/visual_reskin/before_hashes.json`, 기존 frontend 사본은 같은 경로의
`before/frontend/`에 보관했다.

- 보호 대상 **107개 파일 해시 일치**: backend, 한국 분석 모듈, 기존 테스트·fixture,
  frontend JavaScript 등. 이번 작업의 backend/parser/API 변경 없음.
- 기존 파일 중 달라진 파일은 **app.py와 readable_text.py 두 개**.
- **14개 interactive widget 호출의 인자·key·callback 동일**.
- upload 함수 외 기존 app 함수 AST 동일. upload diff는 장식과 wrapper 및
  radio의 표시 열 변경이며 조건 분기·검증·API 요청·파일 타입은 동일.
- PDF/지도/원문 펼치기 JavaScript 이벤트 처리 파일은 변경하지 않았다.
- 기존 테스트의 expected 값은 수정하지 않았다.

검사 결과: [functional_diff.json](data/outputs/visual_reskin/functional_diff.json).
이 비교와 아래 회귀 검사는 확인한 경로의 보호 근거이며 모든 가능한 입력에 대한
동작을 수학적으로 증명한다는 의미는 아니다.

## 테스트 결과

| 검사 | 결과 |
|---|---|
| 루트 전체 `uv run python -m pytest -q` | **384 PASS**; 기존 US 및 KR golden/분석/API/상태 회귀 포함 |
| 독립 한국 시제품 `uv run --project korean_prototype python -m pytest korean_prototype/tests -q` | **56 PASS** |
| 변경/신규 Python 파일 Ruff check, format check | **PASS**, 5개 파일 |
| `scripts/validate_visual_reskin.py` | **PASS**, 보호 파일 107개 / 위젯 호출 14개 |
| `scripts/browser_visual_reskin.py` | **PASS**, 24개 반응형 캡처, US/KR·파일/텍스트 입력·4개 검토 화면·설정/도움말 |
| `scripts/browser_readable_text.py` | **PASS**, 4개 viewport의 Claim/OA/citation/비교 원문 자연스러운 줄바꿈, 원문·선택 상태 유지 |
| `scripts/browser_review_scope.py` | **PASS**, ALL 19/0, R1 15/4 및 Claim 2·5·8·11, R2 19/0; 필터·근거 이동 유지 |
| `scripts/browser_kr_parity.py` | **PASS**, 실제 한국 PDF·인용발명 업로드, 거절 범위·문서 전환·원문 이동 |
| 기존 `browser_jurisdiction.check_korean()` | **PASS**, 실제 한국 XML 업로드, 인용문헌 선택, 지도 선택, 근거 비교, US→KR→US 격리 |
| `scripts/browser_revisions.py` | **PASS**, 기존 개선안 생성·수정본 검증 흐름, HTTP 모의 Ollama 응답 사용 |
| `scripts/validate_kr_parity.py` (`OUT`만 이번 검증 폴더로 지정) | **PASS**, 실제 한국 5개 출원의 PDF/XML 총 10개 입력, 고정 정답 비교 |
| `scripts/audit_golden_pairs.py` | **PASS**, 미국 원본 PDF 3쌍을 실제 multipart API로 재분석; 청구항·거절·종속 영향·인용문헌·근거 위치 정답 일치 |

미국 3쌍: 14/623,904는 직접 지적 19·종속 영향 0·거절 2·실제 인용문헌 5,
15/914,356은 20·0·3·5, 17/708,932는 17·2·5·7을 유지했다.
14/623,904의 R1 종속 영향은 2·5·8·11이며, 17/708,932의 내부 보조 증거 Wei와
거절 미사용 Biyikli/Oda도 그대로다. 세 문서쌍 모두 원문/페이지 위치 불일치 0건.

`browser_jurisdiction.py`의 과거 디자인 픽셀 동일성 검사는 이번 요청의 시각 변경과
충돌하므로 실행하지 않았다. 해당 파일의 기능 검사 함수를 수정 없이 호출했다.
실제 Azure/Qwen 등 유료 LLM 호출 및 출력 품질 검증은 이번 시각 변경의 검사에
포함하지 않았다. 기존 SDK deprecation 경고 2개씩은 테스트 실패가 아니다.

개발 중 업로드 native 제목을 대체하면서 생긴 기존 테스트 실패는 원래
`st.subheader`를 접근 가능한 형태로 유지하여 해결했다. 장식 화살표가 버튼의
접근 가능한 이름에 포함되는 문제도 제거하여 기존 버튼 이름을 유지했다.
브라우저 radio 검사는 Streamlit의 숨겨진 input 대신 실제 사용자가 누르는 label을
클릭하고 checked 상태를 확인한다. 기대 결과를 완화하지 않았다.

## 화면 검증 자료

1920 / 1440 / 1280 / 1024px에서 미국·한국 업로드 각각 4장과 검토 화면 4종 각각
4장, 총 **24개** 캡처를 생성했다. 카드의 화면 밖 이탈·가로 넘침, 사이드바 내용
넘침, 장식 클릭 차단 여부를 검사했다. Streamlit의 기존 사이드바 resize handle은
원래 경계를 넘는 입력 영역이므로 내용 넘침 검사에서 제외하고 기능은 유지했다.

- [반응형 검사 수치](data/outputs/visual_reskin/browser.json)
- [한국 실제 문서 정답 비교](data/outputs/visual_reskin/kr-golden/parser_metrics.json)
- [미국 원본 PDF 3쌍 정답 비교](data/outputs/visual_reskin/golden/golden-checks.json)
- [한국 업로드 1440px](data/outputs/visual_reskin/upload-kr-1440.png)
- [미국 업로드 1024px](data/outputs/visual_reskin/upload-us-1024.png)
- [PDF 검토 1440px](data/outputs/visual_reskin/PDF%20검토-1440.png)
- [관계 지도 1440px](data/outputs/visual_reskin/관계%20지도-1440.png)
- [근거 비교 1440px](data/outputs/visual_reskin/근거%20비교-1440.png)

현재 실행 중인 공통 앱 `http://127.0.0.1:8501`에 적용되어 있다.
