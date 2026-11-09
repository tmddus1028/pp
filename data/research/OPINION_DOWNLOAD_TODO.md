# 의견서 다운로드 체크리스트

PinPoint가 보여 주는 "이렇게 대응해서 등록됐다" 사례의 **출원인 주장(의견서 본문)** 을 채우기 위한 목록입니다.
KIPRIS API에는 의견서 본문이 없고, 특허청 OPD는 문서마다 보안문자(CAPTCHA)를 넣어야 해서 손으로 받습니다.

- 대상: **진보성(제29조제2항) 거절 → 대응 → 등록결정** 81건. 위에서부터 순서대로 (⭐채점표 사건이 맨 위)
- 진행: **80 / 81건 완료** (건당 1~2분)

## 받는 방법 (한 건당)
1. `OPD 열기` 클릭
2. 목록에서 **제출일 날짜의 `의견(답변, 소명)서`** 줄 → **원문** 클릭 (같은 날 `보정서`는 안 받아도 됨)
3. 보안문자 입력 → PDF 다운로드
4. 화살표 뒤 경로에 그 이름 그대로 저장 (폴더가 없으면 만들기)
   - 제출일이 "~사이"로 나온 건: 그 기간에 있는 의견서 날짜를 파일 이름 `YYYYMMDD` 자리에 넣기

## 다 받은 뒤 (또는 중간에 끊을 때)
1. `uv run python scripts/opinion_todo.py` → 받은 건이 자동으로 [x]
2. `git add data/research` → 커밋 → 푸시

