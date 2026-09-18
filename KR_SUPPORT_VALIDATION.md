# 한국 문서 지원 확대 · 2026-09-18

한국 분석 모듈과 공통 adapter를 확장했습니다. 기존 미국 parser·계산·CSS는 변경하지
않았습니다. 공통 화면을 재사용하며 한국 업로드 영역에 접힌 선택 인용발명 입력을 추가하고,
기존 문헌 카드에서 실제 원문으로 이동하도록 연결했습니다.

**실제 5개 사건 × OA XML/PDF = 10개 조합이 동결 라벨 비교를 통과했습니다.**
이는 개발·회귀 사례의 결과입니다. 미지 문서의 일반 정확도, 실제 스캐너 자료,
실제 AI 대응안 품질까지 통과했다는 의미가 아닙니다.

## 1. 작업 전 inventory

구현 전 코드를 조사한 [KR_SUPPORT_INVENTORY.md](KR_SUPPORT_INVENTORY.md)에
US/KR/목표와 조사 파일을 기록했습니다. 당시 한국은 native 특허와 특정 XML 중심이었고,
OA PDF·한국어 OCR은 미지원, 공통 앱 reference 업로드와 실제 원문 검토 문맥도 없었습니다.
기존 미커밋 AI/Qwen/수정본 작업은 보존했습니다.

## 2. 작업 후 기능 matrix

O = 아래 범위에서 실행 확인, 부분 = 구현은 있지만 실제 자료 검증 범위가 제한됨.

| 기능 | 작업 전 KR | 작업 후 KR | 검증 범위 |
|---|---|---|---|
| native 특허 PDF/TXT | O | O | 실제 5개 특허, TXT 단위/API |
| 스캔·혼합 특허 OCR | X | 부분 | 실제 공개 문서를 이미지로 변환한 1사건 |
| OA XML | 특정 1사건 | O | 2019년 5사건 + 구형 구조 추출 검사 |
| OA native PDF | X | O | 실제 5사건 |
| OA 스캔·혼합 PDF | X | 부분 | 공개 OA 6쪽 이미지/일부 이미지 변환 |
| 청구항 탐지·종속관계 | 제한 | O | 실제 36항 + 변형·오류 단위 테스트 |
| 거절이유·법조항 | 제한 | O | 상위 사유 10개, 5종 법조항 |
| Claim 상태 | 일부 | 부분 | 실제 rejected/pending, 나머지 합성 단위 검사 |
| 보정 청구범위 선택 | X | 부분 | API·해시·날짜·명시 선택, 실제 이력 미검증 |
| 인용문헌 추출·중복 제거 | 제한 | O | KR/JP/NPL 고유 8문헌 |
| reference PDF 연결 | 독립 시제품 | O | 공통 앱 2사건, 실제 5 PDF 번호 대조 |
| reference/명세서 검색 | 공통 앱 부족 | 부분 | 실제 원문 후보 + 지정 위치, 의미 정답 미평가 |
| PDF/XML evidence | path 일부 소실 | O | 문자·페이지·XML path 보존 |
| PDF 검토 | 일부 | O | 실제 OA PDF/XML·reference 이동·scope |
| 청구항 분석 | 공통 화면 | O | 원문·상태·종속·선택 이동 |
| 관계 지도 | 공통 화면 | O | 동일 graph, 중복 없는 문헌 노드 |
| 근거 비교 | 원문 제한 | O | 실제 원문·검색 후보 구분 |
| 개선안 문맥 | reference 본문 없음 | O | 2사건 실제 발췌, LLM 응답은 MOCK |
| 수정본 검증 문맥 | reference 본문 없음 | 부분 | diff/검색/근거검사·MOCK; 실제 모델 미검증 |
| 공통 API·전환 | 두 입력 | O | 8000 유지, KR/US 전환·선택 초기화 |

이 20개 묶음 중 범위를 제한한 실행 확인 14개, 부분 검증 6개입니다.
부분 검증을 전체 PASS로 계산하지 않습니다. 기존 2015년 XML 검사에는 미지원 13건이 남습니다.

## 3. 추가한 입력 형식

- 한국 특허와 의견제출통지서의 native PDF, 스캔 PDF, 혼합 PDF.
- 기존 Row/Entry 형태와 구형 P 요소 형태의 KIPRIS XML.
- 통지서 TXT 및 공통 `/analyze/text?jurisdiction=kr`의 XML/TXT 구분.
- 같은 `/analyze/files`의 선택 `references`, `amendments`, `version_history`.

