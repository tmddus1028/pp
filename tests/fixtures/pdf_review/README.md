# PDF Review 합성 fixture

이 디렉터리의 모든 PDF는 `scripts/make_review_fixtures.py`로 만든 **가상 회귀 자료**입니다.
실제 USPTO Office Action 또는 심사관의 실제 문장을 전사한 자료가 아닙니다.

- `office_action_reconstructed.pdf`: 사용자가 알려준 14/623,904의 R1 Claim 범위
  1, 3–4, 6–7, 9–10, 12–19 / §112, R2 Claims 1–19 / §103(a), 특허 3개와 NPL 2개를 재현합니다.
  실제 공개 US 2015/0283132 A1 PDF와 함께 UI 동작을 확인하는 용도입니다.
- `patent.pdf` / `office_action_support.pdf`: Claim 1 직접 지적, Claim 2·3 종속 영향,
  명시적 Paragraph [0018]과 Figure 1 연결을 검증합니다.
- `patent_scan.pdf` / `office_action_scan.pdf`: 위 자료를 300 DPI 이미지로만 넣은 PDF입니다.
  텍스트 레이어 없이 실제 로컬 Tesseract를 실행해 좌표 overlay를 검증합니다.

번호·본문은 가상 사례이며, 이러한 검증을 실제 동일 시점 청구항/OA 쌍의 검증으로 해석하지 않습니다.
