# 개발 계획: AI 특허 검토 지원 MVP

## 목표와 범위

Phase 1~4를 실행 가능한 Python 모듈로 구현한다. 특허 청구항, Office Action의 거절·지적,
인용문헌을 근거 위치와 함께 연결하고 종속 청구항의 추가 검토 범위를 계산한다.
법률 판단, 대응문 작성, 청구항 수정, 등록 가능성 예측은 구현하지 않는다.

## 구현 순서

1. **Scaffold**: FastAPI/Pydantic backend, 독립된 파싱·분석 모듈, Streamlit frontend,
   설정 예시, 테스트와 로컬 데이터 디렉터리를 만든다.
2. **Phase 1**: PDF 페이지별 추출, UTF-8 텍스트/JSON ingestion, 정규화된 텍스트의
   페이지·문자 위치 보존, 손상·암호화·스캔 PDF의 명시적 오류/경고.
3. **Phase 2**: Claims 구간과 번호 파싱, 범위/복수 종속항 파싱, 중복·누락·순환 검증,
   NetworkX 방향 그래프 생성. 종속관계는 LLM에 맡기지 않는다.
4. **Phase 3**: OA를 rejection 단위로 분할하고 원문 근거를 보존한다. 기본 local 모드는
   표준 표현을 규칙으로 추출한다. OpenAI/Azure 모드는 동일한 Pydantic schema로 추출하고
   원문 근거·청구항·법조항·인용문헌을 검증한다. 불확실한 필드는 unknown/null로 둔다.
5. **Phase 4**: citation ID 정규화, 직접 지적/종속 영향 구분, 주요 청구항 계산,
   근거가 연결된 검토 체크리스트와 그래프 JSON 생성, CLI/API 결과 저장·다운로드.
6. **얇은 UI**: 두 문서 업로드/텍스트 입력, 샘플 실행, 요약·관계 그래프·Claim 선택 상세·체크리스트.
7. **평가 기반**: 집합 기반 Precision/Recall/F1, 법조항 분류, 종속 edge 및 영향 집합 평가.
   synthetic fixture와 공개 USPTO 자료를 구분하고 실제 대규모 성능으로 일반화하지 않는다.

## 검증 기준

- 각 기능 모듈에 최소 단위 테스트를 작성하고 통합/API 오류 경로까지 검증한다.
- Claim 목록/범위, 다중 종속, 누락 부모, 순환, 취소 Claim을 다룬다.
- 같은 claim의 별도 거절 사유를 보존하고 overlap chunk만 중복 제거한다.
- 근거는 정규화된 원문에서 재검증할 수 있어야 한다. 추출 실패를 정상 성공으로 숨기지 않는다.
- API 키 없는 로컬 실행을 끝까지 검증한다. 외부 LLM은 mock transport로 계약을 검증하고,
  실제 인증 정보가 없으면 실호출 검증 여부를 분명히 문서화한다.
- 공개 자료의 URL·성격·해시를 기록한다. 등록 특허와 OA 당시 청구항의 버전 차이를 명시한다.

## 기술 선택

Python 3.11+, FastAPI, Pydantic v2, pypdf, NetworkX, Streamlit, OpenAI SDK.
초기 환경 점검에서 PyMuPDF Windows DLL 로드가 실패하여 순수 Python 기반 pypdf로 선택을 변경했다.
원격 서비스 없이 local mode가 동작한다. DB/agent framework/graph DB는 사용하지 않는다.
분석 서비스는 UI와 분리하며 파일 adapter와 provider protocol을 교체할 수 있게 한다.

## 후속 범위

복잡한 레이아웃 복원, amendment 이력 정합성, Specification/Figure 연결,
실제 라벨링 코퍼스 확대와 정량 평가, 사용자 인증·운영 배포는 후속 단계다.

## 구현 결과 · 2026-09-14

- Phase 1~4 파이프라인, FastAPI/CLI, Streamlit UI, 클릭 가능한 관계 그래프 구현.
- OpenAI/Azure 구조화 출력 provider와 원문 근거 검증 구현. 실제 키를 이용한 호출은 미검증.
- 스캔 페이지에만 300 DPI 로컬 Tesseract OCR 자동 fallback 및 원문·페이지 metadata 추가.
- 모듈/API/CLI/UI/공개 자료/OCR 회귀 테스트 107개 통과, backend coverage 92%.
- 가상 예제의 9 Claims / 3 actions / 종속 영향 및 평가 JSON 확인.
- 공개 PDF 2개, 공개 특허 HTML/Claims JSON, 실제 OA 발췌 및 출처 manifest 보관.
- 초기 공개 자료는 OA PDF 직접 다운로드 403, 특허 청구항 페이지의 내장 텍스트 부재를 확인.
- 추가로 출원 14/455,526의 전체 OA와 미수정 청구항 재제출본을 확보해 PDF/API/CLI 검증을 완료.
  같은 버전 판정 근거와 표지 날짜 불일치를 보존하고, 중복 OCR 및 인용 형식 문제를 수정.
  상세 범위와 재현 명령은 [VALIDATION.md](VALIDATION.md)에 기록.
- Specification/Figure/Claim amendment/법률 판단은 구현 범위에 포함하지 않았다.
- OCR 설치·Windows 렌더러 제약·실제 엔진 검증은 [OCR_VALIDATION.md](OCR_VALIDATION.md)에 기록.