파일 크기 제한·XML DTD/외부 엔터티 차단을 유지합니다. 출원번호 불일치,
없는 청구항, 표/본문 매핑 모호함은 오류입니다. 인용발명 하나가 읽히지 않으면
해당 원문만 사용 불가 경고를 남기고 사건 분석은 유지합니다.

## 4. 청구항 parser

`청구항 1.`, `청구항 제1항.`, `【청구항 1】`, `[청구항 1]`, 공백 변형을 지원합니다.
제목이 없으면 문서 후반의 1→2 연속 번호와 실제 종속항 문장을 함께 요구합니다.
숫자 목록만으로 청구항을 만들지 않습니다. 알려진 페이지 머리말/꼬리말은 정규화 단계에서
제외하고 제거 기록과 raw page text를 남깁니다.

단일·복수·범위·선택·간접 종속, 삭제된 부모/없는 부모/순환을 검사합니다.
0902의 청구항 6처럼 제목과 본문이 서로 다른 페이지에 있는 경우를 검증했습니다.
OCR 제목 오타 fallback은 자모 거리와 양쪽 구간 경계를 요구하며 경고를 남깁니다.
그 과정에서 원문 글자를 고쳐 쓰지 않습니다.

## 5. OA parser

거절표와 명시적 거절 본문의 법조항·청구항 범위를 대조합니다. 일반 청구항 언급이나
인용 설명으로 새 거절을 만들지 않습니다. 설명 기재불비 사유는 `subject=description`,
빈 claims로 보존합니다. 서로 다른 법조항/상위 거절번호는 분리합니다.
한 본문에 여러 표 행을 정확히 대응시킬 수 없으면 오류입니다.

구형 XML 178개 중 **165개 추출, 13개 명시적 미지원 오류**입니다.
165개는 수동 정답·청구범위 짝 검증이 없어 정확도 PASS가 아닙니다.
[구형 XML 개별 결과](data/outputs/kr_parity/legacy_xml.json).

상위 거절 내 세부 항목별 인용 조합을 완전히 별도 rejection으로 나누지는 않습니다.
예컨대 0874 R2는 대상 1–9와 인용 1+2를 상위 그룹으로 보존합니다.
이를 모든 청구항에 두 문헌의 동일한 구성 대응이 확인됐다는 의미로 사용하면 안 됩니다.

## 6. OCR 방식

native 텍스트가 페이지당 30자 미만이면 PDFium 텍스트를 재시도하고, 부족하면 PDFium
300 dpi 렌더링(40MP 상한) → Tesseract OEM1/PSM6 `tessdata_best/kor`를 실행합니다.
원본 PDF 재저장 및 LLM 보정은 없습니다. 스캔 외 native 페이지는 유지합니다.
raw OCR, 정규화 텍스트, 페이지, 단어 bbox·신뢰도, OCR 사용 경고를 별도로 보존합니다.

공식 모델 URL·SHA-256·라이선스는
[ocr_model.json](korean_prototype/data/ocr_model.json)에 있습니다.
설치: `uv run python korean_prototype/scripts/install_korean_ocr.py`.
Tesseract 자체 설치도 필요합니다. `KR_TESSERACT_CMD`, `KR_TESSDATA_DIR`로 경로를 지정합니다.
현재 kor 모델은 혼합 영어 약어에 오류가 남습니다.

## 7. 법조항·상태·버전

법조항은 원문, display, jurisdiction, canonical code를 함께 보존합니다.
실제 검증: **29조2항, 29조1항2호, 42조3항1호, 42조4항1호, 42조4항2호**.
파서는 조/조의 가지번호/항/호를 일반적으로 처리하며 법의 적용 타당성을 판정하지 않습니다.

KR 상태는 rejected/objected/allowable/withdrawn/canceled/amended/pending/unknown과
raw 표현·근거를 보존합니다. 공통 화면은 allowable→allowed, amended→pending으로
매핑하되 `source_status=amended`가 남습니다. 미언급 항을 허용으로 추정하지 않습니다.

제공 보정본의 날짜·해시로 OA 이전 후보를 찾습니다. 명시적 `selected_sha256`이 있을 때만
해당 파일을 사용하고, 이력 완전성을 모르므로 uncertain을 유지합니다.
보정 이력 API는 합성 이력으로 검증했습니다. 실제 보정서 이력 검증이나 새 입력 화면은 없습니다.

## 8. Citation normalization

KR 번호의 공백·하이픈·국가 코드 변형, JP 공개번호와 평성 번호,
OA에서 확인한 비특허문헌 서지 정보를 정규화합니다. 번호가 불충분하면 unknown/low로
남깁니다. canonical 문헌 객체 하나와 여러 rejection 연결을 유지합니다.
0948의 R3/R4는 같은 NPL 하나를 공유합니다.

