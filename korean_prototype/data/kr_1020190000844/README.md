# 실제 한국어 검토 자료: 출원 10-2019-0000844

**2026-09-17 확보 현황 갱신:** 아래 기록의 OPD CAPTCHA와 별개로, KIPRIS Plus의
[공개 샘플 ZIP](https://plus.kipris.or.kr/kipris/kpp/FileDown.do?atchFileId=AFI_0000000000000853&fileSn=0&fileFieldName=dowFile0)에서
이 사건의 OA PDF 6쪽과 XML을 직접 확보했다. XML은 기존 파일과 SHA-256이 동일하다.
추가 다운로드 파일은 `data/downloads/Patent_Review_KR_Data_20260917/01_verified/1020190000844/`에
있다(프로젝트 루트 기준). 아래의 PDF 미확보 설명은 이전 OPD 조사 당시 기록이다.
기존 입력 파일 및 manifest의 해시는 변경하지 않았다.

전자쿠폰 시스템 및 전자쿠폰 처리 방법 / 한국기술교육대학교 산학협력단.
2019-03-12 공개 명세서·청구항과 2019-04-09 의견제출통지서를 대응시킨 개발 사례다.

| 파일 | 출처·용도 |
|---|---|
| KR20190025857A.pdf | 한국 공개공보 사본, 17쪽. 청구항 1은 3쪽 |
| office_action_20190409.xml | 사용자 제공 KIPRIS 의견제출통지서 샘플. PDF 페이지 정보 없음 |
| KR20150096573A.pdf | 통지서 인용발명 1, 13쪽 |
| KR20150090348A.pdf | 통지서 인용발명 2, 19쪽 |
| KR20150093093A.pdf | 통지서 인용발명 3, 25쪽 |

PDF는 Google Patents에서 내려받은 한국 공보 사본이며 원본 바이트를 유지했다.
주소·SHA-256은 [manifest.json](manifest.json)에 있다. 유료 데이터 구매는 하지 않았다.
원문에 명시된 기대값은 청구항 1개 / 직접 지적 [1] / 특허법 제29조제2항 / 인용발명 3개다.
이 한 사례로 다양한 한국 출원의 분석 정확도를 일반화할 수 없다.

공개공보 청구항의 전제부·7개 구성을 통지서 구성 대비와 비교했으며 표시 형식을 제외하면
일치했다. [claim_oa_comparison.json](claim_oa_comparison.json)에 두 원문과 비교 결과가 있다.
[공식 KIPRIS 이력](https://www.kipris.or.kr/khome/detail/newWindow.do?applno=1020190000844&right=kpat)도
출원번호와 OA 발송번호 9-5-2019-0256824-92를 확인한다. 공개~통지 사이 보정 기록은 없다.
출원 당시 제출 파일과 모든 보정 원문을 직접 확보해 비교했다는 뜻은 아니다.
등록공보 KR102136729B1은 청구항이 달라 이 데이터에 포함하지 않았다.

[특허청 OPD](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190000844&code=A&docgrp=ALL&from=K)에서
OA PDF 원문 링크까지 확인했으나 CAPTCHA로 다운로드하지 못했다.
화면은 XML의 실제 문단을 표시하며 OA 페이지 번호나 PDF 좌표를 생성하지 않는다.
샘플 제공 조건과 상업 서비스의 대량 데이터 이용조건은 별도 확인 대상이다.