## 목록
- [x] **10-2014-0001347** · 재심사 의견서 · 제출일 2016.04.14 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140001347&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140001347/opinion_20160414.pdf`
- [x] **10-2014-0001427** · 재심사 의견서 · 제출일 2016.04.25 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140001427&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140001427/opinion_20160425.pdf`
- [x] **10-2014-0002504** · 의견서 · 제출일 2015.09.18~2016.03.14 사이 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140002504&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140002504/opinion_YYYYMMDD.pdf`
- [x] **10-2014-0002880** · 의견서 · 제출일 2015.11.18 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140002880&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140002880/opinion_20151118.pdf`
- [x] **10-2014-0003199** · 재심사 의견서 · 제출일 2016.04.01 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140003199&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140003199/opinion_20160401.pdf`
- [x] **10-2019-0000844** · 재심사 의견서 · 제출일 2020.02.10 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190000844&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190000844/opinion_20200210.pdf`
- [x] **10-2019-0000874** · 재심사 의견서 · 제출일 2019.11.05 · ⭐채점표 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190000874&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190000874/opinion_20191105.pdf`
- [x] **10-2013-0092203** · 의견서 · 제출일 2019.09.03 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20130092203&code=A&docgrp=ALL&from=K) → `data/research/kr_1020130092203/opinion_20190903.pdf`
- [x] **10-2013-0106349** · 의견서 · 제출일 2020.03.06 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20130106349&code=A&docgrp=ALL&from=K) → `data/research/kr_1020130106349/opinion_20200306.pdf`
- [x] **10-2013-0130617** · 재심사 의견서 · 제출일 2020.02.24 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20130130617&code=A&docgrp=ALL&from=K) → `data/research/kr_1020130130617/opinion_20200224.pdf`
- [x] **10-2013-0136093** · 의견서 · 제출일 2020.03.05 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20130136093&code=A&docgrp=ALL&from=K) → `data/research/kr_1020130136093/opinion_20200305.pdf`
- [x] **10-2013-7034069** · 재심사 의견서 · 제출일 2019.09.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20137034069&code=A&docgrp=ALL&from=K) → `data/research/kr_1020137034069/opinion_20190909.pdf`
- [x] **10-2014-0000068** · 의견서 · 제출일 2015.11.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140000068&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140000068/opinion_20151109.pdf`
- [x] **10-2014-0000184** · 의견서 · 제출일 2015.11.24 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140000184&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140000184/opinion_20151124.pdf`
- [x] **10-2014-0000258** · 의견서 · 제출일 2015.11.25 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140000258&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140000258/opinion_20151125.pdf`
- [x] **10-2014-0000655** · 의견서 · 제출일 2015.11.30 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140000655&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140000655/opinion_20151130.pdf`
- [x] **10-2014-0001170** · 의견서 · 제출일 2015.11.03 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140001170&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140001170/opinion_20151103.pdf`
- [x] **10-2014-0001373** · 의견서 · 제출일 2015.10.30 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140001373&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140001373/opinion_20151030.pdf`
- [x] **10-2014-0001663** · 의견서 · 제출일 2015.11.06 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140001663&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140001663/opinion_20151106.pdf`
- [x] **10-2014-0002077** · 의견서 · 제출일 2015.11.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140002077&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140002077/opinion_20151109.pdf`
- [x] **10-2014-0002166** · 의견서 · 제출일 2015.12.01 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140002166&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140002166/opinion_20151201.pdf`
- [x] **10-2014-0002447** · 의견서 · 제출일 2015.10.07 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140002447&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140002447/opinion_20151007.pdf`
- [x] **10-2014-0003056** · 의견서 · 제출일 2015.11.25 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140003056&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140003056/opinion_20151125.pdf`
- [x] **10-2014-0003250** · 의견서 · 제출일 2015.11.02 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140003250&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140003250/opinion_20151102.pdf`
- [x] **10-2014-0003324** · 의견서 · 제출일 2015.11.17 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140003324&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140003324/opinion_20151117.pdf`
- [x] **10-2014-0003488** · 의견서 · 제출일 2015.12.22 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140003488&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140003488/opinion_20151222.pdf`
- [x] **10-2014-0003628** · 재심사 의견서 · 제출일 2016.04.22 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140003628&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140003628/opinion_20160422.pdf`
- [x] **10-2014-0014221** · 의견서 · 제출일 2020.08.12 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140014221&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140014221/opinion_20200812.pdf`
- [x] **10-2014-0018052** · 의견서 · 제출일 2020.02.06 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140018052&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140018052/opinion_20200206.pdf`
- [x] **10-2014-0018267** · 의견서 · 제출일 2020.03.30 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20140018267&code=A&docgrp=ALL&from=K) → `data/research/kr_1020140018267/opinion_20200330.pdf`
- [x] **10-2015-0100035** · 의견서 · 제출일 2019.08.29 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20150100035&code=A&docgrp=ALL&from=K) → `data/research/kr_1020150100035/opinion_20190829.pdf`
- [x] **10-2015-0164672** · 의견서 · 제출일 2019.10.01 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20150164672&code=A&docgrp=ALL&from=K) → `data/research/kr_1020150164672/opinion_20191001.pdf`
- [x] **10-2015-7009884** · 의견서 · 제출일 2019.09.26 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20157009884&code=A&docgrp=ALL&from=K) → `data/research/kr_1020157009884/opinion_20190926.pdf`
- [x] **10-2016-0140936** · 의견서 · 제출일 2019.05.08 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20160140936&code=A&docgrp=ALL&from=K) → `data/research/kr_1020160140936/opinion_20190508.pdf`
- [x] **10-2016-0175748** · 의견서 · 제출일 2020.08.18 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20160175748&code=A&docgrp=ALL&from=K) → `data/research/kr_1020160175748/opinion_20200818.pdf`
- [x] **10-2016-7027883** · 의견서 · 제출일 2020.10.08 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20167027883&code=A&docgrp=ALL&from=K) → `data/research/kr_1020167027883/opinion_20201008.pdf`
- [x] **10-2017-0057880** · 의견서 · 제출일 2019.11.11 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20170057880&code=A&docgrp=ALL&from=K) → `data/research/kr_1020170057880/opinion_20191111.pdf`
- [x] **10-2017-0096356** · 의견서 · 제출일 2019.09.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20170096356&code=A&docgrp=ALL&from=K) → `data/research/kr_1020170096356/opinion_20190909.pdf`
- [x] **10-2017-0119456** · 의견서 · 제출일 2019.02.21 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20170119456&code=A&docgrp=ALL&from=K) → `data/research/kr_1020170119456/opinion_20190221.pdf`
- [x] **10-2017-7037188** · 재심사 의견서 · 제출일 2020.07.10 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20177037188&code=A&docgrp=ALL&from=K) → `data/research/kr_1020177037188/opinion_20200710.pdf`
- [x] **10-2018-0047238** · 의견서 · 제출일 2019.05.13 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180047238&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180047238/opinion_20190513.pdf`
- [x] **10-2018-0048938** · 재심사 의견서 · 제출일 2019.12.30 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180048938&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180048938/opinion_20191230.pdf`
- [x] **10-2018-0072607** · 재심사 의견서 · 제출일 2020.03.30 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180072607&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180072607/opinion_20200330.pdf`
- [x] **10-2018-0078709** · 재심사 의견서 · 제출일 2020.11.05 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180078709&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180078709/opinion_20201105.pdf`
- [x] **10-2018-0082461** · 의견서 · 제출일 2019.09.05 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180082461&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180082461/opinion_20190905.pdf`
- [x] **10-2018-0082846** · 의견서 · 제출일 2020.04.06 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180082846&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180082846/opinion_20200406.pdf`
- [x] **10-2018-0090013** · 재심사 의견서 · 제출일 2020.04.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180090013&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180090013/opinion_20200409.pdf`
- [x] **10-2018-0091988** · 의견서 · 제출일 2019.12.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180091988&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180091988/opinion_20191209.pdf`
- [x] **10-2018-0097151** · 재심사 의견서 · 제출일 2020.08.21 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180097151&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180097151/opinion_20200821.pdf`
- [x] **10-2018-0114697** · 의견서 · 제출일 2020.03.09 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180114697&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180114697/opinion_20200309.pdf`
- [x] **10-2018-0119716** · 의견서 · 제출일 2019.10.02 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180119716&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180119716/opinion_20191002.pdf`
- [x] **10-2018-0123719** · 의견서 · 제출일 2019.05.30 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180123719&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180123719/opinion_20190530.pdf`
- [x] **10-2018-0129912** · 의견서 · 제출일 2020.05.11 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180129912&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180129912/opinion_20200511.pdf`
- [x] **10-2018-0132922** · 의견서 · 제출일 2020.08.10~2021.02.17 사이 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180132922&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180132922/opinion_YYYYMMDD.pdf`
- [x] **10-2018-0135073** · 의견서 · 제출일 2019.02.21 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180135073&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180135073/opinion_20190221.pdf`
- [x] **10-2018-0140889** · 의견서 · 제출일 2020.07.07 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180140889&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180140889/opinion_20200707.pdf`
- [x] **10-2018-0143947** · 의견서 · 제출일 2020.03.19 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180143947&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180143947/opinion_20200319.pdf`
- [x] **10-2018-0146156** · 의견서 · 제출일 2020.02.06 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180146156&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180146156/opinion_20200206.pdf`
- [x] **10-2018-0170433** · 의견서 · 제출일 2019.03.18 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20180170433&code=A&docgrp=ALL&from=K) → `data/research/kr_1020180170433/opinion_20190318.pdf`
- [x] **10-2018-7003241** · 의견서 · 제출일 2019.06.05 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20187003241&code=A&docgrp=ALL&from=K) → `data/research/kr_1020187003241/opinion_20190605.pdf`
- [x] **10-2018-7005253** · 의견서 · 제출일 2020.03.16 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20187005253&code=A&docgrp=ALL&from=K) → `data/research/kr_1020187005253/opinion_20200316.pdf`
- [x] **10-2018-7012676** · 의견서 · 제출일 2019.08.08 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20187012676&code=A&docgrp=ALL&from=K) → `data/research/kr_1020187012676/opinion_20190808.pdf`
- [x] **10-2018-7029817** · 재심사 의견서 · 제출일 2019.08.21 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20187029817&code=A&docgrp=ALL&from=K) → `data/research/kr_1020187029817/opinion_20190821.pdf`
- [x] **10-2019-0000903** · 의견서 · 제출일 2019.05.27 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190000903&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190000903/opinion_20190527.pdf`
- [x] **10-2019-0004633** · 의견서 · 제출일 2019.08.07 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190004633&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190004633/opinion_20190807.pdf`
- [x] **10-2019-0016072** · 의견서 · 제출일 2020.07.06 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190016072&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190016072/opinion_20200706.pdf`
- [x] **10-2019-0019880** · 의견서 · 제출일 2020.06.12 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190019880&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190019880/opinion_20200612.pdf`
- [x] **10-2019-0033994** · 의견서 · 제출일 2020.10.12 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190033994&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190033994/opinion_20201012.pdf`
- [ ] **10-2019-0041929** · 의견서 · 제출일 2020.03.04 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190041929&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190041929/opinion_20200304.pdf`
- [x] **10-2019-0086651** · 의견서 · 제출일 2020.06.11 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190086651&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190086651/opinion_20200611.pdf`
- [x] **10-2019-0112130** · 의견서 · 제출일 2019.12.03 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190112130&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190112130/opinion_20191203.pdf`
- [x] **10-2019-0112138** · 의견서 · 제출일 2019.11.28 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190112138&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190112138/opinion_20191128.pdf`
- [x] **10-2019-0116831** · 의견서 · 제출일 2020.02.03 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20190116831&code=A&docgrp=ALL&from=K) → `data/research/kr_1020190116831/opinion_20200203.pdf`
- [x] **10-2019-7015483** · 재심사 의견서 · 제출일 2021.01.26 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20197015483&code=A&docgrp=ALL&from=K) → `data/research/kr_1020197015483/opinion_20210126.pdf`
- [x] **10-2019-7033406** · 의견서 · 제출일 2020.03.26~2020.12.18 사이 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20197033406&code=A&docgrp=ALL&from=K) → `data/research/kr_1020197033406/opinion_YYYYMMDD.pdf`
- [x] **10-2020-0000462** · 의견서 · 제출일 2020.08.10 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20200000462&code=A&docgrp=ALL&from=K) → `data/research/kr_1020200000462/opinion_20200810.pdf`
- [x] **10-2020-0009383** · 의견서 · 제출일 2020.04.20 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20200009383&code=A&docgrp=ALL&from=K) → `data/research/kr_1020200009383/opinion_20200420.pdf`
- [x] **10-2020-0039217** · 의견서 · 제출일 2020.07.31 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20200039217&code=A&docgrp=ALL&from=K) → `data/research/kr_1020200039217/opinion_20200731.pdf`
- [x] **10-2020-0051811** · 재심사 의견서 · 제출일 2020.12.03 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20200051811&code=A&docgrp=ALL&from=K) → `data/research/kr_1020200051811/opinion_20201203.pdf`
- [x] **10-2020-0054728** · 의견서 · 제출일 2020.08.11 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20200054728&code=A&docgrp=ALL&from=K) → `data/research/kr_1020200054728/opinion_20200811.pdf`
- [x] **10-2020-0057122** · 의견서 · 제출일 2020.10.12 · [OPD 열기](https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=KR&appno=20200057122&code=A&docgrp=ALL&from=K) → `data/research/kr_1020200057122/opinion_20201012.pdf`