## 9. Evidence linking

업로드 PDF 본문에서 읽은 문헌번호와 OA 인용번호가 정확히 일치할 때만 연결합니다.
불일치/읽기 실패는 경고이며 임의 연결하지 않습니다. 페이지·문자 위치를 원문에 대조합니다.
XML은 요소 경로를 공통 evidence까지 유지하고 기존 텍스트 뷰어에 표시합니다.
XML의 화면 p.1은 논리 페이지로, OA PDF의 물리 페이지가 아닙니다.

명시 문단·청구항·도면·페이지 지목은 해당 문헌의 표현 범위에서 우선 확인합니다.
없으면 어휘 겹침 기반 후보를 검색합니다. `examiner_explicit_evidence`와
`system_retrieved_evidence` 및 confidence를 구분합니다. 검색은 의미상 지지 판정이 아닙니다.
도면 번호 링크는 도면 페이지 위치를 가리킬 뿐 도형 자체의 의미를 분석하지 않습니다.

## 10–11. 실제 fixture와 expected / actual

원본·출처·해시·수동 라벨: [data/fixtures/korean](data/fixtures/korean/README.md).
개별 실제 결과: [parser_metrics.json](data/outputs/kr_parity/parser_metrics.json).

| 출원 | 청구항 expected=actual | 상위 거절 expected=actual | 상태 expected=actual | 고유 문헌 |
|---|---|---|---|---:|
| 10-2019-0000844 | 1 | R1 29(2): 1 | rejected 1 | 3 |
| 10-2019-0000874 | 1–9 | R1 42(4)(2):5–7; R2 29(2):1–9 | rejected 1–9 | 2 |
| 10-2019-0000902 | 1–16 | R1 42(4)(2):1–10 | rejected1–10; pending11–16 | 0 |
| 10-2019-0000903 | 1 | R1 42(4)(2):1; R2 29(2):1 | rejected1 | 2 |
| 10-2019-0000948 | 1–9 | R1 42(3)(1):설명; R2 42(4)(1):1–9; R3 29(1)(2):1–9; R4 29(2):1–9 | rejected1–9 | 1 |

각 사건의 XML/PDF 입력 결과가 모두 위 라벨과 일치했습니다. 공개된 공식 샘플을 사용하며,
등록 후 청구범위를 임의 대입하지 않았습니다. 보정 이력 완전성은 확인되지 않았으므로
모든 실제 fixture의 청구범위 버전은 uncertain입니다.

## 12. 정량 평가

5개 고유 사건을 두 형식으로 반복한 **개발·회귀 데이터**입니다. 독립 10사건이 아닙니다.

| 측정 | 결과 | 분모·범위 |
|---|---|---|
| 청구항 번호 정확도 | 1.000 | 36항 × 2, 예상/실제 집합 비교 |
| 종속관계 exact accuracy | 1.000 | 72항의 부모 목록 전체 비교 |
| 거절 대상 precision/recall/F1 | 1.000/1.000/1.000 | TP104, FP0, FN0, 상위 사유-항 쌍 |
| 법조항 exact accuracy | 1.000 | 상위 사유 10개 × 2 |
| 문헌 precision/recall/F1 | 1.000/1.000/1.000 | TP16, FP0, FN0, 고유 문헌/사건/형식 |
| 상태 exact accuracy | 1.000 | 실제 rejected/pending 72항 |
| reference 연결 | 5/5 고유 PDF | 2사건의 제공 파일만, 형식별 반복 총10/10 |
| 수동 evidence 시작 페이지 | 82/82 | 청구항 본문72 + PDF 거절10 |
| evidence 내부 위치 일치 | 558/558 | 문자열 slice와 페이지 교차 범위 |

마지막 두 항목은 glyph/bbox 정확도나 근거의 기술적 타당성 지표가 아닙니다.
reference 없는 3사건의 0/0을 reference 정확도 100% 분모에 넣지 않았습니다.

## 13. OCR 평가

[OCR 결과](data/outputs/kr_parity/ocr/metrics.json).
공개 문서를 300 dpi로 이미지화한 파생 자료이며, 실제 스캐너 자료가 아닙니다.

| 입력 | 핵심 결과 | OCR 범위 |
|---|---|---|
| 0844 특허 p.3 이미지 PDF | 청구항1 추출 | 1쪽 |
| 0844 OA 전체 이미지 PDF | 29(2), 대상1, 인용번호3개 exact | 6쪽 |
| 0844 특허 mixed | 청구항1, native p.1 유지 | p.3만 OCR |
| 0844 OA mixed | 법조항/대상/인용번호 exact | p.2만 OCR |

