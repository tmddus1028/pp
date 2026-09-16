# OA 상태 회귀: 원본과 사용자 정답표 재현 입력 구분

## 실제 제공 PDF

`pp_vd3.pdf`는 사용자의 `C:\Users\dltmddus\Desktop\dltmddus\pp\pp_vd3.pdf`를
바이트 그대로 복사했습니다. 원본 PDF를 수정·재저장하지 않았습니다.
SHA-256: `358fb0006ab595e02988cbbe4a83affe285ae609d2518b942a1c9712cf19fe3b`.

- 출원번호 **17/708,932**, 2023-03-16 통지, 11페이지, 기존 텍스트 레이어 사용.
- PDF p.3: Claim 20 취소. 첫 §103 거절은 Claims 1-4, 6, 8, 17-19.
- PDF p.5: Claims 5-6, p.6: Claims 7·9, p.7: Claims 10·11,
  p.9: Claims 12-14에 대한 별도의 §103 거절.
- PDF p.10: Claims 15·16은 거절된 기본항에 종속된 objection이며,
  필요한 한정을 모두 포함해 독립항으로 재작성하면 허용 가능하다고 설명.
- 직접 거절 합집합 **1-14, 17-19 (17개)**, objection **15·16 (2개)**,
  허용 **없음**, 취소 **20**.
- Wu/Ando, 출원 18/731,426, Claims 11-20 허용은 이 PDF에 없습니다.

특허 입력은 `../claim_sections/pp_ex3.pdf`(US20220325409A1)를 재사용합니다.
공개 특허 목록에는 Claim 20이 있으나 이 OA에는 취소로 적혀 있습니다.
OA 당시와 공개 특허의 청구항 버전 일치 또는 전문 정확도를 보증하는 자료가 아닙니다.

## 사용자 정답표 기반 재현 TXT

`18731426_reconstructed.txt`는 사용자 정답표와 표현을 기반으로 만든 **합성 회귀 입력**입니다.
실제 출원 18/731,426의 OA 원본을 입수한 것으로 표시하지 않습니다.

- 직접 거절: 1, 2, 3, 8.
- Objection: 4, 5, 6, 7, 9, 10. 조건부 허용 문구를 allowed로 바꾸지 않습니다.
- 허용: 11~20.
- 거절의 relied-upon 인용: Wu US20230402512, Ando US20210328013.
- Smith/Jones의 단순 언급, Regarding 문장, Allowance 섹션은 새 거절·인용문헌으로 세지 않습니다.

재현: `uv run pytest -q tests/test_oa_status.py`.
