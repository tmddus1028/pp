# 실제 OCR 인용문헌 회귀 사례

`office_action_14623904_ocr_excerpt.txt`는 사용자가 제공한 `pp_vd1.pdf`
(application 14/623,904)의 로컬 분석 결과에서 §103 거절의 첫 문단을
그대로 보존한 **발췌 fixture**입니다. 전체 Office Action을 대신하지 않습니다.

- 원본 SHA-256: `a32001165edc7237bcab3394300c9223c84135e62e9ed577d6ee03e6293c75b8`
- 원래 추출 결과: `W02013/119950 A2` (알파벳 O 대신 숫자 0)
- 재현 오류: Hout의 식별자 연결이 끊겨 뒤에 연속되는 Greco/Lipska NPL까지 누락됨
- 검사: 세 특허와 두 NPL을 추출하면서 원문과 Evidence 오프셋은 그대로 유지

OCR 원문을 교정한 파일이 아닙니다. 실제 전체 PDF/API 검증 결과와 원본 해시는
`data/outputs/audit-20260916/final-golden/`에 별도로 기록했습니다.
문제를 발견하고 보완한 개발·회귀 사례이며 독립 성능 평가 자료는 아닙니다.