공백을 제외한 alignment CER 추정: 특허 **5.89%**, OA **6.02%**,
핵심 거절 도입 문장 **4.63%**. 이는 SequenceMatcher alignment 추정이며
최소 편집거리 CER 또는 WER로 표시하지 않습니다.
표의 일부 글자가 흐트러져 명시적 거절 문장으로 대체 추출한 사례가 있으며 경고합니다.
핵심 필드의 일치가 본문 전체의 정확성을 의미하지 않습니다.

## 14. 브라우저·화면·상태

Edge headless로 실제 로컬 HTTP 앱을 조작했습니다.

| 화면/검사 | 결과 |
|---|---|
| 한국 업로드 | 실제 0874 특허+OA PDF+reference2 업로드 PASS |
| PDF 검토 | 9/0/0/2, R1 3/0/0/0, R2 9/0/0/2; type필터와 summary 분리 PASS |
| Claim/OA 이동 | Claim7 유지, OA PDF 이동, 원 분석 JSON 불변 PASS |
| Citation | 카드2개, 실제 reference PDF 이동, source 후보 PASS |
| 청구항 분석 | 기존 화면 렌더·원문·선택 및 개선/수정 workflow PASS |
| 관계 지도 | 기존 graph 렌더·원문, 중복 문헌 없음 PASS |
| 근거 비교 | 기존 배치, 실제 reference 후보/명세서 표시 PASS |
| US→KR→US | 동일 세션 전환·선택/필터 초기화 PASS |
| KR→US→KR | 동일 세션 scope 및 revision 결과 초기화 PASS |
| 긴 문장 | 1920/1440/1280/1024px 네 화면 자연 줄바꿈 PASS |
| 미국 UI 전후 | 네 화면 픽셀 및 CSS/geometry hash 동일 PASS |

[KR 브라우저 기록](data/outputs/kr_parity/browser/checks.json),
[스크린샷 폴더](data/outputs/kr_parity/browser),
[US 전후 캡처](data/outputs/jurisdiction).
미국 줄바꿈 검사는 24개 화면영역/viewport 조합에서 최소 본문폭302px,
검사 영문 문장은 최대3줄이었습니다. 새 한국 전용 화면이나 CSS는 만들지 않았습니다.
브라우저는 실제 한국 2사건 중심이며 모든 5사건의 모든 클릭 조합을 검사한 것은 아닙니다.

## 15. 개선안 문맥

0844는 실제 인용발명 발췌9개+명세서 후보3개,
0874는 인용발명 발췌6개+명세서 후보3개가 전달됨을 확인했습니다.
발췌마다 제공 문서 ID·정확한 text/start/end/page를 검사합니다.
원문이 없으면 original_available을 거짓으로 유지합니다. 단순 한국어 prompt 변경이 아닙니다.

## 16. 수정본 검증 문맥

수정 요소별 명세서 검색에 더해 업로드된 실제 reference에서도 발췌 후보를 검색합니다.
선행기술 비교 응답은 해당 거절에 연결된 citation_original 근거 ID와 정확한 인용을 요구합니다.
조회한 일부 발췌를 근거로 전체 문헌에 구성이 없다고 확정하지 않습니다.
diff와 후보 검색을 의미상 지지 판정으로 대신하지 않습니다.

브라우저에서 개선안 생성→수정 입력→수정 검증·이력·캐시·scope 분리·provider 오류를
실행했습니다. **HTTP Ollama MOCK 응답**이며 실제 Ollama/Qwen/Azure 추론이 아닙니다.
실제 모델 키가 없어 AI 품질·응답 시간·토큰 비용·대응안 타당성은 테스트하지 못했습니다.

## 17. US regression 및 실행 기록

- 루트 전체 테스트 **382 PASS**, 이후 추가한 API 이력/번호 불일치 검사 포함
  한국 전용 **31 PASS**(기존29+추가2). 독립 한국 환경 **56 PASS**.
- 14/623,904: 공개특허 + **재구성 OA fixture** 검사 PASS. 실제 전체 OA 검증으로 표시하지 않음.
  ALL19/0, R1 15/4(2,5,8,11), R2 19/0과 선택·scope 불변 PASS.
- 15/914,356: 실제 입력 PDF47/13쪽, 청구항1–20, §103 사유3개, 문헌5개 PASS.
- 17/708,932: 실제 OA fixture, 직접17/Objection2/허용0,
  relied7/supporting1/not-relied2 유지. 관련 상태·문헌 테스트39 PASS.
