# 사용자 PDF 원본 회귀 fixture

`pp_ex2.pdf`와 `pp_vd2.pdf`는 사용자가 지정한 파일을 Desktop/dltmddus에서 그대로 복사했다.
PDF 객체, 이미지, OCR layer를 수정하거나 저장·재작성하지 않았다. 해시와 원문 기준 예상값은 `manifest.json`에 기록한다.

- `pp_ex2.pdf`: 47쪽, 공개된 등록특허 US 10,770,170 B2. Claim 1~16은 PDF 46쪽, 17~20은 47쪽.
- `pp_vd2.pdf`: 13쪽, Application 15/914,356의 Office Action 사본. 표지 Notification Date는 07/22/2019.
- 기존 pypdf는 후자의 `/Pages` 트리에서 `Invalid object in /Pages`로 중단된다.
- 이 개발 PC의 PyMuPDF는 DLL ImportError가 발생한다. PDFium으로 두 원본 전체 페이지를 열고 텍스트를 추출했다.

OA PDF 5쪽은 Claims 1~12,20 / 8쪽은 Claims 13,17~19 / 10쪽은 Claims 14~16의 §103(a) 거절을 시작한다.
첫 거절의 Han·Lin·Vogelstein에 두 번째 거절은 Empedocles를, 세 번째는 Newton을 추가한다.
전체 5개 문헌은 특허 3개와 NPL 2개이다. 후속 거절의 명시적인 `as applied ... above`와 정확한 저자명을 확인하여
문헌 정의를 연결하며, 같은 이름에 문헌이 여러 개이면 연결하지 않는다.

등록특허와 심사 당시 Claim 문구가 동일하다고 검증한 자료가 아니다. 문서 열기·구조 추출 회귀이며 법적 내용의 동일성이나
등록 가능성 평가는 포함하지 않는다. 원래 OCR의 철자, 줄 번호, 단어 중간 분리는 자동 교정하지 않는다.
46~47쪽은 실제 글자 원점과 x 좌표로 줄/단 읽기 순서를 정렬하며 문자를 새로 생성·삭제하지 않는 검사를 포함한다.

실행:

```powershell
uv run python -m scripts.validate_pdf_fallback
uv run pytest -q tests/test_pdf_fallback.py
uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_pdf_fallback.py
```
