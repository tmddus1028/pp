# 특허 문서 장식 디테일 검증

2026-09-18. 기존 화면 구조·정렬을 유지하고 장식만 보강했다.

## 추가한 요소와 파일

- `frontend/visual_theme.py`: inline SVG 특허 문서(-6도), 동심원·중심선·치수선·
  보조선·FIG. 1 기술도면. 카드 01은 겹친 문서, 02는 문서/말풍선 outline.
  카드 장식 문구는 `SPECIFICATION & CLAIMS`, `OFFICE ACTION RESPONSE`.
- `frontend/styles/patent_theme.css`: hero 영문 editorial과 짧은 gold rule,
  카드 영문 문구 옆 gold separator, 같은 34px 숫자 밑줄, 구분선의 gold segment,
  breadcrumb/subtitle tracking, 검토 화면 제목 아래 작은 gold rule.
- 이 검증 문서 외 프로그램 변경 파일은 위 **2개뿐**이다.

외부 이미지·폰트·라이브러리·애니메이션 의존성 없음. 문서 opacity .16,
기술도면 .12, editorial .6. SVG 문서 하단은 부드럽게 흐려진다.
장식은 `aria-hidden`, `pointer-events:none`, `user-select:none`으로 적용했다.

## 배치와 기능 보호

카드의 기존 icon slot을 기준으로 장식만 absolute 배치했다. 기존 header grid,
제목/설명문, 업로더, 버튼의 크기·위치는 변경하지 않았다. Hero 역시 기존 높이와
제목 배치를 유지한다. 검토 화면에는 큰 illustration을 반복하지 않는다.

작업 전후 미국/한국 × 1920/1440/1280/1024px의 실제 DOM 좌표를 비교했다.
hero·제목·선택 영역·카드·숫자·설명문·header·icon slot·업로더·버튼·사이드바의
x/y/width/height 차이 **0px**. 제목 및 설명문과 카드 장식의 겹침 없음.

작업 시작 시점의 128개 소스/fixture 파일 중 장식 모듈·테마 CSS 외 **126개 해시 일치**.
`app.py`, backend, parser, API, state/callback, widget key, JavaScript,
기존 테스트는 변경하지 않았다.

## 반응형

| 폭 | 장식 표시 |
|---|---|
| 1920 / 1440 | hero 문서·기술도면·editorial 및 카드 아이콘·영문 caption 모두 표시 |
| 1280 | hero 축소, 카드 caption 유지 |
| 1240 이하 | 카드 영문 caption을 숨기고 기존 icon slot 안에 outline icon만 표시 |
| 1100 이하 | hero 기술도면·editorial 숨김, 문서 opacity .09 |
| 640 이하 | 기존 규칙대로 hero 장식 숨김 |

1101/1200/1240/1241/1260px 경계 부근도 추가 확인: 제목과 장식 겹침 없음.

## 검사 결과

- 작업 전후 geometry 비교: **PASS**, US/KR 8개 조합, 배치 변화 0px.
- 기존 `browser_alignment.py`: **PASS**, 24개 viewport 검사 + 600px stack.
  숫자/제목/설명문/구분선/업로드/카드 하단 정렬 유지.
- 기존 `browser_visual_reskin.py`: **PASS**, US/KR radio, 파일/텍스트 입력 전환,
  인용발명 accordion, 예제 분석, 네 검토 화면 이동, 모델 유지, 설정/도움말.
- 기존 `browser_kr_parity.py`: **PASS**, 실제 한국 PDF·인용발명 파일 업로드,
  분석 시작, 거절 범위·문서 전환·원문 이동.
- `tests/test_korean_integration.py`: **9 PASS**, 기존 통합 회귀.
- 장식 모듈 Ruff check / format: **PASS**.

이번 범위에서는 전체 440개 테스트를 다시 실행하지 않았다. 기존 smoke 및 관련
통합 회귀를 실행했으며 실제 LLM 출력 품질은 검사 대상이 아니다.

## 결과 자료

- [변경 전후 좌표 비교](data/outputs/patent_details/geometry.json)
- [보호 파일 해시 비교](data/outputs/patent_details/functional_diff.json)
- [정렬 검사](data/outputs/patent_details/alignment/browser.json)
- [한국 모드 1440px](data/outputs/patent_details/kr-1440.png)
- [미국 모드 1280px](data/outputs/patent_details/us-1280.png)
- [한국 모드 1024px](data/outputs/patent_details/kr-1024.png)

공통 앱 `http://127.0.0.1:8501`에 적용했다.