- 작업 전 해시와 대조한 US parser/ingestion/graph/service/CSS 보호 파일 **27개 변경0**.
  [해시 대조 결과](data/outputs/kr_parity/us_protected_hash_check.json).
- Ruff 검사 PASS. 테스트 경고2개는 기존 Starlette/httpx·anyio deprecation입니다.

기존 US golden expected는 변경하지 않았습니다. 한국 capability 기대값만 새 실제 동작에
맞춰 보강했고, 정답으로 쓰는 원문 라벨과 자동 결과를 구분했습니다.

재현 명령(프로젝트 루트):

```powershell
uv run python -m pytest -q
uv run python -m scripts.validate_kr_parity
uv run python -m scripts.validate_kr_ocr
uv run python -m scripts.validate_header_citations
uv run python -m scripts.validate_pdf_fallback
uv run --project korean_prototype python -X utf8 scripts/browser_kr_parity.py
uv run --project korean_prototype python -X utf8 scripts/browser_jurisdiction.py
uv run --project korean_prototype python -X utf8 scripts/browser_readable_text.py
uv run --project korean_prototype python -X utf8 scripts/browser_review_scope.py
uv run --project korean_prototype python -X utf8 scripts/browser_revisions.py
```

브라우저 검사는 API8000/UI8501이 필요합니다. revisions 스크립트는 별도의 임시 모의 서버를
사용하고 종료 시 정리합니다. 실제 공급자로 자동 요청하지 않습니다.

## 18. 테스트하지 못한 부분

- 실제 모델 출력: API 키 없음. 모의 응답의 PASS와 구분.
- 실제 저품질·회전·복사기 스캔과 충분한 OCR corpus: 확보 자료 없음.
- 실제 보정 이력 전체와 심사 적용 버전: 이력 자료 없음.
- 허용/철회/삭제/보정 상태가 명시된 실제 여러 OA: 현재 golden 구성에 없음.
- 0903 일본 원문2개와 0948 NPL 본문: 이 fixture에 원문 미확보, 연결 정확도 미평가.
- 모든 5사건의 전체 브라우저 클릭 조합, 스캔 bbox의 수동 좌표 정답: 미수행.
- 모든 시기의 XML/심사 문서, 미지 사건 독립 holdout, 법적·기술적 정답 평가: 미수행.

## 19. 남은 한계

구형 XML13건은 표/본문 매핑을 확신할 수 없어 실패합니다. 상세한 하위 인용 조합 분리,
전부 허용된 통지서처럼 거절표가 없는 문서, 외국 문헌 PDF 자체의 서지 파싱,
OCR 한영 혼합·표 인식은 추가 개선이 필요합니다. 검색 후보의 의미상 타당성을 아직
수동 gold로 평가하지 않았으며 검색 점수가 지지를 보증하지 않습니다.

현재 공개공보와 OA가 같은 출원이라는 확인을 넘어, 심사 당시 버전 동일성은 확정하지
못합니다. API 보정 후보 선택은 이 한계를 표시하며 해결된 것처럼 숨기지 않습니다.

## 20. 현재 완성도 평가

**한국 문서 검토 시제품 약 6.5/10, 실서비스 준비도 약 5/10**으로 평가합니다.
이는 주관적 평가이며 정확도 백분율이 아닙니다. 기존 공통 화면에서 실제 문서 검토에
쓸 수 있는 범위는 늘었지만, 실제 스캔·보정 이력·상태 다양성·실제 AI 품질까지
충분히 검증하지 못해 미국과 완전히 동등하거나 한국 지원이 완료됐다고 결론내리지 않습니다.

## 변경 파일 묶음

- 한국 분석: `korean_prototype/kr_review/{ingestion,parsers,models,service,oa,ocr,links,status,versions}.py`
- 공통 연결: `backend/{main,schemas}.py`, `backend/jurisdictions/korean.py`
- 검토 문맥: `backend/improvements/{context,models,retrieval,revision,revision_models}.py`
- 기존 UI 데이터 연결: `frontend/{app,review_model,evidence_comparison}.py`,
  `frontend/pdf_review_component/review.js`
- fixture/검증: `data/fixtures/korean/`, OCR 모델 manifest·설치 스크립트,
  `tests/test_kr_parity.py`, 관련 한국 기대값 및 browser/validation 스크립트
- 문서: 루트 README, 한국 README, inventory와 이 보고서

이 목록은 이번 한국 지원 작업 기준이며, 작업 전부터 있던 Qwen·수정본 파일 변경을
이번 작업에서 새로 만든 변경으로 합산하지 않습니다.
