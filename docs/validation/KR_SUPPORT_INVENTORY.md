# 한국 문서 지원 inventory · 작업 전 · 2026-09-18

실제 코드를 읽은 시점의 범위입니다. O는 모든 특허에 대한 정확도 보장이 아닙니다.
독립 시제품(8502/8001)과 공통 앱(8501/8000)의 지원을 구분합니다.

| 기능 | US 현재 | KR 현재 | 이번 목표 |
|---|---|---|---|
| 특허 PDF/TXT | 텍스트·페이지 보존 | pypdf/PDFium 텍스트, 정규화 | native/mixed/scanned 페이지 처리 |
| OCR | 영어 Tesseract, 좌표/원문 | 없음 | kor+eng, 원문/정규화/좌표 구분 |
| Claim section | heading+fallback | 청구범위+단독 청구항 제목 필요 | 제목 변형과 보수적 후반부 fallback |
| 종속관계 | 단일/범위/간접, 검증 | 기초 표현+cycle/missing 검증, 머리말에 취약 | 복수/선택/범위/페이지 경계 |
| OA XML | 분석 입력 미지원 | PatentOpinionSubmission 특정 표/본문 | 기존/구형 XML semantic adapter |
| OA PDF | 텍스트/OCR | 거부 | native/scanned/mixed |
| 거절이유 그룹 | 101/112/103 등 명시 구간 | 법조항당 본문 1개 제한 | 법조항·청구항 그룹별 근거 분리 |
| 법조항 | US 원문 추출 | 특허법+제조항호 정규식 | raw/display/code, 조의 가지번호 포함 |
| Claim 상태 | rejected/objected/allowed 등 | rejected/canceled/unknown | 명시 상태와 미확인·보정 정보 분리 |
| 버전 | 사례별 수동 확인 | 출원번호만 비교·경고 | 제공 이력 기반 후보/불확실성 기록 |
| Citation | 특허/NPL·역할·dedupe | KR 번호 일부, 문서 전역 dedupe | 번호/별칭 변형 및 실제 JP 인용 포함 |
| 인용발명 PDF | 공통 업로드 없음 | 독립 시제품만 업로드/번호 연결 | 공통 API 선택 references·부분 실패 |
| 인용발명 retrieval | 공통 모델에 원문 없음 | 독립 시제품 검토 문맥 검색만 | explicit/retrieved 구분, 정확한 위치 |
| Evidence | 문자/페이지·OCR 좌표 | 독립 시제품 XML path, 공통 변환에서 소실 | XML path/PDF 위치 보존 |
| 명세서 연결 | 명시 문단/도면+개선 검토 검색 | 공통 정책이 영어/청구항 이전 문단에 치우침 | KR 문단·원문 후보 분리 |
| PDF Review | 기존 검토·scope·원문 이동 | 특허 PDF/Claim, OA XML 텍스트 | OA PDF·reference 원문도 동일 viewer |
| Claim Analysis | 상태·검색·필터·상세 | 공통 화면 사용, 상태 범위 제한 | 확장된 KR 결과의 공통 표시 |
| Relationship Map | 공통 graph | 공통 graph 사용 | 그룹/종속/문헌의 정확한 입력 |
| Evidence Comparison | 공통 화면 | 원문 범위 제한 | 원문 연결·출처 구분 |
| 개선안·수정본 | provider+근거검사·검색·diff | 한국 prompt/실문서 근거, reference 원문 없음 | 실제 reference evidence 문맥 |
| API | 8000 | 8000 jurisdiction=KR, 두 입력만 | 같은 endpoint의 optional references/이력 |
| 프론트 매핑 | review_model/evidence_comparison 등 | 공통 UI+한국 용어 | 배치/CSS 유지, 필요한 데이터 경로만 |
| 실제 자료 | US golden 3쌍+기타 | 5쌍 확보: PASS1/부분1/미지원3; 구형 XML178 미지원 | 5쌍 원문 라벨·평가, 한계 공개 |
| LLM 실제 품질 | 미검증 | 미검증(API 키 없음) | 문맥·계약 검증과 실제 품질 구분 |

## 조사한 코드

- `korean_prototype/kr_review/{ingestion,parsers,models,service,review,api}.py`
- `backend/jurisdictions/korean.py`, `backend/{main,schemas}.py`
- `backend/ingestion/{ocr,ocr_worker}.py`
- `backend/improvements/{context,retrieval,revision,providers,service}.py`
- `frontend/{app,review_model,pdf_review,evidence_comparison,improvements}.py`
- `tests/test_korean_integration.py`, 독립 한국 tests, 관련 browser 스크립트
- `data/downloads/Patent_Review_KR_Data_20260917` 원본·기존 검증 기록

## 보호 범위와 검증 원칙

US parser/expected와 공통 CSS를 변경하지 않습니다. 한국용 별도 화면을 만들지 않습니다.
현재 공통 모델에는 reference document kind·XML locator·reference source link가 없어
기존 필드를 유지하는 추가 필드가 필요합니다. KR 업로드의 PDF/선택 references 입력과
기존 화면의 source 연결은 기능을 완성하는 최소 변경이며 레이아웃 재설계가 아닙니다.
기존 미커밋 AI/Qwen 작업은 유지합니다. 실제/합성/OCR 변환 fixture와 mocked/live LLM을 구분합니다.
