# 공개 자료와 검증 범위

출처 URL·SHA-256은 [sources.json](sources.json)에 기록했습니다. 다운로드는 2026-09-11에 수행했습니다.

| 파일 | 자료 성격 | 용도 및 한계 |
|---|---|---|
| `official_112f_sample.pdf` | USPTO가 작성한 가상 Claim 1~6 교육자료, 3페이지 | §112(f) 해석 안내를 거절로 오인하지 않는 음성 테스트. 실제 사건이 아닙니다. |
| `US20140201856A1.pdf` | 실제 USPTO 출원공보, Google Patents PDF 미러, 127페이지 | 페이지 추출/부분 스캔 진단. 후반 청구항 페이지에 추출 가능한 텍스트가 없어 전체 PDF만으로 Claims를 추출할 수 없습니다. |
| `US20140201856A1.html` | 같은 공보의 Google Patents 공개 텍스트 미러 | 기계가 읽을 수 있는 Claims 원본. OCR 오류로 보이는 문자열도 임의 수정하지 않았습니다. |
| `US20140201856A1_claims.json` | HTML의 Claims 구간을 추출한 adapter 입력, Claim 1 한 개 | 원문 텍스트 처리 smoke test. 페이지 1은 이 JSON의 논리 페이지이며 원본 PDF 페이지가 아닙니다. |
| `application_14040405_oa_excerpt.txt` | 같은 출원 14/040,405의 실제 OA, 인쇄 페이지 17의 두 문단 발췌 | 유지된 double patenting 지적. 출원공보 이후의 Claim 2~35를 포함하므로 **동일 청구항 버전의 완전한 문서 쌍이 아닙니다**. |

OA의 공개 출처는 [USPTO PTAB 공개 문서](https://ptacts.uspto.gov/ptacts/public-informations/petitions/1529125/download-documents?artifactId=TShcY2BGuTctpTQBXCo0ikH__gGTZ6y97LNNn2JoCZfJquxZDqK8538)입니다.
웹에서 확인 가능한 본문을 발췌했으며 PDF 직접 다운로드는 HTTP 403으로 실패했습니다.
발췌 TXT의 페이지 번호 1은 로컬 파일 기준입니다. 출처의 인쇄 페이지 17은 파일 머리말에 별도 기록했습니다.

이 공개 쌍은 누락 Claim 경고와 인용 특허의 Claim 번호를 출원인의 Claim으로 혼동하지 않는지를 검증합니다.
전체 OA 이해도, 청구항별 거절 정확도, 같은 버전의 end-to-end 성공을 입증하는 벤치마크로 사용하지 않습니다.
`unknown`은 double patenting을 임의로 §103으로 바꾸지 않았다는 뜻입니다.

```powershell
uv run python -m backend.cli --patent data/raw/uspto/US20140201856A1_claims.json --office-action data/raw/uspto/application_14040405_oa_excerpt.txt --provider local --output data/outputs/public_excerpt.json
```

두 PDF는 `uv run python scripts/fetch_public_samples.py`로 다시 다운로드할 수 있습니다.
가상 데모의 정답 라벨은 상위 폴더 `demo_ground_truth.json`에 있으며 공개 USPTO 정답 데이터와 분리했습니다.

후속 실제 평가에는 **OA 당시 제출된 청구항 세트 + 전체 OA + 수동 검증된 label**이 필요합니다.
2026-09-14에 별도의 [전체 OA·미수정 청구항 검증 자료](../uspto_14455526_20160617/README.md)를 추가했습니다.
이 폴더의 버전 불일치 사례는 오류 경로 검증용으로 그대로 유지합니다.
[Office Action Research Dataset](https://www.uspto.gov/ip-policy/economic-research/research-datasets/office-action-research-dataset-patents)과
[Patent Claims Research Dataset](https://www.uspto.gov/ip-policy/economic-research/research-datasets/patent-claims-research-dataset)은 별도 자료입니다.
데이터셋마다 관측 단위와 컬럼이 다르므로 문서 수준 라벨을 청구항별 정답으로 바꾸어 사용하면 안 됩니다.
