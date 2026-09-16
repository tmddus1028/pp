# 로컬 OCR 회귀 fixture

이 문서는 **가상 테스트 자료**입니다. 출원번호 `14/623,904`, Claims `1-19`, §112/§103은
사용자가 제시한 형식을 사용했으나, 거절 설명과 인용문헌 조합은 테스트용으로 새로 작성했습니다.
실제 USPTO Office Action을 다운로드하거나 실제 사건 내용으로 라벨링한 자료가 아닙니다.

| 파일 | 내용 |
|---|---|
| `office_action_text.pdf` | 두 페이지 모두 실제 텍스트 레이어 |
| `office_action_scan.pdf` | 두 페이지 모두 300 DPI 이미지로만 구성, 텍스트 레이어 없음 |
| `office_action_mixed.pdf` | 1페이지 텍스트, 2페이지 이미지 스캔 |
| `expected_pages.json` | 이미지 생성에 사용한 정답 문구; OCR 출력이 아님 |
| `claims.txt` | 가상 청구항 1–19; Claim 2–19는 Claim 1에 종속 |

재생성: 프로젝트 루트에서 `uv run python -m scripts.make_ocr_fixtures`.
ReportLab 기본 Times-Roman 글꼴로 작성한 PDF를 PDFium으로 래스터화하여 플랫폼별 폰트 설치 없이 재생성합니다.
스캔 PDF에는 보이지 않는 OCR 텍스트를 넣지 않습니다.

`tests/test_ocr.py`는 로컬 Tesseract를 실제 호출하여 `Claim`, `Claims 1-19`, `35 U.S.C.`, `§ 112`,
`§ 103`, `14/623,904`, `US 2010/0123456 A1`, `8,765,432 B2`, `Smith`, `Johnson` 보존을 검사합니다.
혼합 문서의 OCR 대상은 `[2]`이며, downstream 결과는 각각 청구항 1–19에 대한 §112(b), §103입니다.
문헌 이름과 번호도 기존 parser까지 전달되는지 검사합니다.

엔진 미설치 환경에서는 `ocr_integration` 테스트만 명시적으로 skip합니다. 나머지 선택적 OCR·오류·계약 테스트는
모의 엔진으로 실행합니다. 엔진이 설치되어 있는데 인식이나 렌더링이 실패하면 skip하지 않고 테스트 실패로 처리합니다.

이 fixture는 깨끗한 인쇄체 2쪽에 대한 회귀 자료입니다. 실제 저해상도/기울임/손글씨 스캔이나 전체 특허 문서의
OCR 정확도를 대표하지 않습니다. 문자를 LLM으로 수정하거나 오인식을 정답으로 바꾸지 않습니다.
