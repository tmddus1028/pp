// 상단 탭 메뉴
let currentTab1 = 'patentTab'; // 현재 탭 메뉴1 (특실, 디자인, 상표, 심판, 기타문헌)
let currentTab2 = 'kpat'; // 현재 탭 메뉴2 (국내, 해외 등)

let filterSet = isMobile() ? false : true;

// Ajax 요청 배열
let requestArr = [];

// 분류통계용 구분값
let resultStatisLoad = false;

// 분류통계용 인명정보
let nameData = {};
let bar02 = {};

// 권리별 국내외 통합검색용
var excludeMap = {
	patent: ['kpatSearchForm', 'kpaSearchForm', 'abpatSearchForm', 'abpatTransSearchForm'],
    design: ['kdgSearchForm', 'abdgSearchForm'],
    trademark: ['ktmSearchForm', 'abtmSearchForm'],
    judgement: ['jgSearchForm', 'ipNaviConflictSearchForm', 'ipNaviPrcdnSearchForm'],
    etc: ['cntstSearchForm', 'cyberSearchForm', 'artiSearchForm'],
};

// 저장용 객체 생성 (권리별 필터 체크값)
let SaveData = {
	optionData: {},
	filterData: {},
	templateData: {},
	statisData: {},
	getOptionData: function(right) {
		return SaveData.optionData[right];
	},
	setOptionData: function(right, data) {
		SaveData.optionData[right] = data;
	},
	getFilterData: function(right) {
		return SaveData.filterData[right];
	},
	setFilterData: function(right, data) {
		SaveData.filterData[right] = data;
	},
	getTemplateData: function(right) {
		return SaveData.templateData[right];
	},
	setTemplateData: function(right, data) {
		if (SaveData.templateData[right] == undefined) {
			SaveData.templateData[right] = data;
		} else {
			if (typeof data == 'object') {
				$.each(data, function(key, value) {
					if (SaveData.templateData[right][key] == undefined) {
						SaveData.templateData[right][key] = value;
					}
				});
			} else {
				SaveData.templateData[right] = data;
			}
		}
	},
	getStatisData: function(right) {
		return SaveData.statisData[right];
	},
	setStatisData: function(right, data) {
		SaveData.statisData[right] = data;
	},
	getParentTab: function(right) {
		if (right == 'kpat' || right == 'abpat' || right == 'abpatTrans' || right == 'kpa') { // 특실
			return 'patent';
		} else if (right == 'kdg' || right == 'abdg') { // 디자인
			return 'design';
		} else if (right == 'ktm' || right == 'abtm') { // 상표
			return 'trademark';
		} else if (right == 'jg' || right == 'ipNaviPrcdn' || right == 'ipNaviConflict') { // 심판
			return 'judgement';
		} else if (right == 'arti' || right == 'cntst' || right == 'cyber') { // 기타문헌
			return 'etc';
		/*
		 * 2026.06.11 OJE
		 * 물질특허/미생물 기탁·분양정보 검색 시, 특허·실용신안 탭으로 보여지도록 처리
		 */
		} else if (right == 'natlPat') {
			if ($('#natlPatSearchForm').find('input[name=pat_tpcd]').val() == '디자인') {
				return 'design';
			} else {
				return 'patent';
			}
		} else if (right == 'mPat' || right == 'etcPat') {
			return 'patent';
		}
	}
};

const filterMappings = {
	left : {
		kpat : ['leftGubn', 'leftHangjung'],
		kpa : ['leftKind'],
		abpat : ['country'],
		abpatTrans : ['country'],
		kdg : ['pattern', 'measure'],
		abdg : ['country'],
		ktm : ['merchandise', 'pattern', 'measure'],
		abtm : ['country'],
		jg : ['patent', 'court', 'relation']
	},
	detail : {
		kpat : ['sd01_ck02', 'sd01_ck03'],
		kpa : ['sd010104_g01_ck'],
		abpat : ['sd010102_g01_ck'],
		abpatTrans : ['sd010103_g01_ck'],
		kdg : ['sd010201_g01', 'sd010201_g02'],
		abdg : ['sd010202_g01'],
		ktm : ['sd010301_g01', 'sd010301_g02', 'sd010301_g03'],
		abtm : ['sd010302_g01'],
		jg : ['sd0104_g01', 'sd0104_g02', 'sd0104_g03']
	}
}

//권리별 form data 저장용 객체 생성
let FormData = {
	data: {},
	getData: function(right) {
		return FormData.data[right];
	},
	setData: function(right, data) {
		FormData.data[right] = data;
	}
};
//
var ImageData = {
	data: {},
	getData: function(right) {
		return ImageData.data[right];
	},
	setData: function(right, data) {
		ImageData.data[right] = data;
	},
};

//권리별 검색결과 저장용 객체 생성
var ResultData = {
	data: {},
	getData: function(right) {
		return ResultData.data[right];
	},
	setData: function(right, data) {
		ResultData.data[right] = data;
	},
	setAllImageData: function(right, data) {
		$.each(data, function(idx, item) {
			$.each(ResultData.getData(right).resultList, function(i, t) {
				if (item.applno == t.DOCID) {
					ResultData.data[right].resultList[i].allImageInfo = item;
				}
			});
		});
	},
	getTabCount: function(right) {
		let tabCount = 0;
		
		//if (right == 'kpat' || right == 'abpat' || right == 'abpatTrans' || right == 'kpa' || right == 'kdc') { // 특실
		if (right == 'kpat' || right == 'abpat' || right == 'abpatTrans' || right == 'kpa') { // 특실
			if (ResultData.data.kpat != undefined && ResultData.data.kpat.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.kpat.countInfo.totalcount);
			}
			if (ResultData.data.abpat != undefined && ResultData.data.abpat.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.abpat.countInfo.totalcount);
			}
			if (ResultData.data.abpatTrans != undefined && ResultData.data.abpatTrans.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.abpatTrans.countInfo.totalcount);
			}
			if (ResultData.data.kpa != undefined && ResultData.data.kpa.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.kpa.countInfo.totalcount);
			}
			/*if (ResultData.data.kdc != undefined && ResultData.data.kdc.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.kdc.countInfo.totalcount);
			}*/
		} else if (right == 'kdg' || right == 'abdg') { // 디자인
			if (ResultData.data.kdg != undefined && ResultData.data.kdg.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.kdg.countInfo.totalcount);
			}
			if (ResultData.data.abdg != undefined && ResultData.data.abdg.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.abdg.countInfo.totalcount);
			}
		} else if (right == 'ktm' || right == 'abtm') { // 상표
			if (ResultData.data.ktm != undefined && ResultData.data.ktm.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.ktm.countInfo.totalcount);
			}
			if (ResultData.data.abtm != undefined && ResultData.data.abtm.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.abtm.countInfo.totalcount);
			}
		} else if (right == 'jg' || right == 'ipNaviPrcdn' || right == 'ipNaviConflict') { // 심판
			if (ResultData.data.jg != undefined && ResultData.data.jg.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.jg.countInfo.totalcount);
			}
			if (ResultData.data.ipNaviPrcdn != undefined && ResultData.data.ipNaviPrcdn.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.ipNaviPrcdn.countInfo.totalcount);
			}
			if (ResultData.data.ipNaviConflict != undefined && ResultData.data.ipNaviConflict.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.ipNaviConflict.countInfo.totalcount);
			}
		} else if (right == 'arti' || right == 'cntst' || right == 'cyber') { // 기타문헌
			if (ResultData.data.arti != undefined && ResultData.data.arti.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.arti.countInfo.totalcount);
			}
			if (ResultData.data.cntst != undefined && ResultData.data.cntst.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.cntst.countInfo.totalcount);
			}
			if (ResultData.data.cyber != undefined && ResultData.data.cyber.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.cyber.countInfo.totalcount);
			}
		} else if (right == 'natlPat' || right == 'mPat' || right == 'etcPat') { // 특화검색
			if (ResultData.data.natlPat != undefined && ResultData.data.natlPat.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.natlPat.countInfo.totalcount);
			}
			if (ResultData.data.mPat != undefined && ResultData.data.mPat.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.mPat.countInfo.totalcount);
			}
			if (ResultData.data.etcPat != undefined && ResultData.data.etcPat.countInfo != undefined) {
				tabCount += parseInt(ResultData.data.etcPat.countInfo.totalcount);
			}
		}
		
		return tabCount;
	}
};

// 권리별 정렬 옵션 셋팅
let sortOption = {
		abpat:{RANK:'srlt.abpat.rank',CC:'srlt.abpat.cc',OPN:'srlt.abpat.opn',TL:'srlt.abpat.tl',IPC:'srlt.abpat.ipc',AN:'srlt.abpat.an',GN:'srlt.abpat.gn',PN:'srlt.abpat.pn',IAN:'srlt.abpat.ian',ION:'srlt.abpat.ion',RN:'srlt.abpat.rn',PD:'srlt.abpat.pd',AD:'srlt.abpat.ad',GD:'srlt.abpat.gd',OPD:'srlt.abpat.opd',IDT:'srlt.abpat.idt',IOD:'srlt.abpat.iod',RD:'srlt.abpat.rd',AP:'srlt.abpat.ap',IN:'srlt.abpat.in',AG:'srlt.abpat.ag'},
		abpatTrans:{RANK:'srlt.abpatTrans.rank',CC:'srlt.abpatTrans.cc',OPN:'srlt.abpatTrans.opn',TL:'srlt.abpatTrans.tl',IPC:'srlt.abpatTrans.ipc',AN:'srlt.abpatTrans.an',GN:'srlt.abpatTrans.gn',PN:'srlt.abpatTrans.pn',IAN:'srlt.abpatTrans.ian',ION:'srlt.abpatTrans.ion',RN:'srlt.abpatTrans.rn',PD:'srlt.abpatTrans.pd',AD:'srlt.abpatTrans.ad',GD:'srlt.abpatTrans.gd',OPD:'srlt.abpatTrans.opd',IDT:'srlt.abpatTrans.idt',IOD:'srlt.abpatTrans.iod',RD:'srlt.abpatTrans.rd',AP:'srlt.abpatTrans.ap',IN:'srlt.abpatTrans.in',AG:'srlt.abpatTrans.ag'},
		kpat:{RANK:'srlt.kpat.rank',AN:'srlt.kpat.an',LST:'srlt.kpat.st',TL:'srlt.kpat.title',IPC:'srlt.kpat.ipc',AP:'srlt.kpat.ap',IN:'srlt.kpat.ag',AG:'srlt.kpat.in',TRH:'srlt.kpat.trh',AD:'srlt.kpat.ad',GN:'srlt.kpat.rn',GD:'srlt.kpat.rd',OPN:'srlt.kpat.unpn',OPD:'srlt.kpat.unpd',PN:'srlt.kpat.pn',PD:'srlt.kpat.pd',RC:'srlt.kpat.pc',RN:'srlt.kpat.prn',RD:'srlt.kpat.prd',IAN:'srlt.kpat.inan',IDT:'srlt.kpat.inad',ION:'srlt.kpat.inunpn',IOD:'srlt.kpat.inunpd',BCTC:'srlt.kpat.bc'},
		kpa:{RANK:'srlt.kpa.rank',KD:'srlt.kpa.kd',EIP:'srlt.kpa.eip',EPN:'srlt.kpa.epn',EAN:'srlt.kpa.ean',TL:'srlt.kpa.tl',AP:'srlt.kpa.eap'},
		abdg:{RANK:'srlt.abdg.rank',CMC:'srlt.abdg.cmc',RN:'srlt.abdg.rn',RD:'srlt.abdg.rd',PN:'srlt.abdg.pn',PD:'srlt.abdg.pd',AN:'srlt.abdg.an',AD:'srlt.abdg.ad',IT:'srlt.abdg.it',DC:'srlt.abdg.dc'},
		kdg:{RANK:'srlt.kdg.rank',ANN:'srlt.kdg.ann',AD:'srlt.kdg.ad',ONN:'srlt.kdg.onn',OD:'srlt.kdg.od',PD:'srlt.kdg.pd',RNN:'srlt.kdg.rnn',RD:'srlt.kdg.rd',PRN:'srlt.kdg.prn',PRD:'srlt.kdg.prd',HN:'srlt.kdg.hn',HD:'srlt.kdg.hd',LAS:'srlt.kdg.las',DC:'srlt.kdg.dc',LC:'srlt.kdg.lc',FC:'srlt.kdg.fc',IVN:'srlt.kdg.ivn',APNM:'srlt.kdg.apnm',AGNM:'srlt.kdg.agnm',TRH:'srlt.kdg.trh',IT:'srlt.kdg.it',DS_SEQ:'srlt.kdg.dsseq'},
		jg:{RANK:'srlt.jg.rank',JG:'srlt.jg.jg',JK:'srlt.jg.jk',JM:'srlt.jg.jm',JS:'srlt.jg.js',JC:'srlt.jg.jc',RD:'srlt.jg.rd',AN:'srlt.jg.an',RN:'srlt.jg.rn',MN:'srlt.jg.mn',DD:'srlt.jg.dd',DP:'srlt.jg.dp',DG:'srlt.jg.dg',PP:'srlt.jg.pp',PG:'srlt.jg.pg',IT:'srlt.jg.it'},
		ktm:{RANK:'srlt.ktm.rn',ANN:'srlt.ktm.ann',AD:'srlt.ktm.ad',PNN:'srlt.ktm.pnn',PD:'srlt.ktm.pd',RNN:'srlt.ktm.orn',RD:'srlt.ktm.ord',RPN:'srlt.ktm.rpn',RPD:'srlt.ktm.rpd',PRN:'srlt.ktm.prn',PRD:'srlt.ktm.prd',MN:'srlt.ktm.mn',HD:'srlt.ktm.hd',LAS:'srlt.ktm.las',PRC:'srlt.ktm.prc',DRC:'srlt.ktm.drc',APNM:'srlt.ktm.apnm',AGNM:'srlt.ktm.agnm',TRH:'srlt.ktm.trh',KTN:'srlt.ktm.ktn'},
		abtm:{RANK:'srlt.abtm.rn',TKM:'srlt.abtm.tkm',NIC:'srlt.abtm.nic',VNC:'srlt.abtm.vnc',OAN:'srlt.abtm.oan',ORN:'srlt.abtm.orn',OAD:'srlt.abtm.oad',ORD:'srlt.abtm.ord',STM:'srlt.abtm.stm'},
		ipNaviConflict:{RANK:'srlt.ipNaviConflict.rn',JG:'srlt.ipNaviConflict.jg',JK:'srlt.ipNaviConflict.jk',JM:'srlt.ipNaviConflict.jm',JS:'srlt.ipNaviConflict.js',JC:'srlt.ipNaviConflict.jc',RD:'srlt.ipNaviConflict.rd',AN:'srlt.ipNaviConflict.an',RN:'srlt.ipNaviConflict.rgn',MN:'srlt.ipNaviConflict.mn',DD:'srlt.ipNaviConflict.dd',DP:'srlt.ipNaviConflict.dp',DG:'srlt.ipNaviConflict.dg',PP:'srlt.ipNaviConflict.pp',PG:'srlt.ipNaviConflict.pg',IT:'srlt.ipNaviConflict.it'},
		ipNaviPrcdn:{RANK:'srlt.ipNaviPrcdn.rn',JG:'srlt.ipNaviPrcdn.jg',JK:'srlt.ipNaviPrcdn.jk',JM:'srlt.ipNaviPrcdn.jm',JS:'srlt.ipNaviPrcdn.js',JC:'srlt.ipNaviPrcdn.jc',RD:'srlt.ipNaviPrcdn.rd',AN:'srlt.ipNaviPrcdn.an',RN:'srlt.ipNaviPrcdn.rgn',DD:'srlt.ipNaviPrcdn.dd',DP:'srlt.ipNaviPrcdn.dp',DG:'srlt.ipNaviPrcdn.dg',PP:'srlt.ipNaviPrcdn.pp',PG:'srlt.ipNaviPrcdn.pg',IT:'srlt.ipNaviPrcdn.it'},
		cntst:{},
		cyber:{RANK:'srlt.cyber.rn',CRO:'srlt.cyber.cro',CT:'srlt.cyber.ct',CRN:'srlt.cyber.crn',CDD:'srlt.cyber.cdd'},
		arti:{}, //NDSL 논문검색필드
		//'arti':{'pubyear':'발행일','title':'논문명','jtitle':'저녈명','NULL':'정확도'}  //Science ON 논문검색필트
		
		natlPat:{RGSTNO:'srlt.natlPat.rgn',TTL:'srlt.natlPat.ttl',INVNT_INSTN_NM:'srlt.natlPat.iin',RGST_DT:'srlt.natlPat.rgd',TERM_EXISTENCE:'srlt.natlPat.te',PAY_TPCD:'srlt.natlPat.pt',EVALUATION:'srlt.natlPat.ev'},
		mPat:{APPLNO:'srlt.mPat.apn',INVNT_TTL:'srlt.mPat.int',CNDRT_EXPTN_DT:'srlt.mPat.cne',SSPAT_TECH_FLD_TPCD:'srlt.mPat.stft'},
		etcPat:{APPLNO:'srlt.etcPat.apn',INVNT_TTL:'srlt.etcPat.int',MICGM_SPNO:'srlt.etcPat.ms',DPST_MICGM_NM:'srlt.etcPat.dmn',MICGM_KIND_NM:'srlt.etcPat.mkn',MOFMC_DT:'srlt.etcPat.md',MICGM_DPATH_NM:'srlt.etcPat.mdn'}
	};

// 권리별 필터 초기값
let initFilterItem = {
	kpat:['allCheck_leftGubn','allCheck_leftHangjung'],
	abpat:['US','EP','WO','JP','CN'],
	abpatTrans:['US'],
	kpa:['allCheck_leftKind'],
	kdg:['allCheck','measure01'],
	abdg:['JP','US'],
	ktm:['allCheckMd','allCheckPt','allCheckMs'],
	abtm:['US','JP'],
	jg:['patent01','court01']
};

// 권리별 필터 초기 데이터
let initFilterData = {
	data: {
		kpat: {
			prefixExpression: ''
		},
		abpat: {
			collectionValues: 'US_T.col,EP_T.col,WO_T.col,PAJ_T.col,CN_T.col'
		},
		abpatTrans: {
			collectionValues: 'US_TRANS_T.col'
		},
		kpa: {
			kind: ''
		},
		kdg: {
			measureString: 'A,B,C,F,G,I,J,R',
			patternString: 'simi,part,etc'
		},
		abdg: {
			collectionValues: 'JP,US'
		},
		ktm: {
			merchandiseString: 'td40,td41,td42,td43,td44,td45,td47,td48,tdmd',
			measureString: 'A,B,C,F,G,I,J,R',
			patternString: 'NAKletter,NAKfigure,NAKlmixed,NAKfmixed,NAKsounds,NAKfragre,TPDcommon,TPDcolors,TPDcolor,TPDdimens,TPDcmixed,TPDdimcol,TPDhologr,TPDaction,TPDvisual,TPDinvisible',
			coexistenceAgreement: 'N'
		},
		abtm: {
			collectionValues: 'US,JP'
		},
		jg: {
			patentString: 'PT,UT,DG,TM',
			courtString: 'PJ,PC,SC,JS,AJ',
			relationString: 'RS,PS'
		}
	},
	setInitFilterData: function(exclude) {
		$.each(initFilterData.data, function(right, item) {
			if (right == exclude) return true;
			let $targetForm = $('#' + right + 'SearchForm');
			$.each(item, function(key, value) {
				$targetForm.find('input[name=' + key + ']').val(value);
			});
			SaveData.filterData = {};
		});
	}
};

// 선택보기 결과 데이터(초기화)
let selectViewData = {
	countInfo: {totalcount: 0, count: 0},
	resultList: []
};

let selectViewFlag = false; // 선택보기 구분값
let dataNotFound = false; // 검색 결과없음 구분값

let isExpandedFilter = false;
let isExpandedDetail = false;

//기술분야 검색용 변수
let currentLevel = 'mid';
let currentData = [];
let currentLargeId = "";
let currentMidId = "";
let currentPage = 0;
let midCategoryData = {};
let lastSelectedMidId = "";
const itemsPerPage = 6;
const techDepthConfig = {
	    "tech_1": { depth: 2 },
	    "tech_2": { depth: 2 },
	    "tech_3": { depth: 3 }
};
const techDataTitle = {
		tech_1:"세계지식재산기구(WIPO)에서  세분화된 국제특허분류(IPC) 코드를 거시적 기술 트렌드 분석에 적합하도록 재구성하여 \n5대 부문과 35개의 기술 분야로 매핑한 글로벌 표준 통계 분류 체계입니다.",
		tech_2:"통계법 제22조에 의거 통계작성기관이 동일한 기준에 따라 통계를 작성할 수 있도록 유엔(UN)이 권고하고 있는 국제표준산업분류를 기초로 \n국가데이터처장이 작성한 통계목적의 분류 체계입니다.",
		tech_3:"과학기술기본법 제27조에 따라 과학기술정보통신부가 국가과학기술 분야 정보의 관리와 유통, 인력 관리의 효율화, 연구개발사업의 효율적 기획 및 \n관리를 위해 수립한 국가 표준 분류 체계입니다."
};
$(document).ready(function()
{
	 // 기술분류정보 초기화
	const $defaultRadio = $('input[name="sd0205_g00"]:checked');
    if ($defaultRadio.length > 0) {
        changeLGCLSCol($defaultRadio[0]);
    }
	// 선택보기 체크박스 클릭 이벤트 등록
	$(document).on('click', 'input[name=resultCheck]', function(e) {
		let checked = $(this).prop('checked');
		let $target = $(this).attr('data-result-check-all') != undefined ? $('input[data-result-check]') : $(this);
		
		$.each($target, function(idx1, item1) {
			let index = parseInt($(item1).attr('id').replace('rc', ''));
			let key = $(item1).val();
			let count = selectViewData.resultList.length;
			
			if (checked) {
				if (count > 100) {
					alert('선택보기는 총 100건까지 제공됩니다.');
					//$(this).prop('checked', false);
					e.preventDefault();
					e.stopPropagation();
					return false;
				} else {
					if (selectViewData.resultList != undefined && !selectViewData.resultList.includes(ResultData.getData(currentTab2).resultList[index])) {
						selectViewData.resultList.push(ResultData.getData(currentTab2).resultList[index]);
						selectViewData.countInfo.totalcount = selectViewData.resultList.length;
						selectViewData.countInfo.count = selectViewData.resultList.length;
					}
				}
			} else {
				let result = false;
				$.each(selectViewData.resultList, function(idx2, item2) {
					$.each(Object.keys(item2), function(i, t) {
						if (item2[t] == key) {
							selectViewData.resultList.splice(idx2, 1);
							result = true;
							return false;
						}
					});
					
					if (result) return false;
				});
				selectViewData.countInfo.totalcount = selectViewData.resultList.length;;
				selectViewData.countInfo.count = selectViewData.resultList.length;;
			}
		});
	});
	
	// 상단 권리탭 버튼 클릭 이벤트 등록
	$(document).on('click', 'button[data-tab=resultTab]', function(e) {
		let targetTab = $(this).data('tab-id');
		if (currentTab1 == targetTab) {
			return false;
		}
		currentTab1 = targetTab;
		
		// 통계_상단 권리탭
		let recordRight; 
		if (targetTab == 'patentTab') {
			recordRight = 'PAT';
		} else if (targetTab == 'designTab') {
			recordRight = 'DG';
		} else if (targetTab == 'trademarkTab') {
			recordRight = 'TM';
		} else if (targetTab == 'judgementTab') {
			recordRight = 'JM';
		} else {
			recordRight = 'OTHER';
		}
		recordServiceStats('KHOME', 'MTAB', recordRight);
		
		// 권리별 국내외 통합검색
		rightTotalSearch(undefined, this, e);
	});
	
	// 보기방식 변경 이벤트 등록
	$(document).on('click', 'button[data-view-type]', function(e) {
		if ($(this).hasClass('active')) {
			return false;
		}
		if (ResultData.getData(currentTab2) == undefined || dataNotFound) {
			alert('검색 결과가 존재하지 않습니다.');
			return false;
		}

		toggleLoadingDialog('#mainResultListArea .body', true);
			
		const $allButtons = $('button[data-view-type]');
		$allButtons.removeClass('active').attr('title', '선택되지 않음');
		
		$(this).addClass('active').attr('title', '선택됨');
		
		if (currentTab2 == 'kpat' && $(this).data('view-option') == 'all'){
			changeImageMain2();
			if (SaveData.getOptionData(currentTab2) == undefined) {
				let optionData = {
					'#sortCondition01': $('#sortCondition01').val(),
					'#sortCondition02': $('#sortCondition02').val(),
					'#sortCondition03': 10
				};
				SaveData.setOptionData(currentTab2, optionData);
			} else {
				SaveData.getOptionData(currentTab2)['#sortCondition03'] = 10;
			}
			initSortOption('allList');
			imgLoadEvent;
			$(window).on('load resize scroll', imgLoadEvent);
		} else {
			initSortOption('changeView');
			let viewCollection = 'us';
			if (currentTab2 == 'abpatTrans') {
				viewCollection = $('#abpatTransSearchForm').find('input[name=viewCollection]').val().toLowerCase();
			}
			getTemplate(currentTab2, 'search', $(this).data('view-option') + 'List', 'changeView', viewCollection);
		}
		
		// 통계_검색결과보기방식
		let viewOption;
		if (this.getAttribute('data-view-option')== 'seoji') {
			viewOption = 'SEOV';
		} else if (this.getAttribute('data-view-option') == 'one') {
			viewOption = 'THMV';
		} else if (this.getAttribute('data-view-option') == 'all') {
			viewOption = 'IMGV';
		} else {
			viewOption = 'BASV';
		}
		recordServiceStats(currentTab2, 'VIEW', viewOption);
	});
	
	if (window.location.pathname.indexOf('/searchResult.do') > -1) {
		// 특화검색 분류
		if ($('#searchKind').val() == 'specializationSearch') {
			let searchRight = $('#searchRight').val();
			initDataForDetailSearch(searchRight);
			initChangeViewBtn(searchRight);
			doSearch(searchRight, 'specialization');
			saveInitFormData();
		} else {
			// 권리별 초기값 저장
			saveInitFormData();
			let tabValue = $('#tab').val();
			
			if (tabValue == '') {
				let searchKind = $('#searchKind').val();
				if (searchKind == 'detailSearch' || searchKind == 'keywordSearch') {
					//2025.05.20 keywordSearch 추가 (지식재산처 연계 - 검색식 입력 연계 시 사용)
					let searchRight = $('#searchRight').val();
					if(searchKind == 'keywordSearch') {
							let queryText = $('#' + searchRight + 'SearchForm').find('input[name=queryText]').val();
							$('#' + searchRight + 'SearchForm').find('input[name=expression]').val(queryText);
							$('#queryText').val(queryText);
					}
					initDataForDetailSearch(searchRight);
					initChangeViewBtn(searchRight);
					doSearch(searchRight, 'detailSearch');
				} else if (searchKind == 'totalSearch'){
					/*
					 * 개인화_김철(기본 검색 권리 설정)
					 */
					if (Object.keys(personalizeSetting).length != 0) {
						switch(personalizeSetting.searchRight){
							case 'patent' :
								currentTab2 = 'kpat'; break;
							case 'design' :
								currentTab2 = 'kdg'; break;
							case 'trademark' :
								currentTab2 = 'ktm'; break;
							case 'judgement' : 
								currentTab2 = 'jg'; break;
							case 'etc' :
								currentTab2 = 'cyber'; break;
						}
						rightTotalSearch();
					} else {
						// 특실 통합 검색(메인화면 검색은 특실로 고정)
						patentTotalSearch();
					}
				}
				
				// sort option 초기화
				initSortOption('init');
				
				// 필터 열기
				searchPageModule.toggleResultFilter(filterSet, true);
			} else {
				searchPageModule.toggleResultFilter(false, false);
				 if (tabValue == 'micro') {
	                    $('#modalSearchDetail #sd02').click();
	                    $('#modalSearchDetail .tab-con.active button[data-visible-control=sd02_04]').click();
	                    fnSearchDetail.open(document.querySelector('#btnOpenSearchDetail'));
	                } else if (tabValue == 'similar') {
	                    $('#modalSearchDetail #sd02').click();
	                    $('#modalSearchDetail .tab-con.active button[data-visible-control=sd02_01]').click();
	                    $('#sd020101_g02_category_01').val('TXT');
	                    $('#sd020101_g02_category_01').trigger('change');
	                    $('#sd020101_g02_text_04').val($('#kdcSearchForm input[name=query]').val());
	                    doDetailSearch();
	                } else if (tabValue == 'product') {
	                	openCodeSupport(this, 'Product', 'explain', '');
	                	//$('#modalSearchDetail .tab-con.active button[data-sdf-support-control=sd010301_g10_text_01]').click();
	                } else {
                        // 지식재산정보 검색 메뉴를 통해 권리를 접근하는 경우 currentTab2 셋팅
                        // 아래 트리거($('button[data-tab=resultTab][data-tab-id*=' + $('#tab').val() + ']').trigger('click');)를 통해 currentTab1 셋팅
                        if (tabValue == 'patent') {
                            currentTab2 = 'kpat';
                        } else if (tabValue == 'design') {
                            currentTab2 = 'kdg';
                        } else if (tabValue == 'trademark') {
                            currentTab2 = 'ktm';
                        } else if (tabValue == 'judgement') {
                            currentTab2 = 'jg';
                        } else if (tabValue == 'etc') {
                            currentTab2 = 'cyber';
                        }
                        
	                    $('button[data-tab=resultTab][data-tab-id*=' + $('#tab').val() + ']').trigger('click');
	                    
	            		fnSearchDetail.open(document.querySelector('#btnOpenSearchDetail'));
	            		
	            		// 상세검색 창 오픈 시,바로 자유검색으로 포커싱 처리(모달이 완전히 로드된 후,이벤트 처리를 위한 setTimeout처리)
	            		setTimeout(function(){
	            			//$('.search-detail-form.active').find('input[data-field=KW]').first().focus()
	            			$('#modalSearchDetail').first().focus()
	            		}, 100);
	            		
	                    /* 추가 파라미터를 받을 경우
	                    const searchParams = new URLSearchParams(window.location.search);
	                    var openDetailSearch = searchParams.get('openDetailSearch');
	                    if (openDetailSearch == 'Y') {
	                        fnSearchDetail.open(document.querySelector('#btnOpenSearchDetail'));
	                    }*/
	                }
			}
		}
	}
	
	// 상단 검색시
	/*
	$(document).on('submit', '#srchFrm', function()
	{
		var inputQuery = $(this).find('input[name=searchQuery]').val().trim();
		
		try
		{
			if (isKeywordValidation(inputQuery))
			{
				$(this).find('input[name=searchExpression]').val(removeOperatorBlank(DelSpecialChar(inputQuery)));
				doSearch('top');
			}
		}
		catch(e)
		{
			alert(e);
			$(this).find('input[name=searchQuery]').focus();
		}
		
		return false;
		
	});
	*/
	
	/* BACK버튼에 대한 이벤트 등록
	window.addEventListener('hashchange', function(e)
	{
		var state = history.state;
		
		if ($('.bg').hasClass('on'))
		{
			close();
			history.forward();
		}
		else if ($('.menu-show').css('display') != 'none')
		{
			closeNaviMenu();
			history.forward();
		}
		else if ($('.guide').css('display') != 'none')
		{
			closeGuide();
			history.forward();
		}
		else if ($('.tip').css('display') != 'none')
		{
			closeTip();
			history.forward();
		}
		else if ($('.vetatest').css('display') != 'none')
		{
			closeUserProposal();
			history.forward();
		}
		else if ($('.inner_popup').length != 0 && $('.inner_popup').css('display') != 'none')
		{
			$('.inner_popup').hide('slide', {direction: 'down'}, 300);
			$('.inner_popup iframe').remove();
			history.forward();
		}
		else if ($('.detail_popup.inner').length != 0 && $('.detail_popup.inner').css('display') != 'none')
		{
			$('.detail_popup.inner').hide('slide', {direction: 'down'}, 300);
			$('.detail_popup.inner div[id*=detail-]').remove();
			history.forward();
		}
		else if ($('.detail_popup').css('display') != 'none')
		{
			// $('.detail_popup').hide('slide', {direction: 'down'}, 300);
			$('.detail_popup').hide();
			$('.detail_popup div[id*=detail-]').remove();
			$('html').removeClass('hide-y-scroll-bar-on-sm-down');
			history.forward();
		}
		else
		{
			if (state.action == undefined && location.hash == '')
			{
				history.back();
			}
			if (state.action == 'MOVE')
			{
				if (e.oldURL.indexOf(state.target + '_PAGE') > -1)
				{
					if ($(window).scrollTop() > 50)
					{
						$.mobile.silentScroll();
					}
				}
				else
				{
					$('#' + state.target).trigger('click');
				}
			}
			
			if (state.params != undefined)
			{
				if (JSON.stringify(currentStateData) !== JSON.stringify(state.params) && state.params.searchExpression != '')
				{
					var srchGb = 'top';
					
					if (state.action.indexOf('SEARCH') > -1) srchGb = state.action.split('_')[0].toLowerCase();
					
					var targetForm = $('#srchFrm');
					
					if (srchGb != 'top' && srchGb != 'smart')
					{
						targetForm = $('#' + state.target.toLowerCase() + 'SrchFrm');
					}
					
					$.each($(targetForm).children('input'), function(idx, item)
					{
						$(item).val(state.params[$(item).attr('name')]);
					});
					
					doSearch(srchGb + '-back');
					
					currentStateData = $('#srchFrm').serializeObject();
				}
				else
				{
					if (!$('#' + state.target).parent().hasClass('on')) rightTabMove($('#' + state.target));
				}
			}
		}
	}); */
	
	// recordAction(currentRight, 'MOVE');
		
	// 권리별 행정상태 전체보기
    $(document).on('click', '.btnToggleStatus', function() {
		let btn = $(this);
		let btnText = btn.find('.btn-text');
		let arrow = btn.find('.arrow');
		let nextStatus, subCheck;
	    if (btn.closest('#mainResultFilter').length > 0) {
	    	isExpandedFilter = btn.attr('aria-expanded') == 'true';
	    	nextStatus = !isExpandedFilter;
	    	subCheck = btn.closest('.list').find('.sub-check');
	    	if(nextStatus) {
	    		btnText.text(i18next.language == 'en' ? 'Fullview Close' : '행정상태 전체보기 닫기');
	    		btnText.attr('data-lang-id', 'scft.status.fullviewclose');
	    	} else {
	    		btnText.text(i18next.language == 'en' ? 'Fullview' :'행정상태 전체보기');
	    		btnText.attr('data-lang-id', 'scft.status.fullview');
	    	}
	    } else {
	    	isExpandedDetail = btn.attr('aria-expanded') === 'true';
	    	nextStatus = !isExpandedDetail;
	    	subCheck = btn.closest('.ck-list').find('.sub-check');
	    	if(nextStatus) {
	    		btnText.text(i18next.language == 'en' ? 'Fullview Close' : '전체보기 닫기');
	    		btnText.attr('data-lang-id', 'adsr.status.fullviewdeailclose');
	    	} else {
	    		btnText.text(i18next.language == 'en' ? 'Fullview' : '전체보기');
	    		btnText.attr('data-lang-id', 'adsr.status.fullviewdeail');
	    	}
	    }
	    subCheck.toggle(nextStatus);
        btn.attr('aria-expanded', nextStatus);
        arrow.toggleClass('is-rotated', nextStatus);

        /*나중 행정상태 기능 변경 시 삭제예정*/
        window.syncStatusTooltips?.();
        
        setTimeout(function() {
            window.dispatchEvent(new Event('scroll')); 
        }, 100);
    });
    const $treeElements = $('#jstreeIPC, #jstreeCPC, #jstreeEPC, #jstreeFI, #jstreeFC, #jstreeLC, #jstreeDR');
    
    $treeElements.on('ready.jstree open_node.jstree', function() {
        applyTabindex(this);
        syncAllCheckboxes(this);
    });

    $treeElements.on('changed.jstree', function(e, data) {
        syncAllCheckboxes(this);
    });
    
    $treeElements.on('keydown', function(e) {
        const key = e.which || e.keyCode;
        if (key !== 13 && key !== 32) return; // 엔터나 스페이스가 아니면 무시
        e.preventDefault();
        e.stopPropagation();
        
        const $target = $(e.target); 
        const $node = $target.closest('.jstree-node');
        const $treeContainer = $target.closest('.jstree');
        const $tree = $treeContainer.jstree(true);
        const nodeId = $node.attr('id');
        
        // 1. 체크박스인 경우: 선택/해제만 동작 (리스트 안 열림)
        if ($target.hasClass('jstree-checkbox') || $target.closest('.jstree-checkbox').length) {
        	$target.trigger('click');
        } 
        // 2. 열기/닫기 아이콘 명확한 타겟팅
        else if ($target.hasClass('jstree-ocl') || $target.closest('.jstree-ocl').length) {
        	$target.trigger('click');
        } 
        // 3. 그 외 (앵커, 테마 아이콘, 텍스트) 클릭 시
        else {
        	$target.trigger('click');
        }
    });
    
});

//상세검색에 따른 초기화
function initDataForDetailSearch(right)
{
	currentTab1 = SaveData.getParentTab(right) + 'Tab';
	currentTab2 = right;
	// 상단 권리탭 초기화
	let $tab1wrap = $('ul.search-tab-head');
	$tab1wrap.find('button[id*=Tab]').removeClass('active');
	$tab1wrap.find('button[id*=Tab]').find('.total').text('');
	// 상단 국가탭 초기화
	let $tab2wrap = $('div[data-tab-id=' + currentTab1 + ']');
	$tab2wrap.find('a[data-subtab-id]').removeClass('active');
	$tab2wrap.find('a[data-subtab-id=' + right + ']').addClass('active');
	$tab2wrap.parent().find('.total').text('');
	// 결과 데이터 객체 초기화 
	ResultData.data = {};
	// form 데이터 초기화
	let $forms = $('form[id*=SearchForm]').not('#' + right + 'SearchForm');
	$forms.find('input[name=queryText]').val('');
	$forms.find('input[name=expression]').val('');
}

//권리별 국내외 통합검색에 따른 초기화
function initDataForTotalSearch(right, resultTab)
{
	currentTab1 = SaveData.getParentTab(right) + 'Tab';
	currentTab2 = right;
	
	// 상단 권리탭 초기화
	let $tab1wrap = $('ul.search-tab-head');
	$tab1wrap.find('button[id*=Tab]').removeClass('active');
	$tab1wrap.find('button[id*=Tab]').find('.total').text('');
	
	// 상단 국가탭 초기화
	let $tab2wrap = $('div[data-tab-id=' + currentTab1 + ']');
	$tab2wrap.find('a[data-subtab-id]').removeClass('active');
	$tab2wrap.find('a[data-subtab-id=' + right + ']').addClass('active');
	$tab2wrap.parent().find('.total').text('');
	
	// 결과 데이터 객체 초기화 
	ResultData.data = {};
	
	// form 데이터 초기화
	let $forms = $('form[id*=SearchForm]');
	/* 현 상단 탭 하위 권리를 제외한 나머지 하위 권리 폼 조회*/
	excludeMap[resultTab].forEach(function (id) {
        $forms = $forms.not('#' + id);
    });
	$forms.find('input[name=queryText]').val('');
	$forms.find('input[name=expression]').val('');
}

// 선택보기
function selectResultView()
{
	$('#' + currentTab2 + 'SearchForm').find('input[name=currentPage]').val(1);
	$('#' + currentTab2 + 'SearchForm').find('input[name=numPerPage]').val(100);
	
	getTemplate(currentTab2, 'search', $('button[data-view-type].active').data('view-option') + 'List', 'selectView');
	
	selectViewFlag = true;
}

// 선택보기 초기화
function initSelectView(mode)
{
	resultCheck.cancel(false);
	selectViewData.countInfo.totalcount = 0;
	selectViewData.countInfo.count = 0;
	selectViewData.resultList = [];
	
	if (mode == 'cancel' && selectViewFlag) {
		// 기존 페이지 번호 및 페이지당 갯수 초기화
		$('#' + currentTab2 + 'SearchForm').find('input[name=currentPage]').val($('#pagination').find('a.active').text());
		$('#' + currentTab2 + 'SearchForm').find('input[name=numPerPage]').val($('#sortCondition03').val());
		if(currentTab2 != 'abpatTrans') {
			getTemplate(currentTab2, 'search', $('button[data-view-type].active').data('view-option') + 'List');
		} else {
			getTemplate(currentTab2, 'search', $('button[data-view-type].active').data('view-option') + 'List','',$('#' + currentTab2 + 'SearchForm').find('input[name=viewCollection]').val());
		}
		
	}
	selectViewFlag = false;
}

//행위 기록
function recordAction(target, action)
{
	let newHash = '#' + target + "_" + action;
	let data = null;
	
	if (action.indexOf('FILTER') > -1 || action.indexOf('SORT') > -1)
	{
		data = $('#' + target.toLowerCase() + 'SrchFrm').serializeObject();
	}
	else
	{
		data = $('#srchFrm').serializeObject();
	}
	
	if (location.hash != newHash && action.indexOf('_SEARCH') < 0)
	{
		window.history.pushState({'target':target,'action':action,'params':data}, null, newHash);
	}
	else if (action.indexOf('_SEARCH') > -1)
	{
		window.history.pushState({'target':target,'action':action,'params':data}, null, newHash + '_' + new Date().getMilliseconds());
	}
	
	currentStateData = data;
}

//권리별 초기값 저장용
function saveInitFormData()
{
	// 권리별 form
	$('form[name*=SearchForm]').each(function(idx, item) {
		let right = $(item).attr('name').replace('SearchForm', '');
		let tempData = {};
		$(item).find('input[type=hidden]').each(function(i, t) {
			tempData[$(t).attr('name')] = $(t).val();
		});
		FormData.setData(right, tempData);
	});
}

//상단탭 로딩 이미지 toggle
function toggleLoadingForTab(right, mode, turnOn)
{
	// 권리탭 로딩 이미지 활성화
	let parentTab = SaveData.getParentTab(right);
	let $target = $('#' + parentTab + 'TotalCount');
	
	if (turnOn) {
		$target.hide();
		$target.parent().addClass('loading');
		$target.parent().prop('disabled', true);
	} else {
		if (mode != 'totalSearch') {
			$target.show();
			$target.parent().removeClass('loading');
			$target.parent().prop('disabled', false);
		}
	}
	
	// 국가탭 로딩 이미지 활성화
	$target = $('#' + right + 'TotalCount');
	if (turnOn) {
		$target.hide();
		$target.parent().addClass('loading');
		$target.parent().css('pointer-events', 'none');
	} else {
		$target.show();
		$target.parent().removeClass('loading');
		$target.parent().css('pointer-events', '');
	}
}

// 요청 중인 request 확인
function checkRequest()
{
	if (requestArr.length != 0) {
		requestArr.forEach(function(req) {
			if (req.readyState != 4 && req.statusText != 'abort') {
				req.abort();
			}
		});
		requestArr = [];
	}
}

//상단 키워드 검색
function totalSearch(inResult)
{
	let reSearch = $('#reSearch').prop('checked');
	// 검색바에서 키워드 추출
	let queryText = '';
	let expression = '';
	
	if (reSearch || inResult != undefined) {
		$targetForm = $('#' + currentTab2 + 'SearchForm');
		if (inResult != undefined) {
			queryText = '(' + $targetForm.find('input[name=queryText]').val() + ')*' + inResult;
		} else {
			queryText = '(' + $targetForm.find('input[name=queryText]').val() + ')*' + $('#queryText').val();
		}
		$('#queryText').val(queryText);
		$('#reSearch').prop('checked', false);
	}
	
	queryText = $.trim($('#queryText').val());
	
	//권리별 검색어 title 설정하는 부분
	activeTab = document.querySelector('.btn-tab.active');
	activeTabId = activeTab ? activeTab.dataset.tabId : "";
	const activTapMap = {
			patentTab: "특허 검색",
			designTab: "디자인 검색",
			trademarkTab: "상표 검색",
			judgementTab: "심판 검색",
			etcTab: "기타 검색"
	};
	document.title = "홈 > 지식재산정보검색 > " + activTapMap[activeTabId] + " (검색어: " + queryText + ")";
	
	// 검색 키워드 valid 체크
	try {
		if (isKeywordValidation(queryText)) {
			/* By J.H.S 20130813 국문 메인홈페이지에서 검색 할 때 출원번호, 등록번호 - 형식으로 입력시 "" 치환하여 검색식 입력하도록 개선함. */
			//입력된 숫자가 등록번호형식일 경우 "10-0000123" 대쉬 제거 by lhy 2013.03.19
			var regExpRegNum1 = /^\d{2}-\d{7}$/;
			if(regExpRegNum1.test(queryText)){
				queryText = queryText.replace("-","");
			}

			//입력된 숫자가 등록번호형식일 경우 "10-0000123-0000" 대쉬 제거 by lhy 2013.03.19
			var regExpRegNum2 = /^\d{2}-\d{7}-\d{4}$/;
			if(regExpRegNum2.test(queryText)){
				queryText = queryText.replace(/-/gi,"");
			}

			//입력된 숫자가 출원번호형식일 경우 "40-2003-0048429" 대쉬 제거 by lhy 2013.03.19
			var regExpRegNum3 = /^\d{2}-\d{4}-\d{7}$/;
			if(regExpRegNum3.test(queryText)){
				queryText = queryText.replace(/-/gi,"");
			}

			//인명정보 Validation(하이픈[-]제거)
			queryText = bioInfoValidation(queryText);
			
			//독일어 특수문자 치환
            queryText = convertGermanEntities(queryText);
			
			expression = DelSpecialChar(queryText);
			expression = removeOperatorBlank(expression);
			
			// queryText = sanitizeInput(queryText);
			// expression = sanitizeInput(expression);
			// 검색 데이터 셋팅
			$('form[name*=SearchForm]').each(function(idx, item) {
				let right = $(item).attr('name').replace('SearchForm', '');
				FormData.data[right].queryText = queryText;
				FormData.data[right].expression = queryText;
				
				$(item).find('input[type=hidden]').each(function(i, t) {
					$(t).val(FormData.data[right][$(t).attr('name')]); 
				});
			});


			// 현재탭 제외 나머지 권리 필터 값 초기화
			initFilterData.setInitFilterData(currentTab2);
			
			// 필터 valid 체크
			if (!filterValidation('totalSearch', currentTab2, $('#mainResultFilter').find('ul.list'))) {
				return;
			}
			
			// 권리별 필터 값 셋팅
			setFilterValues('totalSearch', currentTab2, $('#mainResultFilter').find('input[type=checkbox], input[type=radio]'));

			//필터값을 상세검색에도 적용
			syncDetailSearchByFilter('filterSearch', currentTab2);
			
			// 최근 검색어 닫기
			$('#btnCloseMainSearch').click();
			
			checkRequest();
			
			$('#searchKind').val('totalSearch');
			initSortOption('totalSearch');
			
			patentTotalSearch();
			designTotalSearch();
			trademarkTotalSearch();
			judgementTotalSearch();
			etcTotalSearch();
			
			// SaveData.filterData = {};
		}
	} catch (e) {
		alert(e);
		return false;
	}
	
	// 2025.09.29 특화검색은 항상 가림
	if(!(/kpat|kpa|abpat|abpatTrans/.test(currentTab2))) $('a[data-subtab-id=kpat]').addClass('active');
	['natlPat', 'mPat', 'etcPat'].forEach(id => {
		$(`div[data-tab-id=patentTab] a[data-subtab-id=${id}]`).addClass('hidden');
		$(`div[data-tab-id=patentTab] a[data-subtab-id=${id}]`).removeClass('active');
		if (/natlPat|mPat|etcPat/.test(currentTab2)) {
			initChangeViewBtn('kpat');
			$('a[data-subtab-id=kpat]').trigger('click');
		} else {
			initChangeViewBtn(currentTab2);
		}
	});

}

//권리별 국내외 통합검색
function rightTotalSearch(inResult, $Btn, e)
{
	//$Btn, e 파라미터가 undefined가 아닌 경우, 탭 이동을 통한 검색
	//그 외는 상단 검색입력창을 통한 검색
	if ($Btn != undefined && e != undefined) {
		var isAuto = !e.originalEvent || e.originalEvent.isTrusted === false; // originalEvent 자체가 없거나
        if (isAuto) {
            return false;
        }
        
        const tabId = $Btn.id;
        const $tabCon = $('.tab-con[data-tab-id="' + tabId + '"]');
        const $activeSubBtn = $tabCon.find('.btn-classify.active');
        const subTabId = $activeSubBtn.data('subtab-id');
        if (tabId == 'patentTab' && subTabId == undefined) {
            currentTab2 = 'kpat';
        } else {
            currentTab2 = subTabId;
        }
	}
	
	//현재 하위 권리에 따라 상위 권리를 구분(특실,디자인,상표,심판,기타문헌)
	let tempResultTab = ''; 
	if (/kpat|kpa|abpat|abpatTrans/.test(currentTab2)) {
		tempResultTab = 'patent';
	} else if (/kdg|abdg/.test(currentTab2)) {
		tempResultTab = 'design';
	} else if (/ktm|abtm/.test(currentTab2)) {
		tempResultTab = 'trademark';
	} else if (/jg|ipNaviPrcdn|ipNaviConflict/.test(currentTab2)) {
		tempResultTab = 'judgement';
	} else if (/cntst|cyber|arti/.test(currentTab2)) {
		tempResultTab = 'etc';
	} else if (/natlPat|mPat|etcPat/.test(currentTab2)) {
		tempResultTab = 'patent';
	}
	
	let reSearch = $('#reSearch').prop('checked');
	// 검색바에서 키워드 추출
	let queryText = '';
	let expression = '';
	
	// 결과 내 재검색 셋팅
	if (reSearch || inResult != undefined) {
		$targetForm = $('#' + currentTab2 + 'SearchForm');
		if (inResult != undefined) {
			queryText = '(' + $targetForm.find('input[name=queryText]').val() + ')*' + inResult;
		} else {
			queryText = '(' + $targetForm.find('input[name=queryText]').val() + ')*' + $('#queryText').val();
		}
		$('#queryText').val(queryText);
		$('#reSearch').prop('checked', false);
	}
	
	queryText = $.trim($('#queryText').val());
	
	// 검색 키워드 valid 체크
	try {
		if (isKeywordValidation(queryText)) {
			/* By J.H.S 20130813 국문 메인홈페이지에서 검색 할 때 출원번호, 등록번호 - 형식으로 입력시 "" 치환하여 검색식 입력하도록 개선함. */
			//입력된 숫자가 등록번호형식일 경우 "10-0000123" 대쉬 제거 by lhy 2013.03.19
			var regExpRegNum1 = /^\d{2}-\d{7}$/;
			if(regExpRegNum1.test(queryText)){
				queryText = queryText.replace("-","");
			}

			//입력된 숫자가 등록번호형식일 경우 "10-0000123-0000" 대쉬 제거 by lhy 2013.03.19
			var regExpRegNum2 = /^\d{2}-\d{7}-\d{4}$/;
			if(regExpRegNum2.test(queryText)){
				queryText = queryText.replace(/-/gi,"");
			}

			//입력된 숫자가 출원번호형식일 경우 "40-2003-0048429" 대쉬 제거 by lhy 2013.03.19
			var regExpRegNum3 = /^\d{2}-\d{4}-\d{7}$/;
			if(regExpRegNum3.test(queryText)){
				queryText = queryText.replace(/-/gi,"");
			}

			//인명정보 Validation(하이픈[-]제거)
			queryText = bioInfoValidation(queryText);
			
			//독일어 특수문자 치환
            queryText = convertGermanEntities(queryText);
			
            queryText = DelSpecialChar(queryText);
            queryText = removeOperatorBlank(queryText);
			
			// 검색 데이터 셋팅
			/* 상단 권리별 하위 권리탭 조회 */
			let $forms = $('form[id*=SearchForm]').filter(function() {
				return excludeMap[tempResultTab].includes(this.id);
			});
			
			/* 하위 권리탭 내 FormData값세팅 */
			$forms.each(function(idx, item) {
				let right = $(item).attr('name').replace('SearchForm', '');
				FormData.data[right].queryText = queryText;
				FormData.data[right].expression = queryText;
				
				$(item).find('input[type=hidden]').each(function(i, t) {
					/*
					 * 개인화_김철(정렬상태 고정 유무)
					 * 정렬항목(sortField), 정렬순서(sortState), 정렬갯수(numPerPage)에 대한 FormData 초기화 분기
					 */
					if (Object.keys(personalizeSetting).length != 0) {
						if (personalizeSetting.sortFixed === 'fixed') {
							if ($(t).attr('name') != 'sortField' && $(t).attr('name') != 'sortState' && $(t).attr('name') != 'numPerPage') {
								$(t).val(FormData.data[right][$(t).attr('name')]);
							}
						} else {
							$(t).val(FormData.data[right][$(t).attr('name')]);
						}
					} else {
						$(t).val(FormData.data[right][$(t).attr('name')]);
					}
				});
			});

			/*$forms.each(function() {
			    var right = this.id.replace('SearchForm', '');
			    // 현재탭 제외 나머지 권리 필터 값 초기화
				initFilterData.setInitFilterData(right);
			});*/
			
			// 현재탭 제외 나머지 권리 필터 값 초기화
			initFilterData.setInitFilterData(currentTab2);
			
			// 권리별 필터 값 셋팅
			/* 탭 이동을 통한 검색 시, setFilterValues()와 filterValidation() 실행 시, 필터가 렌더 되는 시점에 따라 올바르게 동작하지 않을 수 있음
			 * 그래서 탭 이동을 통한 검색 시, filter가 렌더(innerHTML)되는 로직 마지막에 setFilterValues()와 filterValidation()수행하도록 조치
			 */
			if ($Btn != undefined && e != undefined) {
				// 상단 탭 이동에 따른 검색일 경우
				getTemplate(currentTab2, 'search', 'filter', 'rightTotalSearch');
			} else {
				// 메인 화면 검색 또는 상단 검색입력창을 통한 검색일 경우
				if (ResultData.getData(currentTab2) == undefined) {
					getTemplate(currentTab2, 'search', 'filter', 'rightTotalSearch');
				} else {
					setFilterValues('totalSearch', currentTab2, $('#mainResultFilter').find('input[type=checkbox], input[type=radio]'));
					if (!filterValidation('totalSearch', currentTab2, $('#mainResultFilter').find('ul.list'))) {
						return;
					}
				}
			}
			
			// 필터값을 상세검색에도 적용
			syncDetailSearchByFilter('filterSearch', currentTab2);
			
			// 최근 검색어 닫기
			$('#btnCloseMainSearch').click();
			
			checkRequest();
			
			$('#searchKind').val('totalSearch');
			initSortOption('totalSearch');
			
			// 권리별 국내외 통합검색 수행
			setTimeout(function(){
				customTotalSearch(currentTab2, tempResultTab);
	        }, 200);
		}
	} catch (e) {
		alert(e);
		return false;
	}
	
	// 2025.09.29 특화검색은 항상 가림
	//if(!(/kpat|kpa|abpat|abpatTrans/.test(currentTab2))) $('a[data-subtab-id=kpat]').addClass('active');
	['natlPat', 'mPat', 'etcPat'].forEach(id => {
		$(`div[data-tab-id=patentTab] a[data-subtab-id=${id}]`).addClass('hidden');
		$(`div[data-tab-id=patentTab] a[data-subtab-id=${id}]`).removeClass('active');
		if (/natlPat|mPat|etcPat/.test(currentTab2)) {
			initChangeViewBtn('kpat');
			$('a[data-subtab-id=kpat]').trigger('click');
		} else {
			initChangeViewBtn(currentTab2);
		}
	});

}

// 권리별 국내외 통합검색
function customTotalSearch(right, resultTab)
{
	// resultTab : 상위 권리(특실, 디자인, 상표, 심판, 기타문헌)
	switch (resultTab) {
		case 'patent' : patentTotalSearch(); break;
		case 'design' : designTotalSearch(); break;
		case 'trademark' : trademarkTotalSearch(); break;
		case 'judgement' : judgementTotalSearch(); break;
		case 'etc' : etcTotalSearch(); break;
	}
	
	// 초기화
	initDataForTotalSearch(right, resultTab); 	//권리별 국내외 통합검색에 따른 초기화
	initChangeViewBtn(right);					//권리별 검색결과 보기방식 초기화
	//initSortOption('totalSearch');
	
	// 하위 권리별  title 설정하기(웹접근성)
    const activTapMap = {
            kpat: "국내 특허 검색",
            abpat: "해외 특허 검색",
            abpatTrans: "해외 특허 검색",
            kpa: "KPA 특허 검색",
            kdg: "국내 디자인 검색",
            abdg: "해외 디자인 검색",
            ktm: "국내 상표 검색",
            abtm: "해외 상표 검색",
            jg: "심판 검색",
            ipNaviConflict: "분쟁 검색",
            ipNaviPrcdn: "판례 검색",
            cyber: "인터넷기술공지 검색",
            cntst: "아이디어공모전 검색",
            arti: "논문 검색"
    };
	
	//웹접근성 권리별 title 검색 설정
	let targetFormQueryText = $('#' + right + 'SearchForm').find('input[name=queryText]').val();
	document.title = "홈 > 지식재산정보검색 > " + activTapMap[right] + " (검색어: " + targetFormQueryText + ")";
}

//특허·실용신안 통합 검색
function patentTotalSearch()
{
	Promise.allSettled([doSearch('kpat', 'totalSearch'), doSearch('kpa', 'totalSearch'), doSearch('abpat', 'totalSearch'), doSearch('abpatTrans', 'totalSearch')])
	.then(function(results) {
		callBackForSearch('kpat', results, $('#patentTotalCount'));
	});
}

//디자인 통합 검색
function designTotalSearch()
{
	Promise.allSettled([ doSearch('kdg', 'totalSearch'), doSearch('abdg', 'totalSearch')])
	.then(function(results) {
		callBackForSearch('kdg', results, $('#designTotalCount'));
	});
}

//상표 통합 검색
function trademarkTotalSearch()
{
	Promise.allSettled([doSearch('ktm', 'totalSearch'), doSearch('abtm', 'totalSearch')])
	.then(function(results) {
		callBackForSearch('ktm', results, $('#trademarkTotalCount'));
	});
}

//심판 통합 검색
function judgementTotalSearch()
{
	Promise.allSettled([doSearch('jg', 'totalSearch'),doSearch('ipNaviPrcdn', 'totalSearch'),doSearch('ipNaviConflict', 'totalSearch')])
	.then(function(results) {
		callBackForSearch('jg', results, $('#judgementTotalCount'));
	});
}

//기타문헌 통합 검색
function etcTotalSearch()
{
	Promise.allSettled([doSearch('cntst', 'totalSearch'), doSearch('cyber', 'totalSearch'), doSearch('arti', 'totalSearch')])
	.then(function(results) {
		callBackForSearch('cntst', results, $('#etcTotalCount'));
	});
}

function callBackForSearch(right, results, $targetObj) {
	let abortYn = 'N';
	results.forEach(function(req) {
		if (req.status == 'rejected') {
			if (req.reason.statusText == 'abort') {
				abortYn = 'Y';
			}
		}
	});
	
	if (abortYn == 'N') {
		let totalCount = ResultData.getTabCount(right).toLocaleString();
		$targetObj.text(totalCount);
	} else {
		$targetObj.text('');
	}
	$targetObj.parent().removeClass('loading');
	$targetObj.parent().prop('disabled', false);
	$targetObj.show();
}

// 권리별 필터 초기화
function initFilter(right, mode, template)
{
	let bindTemplate = Handlebars.compile(template);
	if(dataNotFound && /natlPat|mPat|etcPat|ipNaviPrcdn|ipNaviConflict|arti|cntst|cyber/.test(right)) {
		searchPageModule.toggleResultFilter(false, false);
	} else {
		if(ResultData.getData(right) != undefined) {
			let resultHTML = bindTemplate(ResultData.getData(right).countInfo);
			resultHTML = updateContent(resultHTML);
			$('#mainResultFilter > div.body').html(resultHTML);
		}else {
			$('#mainResultFilter > div.body').html(bindTemplate());
		}

		let tempData = SaveData.getFilterData(right);
		if (sessionStorage.getItem('filterData') != null) {
			tempData = JSON.parse(sessionStorage.getItem('filterData'));
		}

		if (tempData == undefined || right != tempData.right) {
			tempData = initFilterItem[right];
			$.each(tempData, function(idx, key) {
				if (!$('#' + key).prop('checked')) {
					$('#' + key).click();
				}
			});
		} else {
			$.each(tempData, function(key, value) {
				$('#' + key).prop('checked', value);
			});
		}
		searchPageModule.toggleResultFilter(filterSet, true);
		
		// 검색결과 필터 행정상태(기본값 이외 선택시 전체보기)
		filterHangjungToggle(currentTab2);
		
		//필터값을 상세검색에도 적용
		syncDetailSearchByFilter('filterSearch', currentTab2);
		
		// 상단 탭 이동에 따른 통합 검색 시, 이동 상위 권리탭에 대한 하위 권리의 필터가 렌더 된 후 setFilterValues(), filterValidation()가 동작하도록 조치
		if (mode == 'rightTotalSearch') {
			setFilterValues('totalSearch', right, $('#mainResultFilter').find('input[type=checkbox], input[type=radio]'));
			
			// 필터 valid 체크
			if (!filterValidation('totalSearch', currentTab2, $('#mainResultFilter').find('ul.list'))) {
				return;
			}
		}
	}
}


//(공통) 템플릿 호출 및 저장
function getTemplate(right, kind, page, mode, result)
{
	let data = SaveData.getTemplateData(right);
	let template = '';
	
	if (data != undefined) {
		if (data[kind + "/" + page] != undefined) {
			template = data[kind + "/" + page];
		}
	}
	
	if (template == '' || template == undefined) {
		let templateUrl = '/khome/template/getTemplate.do?right=' + right + '&kind=' + kind + '&page=' + page;
		//$.get(templateUrl, function(template) {
		fetch(templateUrl).then(function(res){ return res.text(); }).then(function(template) {
			let tempData = {};
			tempData[kind + "/" + page] = template;
			SaveData.setTemplateData(right, tempData);
			
			if (page.indexOf('List') > -1) {
				if (kind == 'search') {
					if (/natlPat|mPat|etcPat/.test(right)) {
						renderDataForSpecializationSearch(right, mode, template, kind);
					} else if (/gi/.test(right))  {
						renderDataForGiSearch(right, mode, template, result);
					} else if (right == 'abpatTrans') {
						renderDataForSearch(right, mode, template, result == undefined ? 'us' : result);
					} else {
						renderDataForSearch(right, mode, template, page);
					}
				} else if (kind == 'common') {
					renderDataForCode(right, mode, template, result);
				}
			} else if (page == 'filter') {
				initFilter(right, mode, template);
			} else if (page.indexOf('view') > -1) {
				if (/gi/.test(right)) {
					renderDataForGiSearch(right, mode, template, result);
				} else {
					renderDataForDetail(right, result, template, mode);
				}
			} else if ((page == 'image' || page == 'imagePop') && right =='kpat') {
				renderDataForAllimg(right, result, template, mode);
			} else if (page == 'resultStatis') {
				renderDataForResultStatis(right, result, template);
			} else if (page == 'similar' || page == 'special' || page == 'specialJp' || page == 'specialIdea') {
				renderDataForSimilarPop(right, result, template, page);
			} else if (page == 'dataNotFound') {
				renderForBlank(right, template);
			} else if (kind.indexOf('myFolder') > -1) {
				renderDataForFolder(result, template, mode);
			} else if (kind.indexOf('mngtQry') > -1) {
				renderDataForMngtQry(result, template, mode);
			} else if (page == 'translate'|| page == 'translateKpat'|| page == 'translateCN') {
				renderTranslate(right, result, template);
			} else if (page == 'kpat'|| page == 'kdg'|| page == 'ktm') {
				renderInfoData(right, result, template);
			} else if (kind.indexOf('myInterest') > -1) {
				renderDataForMyInterest(result, template, mode);
			} else if (page.indexOf('keyword') > -1) {
				renderDataForSearchKeywordWeight(result, template, mode);
			} else if (page == 'extinct') {
				renderExtinctData(right, result, template);
			}
		});
	} else {
		if (page.indexOf('List') > -1) {
			if (kind == 'search') {
				if (/natlPat|mPat|etcPat/.test(right)) {
					renderDataForSpecializationSearch(right, mode, template, kind);
				} else if (/gi/.test(right))  {
					renderDataForGiSearch(right, mode, template, result);
				} else if (right == 'abpatTrans') {
					renderDataForSearch(right, mode, template, result == undefined ? 'us' : result);
				} else {
					renderDataForSearch(right, mode, template, page);
				}
			} else if (kind == 'common') {
				renderDataForCode(right, mode, template, result)
			}
		} else if (page == 'filter') {
			initFilter(right, mode, template);
		} else if (page.indexOf('view') > -1) {
			if (/gi/.test(right)) {
				renderDataForGiSearch(right, mode, template, result);
			} else {
				renderDataForDetail(right, result, template, mode);
			}
		} else if ((page == 'image' || page == 'imagePop') && right =='kpat') {
			renderDataForAllimg(right, result, template, mode);
		} else if (page == 'resultStatis') {
			renderDataForResultStatis(right, result, template);
		} else if (page == 'similar' || page == 'special' || page == 'specialJp' || page == 'specialIdea') {
			renderDataForSimilarPop(right, result, template, page);
		} else if (page == 'dataNotFound' || page == 'searchTip') {
			renderForBlank(right, template);
		} else if (kind.indexOf('myFolder') > -1) {
			renderDataForFolder(result, template, mode);
		} else if (kind.indexOf('mngtQry') > -1) {
			renderDataForMngtQry(result, template, mode);
		} else if (page == 'translate') {
			renderTranslate(right, result, template);
		} else if (page == 'kpat'|| page == 'kdg'|| page == 'ktm') {
			renderInfoData(right, result, template);
		} else if (kind.indexOf('myInterest') > -1) {
			renderDataForMyInterest(result, template, mode);
		} else if (page.indexOf('keyword') > -1) {
			renderDataForSearchKeywordWeight(result, template, mode);
		} else if (page == 'extinct') {
			renderExtinctData(right, result, template);
		}
	}
}

//지리적표시 검색(일반,상세)
function openPopGiSearch(param, mode)
{
	if (/init|return|search/.test(mode)){
		let $targetForm = $('#' + param + 'SearchForm');
		$('.gi-detail-area').addClass('hidden');
		
		if (mode == 'init') {
			let tempCountYn = $('input[name=countYn]').val();
			if (tempCountYn == 'N') {
				return false;
			}
		} 
		else if (mode == 'return') {
			// 초기화(처음으로)
			$('.gi-intro').removeClass('hidden');
			$('#giSearch').val('');
			$('.gi-result-area').html('');
			$('.gi-detail-area').html('');
			return false;
		} else if (mode == 'search') {
			if ($('#giSearch').val() == '') {
				alert('검색어를 입력해주세요.');
				return false;
			}
			// 통계_지리적표시 보기 내 검색
			recordServiceStats('KTM', 'OPSVC', 'SGI');
			$targetForm.find('input[name=queryText]').val($('#giSearch').val());
		}
		
		toggleLoadingDialog('#content', true);
		let ajaxResult = $.ajax({
			async: true,
			type: 'POST',
			url: $targetForm.attr('action'),
			data: $targetForm.serialize(),
			dataType: 'json',
			success: function(data)
			{
				ResultData.setData(param, data);
				$('input[name=countYn]').val('Y');
				$('.gi-intro').addClass('hidden');
				$('#giSearch').val(data.queryText);
				getTemplate(param, 'search', 'giList', 'giSearch', data);
			},
			error: function(xhr, status, error)
			{
				alert('통신 중 오류가 발생하였습니다.');
			}
		});
		return ajaxResult;
	} else if (/detail/.test(mode)) {
		// 폼 셋팅
		let $giDetailForm = $('<form>', {
			id: '$giDetailForm',
			name: '$giDetailForm',
			method: 'POST',
			action: '/kdtj/tmgi1000a.do'
		});
		
		// 파라미터 셋팅
		let dateQuery = {};
		dateQuery['method'] = 'getGiDetail';
		dateQuery['RFEVDNO'] = param;
		$.each(dateQuery, function(key, val) {
			$giDetailForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
		});
		
		toggleLoadingDialog('#content', true);
		let ajaxResult = $.ajax({
			async: false,
			type: 'POST',
			url: $giDetailForm.attr('action'),
			data: $giDetailForm.serialize(),
			dataType: 'json',
			success: function(data)
			{
				getTemplate('gi', 'detail', 'view', 'giDetail', data);
			},
			error: function(xhr, status, error)
			{
				alert('통신 중 오류가 발생하였습니다.');
			}
		});
	}
}

//유사특허 상세 데이터 렌더링
function openPopKdcSearchSpecial(right, params)
{
	let tempRight = '';
	let $tempForm = $('<form>', {
		id: 'tempForm',
		name: 'tempForm',
		method: 'POST',
		target: right,
		action: '/kdc/docresult.do'
	});
	
	$.each(params, function(key, val) {
		$tempForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
		if (key == 'next' && val == 'jpList') {
			tempRight = 'abpat';
		} else if (key == 'next' && val == 'ideaList') {
			tempRight = 'idea';
		}
	});
	
	toggleLoadingDialog('#content', true);
	
	// 저장항목 검색
	$.ajax({
		type: 'POST',
		url: $tempForm.attr('action'),
		data: $tempForm.serialize(),
		dataType: 'json',
		success: function(data)
		{
			if (tempRight == 'abpat') {
				getTemplate('kdc', 'search', 'specialJp', 'openPop', data);
			} else if (tempRight == 'idea'){
				getTemplate('kdc', 'search', 'specialIdea', 'openPop', data);
			} else {
				getTemplate('kdc', 'search', 'special', 'openPop', data);
			}
		},
		error: function(xhr, status, error)
		{
			alert('통신 중 오류가 발생하였습니다.');
		},
	});
}

// 검색결과 유사특허 검색
function openPopKdcSearch(right, applno)
{
	let reqUrl = '';
	let params = '';
	
	reqUrl = '/kdc/docresult.do';
	params = 'collection=kr+pat++sil+&query=' + applno + '&next=SimpleList&exquery=&startDate=&endDate=&osDate=&odDate=&gsDate=&gdDate=&filechk=&expand=NO&searchMethod=&strstat=SMART%7CAN%7C&checkPot=S';
	
	let ajaxResult = $.ajax({
		async: false,
		type: 'POST',
		url: reqUrl,
		data: params,
		dataType: 'json',
		success: function(data)
		{
			getTemplate(right, 'search', 'similar', 'openPop', data);
		},
		error: function(xhr, status, error)
		{
			alert('통신 중 오류가 발생하였습니다.');
		}
	});
	return ajaxResult;
}

//지리적표시 결과화면 렌더링
function renderDataForGiSearch(right, mode, template, result)
{
	let data = '';
	if (mode == 'giSearch') {
		data = ResultData.getData(right);
	} else if (mode == 'giDetail') {
		data = result;
	}
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	
	// 상세보기 화면 초기화
	$('.gi-detail-area').addClass('hidden');
	
	// 화면 렌더링
	if (mode == 'giSearch') {
		$('.gi-result-area').html(resultHTML);
		let targetFormId = '#' + right + 'SearchForm';
		let currentPage = parseInt($(targetFormId).find('input[name=currentPage]').val());
		let numPerPage = parseInt($(targetFormId).find('input[name=numPerPage]').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#gi-pagination'), 'giSearchResult');
	} else if (mode == 'giDetail') {
		$('.gi-detail-area').removeClass('hidden');
		$('.gi-detail-area').html(resultHTML);
	}
	toggleLoadingDialog(loadingDialogTarget, false);
}

// 특화검색 결과화면 렌더링
function renderDataForSpecializationSearch(right, mode, template, kind)
{
	// 데이터 셋팅
	let data = '';
	if (mode == 'selectView') {
		data = selectViewData;
		totalcount = data.countInfo.totalcount;
	} else {
		data = ResultData.getData(right);
		totalcount = data.countInfo.totalcount;
	}
	
	// 템플릿 데이터 바인딩
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	
	// 검색결과 건수 텍스트 변경
	let resultTopText = '';
	let targetFormId = '#' + right + 'SearchForm';
	//resultTopText = '[' + data.specialFg + ']' + '  ' + '총 <em>' + data.countInfo.totalcount.toLocaleString() + '</em>건이 검색되었습니다.';
	//resultTopText = '총 <em>' + data.countInfo.totalcount.toLocaleString() + '</em>건이 검색되었습니다.';

	if(mode == 'selectView') {
		resultTopText = '<span data-lang-id="srlt.txt21">'+i18next.t('srlt.txt21')+'</span> <em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt17">'+i18next.t('srlt.txt17')+'</span> <em>' + totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt18">'+i18next.t('srlt.txt18')+'</span>';
	} else {
		resultTopText = '<span data-lang-id="srlt.txt21">'+i18next.t('srlt.txt21')+'</span> <em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt20">'+i18next.t('srlt.txt20')+'</span>';
	}
	$('#resultTotal').html(resultTopText);
	
	// 필터 off
	searchPageModule.toggleResultFilter(false, false);
	
	// 템플릿 삽입
	$('#resultSection').html(resultHTML);
	
	// 페이징 셋팅
	/* if (mode != 'selectView') {
		let targetFormId = '#' + right + 'SearchForm';
		let currentPage = parseInt($(targetFormId).find('input[name=currentPage]').val());
		let numPerPage = parseInt($(targetFormId).find('input[name=numPerPage]').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#pagination'), 'specializationForm');
	} else {
		$('#pagination').html('');
	}*/
		let currentPage = parseInt($(targetFormId).find('input[name=currentPage]').val());
		let numPerPage = parseInt($(targetFormId).find('input[name=numPerPage]').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#pagination'), 'specializationForm');
	
	// 권리탭 셋팅(임시)
	if (data.rightFg != undefined) {
		$('div[data-tab-id=designTab] a[data-subtab-id=' + right + ']').removeClass('hidden');
		$('div[data-tab-id=designTab] #specializationTotalCount').siblings('em').text(data.specialFg);
	} else {
		$('div[data-tab-id=patentTab] a[data-subtab-id=' + right + ']').removeClass('hidden');
		$('div[data-tab-id=patentTab] #specializationTotalCount').siblings('em').text(data.specialFg);
	}
	currentTab1 = SaveData.getParentTab(right) + 'Tab';
	currentTab2 = right;
	let $tab2wrap = $('div[data-tab-id=' + currentTab1 + ']');
	$tab2wrap.find('a[data-subtab-id]').removeClass('active');
	$tab2wrap.find('a[data-subtab-id=' + right + ']').addClass('active');

	//2025.09.18 상세보기 초기화
	searchDrag.toggleDetail(false, false);
	
	// 보기방식 셋팅
	initChangeViewBtn(right);
	$('#resultSection').attr('data-view-type', $('button[data-view-type].active').data('view-option'));
	
	// 정렬 셋팅
	if (mode != 'optionSearch') {
		initSortOption('renderData');
	}
	
	// 로딩 끝
	toggleLoadingDialog(loadingDialogTarget, false);
}

// 검색결과 화면 페이지당 검색갯수 초기화
function initSortCondition(num)
{
	if (num != undefined) {
		$('#sortCondition03').html('');
		$('#sortCondition03').append('<option value="' + num + '" selected="" data-lang-id="srlt.' + num + '">' + num + '개</option>');
		$('#' + currentTab2 + 'SearchForm').find('input[name=numPerPage]').val(num);
	} else {
		$('#sortCondition03').html('');
		$('#sortCondition03').append('<option value="10" data-lang-id="srlt.10">10개</option>');
		$('#sortCondition03').append('<option value="30" selected="" data-lang-id="srlt.30">30개</option>');
		$('#sortCondition03').append('<option value="60" data-lang-id="srlt.60">60개</option>');
		$('#sortCondition03').append('<option value="90" data-lang-id="srlt.90">90개</option>');
		$('#' + currentTab2 + 'SearchForm').find('input[name=numPerPage]').val('30');
	}
}

// 검색키워드 보기 렌더링
function renderDataForSearchKeywordWeight(data, template, mode)
{
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('#modalSearchKeyword').html(resultHTML);
	
	initSearchKeywordWeight('init');
	
	toggleLoadingDialog(loadingDialogTarget, false);
}

// 지식재산저장소 렌더링
function renderDataForMyInterest(data, template, mode)
{
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('#newDataResultSection').html(resultHTML);
	let currentPage = parseInt($('#currentMyInterestPage').val());
	let numPerPage = parseInt($('#numPerMyInterestPage').val());
	
	if (data.countInfo.totalcount != undefined) {
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#myInterest-pagination'), 'myInterestForm');
	}
	
	toggleLoadingDialog(loadingDialogTarget, false);
}

// 내검색식 렌더링
let mngtQryInitFgA = 'N'; // 최초 1회 실행을 위한 플래그 A
let mngtQryInitFgB = 'Y'; // 최초 1회 실행을 위한 플래그 B
function renderDataForMngtQry(data, template, mode) 
{
	let bindTemplate;
	let resultHTML;
	if(mode != 'mngtQryListLeft') {
		bindTemplate = Handlebars.compile(template);
		resultHTML = bindTemplate(data);
		resultHTML = updateContent(resultHTML);
	}
	if (mode == 'mngtQryList') {
		$('#myExpressionView .folder-list-area').html(resultHTML);
		$('#myExpressionView .btn-folder').eq(0).trigger('click');
		mngtQryInitFgB = 'Y';
	} else if (mode == 'mngtQryResult') {
		$('#myExpressionView .folder-detail-area').html(resultHTML);
		let currentPage = parseInt($('#currentMngtQryPage').val());
		let numPerPage = parseInt($('#numPerMngtQryPage').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#mngtQry-pagination'), 'mngtQryForm');
		mngtQryInitFgA = 'Y';
	} else if (mode == 'mngtQryMailing') {
		$('#myExpressionView .folder-detail-area').html(resultHTML);
		// 페이징 임시 주석
		/*let currentPage = parseInt($('#currentMngtQryPage').val());
		let numPerPage = parseInt($('#numPerMngtQryPage').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#mngtQryMailing-pagination'), 'mngtQryForm');*/
	} else if (mode == 'mngtQryApplyForm') {
		$('#myExpressionMailing .con-body').html(resultHTML);
		
		//let tempKind = $('#mailingKind').val();
		let tempKind = data.kind;
		$('#expressionMail').val(data.title);
		$('#myExpressionMailing .fg-body').eq(6).find('p').text(getCurrentDateTime('yyyy년 mm월 dd일'));
		
		if (tempKind == 'ABR') { 					// 해외특허
			$('#emck0101').prop('disabled', true);
			$('#emck0102').prop('checked', true);
		} else if (tempKind == 'TM') {				// 해외상표
			$('#emck0101').prop('disabled', true);
			$('#emck0102').prop('checked', true);
		} else if (tempKind == 'TXT') {				// 문장검색
			$('#emck0102').prop('disabled', true);
		} else {
													// 그외
		}
	} else if (mode == 'mngtQryUpdateForm') {
		$('#myExpressionMailingUpdate .con-body').html(resultHTML);
		
		let tempKind = data.kind;
		let tempSrch_dt_fg = data.srch_dt_fg; //매일(D), 매주(W), 매월(M)
		let tempSrch_term_fg = data.srch_term_fg; // 공개일자(OD, OPD), 공고일자(PD)
		
		$('#expressionMail').val(data.title);
		$('#myExpressionMailingUpdate .fg-body').eq(6).find('p').text(getCurrentDateTime('yyyy년 mm월 dd일'));
		
		if (tempKind == 'KP') {
			$('#emck0001').trigger('click')
			$('#emck0002').prop('disabled', true);
			$('#emck0003').prop('disabled', true);
			$('#emck0004').prop('disabled', true);
			$('#emck0005').prop('disabled', true);
			
			// 검색주기
			if (tempSrch_dt_fg == 'D') {
				$('#emck0401').prop('checked', true);
			} else {
				$('#emck0402').prop('checked', true);
			}
			
			// 기준일자
			if (tempSrch_dt_fg == 'OPD') {
				$('#emck0301').prop('checked', true);
			} else {
				$('#emck0302').prop('checked', true);
			}
		} else if (tempKind == 'KD') {
			$('#emck0001').prop('disabled', true);
			$('#emck0002').trigger('click')
			$('#emck0003').prop('disabled', true);
			$('#emck0004').prop('disabled', true);
			$('#emck0005').prop('disabled', true);
			
			// 검색주기
			if (tempSrch_dt_fg == 'D') {
				$('#emck0401').prop('checked', true);
			} else {
				$('#emck0402').prop('checked', true);
			}
			
			// 기준일자
			if (tempSrch_dt_fg == 'OD') {
				$('#emck0301').prop('checked', true);
			} else {
				$('#emck0302').prop('checked', true);
			}
		} else if (tempKind == 'KT') {
			$('#emck0001').prop('disabled', true);
			$('#emck0002').prop('disabled', true);
			$('#emck0003').trigger('click')
			$('#emck0004').prop('disabled', true);
			$('#emck0005').prop('disabled', true);
			
			// 검색주기
			if (tempSrch_dt_fg == 'D') {
				$('#emck0401').prop('checked', true);
			} else {
				$('#emck0402').prop('checked', true);
			}
		} else if (tempKind == 'US' || tempKind == 'EP' || tempKind == 'WO' || tempKind == 'CN' || tempKind == 'JP') {
			$('#emck0001').prop('disabled', true);
			$('#emck0002').prop('disabled', true);
			$('#emck0003').prop('disabled', true);
			$('#emck0004').trigger('click')
			$('#emck0005').prop('disabled', true);
			
			// 권리구분
			if (tempKind == 'US') {
				$('#emck0101').prop('checked', true);
			} else if (tempKind == 'EP') {
				$('#emck0102').prop('checked', true);
			} else if (tempKind == 'WO') {
				$('#emck0103').prop('checked', true);
			} else if (tempKind == 'JP') {
				$('#emck0104').prop('checked', true);
			} else if (tempKind == 'CN') {
				// 클릭에 따른 검색주기 매월 생성으로 별도 트리거 처리
				$('#emck0105').trigger('click');
			}
		} else if (tempKind == 'SK' || tempKind == 'SJ') {
			$('#emck0001').prop('disabled', true);
			$('#emck0002').prop('disabled', true);
			$('#emck0003').prop('disabled', true);
			$('#emck0004').prop('disabled', true);
			$('#emck0005').trigger('click')
			
			// 권리구분
			if (tempKind == 'SK') {
				$('#emck0201').prop('checked', true);
			} else if (tempKind == 'SJ') {
				$('#emck0202').prop('checked', true);
			}
			
			// 검색주기
			if (tempSrch_dt_fg == 'D') {
				$('#emck0401').prop('checked', true);
			} else {
				$('#emck0402').prop('checked', true);
			}
		}
	} else if (mode == 'mngtQryListLeft') {
		if($('#myExpressionView .btn-folder').hasClass('active')) {
			$('#myExpressionView .btn-folder').attr('title','선택되지 않음');
			$('#myExpressionView .btn-folder.active').attr('title','선택됨');
		}
		$('#myExpressionView .folder-list-area').html(resultHTML);
	}
	commonLayout();
	toggleLoadingDialog(loadingDialogTarget, false);
	
	// 화면 렌더링 후, init 수행
	if (mngtQryInitFgA == 'Y' && mngtQryInitFgB == 'Y' && data.myKiprisYn != 'Y') {
		fnMy.init();
		mngtQryInitFgB = 'N';
	} else if (data.myKiprisYn == 'Y') {
		fnMangeFolder.init();
	}
}

//마이폴더 폴더리스트 렌더링
let myfolderInitFgA = 'N'; // 최초 1회 실행을 위한 플래그 A
let myfolderInitFgB = 'Y'; // 최초 1회 실행을 위한 플래그 B
function renderDataForFolder(data, template, mode) 
{
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	
	if (mode == 'folderList') {
		$('#myFolderView .folder-list-area').html(resultHTML);
		if (parseInt(data.resultCount) == 0) {
			getTemplate('common', 'myKipris/myFolder', 'noData', 'folderRight', data);
			toggleLoadingDialog(loadingDialogTarget, false);
		} else if (data.folderList.length == 0) {
			getTemplate('common', 'myKipris/myFolder', 'noData', 'folderRight', data);
			toggleLoadingDialog(loadingDialogTarget, false);
		} else {
			getTemplate('common', 'myKipris/myFolder', 'right', 'folderRight', data);
		}
		myfolderInitFgB = 'Y';
	} else if (mode == 'folderRight') {
		if (parseInt(data.resultCount) == 0) {
			$('#myFolderView .folder-detail-area').html(resultHTML);
			toggleLoadingDialog(loadingDialogTarget, false);
		} else {
			$('#myFolderView .folder-detail-area').html(resultHTML);
			$('#myFolderView .btn-category').eq(0).trigger('click');
		}
	} else if (mode == 'folderResult') {
		$('#myFolderView #resultSection').html(resultHTML);
		let currentPage = parseInt($('#currentMyFolderPage').val());
		let numPerPage = parseInt($('#numPerMyFolderPage').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#myfolder-pagination'), 'myFolderForm');
		toggleLoadingDialog(loadingDialogTarget, false);
		myfolderInitFgA = 'Y';
	} else if (mode == 'folderResult_search') {
		$('#myFolderView #resultSection').html(resultHTML);
		let currentPage = parseInt($('#currentMyFolderPageSrch').val());
		let numPerPage = parseInt($('#numPerMyFolderPage').val());
		generatePagingHtml(currentPage, numPerPage, data.countInfo.totalcount, $('#myfolder-pagination'), 'myFolderForm_search');
		toggleLoadingDialog(loadingDialogTarget, false);
	}
	
	// 화면 렌더링 후, init 수행
	if (myfolderInitFgA == 'Y' && myfolderInitFgB == 'Y' && data.myKiprisYn != 'Y') {
		fnMy.init();
		myfolderInitFgB = 'N';
	} else if (data.myKiprisYn == 'Y') {
		fnMangeFolder.init();
	}
	
	if($('#myFolderView .btn-category').hasClass('active')) {
		$('#myFolderView .btn-category').attr('title','선택되지 않음');
		$('#myFolderView .btn-category.active').attr('title','선택됨');
	}
}

//코드검색결과 렌더링
function renderDataForCode(right, mode, template, data)
{
	let $target;
	if (right == 'CRM') {
		$target = $('#container .search-service-list');
	} else {
		$target = $('#support' + right + ' .support-search-list');
		if ($target.find('input[name=kindName]').length != 0) {
			data.kindName = $target.find('input[name=kindName]').val();
		}
	}
	
	// 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$target.find('.list-body').html(resultHTML);
	
	if (mode == 'explain') {
		$('#support' + right + ' .form-search').attr('onkeydown', "handleEnter(event, doCodeSearch, ['" + right + "', 'explain'])");
		$('#support' + right + ' .btn-search').attr('onclick', "doCodeSearch('" + right + "','explain')");
	}
	if (mode == 'explain' || mode == 'pagingexp') {
		$target.find('input[type=checkbox]').prop('disabled', true);
	}
	
	// 페이징 생성
	if (right != 'LC' && right != 'Expand') {
		let pageNum = parseInt($target.find('input[name=pageNum]').val());
		if(mode == 'explain' || mode == 'pagingexp') {
			generatePagingHtml(pageNum, 10, data.countInfo.totalcount, $target, 'support' + right + 'exp');
		} else {
			generatePagingHtml(pageNum, 10, data.countInfo.totalcount, $target, 'support' + right);
		}
		
		$('#' + right.toLowerCase() + 'TotalCount').text(data.countInfo.totalcount.toLocaleString());
	}
	
	if (right == 'CRM') {
		$target.siblings('.recommend-intro').addClass('hide');
	} else {
		$target.siblings('.support-info').addClass('hide');
	}
	$target.removeClass('hide');
	
	toggleLoadingDialog(loadingDialogTarget, false);
}

//검색결과 없음 렌더링
function renderForBlank(right, template)
{
	let isSpecializationSearch = /natlPat|mPat|etcPat/.test(right);
	let queryData = {queryText: $('#' + right + 'SearchForm').find('input[name=queryText]').val(), isSpecializationSearch:isSpecializationSearch};
	
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(queryData);
	resultHTML = updateContent(resultHTML);
	$('#resultSection').attr('data-view-type', 'basic');
	$('#resultSection').html(resultHTML);
	//2025.09.18 지리적표시 등 검색결과 없을 경우 total-box button 지움
	$('.total-box').find('button').hide();
	toggleLoadingDialog(loadingDialogTarget, false);
	
	/*
	 * 2026.06.11 OJE
	 * 선택보기 후, 검색 시 결과가 없는 경우
	 * 이전 선택보기가 남아있지 않도록 선택보기 초기화
	 */
	initSelectView();
}

//검색결과 데이터 렌더링
function renderDataForSearch(right, mode, template, page)
{
	// 저장된 결과값 및 대상 form 셋팅
	let data;
	let totalcount;
	if (mode == 'selectView') {
		data = selectViewData;
		totalcount = data.countInfo.totalcount;
	} else {
		data = ResultData.getData(right);
		totalcount = data.countInfo.totalcount;
		// 해외특허 한글검색 관련 추가
		if (right == 'abpatTrans') {
			data.resultList = data[page + 'ResultList'];
			totalcount = data.countInfo[page.replace(/\b[a-z]/, letter => letter.toUpperCase()) + 'RecordCount'];
		}
	}
	
	let targetFormId = '#' + right + 'SearchForm';
	
	// 상단 권리탭 건수 변경(필터 검색일 경우만)
	if (mode == 'filter' || mode == 'statResearch') {
		setTabCount(right);
	}
	
	// 검색결과 상단의 키워드에 대한 결과건수 텍스트 변경
	let resultTopText = '';
	if (mode == 'selectView') {
		if (right == 'abpatTrans') {
			// resultTopText = '<h3 id="resultTotal" class="total">[' + getNatlDesc(page) + '] <em>' + $(targetFormId).find('input[name=queryText]').val() + '</em><span data-lang-id="srlt.txt16">'+i18next.t('srlt.txt16')+'</span> <em>' + ResultData.getData(right).countInfo[page + 'RecordCount'].toLocaleString() + '</em><span data-lang-id="srlt.txt17">'+i18next.t('srlt.txt17')+'</span><em>' + totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt18">'+i18next.t('srlt.txt18')+'</span></h3>';
			resultTopText = '<h3 id="resultTotal" class="total"><em>' + $(targetFormId).find('input[name=queryText]').val() + '</em><span data-lang-id="srlt.txt16">'+i18next.t('srlt.txt16')+'</span> <em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt17">'+i18next.t('srlt.txt17')+'</span> <em>' + totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt18">'+i18next.t('srlt.txt18')+'</span></h3>';
		} else {
			resultTopText = '<h3 id="resultTotal" class="total"><em>' + $(targetFormId).find('input[name=queryText]').val() + '</em><span data-lang-id="srlt.txt16">'+i18next.t('srlt.txt16')+'</span> <em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt17">'+i18next.t('srlt.txt17')+'</span> <em>' + totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt18">'+i18next.t('srlt.txt18')+'</span></h3>';
		}
	} else {
		if (right == 'abpatTrans') {
			// resultTopText = '<h3 id="resultTotal" class="total">[' + getNatlDesc(page) + '] <em>' + $(targetFormId).find('input[name=queryText]').val() + '</em><span data-lang-id="srlt.txt19">'+i18next.t('srlt.txt19')+'</span> <em>' + totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt20">'+i18next.t('srlt.txt20')+'</span></h3>';
			resultTopText = '<h3 id="resultTotal" class="total"><em>' + $(targetFormId).find('input[name=queryText]').val() + '</em><span data-lang-id="srlt.txt19">'+i18next.t('srlt.txt19')+'</span> <em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt20">'+i18next.t('srlt.txt20')+'</span></h3>';
		} else {
			resultTopText = '<h3 id="resultTotal" class="total"><em>' + $(targetFormId).find('input[name=queryText]').val() + '</em><span data-lang-id="srlt.txt19">'+i18next.t('srlt.txt19')+'</span> <em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="srlt.txt20">'+i18next.t('srlt.txt20')+'</span></h3>';
			
			if (right == 'ktm') {
				if (data.giCount == '0') {
					resultTopText += '<button type="button" class="btn" data-level="primary" data-size="xs" data-lang-id="dtvw.trademark.lgim" title="새 창, 지리적표시" onclick="openWindow(\'giSearch\', {queryText:\'' + $(targetFormId).find('input[name=queryText]').val() + '\', countYn:\'N\'})">'+i18next.t('dtvw.trademark.lgim')+'</button>';
				} else {
					resultTopText += '<button type="button" class="btn" data-level="primary" data-size="xs" data-lang-id="dtvw.trademark.gimc" title="새 창, 지리적표시" onclick="openWindow(\'giSearch\', {queryText:\'' + $(targetFormId).find('input[name=queryText]').val() + '\', countYn:\'Y\'})">'+i18next.t('dtvw.trademark.gimc')+' '+data.giCount+i18next.t('dtvw.trademark.case')+'</button>'
				}
			}
		}
	}
	//$('#resultTotal').html(resultTopText);
	$('.total-box').html(resultTopText);
	
	// 국내 특실 검색 결과 화면에서 '기술검색 인사이트 배너' 제공 
	checkHeadBanner(currentTab2);
	
	let currentPage = '';
	if (currentTab2 == 'ipNaviConflict' || currentTab2 == 'ipNaviPrcdn') {
		currentPage = parseInt($(targetFormId).find('input[name=pageNum]').val());
	} else {
		currentPage = parseInt($(targetFormId).find('input[name=currentPage]').val());
	}
	let numPerPage =  '';
	if (currentTab2 == 'ipNaviConflict' || currentTab2 == 'ipNaviPrcdn') {
		numPerPage = parseInt($(targetFormId).find('input[name=maxCount]').val());
	} else {
		numPerPage = parseInt($(targetFormId).find('input[name=numPerPage]').val());
	}
	
	// 검색필터 초기화(페이징 검색, 보기방식 변경 제외)
	if (mode != 'paging' && mode != 'changeView' && mode != 'selectView') {
		// 기타문헌 등 필터가 존재하지 않을 경우, 필터 부분 감추기
		if (currentTab1 == 'etcTab') {
			searchPageModule.toggleResultFilter(false, false);
		} 
		// 심판(판례,분쟁), 필터 부분 감추기
		else if (currentTab1 == 'judgementTab' && (currentTab2 == 'ipNaviPrcdn' || currentTab2 == 'ipNaviConflict')) {
			searchPageModule.toggleResultFilter(false, false);
		} else {
			if (mode != 'existResult') {
				getTemplate(right, 'search', 'filter', mode);
			}
		}
		
		// 선택보기 초기화
		initSelectView();
	}
	
	// 상세보기 닫기
	searchDrag.toggleDetail(false, false);
	
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('#resultSection').html(resultHTML);
	
	// 도면일괄보기(국내 특실)
	if (page == 'allList' && right == 'kpat') {
		imageLoadMain();
	}
	
	generatePagingHtml(currentPage, numPerPage, totalcount, $('#pagination'), 'searchResult');
	$('#resultSection').attr('data-view-type', $('button[data-view-type].active').data('view-option'));
	toggleLoadingDialog(loadingDialogTarget, false);
}

//검색결과 메인화면 도면 일괄보기 렌더링
function renderDataForAllimgMain(right, data, template)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('.thumb-wrap').html(resultHTML);
	toggleLoadingDialog(loadingDialogTarget, false);
}

//검색결과 상세보기 데이터 렌더링
function renderDataForDetail(right, data, template, mode)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	
	if(right == 'kpat' && mode == 'openDetail') {
		const regex = /(<div[^>]*id\s*=\s*['"]kpa_all['"][^>]*?)(style\s*=\s*['"][^'"]*?display\s*:\s*none[^'"]*?['"])([^>]*>)/i;
		const regex2 = /(<div[^>]*id\s*=\s*['"]sum_all['"][^>]*?)(style\s*=\s*['"][^'"]*?display\s*:\s*block[^'"]*?['"])([^>]*>)/i;
		const kpaTitle = resultHTML.indexOf('KPA_title');
		const kpaAbs = resultHTML.indexOf('kpa-content');
		const kpaAll = resultHTML.indexOf('kpa_all');
		const sumAll = resultHTML.indexOf('sum_all');
		if(i18next.language == 'en' && kpaTitle != -1 && kpaAbs != -1) {
			const replacement = '$1style="display: block"$3';
			const replacement2 = '$1style="display: none"$3';
			resultHTML = resultHTML.replace(regex, replacement);
			resultHTML = resultHTML.replace(regex2, replacement2);
			
		}
	}
	
	if (mode == 'HAENGJEONG') {		
		if (right == 'ktm') {
			$('.tab-con[data-tab-id=detail07]').html(resultHTML);
		}
		else if (right == 'kdg') {
			$('.tab-con[data-tab-id=detail08]').html(resultHTML);
		}
		else {
			$('.tab-con[data-tab-id=detail09]').html(resultHTML);
		}
	} else if (mode == 'RGSTFEE') {
		$('.tab-con[data-tab-id=detail03]').html(resultHTML);
	} else {
		$('#mainResultDetail').html(resultHTML);
		
		if(mode == 'P') {
			if(right == 'kdg'){
				$('button[data-tab-id=detail03]').trigger('click');
			} else {
				$('button[data-tab-id=detail02]').trigger('click');
			}
			toggleLoadingDialog('#pdfViewer01', true);
		}
		if(mode == 'R') {
			if(right == 'kdg'){
				$('button[data-tab-id=detail04]').trigger('click');
				toggleLoadingDialog('#pdfViewer03', true);
			} else {
				$('button[data-tab-id=detail03]').trigger('click');
				toggleLoadingDialog('#pdfViewer02', true);
			}
		}
		if(mode == 'C') {
			if(right == 'kdg'){
				$('button[data-tab-id=detail05]').trigger('click');
			} else {
				$('button[data-tab-id=detail04]').trigger('click');
			}
		}
		if ('kpat|kpa|abpat|abpatTrans|ktm|abtm|kdg|abdg'.indexOf(right) > -1) {
			/*
			 * 개인화_김철(도면정보 보기방식)
			 * function toggleBlueprint(trigger, isUse)
			 * trigger : 도면창 열고 닫기 여부
			 * isUser : 도면창 사용 미사용 여부
			 */
			if (Object.keys(personalizeSetting).length != 0) {
				if (personalizeSetting.imageView == 'close') {
					searchPageModule.toggleBlueprint(false, true);
					if (right == 'kdg' || right == 'abdg') {
						setImageOpen(false);
					} else {
						setImageOpen(true);
					}
				} else {
					if (right == 'kdg' || right == 'abdg') {
						setImageOpen(true);
						searchPageModule.toggleBlueprint(false, false);
					} else {
						searchPageModule.toggleBlueprint(true, true);
					}
				}
			} else {
				if (right == 'kdg' || right == 'abdg') {
					searchPageModule.toggleBlueprint(false, false);
				} else {
					searchPageModule.toggleBlueprint(true, true);
				}
			}
		} else {
			searchPageModule.toggleBlueprint(false, false);
		}
	}
	
	// 개인화_김철
	if (Object.keys(personalizeSetting).length != 0) {
		if (personalizeSetting.detailNavigate == true && ($('#mainResultDetail .navigation').length == 0)) {
			let navigationHtml = '<div class="navigation">'
				+ '<button type="button" class="btn-nav btn-prev" onclick="moveDetail(\'prev\');"><span class="blind">이전 게시글</span></button>'
				+ '<button type="button" class="btn-nav btn-next" onclick="moveDetail(\'next\');"><span class="blind">다음 게시글</span></button>'
				+ '</div>';
			$('#mainResultDetail .head-top').prepend(navigationHtml);
		}
	}
	
	toggleLoadingDialog(loadingDialogTarget, false);
}

//검색결과 상세보기 도면 전체보기 렌더링
function renderDataForAllimg(right, data, template, mode)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('.bp-list').html(resultHTML);
	
	if (right == 'kpat') {
		imageLoad();
		
		if (mode == 'openAllimgPop') {
			$('.bp-list').bind('scroll', function() {
				let innerHeight = $(this).innerHeight();
				let scroll = $(this).scrollTop() + $(this).innerHeight() + 10;
				let height = $(this)[0].scrollHeight;
				
				if (scroll >= height)
				{
					imageLoad("hidden");
				}
			});
			
			$('.list .img-box').closest('button').eq(imgSeq).focus();
			$('.list .img-box').closest('button').eq(imgSeq).addClass('active');
			$('.list .img-box').closest('button').eq(imgSeq).blur(); //focus 시, 테두리 색이 적용됨을 지우기 위함
		} else {
			$('.bp-con').bind('scroll', function() {
				let innerHeight = $(this).innerHeight();
				let scroll = $(this).scrollTop() + $(this).innerHeight() + 10 ;
				let height = $(this)[0].scrollHeight;
				
				if (scroll >= height)
				{
					imageLoad("hidden");
				}
			});
		}
		toggleLoadingDialog(loadingDialogTarget, false);	
	}
}

// 결과 분류통계 데이터 렌더링
function renderDataForResultStatis(right, data, template)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('#modalStatistics .stats-body').html(resultHTML);
	
	let resultTopText;
	if (right == 'abpatTrans') {
		let viewCollection = $('#abpatTransSearchForm').find('input[name=viewCollection]').val().toLowerCase().replace(/\b[a-z]/, letter => letter.toUpperCase());
		resultTopText = '[' + getNatlDesc(viewCollection) + '] <em>' + $('#' + right + 'SearchForm').find('input[name=queryText]').val() + '</em><span data-lang-id="itemclass.txt6">'+i18next.t('itemclass.txt6')+'</span><em>' + ResultData.getData(right).countInfo[viewCollection + 'RecordCount'].toLocaleString() + '</em><span data-lang-id="itemclass.txt5">'+i18next.t('itemclass.txt5')+'</span>';
	} else {
		resultTopText = '<em>' + $('#' + right + 'SearchForm').find('input[name=queryText]').val() + '</em><span data-lang-id="itemclass.txt6">'+i18next.t('itemclass.txt6')+'</span><em>' + ResultData.getData(right).countInfo.totalcount.toLocaleString() + '</em><span data-lang-id="itemclass.txt5">'+i18next.t('itemclass.txt5')+'</span>';
	}
	$('#modalStatistics .total').html(resultTopText);
	
	setChartData(right, data);
}

// 시각화 통계를 위한 데이터 셋팅 및 차트 렌더링
function setChartData(right, data)
{
	// 권리별 key값 셋팅
	let keySets = {
		abpat: {
			years: {AD: 'itemclass.txt8', OPD: 'itemclass.txt9', GD: 'itemclass.txt10'},
			codes: {IPC: 'IPC', CPC: 'CPC'}
		},
		abpatTrans: {
			years: {AD: 'itemclass.txt8', OPD: 'itemclass.txt9', GD: 'itemclass.txt10'},
			codes: {IPC: 'IPC', CPC: 'CPC'}
		},
		kpat: {
			years: {ADP: 'itemclass.txt8', ODP: 'itemclass.txt9', GDP: 'itemclass.txt10'},
			codes: {IPC: 'IPC', CPC: 'CPC'},
			names: {APC: 'itemclass.txt12', IN: 'itemclass.txt13'},
		},
		ktm: {
			years: {AD: 'itemclass.txt8', PD: 'itemclass.txt9', RD: 'itemclass.txt10'},
			codes: {SC: '유사군', PRC: '상품분류'},
			names: {APC: 'itemclass.txt12'}
		},
		kdg: {
			years: {AD: 'itemclass.txt8', OD: 'itemclass.txt9', RD: 'itemclass.txt10'},
			codes: {BLC: '국제분류'},
			names: {APC: 'itemclass.txt12', IVN:'itemclass.txt22'}
		},
		abdg: {
			years: {AD: '출원년도', PD: '공고년도', RD: '등록년도'},
			codes: {LC: '국제분류'}
		},
		abtm: {
			years: {OAD: '출원년도', ORD: '등록년도'},
			codes: {OCI: '상품분류'}
		}
	};
	
	// key 값을 추출한 후 fldNm 값을 배열로 셋팅, fldNm값별  hitCnt값 셋팅
	let tempYearLabels = [];
	let codeLabels1 = [], codeLabels2 = [];
	let nameLabels = {};
	let hitCntMap = {};
	Object.keys(keySets[right]).forEach(function(kind) {
		Object.keys(keySets[right][kind]).forEach(function(key, index) {
			let dataSize = (data[key] ? data[key].length : 0);
			for (let i = 0; i < dataSize; i++) {
				let item = data[key][i];
				if (item == '') {
					continue;
				}
				if (kind == 'years') {
					// 년도 결과 목록 중 상위 20개만 시각화 
					if (i >= 20) break;
					tempYearLabels.push(item.fldNm);
				} else if (kind == 'codes') {
					// 코드 결과 목록 중 상위 10개만 시각화 
					if (i >= 10) break;
					
					// 코드는 시각화 최대 2개까지만 제공
					if (index == 0) {
						codeLabels1.push(item.fldNm);
					} else if (index == 1) {
						codeLabels2.push(item.fldNm);
					}
				} else if (kind == 'names') {
					// 코드 결과 목록 중 상위 10개만 시각화 
					if (i >= 10) break;
					
					if (nameLabels[key] == undefined) {
						nameLabels[key] = [];
					}
					nameLabels[key].push(item.fldNm);
				}
				
				if (!hitCntMap[key]) {
					hitCntMap[key] = {};
				}
				hitCntMap[key][item.fldNm] = item.hitCnt ? parseInt(item.hitCnt, 10) : 0;
			}
		});
	});
	
	// 중복을 제거한 배열 생성
	let yearLabels = Array.from(new Set(tempYearLabels));
	
	// 배열 정렬
	yearLabels.sort();
	
	let tempArr = [];
	Object.keys(keySets[right]['years']).forEach(function(key) {
		if (hitCntMap[key] != undefined) {
			let langId = keySets[right]['years'][key];
			let translatedLabel = i18next.t(langId,{defaultValue:keySets[right]['years'][key]});
			
			let labelHtml = document.createElement("span");
			labelHtml.setAttribute("data-lang-id",langId);
			labelHtml.textContent = translatedLabel;
			
			let tempData = {
				label: translatedLabel,
				data: yearLabels.map(function(year) {
					return hitCntMap[key][year] || 0;
				})
			};
			tempArr.push(tempData);
		}
	});
	
	
	// 출원년도/공개년도/등록년도
	let yearData = {
		yearLabels : yearLabels,
		data : tempArr
	};
	
	let bar01 = modalStatistics.render('bar01', 'barVrtl', {
		labels : yearData.yearLabels,
		datasets : yearData.data,
		legend : 'bar01_legned',
	});
	
	// 분류코드
	let codeData1 = {}, codeData2 = {};
	let codeTitle1 = '', codeTitle2 = '';
	Object.keys(keySets[right]['codes']).forEach(function(key, index) {
		if (index == 0) {
			codeTitle1 = keySets[right]['codes'][key];
			codeData1 = {
				labels : codeLabels1,
				data : codeLabels1.map(function(code) {
					return hitCntMap[key][code] || 0;
				})
			}
		} else if (index == 1) {
			codeTitle2 = keySets[right]['codes'][key];
			codeData2 = {
				labels : codeLabels2,
				data : codeLabels2.map(function(code) {
					return hitCntMap[key][code] || 0;
				})
			}
		}
	});
	
	if (!$.isEmptyObject(codeData1)) {
		let doughnut01 = modalStatistics.render('doughnut01', 'doughnut', {
			title : codeTitle1,
			labels : codeData1.labels,
			hoverOffset: 4,
			data : codeData1.data,
			legend : 'doughnut01_legned',
		});
	}
	
	if (!$.isEmptyObject(codeData2)) {
		let doughnut02 = modalStatistics.render('doughnut02', 'doughnut', {
			title : codeTitle2,
			labels : codeData2.labels,
			hoverOffset: 4,
			data : codeData2.data,
			legend : 'doughnut02_legned',
		});
	}
	
	// 인명정보
	//let nameData = {};
	if (keySets[right]['names'] != undefined) {
		Object.keys(keySets[right]['names']).forEach(function(key, index) {
			if (nameLabels[key] == undefined) {
				nameLabels[key] = [];
				hitCntMap[key] = {};
				nameData['labels' + index] = nameLabels[key];
				nameData['data' + index] = nameLabels[key].map(function(name) {
					return hitCntMap[key][name] || 0;
				});
			}
			else {
				nameData['labels' + index] = nameLabels[key];
				nameData['data' + index] = nameLabels[key].map(function(name) {
					return hitCntMap[key][name] || 0;
				});
			}
		});
		
		//let bar02 = {};
		bar02 = modalStatistics.render('bar02', 'barHrzn', {
			labels : nameData.labels0,
			data : nameData.data0,
		});
	}
	
	// 분류통계용 구분값 셋팅
	resultStatisLoad = true;
	// 분류통계 초기화
	modalStatistics.init();
	// 공통 레이아웃 초기화
	commonLayout();
	// 로딩창 끄기
	$('#statisLoading').hide();
}

//검색결과 유사특허 새창 렌더링
function renderDataForSimilarPop(right, data, template, page)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('#resultSection').html(resultHTML);
	
	if (page == 'specialJp' || page == 'specialIdea') {
		$('.resultSection[data-view-type="basic"] .result-item .content').css('padding-left', '0rem');
	}
	
	toggleLoadingDialog(loadingDialogTarget, false);
}

// 보기방식 변경 버튼 셋팅
function initChangeViewBtn(right)
{
	/*
	 * 개인화_김철(검색결과 보기방식)
	 * 국내 특실, 디자인, 심판에 한정하여 로그인 시, 개인화 설정 값을 토대로 검색결과 보기방식 세팅
	 */
	if (Object.keys(personalizeSetting).length != 0 && (right == 'kpat' || right == 'kdg' || right == 'ktm')) {
		$('button[data-view-type]').removeClass('active').attr('title', '선택되지 않음');
		$('button[data-view-type]').parent().show();
		if (right == 'kpat') {
			$('button[data-view-type][data-view-option="' + personalizeSetting.searchResult.patent + '"]').addClass('active').attr('title','선택됨');
			$('button[data-view-type]').eq(0).data('view-option', 'basic');
		} else if (right == 'kdg') {
			$('button[data-view-type]').eq(2).parent().hide();
			$('button[data-view-type][data-view-option="' + personalizeSetting.searchResult.design + '"]').addClass('active').attr('title','선택됨');
			$('#resultSection').attr('data-bp-grid', '7');
			$('button[data-view-type]').eq(0).data('view-option', 'one');
		} else if (right == 'ktm') {
			$('button[data-view-type]').eq(3).parent().hide();
			$('button[data-view-type]').eq(2).parent().hide();
			$('button[data-view-type][data-view-option="' + personalizeSetting.searchResult.trademark + '"]').addClass('active').attr('title','선택됨');
			$('button[data-view-type]').eq(0).data('view-option', 'one');
		}
	} else {
		// 보기방식 버튼 첫번째로 초기화
		$('button[data-view-type]').removeClass('active').attr('title', '선택되지 않음');
		$('button[data-view-type]').eq(0).addClass('active');
		
		// 권리별 보기방식 셋팅
		$('button[data-view-type]').parent().show();
		if (right == 'kpat') {
			//$('button[data-view-type]').eq(3).parent().hide();
			$('button[data-view-type]').eq(0).data('view-option', 'basic').attr('title','선택됨');
			//$('#resultSection').attr('data-view-type', 'basic');
		} else if (right == 'kdg' || right == 'abdg') {
			$('button[data-view-type]').eq(2).parent().hide();
			$('button[data-view-type]').eq(0).data('view-option', 'one').attr('title','선택됨');
			$('#resultSection').attr('data-bp-grid', '7');
		} else if (right == 'abpat' || right == 'abpatTrans') {
			$('button[data-view-type]').eq(3).parent().hide();
			$('button[data-view-type]').eq(0).data('view-option', 'basic').attr('title','선택됨');
			//$('#resultSection').attr('data-view-type', 'basic');
		} else if (right == 'kpa') {
			$('button[data-view-type]').not(':even').parent().hide();
			$('button[data-view-type]').eq(0).data('view-option', 'seoji').attr('title','선택됨');
			//$('#resultSection').attr('data-view-type', 'seoji');
		} else if (right == 'ktm' || right == 'abtm') {
			$('button[data-view-type]').eq(3).parent().hide();
			$('button[data-view-type]').eq(2).parent().hide();
			$('button[data-view-type]').eq(0).data('view-option', 'one').attr('title','선택됨');
			//$('#resultSection').attr('data-view-type', 'one');
		} else if (currentTab1 == 'etcTab' || currentTab1 == 'judgementTab' || right == 'natlPat' || right == 'mPat' || right == 'etcPat') {
			$('button[data-view-type]').not(':eq(0)').parent().hide();
			$('button[data-view-type]').eq(0).data('view-option', 'info').attr('title','선택됨');
			//$('#resultSection').attr('data-view-type', 'info');
		} else {
			$('button[data-view-type]').eq(0).data('view-option', 'basic').attr('title','선택됨');
			//$('#resultSection').attr('data-view-type', 'basic');
		}
	}
}

//권리 탭 이동
function subTabMove(right, obj)
{
	// 통계_상세 권리 탭
	if(right != 'natlPat' && right != 'mPat' && right != 'etcPat'){	//특화검색  제외
		recordServiceStats('KHOME', 'STAB', right);
	}
	
	if ($(obj).hasClass('active') && event != undefined && $(event.currentTarget).is('a')) {
		return;
	} else {
		// 타겟탭으로 현재탭 설정
		currentTab2 = right;
		
		// 선택보기 초기화
		if ($('#floatingSelectedView').hasClass('active')) {
			resultCheck.cancel(false);
		}
		
		// 보기방식 변경버튼 초기화
		initChangeViewBtn(right);
		
		if (ResultData.getData(currentTab2) == undefined || ResultData.getData(currentTab2).countInfo.totalcount <= 0) {
			dataNotFound = true;
		} else {
			dataNotFound = false;
		}
		
		// 필터영역 사용여부 셋팅
		if (currentTab1 == 'etcTab' || dataNotFound || currentTab2 == 'natlPat' || currentTab2 == 'mPat' || currentTab2 == 'etcPat') {
			searchPageModule.toggleResultFilter(false, false);
		} else {
			searchPageModule.toggleResultFilter(filterSet, true);
		}
		
		// 정렬영역 사용여부 셋팅
		if (currentTab2 == 'ipNaviConflict' || currentTab2 == 'ipNaviPrcdn' || currentTab2 == 'cntst' || currentTab2 == 'arti') {
			$('.head-function .condition').find('button, select').prop('disabled', true);
		} else {
			$('.head-function .condition').find('button, select').prop('disabled', false);
		}
		
		// 상세보기 닫기
		searchDrag.toggleDetail(false, false);
		
		// 검색결과 데이터 렌더링
		if (dataNotFound) {
			// data 객체 빈값 확인
			if (!$.isEmptyObject(ResultData.data)) {
				getTemplate(right, 'common', 'dataNotFound');
			}
			$('#resultTotal').empty();
			//searchPageModule.toggleResultFilter(false, false);
			//2025.09.18 페이징 숨기고, 필터는 항상 켬
			$('#pagination').addClass('hidden');
			searchPageModule.toggleResultFilter(true, true);
			getTemplate(right, 'search', 'filter');
		} else {
			// 권리별 정렬 옵션 셋팅
			initSortOption('tabMove');
			if (currentTab2 == 'natlPat' || currentTab2 == 'mPat' || currentTab2 == 'etcPat') { // 특화검색 분류
				getTemplate(right, 'search', $('button[data-view-type].active').data('view-option') + 'List', 'tabMove');
			} else {
				let viewCollection = 'us';
				if (currentTab2 == 'abpatTrans') {
					viewCollection = $('#abpatTransSearchForm').find('input[name=viewCollection]').val().toLowerCase();
				}
				getTemplate(right, 'search', $('button[data-view-type].active').data('view-option') + 'List', 'tabMove', viewCollection);
			}
		}
		
		$(obj).parent().siblings().find('a.active').removeClass('active');
		$(obj).addClass('active');
		
		// 분류통계용 구분값 초기화
		resultStatisLoad = false;
		// 상세보기 도면정보 초기화
		$('#mainResultDetailArea').removeAttr('data-blueprint-use');
	}
	setTimeout(() => {
	    window.reInitTooltips();
	}, 0);
}

//필터  valid 체크
function filterValidation(from, right, $targetObj)
{
	let flag = true;
	
	/*
	 * 2026.06.11 OJE
	 * 선택보기 상태에서도 상세검색, 상단입력창 및 상단탭을 통하여 검색이 가능하도록, from 값이 detailSearch, totalSearch가 아닌 경우에만 false를 반환하도록 조건 수정
	 */
	if (selectViewFlag && from != 'detailSearch' && from != 'totalSearch') {
		alert('선택보기 중에는 필터가 적용되지 않습니다.');
		flag = false;
	} else {
		$.each($targetObj, function(idx, item) {
            // 국내 특실, 디자인, 상표의 실시권, 사용권, 대표화학식, 기타항목 제외 처리
            if ($(item).find('input[type=checkbox]').eq(1).attr('name') == 'leftLicensee' || $(item).find('input[type=checkbox]').eq(0).attr('name') == 'leftChemical' || $(item).find('input[type=checkbox]').eq(0).attr('data-check') == 'etcFilter'
            	|| $(item).find('input[type=checkbox]').eq(0).attr('name') == 'leftFamily' ) {
                return true;
            }
			
			var $chkObj = $(item).find('input[type=checkbox]:checked, input[type=radio]:checked').not('[data-check-all]');
			if ($chkObj.length == 0) {
				if (from == 'filterSearch' || from == 'totalSearch') {
					alert($(item).siblings('strong.tit').text() + ' 중 하나 이상은 반드시 선택해주세요.');
				} else {
					alert($(item).find('.fg-head > .tit').text() + ' 중 하나 이상은 반드시 선택해주세요.');
				}
				flag = false;
				return false;
			}
		});
	}
	
	return flag;
}

// 2025.09.18 필터 -> 상세검색
function syncDetailSearchByFilter(from, right) {
	if(currentTab1 == 'etcTab' || currentTab2 == 'ipNaviPrcdn' || currentTab2 == 'ipNaviConflict' || currentTab2 == 'cyber') return false;

	if(right == undefined || right == '') return false;

	if(/natlPat|mPat|etcPat/.test(right)) return false;

	let left = filterMappings['left'][right];

	let detail = filterMappings['detail'][right];

	for(var i=0; i < left.length; i++) {
		let leftName = left[i];
		let targetName = detail[i];
		$('#sd01Pannel').find("input[name=" + targetName + "]").prop("checked", false);
		$('#mainResultFilter').find("input[name=" + leftName + "]:checked").each(function() {
			const id = $(this).attr("id"); // 예: leftGubn01, allCheck_leftGubn
			//console.log(id);
			$('#sd01Pannel').find("input[name=" + targetName + "][data-filter-id=" + id + "]")
				.prop("checked", true);
		});
	}
	
	// 상세검색 행정상태 토글 동기화(기본값 이외 선택시 전체보기)
	detailHangjungToggle(right);
}

// 필터 값 셋팅
function setFilterValues(from, right, $targetObj)
{
	let $targetForm, mainYn;
	if ($('#' + right + 'SearchForm').length == 0) {
		$targetForm = $('#mainSearchForm');
		mainYn = 'Y';
	} else {
		$targetForm = $('#' + right + 'SearchForm');
		mainYn = 'N';
	}
	
	if (right == 'abpat') { // 해외특허
		let tempCollections = '';
		// 검색필터의 대분류 카테고리(권리, 국가, 유형 등)
		$.each($targetObj, function(idx, item) {
			if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
				tempCollections += $(item).val() + ',';
			}
		});
		tempCollections = tempCollections.slice(0, -1); // 마지막 콤마 절삭
		
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'collectionValues', value: tempCollections}));
		} else {
			$targetForm.find('input[name=collectionValues]').val(tempCollections);
		}
	} else if (right == 'abpatTrans') { // 해외특허 한글검색
		let tempCollections = '';
		let viewCollection = 'us';
		// 검색필터의 대분류 카테고리(권리, 국가, 유형 등)
		/*if ($('#searchKind').val() == 'totalSearch') {
			tempCollections = 'US_TRANS_T.col,EP_TRANS_T.col,PAJ_TRANS_T.col';
			$.each($targetObj, function(idx, item) {
				if ($(item).is(':checked')) {
					viewCollection = $(item).attr('id');
				}
			});
		} else {*/
			$.each($targetObj, function(idx, item) {
				if ($(item).is(':checked')) {
					tempCollections = $(item).val();
					if (from == 'filterSearch' || from == 'totalSearch') {
						viewCollection = $(item).attr('id');
					} else {
						viewCollection = $(item).data('filter-id');
					}
				}
			});
		//}
		
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'collectionValues', value: tempCollections}));
		} else {
			$targetForm.find('input[name=collectionValues]').val(tempCollections);
			$targetForm.find('input[name=viewCollection]').val(viewCollection.toLowerCase());
		}
	} else if (right == 'kpat') { //국내특허
		let tempCls = ''; // 권리구분용
		let tempLst = ''; // 행정상태용 
		let tempLf = ''; // 실시권정보용
		let tempLfFg = true; // 실시권정보용
		let tempExpression = '';
		let tempBfexpression = '';
		let tempPfexpression = '';
		
		// 다음 검색을 위한 expression 셋팅
		let temp = $targetForm.find('input[name="queryText"]').val();
		$targetForm.find('input[name=expression]').val(temp);
		
		$.each($targetObj, function(idx, item) {
			let objName = '';
			if (from == 'filterSearch' || from == 'totalSearch') {
				objName = $(item).attr('name');
			} else {
				objName = $(item).data('filter-id');
			}
			
	    	if (objName.indexOf('leftGubn') > -1) {
	    		if ($(item).is('[data-check-all]') && $(item).is(':checked')) {
	    			tempCls = 'all';
	    		}
	    		
	    		if (tempCls == 'all') {
	    			return true; // continue
	    		} else {
	    			if ($(item).is(':checked')) {
	    				if (tempCls != '') {
				    		tempCls += '+';
				    	}
	    				tempCls += '(' + $(item).val() + '<IN>CLS)';
	    			}
	    		}
	    	} else if (objName.indexOf('leftHangjung') > -1) {
	    		if ($(item).is('[data-check-all]') && $(item).is(':checked')) {
	    			tempLst = 'all';
	    		}
	    		
	    		if (tempLst == 'all') {
	    			return true; // continue
	    		} else {
	    			if ($(item).is(':checked')) {
	    				if (tempLst != '') {
	    					tempLst += '+';
				    	}
	    				tempLst += '{' + $(item).val() + '<IN>LST}';
	    			}
	    		}
	    	} else if (objName.indexOf('leftLicensee') > -1) {
	    		if ($(item).is('[data-check-all]') && $(item).is(':checked')) {
	    			tempLf = 'LF=[Y]+LF=[E]+LF=[N]';
	    			tempLfFg = false;
	    		} else if (tempLfFg == true && $(item).is(':checked')){
	    			tempLf = 'LF=[Y]';
	    			if (tempLf != 'LF=[Y]') {
	    				tempLf += '+';
			    	}
	    			tempLf += '+LF=[' + $(item).val() + ']';
	    		}
	    	} else if (objName.indexOf('leftChemical') > -1) {
	    		if ($(item).is('[data-check=leftChemical]') && $(item).is(':checked')) {
	    			// 대표화학식 외 필터 검색에 주는 영향을 고려하여 괄호를 통해 우선처리하고 OR처리
	    			tempPfexpression += '(CHM=[Y])*';
	    		}
	    	} else if (objName.indexOf('leftFamily') > -1) {
	    		if ($(item).is('[data-check=leftFamily]') && $(item).is(':checked')) {
	    			tempPfexpression += '(FMEX=[Y])*';
	    		}
	    	}
		});
		
		// prefix 셋팅(권리구분, 행정상태)
		if (tempCls != 'all' && tempCls != '') {
			tempPfexpression += '(' + tempCls + ')';
		}
		if (tempLst != 'all' && tempCls != '') {
			if (tempPfexpression != '') {
				tempPfexpression += '*';
			}
			tempPfexpression += '(' + tempLst + ')';
		}
		
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'prefixExpression', value: tempPfexpression}));
		} else {
			$targetForm.find('input[name=prefixExpression]').val(tempPfexpression);
		}
		
		// expresstion 셋팅(실시권 정보)
		if (tempLf != '') {
			tempExpression = $targetForm.find('input[name=expression]').val();
			$targetForm.find('input[name=expression]').val(tempExpression + '*' + '(' + tempLf + ')');
		}
	} else if (right == 'kpa') { //KPA
		let tempKind = ''; // kind용
		$.each($targetObj, function(idx, item) {
			if ($(item).is('[data-check-all]') && $(item).is(':checked')) {
				return false;
			} else {
				if ($(item).is(':checked')) {
					tempKind = $(item).val();
				}
			}
		});
		
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'kind', value: tempKind}));
		} else {
			$targetForm.find('input[name=kind]').val(tempKind);
		}
	} else if (right == 'abdg') {
		let tempCollections = '';
		$.each($targetObj, function(idx, item) {
			if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
				tempCollections += $(item).val() + ',';
			}
		});
		tempCollections = tempCollections.slice(0, -1); // 마지막 콤마 절삭
		
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'collectionValues', value: tempCollections}));
		} else {
			$targetForm.find('input[name=collectionValues]').val(tempCollections);
		}
	} else if (right == 'kdg') {
		let tempPtn = ''; // 유형
		let tempMeasure = ''; // 행정상태 
		let tempLf = ''; // 실시권정보
		let tempExpression = '';
		
		// 다음 검색을 위한 expression 셋팅
		let temp = $targetForm.find('input[name="queryText"]').val();
		$targetForm.find('input[name=expression]').val(temp);
		
		$.each($targetObj, function(idx, item) {
			let objName = '';
			if (from == 'filterSearch' || from == 'totalSearch') {
				objName = $(item).attr('name');
			} else {
				objName = $(item).data('filter-id');
			}
			
			if ('pattern|simi|part|etc'.indexOf(objName) > -1) { //유형
    			if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
    				if (tempPtn != '') {
    					tempPtn += ',';
			    	}
    				tempPtn += $(item).val();
    			}
			} else if (objName.indexOf('measure') > -1) { //행정상태
    			if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
    				if (tempMeasure != '') {
    					tempMeasure += ',';
			    	}
    				tempMeasure += $(item).val();
    			}
			} else if (objName.indexOf('leftLicensee') > -1) { //실시권정보
				if ($(item).is(':checked')) {
	    			if (tempLf != '') {
	    				tempLf += '+';
			    	}
	    			tempLf += 'LF=[' + $(item).val() + ']';
	    		}
			}
		});
		
		// 셋팅(유형, 행정상태)
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'patternString', value: tempPtn}));
			$targetForm.append($('<input/>', {type: 'hidden', name: 'measureString', value: tempMeasure}));
		} else {
			$targetForm.find('input[name=patternString]').val(tempPtn); // 유형
			$targetForm.find('input[name=measureString]').val(tempMeasure); // 행정상태
		}
		
		// expresstion 셋팅(실시권 정보)
		if (tempLf != '') {
			tempExpression = $targetForm.find('input[name=expression]').val();
			$targetForm.find('input[name=expression]').val(tempExpression + '*' + '(' + tempLf + ')');
		}
	} else if(right == 'jg') {
		let tempPtn = ''; // 권리구분
		let tempCourt = ''; // 심급구분
		let tempRel = ''; // 당사자구분
		
		$.each($targetObj, function(idx, item) {
			let objName = '';
			if (from == 'filterSearch' || from == 'totalSearch') {
				objName = $(item).attr('name');
			} else {
				objName = $(item).data('filter-id');
				// 완전일치검색 여부(법조항)체크리스트 제외
				if (objName == 'ems') {
					return false;
				}
			}
			
			if (objName.indexOf('patent') > -1) { // 권리구분
    			if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
    				if (tempPtn != '') {
    					tempPtn += ',';
			    	}
    				tempPtn += $(item).val();
    			}
			} else if (objName.indexOf('court') > -1) { // 심급구분
				if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
    				if (tempCourt != '') {
    					tempCourt += ',';
			    	}
    				tempCourt += $(item).val();
    			}
			} else if (objName.indexOf('relation') > -1) { // 당사자구분
				if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
    				if (tempRel != '') {
    					tempRel += ',';
			    	}
    				tempRel += $(item).val();
    			}
			}
		});
		
		// 셋팅(권리구분, 행정상태)
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'patentString', value: tempPtn}));
			$targetForm.append($('<input/>', {type: 'hidden', name: 'courtString', value: tempCourt}));
			$targetForm.append($('<input/>', {type: 'hidden', name: 'relationString', value: tempRel}));
		} else {
			$targetForm.find('input[name=patentString]').val(tempPtn); // 권리구분
			$targetForm.find('input[name=courtString]').val(tempCourt); // 심급구분
			$targetForm.find('input[name=relationString]').val(tempRel); // 당사자구분
		}
	} else if (right == 'abtm') { // 해외상표
		let tempCollections = '';
		// 검색필터의 대분류 카테고리(권리, 국가, 유형 등)
		$.each($targetObj, function(idx, item) {
			if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
				tempCollections += $(item).val() + ',';
			}
		});
		tempCollections = tempCollections.slice(0, -1); // 마지막 콤마 절삭
		
		if (mainYn == 'Y') {
			$targetForm.append($('<input/>', {type: 'hidden', name: 'collectionValues', value: tempCollections}));
		} else {
			$targetForm.find('input[name=collectionValues]').val(tempCollections);
		}
	} else if (right == 'ktm') { // 국내상표
		let tempMcds = ''; // 권리구분
        let tempPtn = ''; // 상표유형
        let tempMeasure = ''; // 행정상태 
        let tempLf = ''; // 실시권정보
        let tempLfFg = true;
        let etcItem = {}; // 기타항목 정보
        let tempExpression = '';
        
        // 다음 검색을 위한 expression 셋팅
        let temp = $targetForm.find('input[name="queryText"]').val();
        $targetForm.find('input[name=expression]').val(temp);
        
        $.each($targetObj, function(idx, item) {
            let objName = '';
            if (from == 'filterSearch' || from == 'totalSearch') {
                objName = $(item).attr('name');
            } else {
                objName = $(item).data('filter-id');
            }
            
            if (objName.indexOf('merchandise') > -1) { // 권리구분
                if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
                    /*if (tempMcds != '') {
                        tempMcds += ',';
                    }*/
                    tempMcds += $(item).val() + ',';
                }
            } else if (objName.indexOf('pattern') > -1) { //유형
                if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
                    if (tempPtn != '') {
                        tempPtn += ',';
                    }
                    tempPtn += $(item).val();
                }
            } else if (objName.indexOf('measure') > -1) { // 행정상태
                if (!$(item).is('[data-check-all]') && $(item).is(':checked')) {
                    if (tempMeasure != '') {
                        tempMeasure += ',';
                    }
                    tempMeasure += $(item).val();
                }
            } else if (objName.indexOf('leftLicensee') > -1) { // 실시권정보
                if ($(item).is('[data-check-all]') && $(item).is(':checked')) {
                    tempLf = 'LF=[Y]+LF=[E]+LF=[N]';
                    tempLfFg = false;
                } else if (tempLfFg == true && $(item).is(':checked')) {
                    tempLf = 'LF=[Y]';
                    if (tempLf != 'LF=[Y]') {
                        tempLf += '+';
                    }
                    tempLf += '+LF=[' + $(item).val() + ']';
                }
            } else if ($(item).data('check') == 'etcFilter') { // 기타항목
                etcItem[objName] = $(item).is(':checked') ? 'Y' : 'N';
            }
        });
        
        // 셋팅(유형, 권리구분, 행정상태)
        if (mainYn == 'Y') {
            $targetForm.append($('<input/>', {type: 'hidden', name: 'patternString', value: tempPtn}));
            $targetForm.append($('<input/>', {type: 'hidden', name: 'merchandiseString', value: tempMcds}));
            $targetForm.append($('<input/>', {type: 'hidden', name: 'measureString', value: tempMeasure}));
        } else {
            $targetForm.find('input[name=patternString]').val(tempPtn); // 유형
            $targetForm.find('input[name=merchandiseString]').val(tempMcds); // 권리구분
            $targetForm.find('input[name=measureString]').val(tempMeasure); // 행정상태
        }
        
        // expresstion 셋팅(실시권 정보)
        if (tempLf != '') {
            tempExpression = $targetForm.find('input[name=expression]').val();
            $targetForm.find('input[name=expression]').val(tempExpression + '*' + '(' + tempLf + ')');
        }
        
        // 기타항목 값 셋팅
        if (from == 'detailSearch' && mainYn == 'N') {
            let etcObjs = $('#mainResultFilter').find('input[type=checkbox][data-check=etcFilter]');
            $.each(etcObjs, function(idx, item) {
                $targetForm.find('input[name=' + $(item).attr('name') + ']').val('N');
            });
        } else {
            $.each(etcItem, function(key, value) {
                $targetForm.find('input[name=' + key + ']').val(value);
            });
        }
	}
	
	// 필터 체크값 저장
	let tempData = {};
	$.each($targetObj, function(idx, item) {
		let objId = '';
		if (from == 'filterSearch' || from == 'totalSearch') {
			objId = $(item).attr('id');
		} else {
			objId = $(item).data('filter-id');
		}
		tempData[objId] = $(item).prop('checked');
	});
	
	tempData.right = right;
	
	if (mainYn == 'Y') {
		sessionStorage.setItem('filterData', JSON.stringify(tempData));
	} else {
		if (sessionStorage.getItem('filterData') != null) {
			sessionStorage.removeItem('filterData');
		}
		SaveData.setFilterData(right, tempData);
	}
}

//필터 검색 (적용 버튼)
function filterSearch() {
	// 통계_필터
	if ($('#allCheck_leftLicensee').is(':checked')){
		recordServiceStats(currentTab2, 'LEFT', 'LFY');
	}
	if ($('#leftLicensee01').is(':checked')){
		recordServiceStats(currentTab2, 'LEFT', 'LFE');
	}
	if ($('#leftLicensee02').is(':checked')){
		recordServiceStats(currentTab2, 'LEFT', 'LFN');
	}
	if ($('#leftChemical').is(':checked')){
		recordServiceStats(currentTab2, 'BIBLO', 'CHBIB');
	}
	if ($('#leftFamily').is(':checked')){
		recordServiceStats(currentTab2, 'LEFT', 'FMEX');
	}

	/*if (ResultData.getData(currentTab2) == undefined || dataNotFound) {
		alert('검색 결과가 존재하지 않습니다.');
		return false;
	}*/

	// 필터 valid 체크
	if (!filterValidation('filterSearch', currentTab2, $('#mainResultFilter').find('ul.list'))) {
		return;
	}
	
	// 해외특허 한글검색 결과 존재여부 체크
	let existResult = false;
	let checkedCountry;
	if (currentTab2 == 'abpatTrans') {
		let collectionValues = $('#abpatTransSearchForm').find('input[name=collectionValues]').val();
		let collectionArr = collectionValues.split(',');
		if (collectionArr.length > 1) {
			checkedCountry = $('#mainResultFilter').find('ul.list input[type=radio]:checked').attr('id').toLowerCase();
			if (ResultData.getData(currentTab2)[checkedCountry + 'ResultList'] != undefined && ResultData.getData(currentTab2)[checkedCountry + 'ResultList'].length > 0) {
				if ($('#' + currentTab2 + 'SearchForm').find('input[name=currentPage]').val() == 1) {
					existResult = true;
				}
			}
		} else {
			existResult = false;
		}
	}
	
	if (existResult) {
		// 분류통계용 구분값 초기화
		resultStatisLoad = false;
		// 보기방식 버튼 첫번째로 초기화
		$('button[data-view-type]').removeClass('active');
		$('button[data-view-type]').eq(0).addClass('active');
		// form에 선택권리값 셋팅
		$('#abpatTransSearchForm').find('input[name=viewCollection]').val(checkedCountry);
		let tempData = {};
		tempData[checkedCountry.toUpperCase()] = true;
		SaveData.setFilterData(currentTab2, tempData);
		// 템플릿 호출
		getTemplate(currentTab2, 'search', 'basicList', 'existResult', checkedCountry);
	} else {
		// 정렬값 초기화
		initSortOption('filterSearch');
		// 권리별 필터 값 셋팅
		setFilterValues('filterSearch', currentTab2, $('#mainResultFilter').find('input[type=checkbox], input[type=radio]'));
		
		//2025.09.18 필터값을 상세검색에도 적용
		syncDetailSearchByFilter('filterSearch', currentTab2);

		// 검색 시작
		doSearch(currentTab2, 'filter');
	}
}

// sort option 초기화
function initSortOption(mode)
{
	let optionHtml = '';
	$.each(sortOption[currentTab2], function(key, value) {
		let langId = sortOption[currentTab2][key];
		let translatedValue = i18next.t(langId,{defaultValue:value});
		optionHtml += '<option value="' + key + '"data-lang-id="'+langId+'">' + translatedValue + '</option>';
	});
	
	$('#sortCondition01').html(optionHtml);
	
	let option;
	if (mode == 'allList') {
		option = '<option value="10" data-lang-id="srlt.10">'+i18next.t("srlt.10")+'</option>';
	} else {
		option = '<option value="10" data-lang-id="srlt.10">'+i18next.t('srlt.10')+'</option>';
		option += '<option value="30" data-lang-id="srlt.30">'+i18next.t('srlt.30')+'</option>';
		option += '<option value="60" data-lang-id="srlt.60">'+i18next.t('srlt.60')+'</option>';
		option += '<option value="90" data-lang-id="srlt.90">'+i18next.t('srlt.90')+'</option>';
		
	}
	$('#sortCondition03').html(option);
	
	/*
	 * 개인화_김철(정렬상태 고정)
	 * 검색결과 화면에서 정렬상태 초기화 여부 분기
	 * 화면상으로 보이는 정렬상태에 대한 부분이며, 실제 검색을 위한 폼데이터는 별도로 다른 로직에서 관리
	 */
	if (mode == 'tabMove' || mode == 'changeView' || ((Object.keys(personalizeSetting).length != 0) && personalizeSetting.sortFixed === 'fixed')) {
		if (!$.isEmptyObject(SaveData.getOptionData(currentTab2))) {
			$.each(SaveData.getOptionData(currentTab2), function(key, value) {
				$(key).val(value);
			});
		} else {
			$('#sortCondition01 > option').eq(0).prop('selected', true);
			$('#sortCondition02 > option').eq(0).prop('selected', true);
			$('#sortCondition03 > option').eq(1).prop('selected', true);
		}
	} else {
		if (mode != 'allList') {
			SaveData.optionData = {};
			$.each($('form'), function(idx, item) {
				let rt = $(this).attr('name').replace('SearchForm', '');
				let firstValue = sortOption[rt] ? Object.keys(sortOption[rt])[0] : '';
				$(item).find('input[name=sortField]').val(firstValue);
				$(item).find('input[name=sortState]').val('DESC');
				$(item).find('input[name=numPerPage]').val('30');
			});
			
			$('#sortCondition01 > option').eq(0).prop('selected', true);
			$('#sortCondition02 > option').eq(0).prop('selected', true);
			$('#sortCondition03 > option').eq(1).prop('selected', true);
		}
	}
}

//sort 검색 (적용 버튼)
function optionSearch()
{
	if (ResultData.getData(currentTab2) == undefined || dataNotFound) {
		alert('검색 결과가 존재하지 않습니다.');
		return false;
	}
	
	let sortField = $('#sortCondition01').val(); // 정렬 대상 필드
	let sortState = $('#sortCondition02').val(); // 정렬 순서
	let numPerPage = $('#sortCondition03').val(); // 페이지 당 건수
	
	/*$('#abpatSearchForm').find('input[name=sortField]').val(sortField);
	$('#abpatSearchForm').find('input[name=sortState]').val(sortState);
	$('#abpatSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#kpatSearchForm').find('input[name=sortField]').val(sortField);
	$('#kpatSearchForm').find('input[name=sortState]').val(sortState);
	$('#kpatSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#kpaSearchForm').find('input[name=sortField]').val(sortField);
	$('#kpaSearchForm').find('input[name=sortState]').val(sortState);
	$('#kpaSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#abdgSearchForm').find('input[name=sortField]').val(sortField);
	$('#abdgSearchForm').find('input[name=sortState]').val(sortState);
	$('#abdgSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#kdgSearchForm').find('input[name=sortField]').val(sortField);
	$('#kdgSearchForm').find('input[name=sortState]').val(sortState);
	$('#kdgSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#jgSearchForm').find('input[name=sortField]').val(sortField);
	$('#jgSearchForm').find('input[name=sortState]').val(sortState);
	$('#jgSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#abtmSearchForm').find('input[name=sortField]').val(sortField);
	$('#abtmSearchForm').find('input[name=sortState]').val(sortState);
	$('#abtmSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#ktmSearchForm').find('input[name=sortField]').val(sortField);
	$('#ktmSearchForm').find('input[name=sortState]').val(sortState);
	$('#ktmSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#cntstSearchForm').find('input[name=sortField]').val(sortField);
	$('#cntstSearchForm').find('input[name=sortState]').val(sortState);
	$('#cntstSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	$('#cyberSearchForm').find('input[name=sortField]').val(sortField);
	$('#cyberSearchForm').find('input[name=sortState]').val(sortState);
	$('#cyberSearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	//$('#artiSearchForm').find('input[name=sortField]').val(sortField); // 구 NDSL 논문검색 소트필드 없음
	//$('#artiSearchForm').find('input[name=sortState]').val(sortState); // 신 Science ON 논문검색시 주석처리 해제
	$('#artiSearchForm').find('input[name=numPerPage]').val(numPerPage);*/
	
	$('#' + currentTab2 + 'SearchForm').find('input[name=sortField]').val(sortField);
	$('#' + currentTab2 + 'SearchForm').find('input[name=sortState]').val(sortState);
	$('#' + currentTab2 + 'SearchForm').find('input[name=numPerPage]').val(numPerPage);
	
	// 권리별 검색옵션 저장
	let optionData = {'#sortCondition01': sortField, '#sortCondition02': sortState, '#sortCondition03': numPerPage};
	SaveData.setOptionData(currentTab2, optionData);
	
	doSearch(currentTab2, 'optionSearch');
}

// Ajax 검색 공통
function doSearch(right, mode)
{
	// 특화검색(임시)_삭제예정
	if(/natlPat|mPat|etcPat/.test(right) && /excelDown/.test(mode)){
		toggleLoadingDialog('#mainResultArea', true);
	} else {
		$('a[data-subtab-id=natlPat]').addClass('hidden');
		$('a[data-subtab-id=mPat]').addClass('hidden');
		$('a[data-subtab-id=etcPat]').addClass('hidden');
	}
	
	// 탭 로딩 on (분류통계 제외)
	if (mode != 'piSearch' && !/excelDown/.test(mode) && !/rtfDown/.test(mode)) {
		toggleLoadingForTab(right, mode, true);
		if (right == currentTab2) {
			// toggleLoadingDialog('#mainResultArea', true);
			toggleLoadingDialog('#container', true);
			/*
			 * 개인화_김철(검색결과 보기방식)
			 * 기존 if문 조건에 개인화 설정 여부 분기
			 */
			if ((mode != 'optionSearch' && mode != 'paging') && Object.keys(personalizeSetting).length == 0) {
				// 보기방식 버튼 첫번째로 초기화
				$('button[data-view-type]').removeClass('active');
				$('button[data-view-type]').eq(0).addClass('active');
			}
		}
	}
	
	let $targetForm = $('#' + right + 'SearchForm');
	
	// 현재페이지 초기화
	if (mode == 'totalSearch' || mode == 'detailSearch' || mode == 'filter' || mode == 'optionSearch') {
		$targetForm.find('input[name=currentPage]').val(1);
	}
	
	if (right == 'kpat') {
		let prefixValue = $targetForm.find('input[name=prefixExpression]').val();
		$targetForm.find('input[name=prefixExpression]').val(decodeHtmlEntities(prefixValue));
		
		if ((Object.keys(personalizeSetting).length != 0) && (personalizeSetting.searchResult.patent == 'all')) {
			$targetForm.find('input[name=viewMode]').val('All');
			$targetForm.find('input[name=numPerPage]').val('10');
		}
	}
	
	let option = {
		async: true,
		type: 'POST',
		url: $targetForm.attr('action'),
		data: $targetForm.serialize(),
		dataType: 'json',
		success: function(data)
		{
			// resultCode > 00 : 성공, 99: 오류, 98: DataNotFound, 97: abort, 그외:RTF
			if (data.resultCode == '00') {
				if (mode == 'piSearch') {
					SaveData.setStatisData(right, data);
					getTemplate(right, 'search', 'resultStatis', mode, data.resultJson);
					$targetForm.find('input[name=piSearchYN]').val('');
				} else if (/excelDown/.test(mode)) {
					if(right != 'abpatTrans'){
						if(right == 'natlPat' || right == 'mPat' || right == 'etcPat') {
							excelDownload(right, data.resultList, 'now', mode.split('-')[1]);
						} else {
							excelDownload(right, data.resultList, mode.split('-')[1]);
						}
					} else {
						let abpatTransNation = $targetForm.find('input[name=viewCollection]').val();
						if(abpatTransNation == 'us'){
							excelDownload(right, data.usResultList, mode.split('-')[1]);
						} else if (abpatTransNation == 'ep') {
							excelDownload(right, data.epResultList, mode.split('-')[1]);
						} else if (abpatTransNation == 'jp') {
							excelDownload(right, data.jpResultList, mode.split('-')[1]);
						}
					}
					$targetForm.find('input[name=downYn]').val('');
				} else {
					if (data.countInfo.totalcount <= 0) {
						showDataNotFound(right, "98", mode);
					} else {
						// 검색결과 저장
						ResultData.setData(right, data);
						
						if (right == 'kdc') { // 유사특허(only)
							if (data.searchTargetSub == 'korea') {
								getTemplate(right, 'search', 'basicListKorea', mode);
							} else if (data.searchTargetSub == 'world') {
								getTemplate(right, 'search', 'basicListWorld', mode);
							}
						} else if (right == 'natlPat' || right == 'mPat' || right == 'etcPat') { // 특화검색(국유,물질,미생물)
							getTemplate(right, 'search', 'infoList', mode);
						}
						// 일반검색
						else {
							if (right == currentTab2) {
								let viewCollection = 'us';
								if (right == 'abpatTrans') {
									viewCollection = $targetForm.find('input[name=viewCollection]').val().toLowerCase();
								}
								getTemplate(right, 'search', $('button[data-view-type].active').data('view-option') + 'List', mode, viewCollection);
								if ((Object.keys(personalizeSetting).length != 0) && (personalizeSetting.searchResult.patent == 'all')) {
									if (SaveData.getOptionData(currentTab2) == undefined) {
										let optionData = {
											'#sortCondition01': $('#sortCondition01').val(),
											'#sortCondition02': $('#sortCondition02').val(),
											'#sortCondition03': 10
										};
										SaveData.setOptionData(currentTab2, optionData);
									} else {
										SaveData.getOptionData(currentTab2)['#sortCondition03'] = 10;
									}
									initSortOption('allList');
									imgLoadEvent;
									$(window).on('load resize scroll', imgLoadEvent);
								}
							}
						}
					}
				}
				dataNotFound = false;
			} else {
				if (/rtfDown/.test(mode)) {
					let blob = new Blob([data], {type: 'application/rtf'});
					let url = URL.createObjectURL(blob);
					let link = document.createElement('a');
					link.href = url;
					link.download = Date.now();
					link.click();
					$(link).remove();
					
					toggleLoadingDialog('#modalDownload .modal-con', false);
				} else {
					showDataNotFound(right, data.resultCode, mode);
				}
			}
			
			if (right == currentTab2) {
				if (mode == 'totalSearch' || mode == 'detailSearch' || mode == 'specialization') {
					if (mode != 'specialization') {
						saveRecentKeyword($('#queryText').val());
					}
					let logQuery = $('#queryText').val();
					if (mode == 'specialization') {
						var excludedNames = ['mode', 'numPerPage', 'currentPage', 'sortField', 'sortState'];
						logQuery = $targetForm.find(':input').filter(function(){
							return this.name && !excludedNames.includes(this.name) && $(this).val() != '';
						}).serialize();
						logQuery = decodeURIComponent(logQuery);
					}
					insertQueryLog(right, mode, logQuery);
					
					// 내부검색어 수집 관련 GTM 이벤트 호출 추가
					window.dataLayer = window.dataLayer || [];
					window.dataLayer.push({
					    event: 'kipris_search_complete',
					    _TRK_IK: logQuery
					});
				}
			}
		},
		error: function(xhr, status, error)
		{
			showDataNotFound(right, '99', mode);
		},
		complete: function()
		{
			// 탭 로딩 off
			if (mode != 'piSearch' && !/excelDown/.test(mode) && !/rtfDown/.test(mode)) {
				toggleLoadingForTab(right, mode, false);
				
				if (mode == 'specialization') {
					$('div[data-tab-id=' + SaveData.getParentTab(right) + 'Tab] a[data-subtab-id=' + right + ']').removeClass('hidden');
					$('div[data-tab-id=' + SaveData.getParentTab(right) + 'Tab] #' + right + 'TotalCount').siblings('em').text(ResultData.getData(right).specialFg);
					$('div[data-tab-id=' + SaveData.getParentTab(right) + 'Tab] #' + right + 'TotalCount').text(ResultData.getData(right).countInfo.totalcount.toLocaleString());
				} else {
					$('#' + right + 'TotalCount').text(ResultData.getData(right).countInfo.totalcount.toLocaleString());
				}
				
				if (mode == 'detailSearch' || mode == 'totalSearch') {
					setTimeout(function(){
						setTabCount(right);
						$('button[data-tab-id=' + currentTab1 + ']').trigger('click');
			        }, 0);
				} else if (mode == 'specialization') {
					setTabCount(right);
					$('button[data-tab-id=' + SaveData.getParentTab(right) + 'Tab]').trigger('click');
				}
				
				// 구분값 초기화
				if (right == currentTab2) {
					resultStatisLoad = false;
					selectViewFlag = false;
					tempQuery = '';
					rgstListHtml = '';
				}
				
				// 스크롤 초기화
				window.scroll({
					top: 0,
					left: 0,
					// behavior: 'smooth'
				});
			}
			if (/rtfDown/.test(mode)) {
				// RTF파라미터 초기화
				$targetForm.find('input[name=viewField]').val('');
				$targetForm.find('input[name=downStart]').val('');
				$targetForm.find('input[name=downEnd]').val('');
				$targetForm.find('input[name=fileType]').val('');
				$targetForm.find('input[name=downYn]').val('');

				// 추가 다운항목(초기화)
				let $initCheckedElsPlus = $('input[name=mdown05]');
				$.each($initCheckedElsPlus, function(i, t){
					let tempVal = $(t).val();
					$targetForm.find('input[name=incl' + tempVal + ']').val('');
				});
				
				// 대표도면 포함 여부(초기화)
				$targetForm.find('input[name=inclDraw]').val(''); // 도면포함 여부 초기화
				
				// 선택보기 완료 후, 검색식 이전으로 원복
				if (mode == 'rtfDown-selected') {
					$targetForm.find('input[name=queryText]').val(initQueryText);
					$targetForm.find('input[name=expression]').val(initExpression);
				}
			}
		}
	};
	
	// 온라인 다운로드 구분(rtf)
	if (/rtfDown/.test(mode)) {
		option.xhrFields = {responseType: 'blob'};
		delete option.dataType;
	}
	
	// ajax 최종 통신
	let ajaxResult = $.ajax(option);
	
	requestArr.push(ajaxResult);
	
	return ajaxResult;
}

// 검색결과 없음 셋팅
function showDataNotFound(right, resultCode, mode) {
	if (mode != 'piSearch' && !/excelDown/.test(mode)) {
		ResultData.setData(right, {countInfo: {totalcount: 0}, resultCode: resultCode, resultList: []});
		setTabCount(right);
		$('#' + right + 'TotalCount').text(0);
		if (right == currentTab2) {
			searchDrag.toggleDetail(false, false);
			getTemplate(right, 'common', 'dataNotFound', mode);
			$('#resultTotal').empty();
			$('#pagination').addClass('hidden');
			if(/natlPat|mPat|etcPat|ipNaviPrcdn|ipNaviConflict|arti|cntst|cyber/.test(right)) {
				searchPageModule.toggleResultFilter(false, false);
				dataNotFound = true;
			} else {
				//2025.09.18 필터를 항상 켬
				searchPageModule.toggleResultFilter(true, true);
				getTemplate(right, 'search', 'filter', mode);
			}
		}
	}
}

// 상단 권리탭 건수 셋팅
function setTabCount(right) {
	let totalCount = ResultData.getTabCount(right).toLocaleString();
	$('#' + SaveData.getParentTab(right) + 'TotalCount').text(totalCount);
}

// 결과 분류통계 버튼
function openResultStatis()
{
	if (selectViewFlag) {
		alert(i18next.t('itemclass.txt14'));
		return false;
	} else if (ResultData.getData(currentTab2) == undefined || dataNotFound) {
		alert(i18next.t('itemclass.txt15'));
		return false;
	} else {
		if (currentTab2 == 'abpat') {
			let $checkedFilter = $('#mainResultFilter').find('input[type=checkbox]:checked');
			if (Object.keys(ResultData.getData(currentTab2).countInfo).length > 2) {
				alert(i18next.t('itemclass.txt16'));
				return false;
			} else if ('US|EP|WO|PAJ|CN'.indexOf($checkedFilter.val().split('_')[0]) == -1) {
				alert(i18next.t('itemclass.txt17'));
				return false;
			}
		} else if (currentTab2 == 'abdg') {
			let $checkedFilter = Object.keys(ResultData.getData(currentTab2).countInfo).length;
			if ($checkedFilter > 3) {
				alert(i18next.t('itemclass.txt23'));
				return false;
			}
		} else if (currentTab2 == 'abtm') {
			let $checkedFilter = Object.keys(ResultData.getData(currentTab2).countInfo).length;
			if ($checkedFilter > 2) {
				alert(i18next.t('itemclass.txt26'));
				return false;
			}
		}
		if ('kpa|natlPat|mPat|etcPat|kdc|Chem'.indexOf(currentTab2) > -1 || 'judgementTab|etcTab'.indexOf(currentTab1) > -1) {
			alert(i18next.t('itemclass.txt18'));
			return false;
		}
		
		if (!resultStatisLoad) {
			$('#statisLoading').show();
			$('#' + currentTab2 + 'SearchForm').find('input[name=piSearchYN]').val('Y');
			doSearch(currentTab2, 'piSearch');
		}
		modal.open('#modalStatistics', $('button.btn-statistics'));
		
		// 통계_결과분류통계
		if (currentTab2 == 'abpat' || currentTab2 == 'abdg' || currentTab2 == 'abtm') {
			let cntry = $('#mainResultFilter').find('input[type=checkbox]:checked').attr('id');
			recordServiceStats(currentTab2, 'OPSVC', 'PI' + cntry, cntry);
		} else if (currentTab2 == 'abpatTrans') {
			let cntry = $('#mainResultFilter').find('input[type=radio]:checked').attr('id');
			recordServiceStats(currentTab2, 'OPSVC', 'PI' + cntry, cntry);
		} else {
			recordServiceStats(currentTab2, 'OPSVC', 'PI');
		}
	}
}

//JSON 트리 구조 변환 함수
function buildTreeData(data, right) {
    const transformData = data.map(item => {
    	let parentId = '';
    	if (right == 'LC') {
    		if (item.code1 == null) {
        		parentId = '#';
        	} else {
        		parentId = item.code1;
        	}
    	} else if (right == 'DR') {
    		if (item.code2 == '00') {
    			parentId = '#';
    		} else {
    			if (item.code2 != '00') parentId += item.code1;
    			if (item.code3 != '00') parentId += item.code2;
    		}
    	} else {
    		if (item.code2 == null) {
        		parentId = '#';
        	} else {
        		if (item.code2 != null) parentId += item.code1;
        		if (item.code3 != null) parentId += item.code2;
        		if (right == 'IPC' || right == 'CPC' || right == 'EPC' || right == 'FI') {
        			if (item.code4 != null || item.code5 == '00') parentId += item.code3;
            		if (item.code4 != null && item.code5 != '00') parentId += item.code4 + '/00';
        		} else {
        			if (item.code4 != null) parentId += item.code3;
            		if (item.code5 != null) parentId += item.code4;
        		}
        	}
    	}
    	
    	let description = '';
    	if (item.korDesc != undefined && item.korDesc != '') {
    		description = item.korDesc.replace(/<[^>]*>?/g, '').replace(/(?:\r|\n|\r\n)/g, '');
    		if ((right == 'IPC' || right == 'CPC') && parentId == '#') {
    			switch (item.code1) {
        			case 'C' : description = '화학; 야금'; break;
        			case 'Y' : description = '새로운 기술 발전의 일반적 구분표;'; break;
        		}
        	} else if (right == 'FI' && parentId == '#') {
        		switch (item.code1) {
        			case 'C' : description = '화학; 야금'; break;
        			case 'D' : description = '섬유;'; break;
        			case 'G' : description = '물리학;'; break;
        			case 'H' : description = '전기;'; break;
        		}
        	}
    	} else {
    		description = item.engDesc.replace(/<[^>]*>?/g, '').replace(/(?:\r|\n|\r\n)/g, '');
    	}
    	
    	let currentId = '';
    	let children = false;
    	if (right == 'DR') {
    		currentId = item.code1;
    		if (item.code2 != '00') currentId += item.code2;
    		if (item.code3 != '00') currentId += item.code3;
    	} else {
    		currentId = item.code;
    		children = item.children == 'Y' ? true : false;
    	}
    	
    	return {
    		id: currentId,
	    	parent: parentId,
	    	text: currentId + '<span class="description">' + description + '</span>',
	    	children: children,
	    	description: description,
	    	code1: item.code1 || '',
	    	code2: item.code2 || '',
	    	code3: item.code3 || '',
	    	code4: item.code4 || '',
	    	code5: item.code5 || ''
    	};
    });
    
    return transformData;
}

// 코드 검색형 입력도우미 오픈 (mode:helper|explain, helper => view: true/false, explain => view: codeValue)
function openCodeSupport(obj, right, mode, view)
{
	let openerType = '';
	if (right == 'Product') {
		let tempArr = mode.split('-');
		mode = tempArr[0];
		openerType = tempArr[1];
		
		// 상단 분류 버튼 이벤트 등록
		$(document).on('click', '#supportProduct .search-assist button', function(e) {
			if ($(this).hasClass('active')) {
				return false;
			}
			
			let $allButtons = $('#supportProduct .search-assist button');
			$allButtons.removeClass('active').attr('title', '선택되지 않음');
			
			$(this).addClass('active').attr('title', '선택됨');
			
			let searchType;
			if ($(this).data('type') == 'piSearch') {
				searchType = 'piSearch';
				let $searchDiv = $('#supportProduct .support-search');
				$searchDiv.find('input[name=piSearchYn]').val('Y');
				$searchDiv.find('input[name=piField]').val('RU');
				$searchDiv.find('input[name=piValue]').val($(this).text());
			} else {
				searchType = 'search';
				$('#RU').val($(this).text());
			}
			doCodeSearch('Product', searchType, mode == 'explain' ? 'Y' : 'N');
		});
		
		// 정렬 버튼 이베튼 등록
		$(document).on('click', '#supportProduct .support-search-list .utils-prouct button[data-sort]', function(e) {
			if ($(this).hasClass('active')) {
				return false;
			}
			let $allButtons = $('#supportProduct .support-search-list .utils-prouct button[data-sort]');
			$allButtons.removeClass('active').attr('title', '선택되지 않음');
			
			$(this).addClass('active').attr('title', '선택됨');
			
			let $searchDiv = $('#supportProduct .support-search');
			$searchDiv.find('input[name=sortField]').val($(this).data('sort-field'));
			$searchDiv.find('input[name=sortState]').val($(this).data('sort').toUpperCase());
			
			doCodeSearch('Product', 'sort', mode == 'explain' ? 'Y' : 'N');
		});
	} else if (right == 'Expand') {
		// 통계_검색어확장
		recordServiceStats(currentTab2, 'OPSVC', 'SEP');
		let srchKeyword = $.trim($('#sd01_g01_text').val());
		if (srchKeyword == '') {
			alert('검색어 확장을 위해 자유검색(전문)에 키워드를 입력해 주세요.');
			$('#sd01_g01_text').focus();
			return false;
		} else if (/[^가-힣|a-z|A-Z]/gi.test(srchKeyword)) {
			alert('검색어 확장은 하나의 단어로만 이용 가능합니다.\n예) 자동차(O), 자동차*엔진(X)');
			$('#sd01_g01_text').focus();
			return false;
		}
		$('#support' + right + ' .word-expand p.txt').text(srchKeyword);
		$('#support' + right + ' .support-search-list .list-body').empty();
	}
	
	if (mode == 'helper') {
		if (view) {
			if ($('#jstree' + right).jstree(true)) {
				initModalSupport(right);
			} else {
				const $jstree = $('#jstree' + right).jstree({
					core: {
						data: function(node, callback) {
							$.ajax({
								type: 'POST',
								url: '/khome/search/codeSearch.do',
								data: node.id == '#' ? {right: right, mode: 'tree_root'} : {
									right: right,
									mode: 'tree_child',
									code: node.id,
									code1: node.original.code1,
									code2: node.original.code2,
									code3: node.original.code3,
									code4: node.original.code4,
									code5: node.original.code5
								},
								dataType: 'json',
								success: function(data)
								{
									callback(buildTreeData(data.resultList, right));
								}
							});
						},
						themes: {
							variant: 'large'
						}
					},
					plugins: ['checkbox', 'search'],
					checkbox: {
						three_state: false,
						cascade: 'none'
					}
				});
			    
			    // 체크박스 선택시 값 업데이트
			    $jstree.bind('changed.jstree', function(e, data) {
			    	supportCheckValue(data.selected, '#supportSubmit' + right);
			    });
			}
		} else {
			if (right == 'Product') {
				$('#openerType').val(openerType);
			} else if (right == 'Expand') {
				doCodeSearch(right, 'search', 'N');
			}
		}
		
		if (right == 'Product') {
			$('#supportProduct .con-foot').show();
		} else {
			//$('#support' + right + ' .support-submit-area').find('input[type=text], button').prop('disabled', false);
			$('#support' + right + ' .support-submit-area').show();
		}
		if('IPC|CPC|EPC|UPC|FI|FT|DC|LC'.indexOf(right) > -1) {
			const onclickVal = $('#support' + right + ' .btn-search').attr('onclick');
			if(onclickVal && onclickVal.includes("'explain'")) {
				$('#support' + right + ' .form-search').attr('onkeydown', "handleEnter(event, doCodeSearch, ['" + right + "', 'search'])");
				$('#support' + right + ' .btn-search').attr('onclick', "doCodeSearch('" + right + "','search')");
			} 
		}
	} else {
		if (view != '') {
			if (right == 'Product') {
				// 상품분류(상표)
				if ($(obj).data('similar-fg') != 'Y') {
					let tempVer = '';
					let tempVerFg = view.split('|')[0];
					let tempRU = view.split('|')[1];
					if (tempVerFg == 'K') {
						tempVer = '6'; 		// 한국분류(구분류)
					} else {
						//tempVer = '122024'; // 12판 2024년
						if ($('#VER').eq(0).val() == undefined || $('#VER').eq(0).val() == '') {
							tempVer = '122025'; // 12판 2025년
						} else {
							tempVer = $('#VER').eq(0).val(); // 가장 최신으로
						}
					}
					$('#VER').val(tempVer);
					$('#RU').val(tempRU);
				} 
				// 유사군분류(상표)
				else {
					$('#SIMM').val(view);
				}
				
				$('#supportProduct .con-foot').hide();
			} else {
				$('#' + right.toLowerCase() + 'Value').val(view);
				//$('#support' + right + ' .support-submit-area').find('input[type=text], button').prop('disabled', true);
				$('#support' + right + ' .support-submit-area').hide();
			}
			
			doCodeSearch(right, mode, view);
		}
	}
	fnSearchDetail.openSupport(obj, right.toLowerCase());
}

// 초기화
function initModalSupport(right)
{
	if ($('#jstree' + right).length != 0) {
		$('#jstree' + right).jstree('close_all'); // 펼쳐진 노드 모두 닫기
		$('#jstree' + right).jstree('deselect_all'); // 모든 노드 체크 해제
		
		if (right == 'DR') {
			$('#jstree' + right).jstree('clear_search'); // 검색 결과  초기화
		}
	}

	let $supportDiv = $('#support' + right);
	$supportDiv.find('.con-body').scrollTop(0);
	
	if ($supportDiv.find('.support-info').hasClass('hide')) {
		$supportDiv.find('.support-info').removeClass('hide');
		$supportDiv.find('.support-search-list').addClass('hide');
	}
	
	if (right == 'Product') {
		let $searchDiv = $supportDiv.find('.support-search');
		$searchDiv.find('input[type=text]').val('');
		$searchDiv.find('input[type=checkbox]').prop('checked', false);
		$searchDiv.find('#VER option').eq(0).prop('selected', true);
		
		let $assistDiv = $supportDiv.find('.search-assist');
		$assistDiv.find('.form-grid-group:eq(1) .row').empty();
		$assistDiv.find('.form-grid-group:eq(0)').removeClass('hidden');
		$assistDiv.find('.form-grid-group:eq(1)').addClass('hidden');
	} else {
		searchCommonModule.resetValue('#' + right.toLowerCase() + 'Value');
	}
	
	initModalValues(right, 'init');
}

function initModalValues(right, mode)
{
	supportCheckArray = [];
	searchCommonModule.resetValue('#supportSubmit' + right);
	
	if (right == 'Product' && mode != 'sort' && mode != 'excel') {
		let $searchDiv = $('#supportProduct .support-search');
		if (mode != 'piSearch') {
			$searchDiv.find('input[name=piSearchYn]').val('');
			$searchDiv.find('input[name=piField]').val('');
			$searchDiv.find('input[name=piValue]').val('');
		}
		$searchDiv.find('input[name=sortField]').val('');
		$searchDiv.find('input[name=sortState]').val('');
		$('#supportProduct .support-search-list .utils-prouct button[data-sort]').removeClass('active').attr('title','선택되지 않음');
		$('#supportProduct .support-search-list .utils-prouct button[data-sort]').eq(0).addClass('active').attr('title','선택됨');
	}
	if(mode == 'init') {
		if (right == 'CRM') {
			$('.search-service-list').find('input[name=pageNum]').val('1');
		} else {
			$('#support' + right + ' .support-search-list').find('input[name=pageNum]').val('1');
		}
	}
}

// tree 검색
function doTreeSearch(right)
{
	let inputValue = $.trim($('#' + right.toLowerCase() + 'Value').val());
	let $jstreeInstance = $('#jstree' + right).jstree(true);
	
	$jstreeInstance.close_all();
	$jstreeInstance.clear_search();
	$jstreeInstance.search(inputValue);
}

// 공통 코드 검색 (mode:sort => obj:button, mode:search|piSearch => obj:explainYn)
function doCodeSearch(right, mode, obj)
{
	let inputValue;
	let totalcount;
	
	if (right == 'Product') {
		if (mode == 'excel') {
			totalcount = $('#support' + right + ' .support-search-list').find('input[name=totalcount]').val();
			if (totalcount == 0) {
				alert('검색된 결과가 존재하지 않습니다.');
				return false;
			} else if (totalcount > 5000) {
				alert('최대 저장 건수를 초과하였습니다.(최대 5,000건)');
				return false;
			}
		}
	} else if (right == 'Expand') {
		inputValue = $.trim($('#sd01_g01_text').val());
	} else {
		inputValue = $.trim($('#' + right.toLowerCase() + 'Value').val());
		if (inputValue == '') {
			alert('검색하실 키워드를 입력해 주세요.');
			$('#' + right.toLowerCase() + 'Value').focus();
			return false;
		}
	}
	
	toggleLoadingDialog('#support' + right + ' .modal-con', true);
	
	let pageNum = 1;
	if (mode == 'paging' || mode == 'pagingexp') {
		if (right == 'CRM') {
			pageNum = $('.search-service-list').find('input[name=pageNum]').val();
		} else {
			pageNum = $('#support' + right + ' .support-search-list').find('input[name=pageNum]').val();
		}
	} else {
		initModalValues(right, mode);
	}
	
	let params = {right: right, pageNum: pageNum, mode: mode};
	if (right == 'IPC') {
		let expression = inputValue + '*IPC_VER=[' + $('#ipcVer').val() + ']';
		params.searchExpression = expression;
	} else if (right == 'Product') {
		$targetDiv = $('#supportProduct .support-search');
		inputValue = 'VER=[' + $targetDiv.find('#VER').val() + ']';
		$.each($targetDiv.find('input[type=text]'), function(idx, item) {
			let tempValue = $.trim($(item).val());
			if (tempValue != '') {
				inputValue += '*' + $(item).attr('name') + '=[' + tempValue + ']';
			}
			//25.10.30 지정상품 명칭 및 유사군코드 일부 변경 알림 팝업 띄우기
			const triggerValues = ['G1004', 'g1004', 'G110101', 'g110101'];
			const tempValueList = tempValue.split(',').map(v => v.trim());
			if (($(item).attr('name') === 'SIMM') && tempValueList.some(v => triggerValues.includes(v)) && (pageNum === 1)){
				openModalSimilarCodeNotice();
			}			
		});
		
		$.each($targetDiv.find('input[type=checkbox]:checked').not('#exceptYn'), function(idx, item) {
			let tempValue = $.trim($(item).val());
			if (tempValue != '') {
				inputValue += '*' + $(item).attr('name') + '=[' + tempValue + ']';
			}
		});
		
		$.each($targetDiv.find('input[type=hidden]'), function(idx, item) {
			let tempValue = $.trim($(item).val());
			if (tempValue != '') {
				params[$(item).attr('name')] = tempValue;
			}
		});
		
		params.searchExpression = inputValue;
		if ($targetDiv.find('#exceptYn').prop('checked')) {
			params.exceptYn = $targetDiv.find('#exceptYn').val();
		}
		
		if (mode == 'excel') {
			params.pageUnit = totalcount;
		}
	} else if (right == 'CRM') {
		let crmKind = $('#crmKind').val();
		let crmCode = 'all';
		if (crmCode != '') {
			crmCode = $('#crmCode').val();
		}
		
		params.crmKind = crmKind;
		params.crmCode = crmCode;
		params.searchExpression = inputValue;
	} else {
		params.searchExpression = inputValue;
	}
	
	$.ajax({
		async: true,
		type: 'POST',
		url: '/khome/search/codeSearch.do',
		data: params,
		dataType: 'json',
		success: function(data)
		{
			if (data.resultCode == '00') {
				if (right == 'Product') {
					data.openerType = $('#openerType').val();
					
					// 검색결과 상단 검색 분류(카테고리) html 생성
					if (data.countInfo.totalcount != 0 && mode != 'piSearch' && mode != 'sort' && mode != 'excel') {
						let keyArray = Array.from(new Set(Object.keys(data.categoryGroup)));
						keyArray.sort();
						
						let categoryGrid = '';
						$.each(keyArray, function(idx, item) {
							categoryGrid += '<li class="col-auto">';
							categoryGrid += '<button type="button" class="btn" data-size="xs" data-type="piSearch" title="' + item + '류 ' + data.categoryGroup[item] + '건">' + item + '</button>';
							categoryGrid += '</li>';
						});
						
						let $assistDiv = $('#supportProduct .search-assist');
						$assistDiv.find('.form-grid-group:eq(1) .row').html(categoryGrid);
						$assistDiv.find('.form-grid-group:eq(0)').addClass('hidden');
						$assistDiv.find('.form-grid-group:eq(1)').removeClass('hidden');
					}
					$('#support' + right + ' .support-search-list').find('input[name=totalcount]').val(data.countInfo.totalcount);
				} else if (right == 'Expand') {
					supportCheckArray.push(inputValue);
				}
				
				if (mode == 'excel') {
					excelDownloadForGoods(data);
				} else {
					if ('AP|IN|IV|AG|RG|DP|PP|DG|PG'.indexOf(right) > -1) {
						// 김성준 주무관님 요청_팜헌응옥(620250070627)주소 예외 처리_(김철, 250327)
						$.each(data.resultList, function(idx, item){
							if (item.DOCID == '620250070627') {
								item.ADDR = '호주 프레스턴 빅토리아...';
							} 
						});
						getTemplate(right, 'common', 'personList', mode, data);
					} else {
						getTemplate(right, 'common', right.toLowerCase() + 'List', mode, data);
					}
				}
			} else {
				alert('검색 중 오류가 발생하였습니다.');
				toggleLoadingDialog(loadingDialogTarget, false);
			}
		},
		error: function(xhr, status, error)
		{
			// alert('검색 중 오류가 발생하였습니다.');
			toggleLoadingDialog(loadingDialogTarget, false);
		}
	});
}

// 상세보기 열기
var keyboardOpenDetailInfo = {
	openDetailFg: false,
	repeatLock: false,
	currentIndex: 0
};
function openDetail(right, applno, mode, el)
{	
	/*
	 * 개인화_김철(상세정보 보기방식)
	 * 분할화면(el != undefined), 새창(el == undefined)
	 * 최초로 검색결과에서 상세정보를 여는 경우, (el != undefined) 조건하에 새창 열고 return false;
	 * 새창 열기에서 다시금 함수 진입 시, (el == undefined) 조건하에 아래 로직 수행
	 */
	if (Object.keys(personalizeSetting).length != 0 && el != undefined) {
		if (personalizeSetting.detailView == 'window') {
			openWindow('detail', {applno:applno, right:right});
			return false;
		}
	}
	
	// 개인화 정보 전역변수 셋팅
	/*let tempResultList = {};
	if (window.opener) {
		tempResultList = window.opener.ResultData.getData(right).resultList;
	} else {
		tempResultList = ResultData.getData(right).resultList;
	}
	keyboardOpenDetailInfo.currentIndex = tempResultList.findIndex(function(item){
		keyboardOpenDetailInfo.openDetailFg = true;
		repeatFg = true;
	    return Object.values(item)[0] == applno;
	});*/
	
	if (currentTab2 != right) {	// 새창열기 때 탭 권리 저장
		if (!/natlPat|mPat|etcPat/.test(currentTab2)) {
			currentTab2 = right;
		}
	}
	
	// 통계_상세정보 조회
	if (right == 'abpat' || right == 'abpatTrans' || right == 'abdg' || right == 'abtm') {
		if(applno !== null && applno !== ''){
			recordServiceStats(right, 'BIBLO', 'BIB', applno.substr(0, 2).toUpperCase());
		}
	} else if (right != 'natlPat' && right != 'mPat' && right != 'etcPat' && right != '' && right !== null) {	// 특화검색 제외
		recordServiceStats(right, 'BIBLO', 'BIB');
	}
	
	// 통계_통합행정정보 조회
	if (mode == 'HAENGJEONG' ) {
		recordServiceStats(right, 'BIBLO', 'HSTR');
	}
	
	// html 초기화
	if (mode != 'HAENGJEONG' && mode != 'RGSTFEE') {
		$('#mainResultDetail').html('');
	}
	
	// 새창 유무에 따른 상세보기 화면 확장_새창(el==undefined)
	if (el != undefined) {
		searchDrag.toggleDetail(true, el);
	}
	toggleLoadingDialog('#mainResultDetail', true);
	
	let reqUrl = '';
	let params = '';
	let masterKey = '';
	let ajaxResult = '';
	
	switch(right){
		case 'kpat' : // 국내특실
			reqUrl = '/' + right + '/biblioDynapatha.do';
			if (mode == 'HAENGJEONG') {
				params = 'method=biblioMain_biblio&getType=' + mode + '&applno=' + applno;
			} else {
				params = 'method=biblioMain_biblio&applno=' + applno;
			}
			dpCnf.ctx = '/kpat';
			break;
		case 'abpat' : // 해외특허(영어검색)
			reqUrl = '/' + right + '/biblioDynapatha.do';
			if (applno.indexOf(',') > -1) {
				masterKey = applno.split(',');
				params = 'method=biblioMain_biblio&publ_key=' + (masterKey[0] + masterKey[1]) + '&cntry=' + masterKey[0];
			} else {
				params = 'method=biblioMain_biblio&publ_key=' + applno + '&cntry=' + applno.substring(0,2);
			}
			dpCnf.ctx = '/abpat';
			break;
		case 'abpatTrans' : // 해외특허(한글검색)
			reqUrl = '/abpat/biblioDynapatha.do';
			if (applno.indexOf(',') > -1) {
				masterKey = applno.split(',');
				params = 'method=biblioMain_biblio&publ_key=' + (masterKey[0] + masterKey[1]) + '&cntry=' + masterKey[0];
			} else {
				params = 'method=biblioMain_biblio&publ_key=' + applno + '&cntry=' + applno.substring(0,2);
			}
			dpCnf.ctx = '/abpat';
			break;
		case 'kpa' : // KPA
			if (mode == 'RGSTFEE') {
				// 통계_통합행정정보 조회
				recordServiceStats('KPA', 'BIBLO', 'RGFEE');
				reqUrl = '/' + right + '/rgin1000a.do';
				params = 'rgstno=' + applno; // applno == rgstno
			} else {
				reqUrl = '/' + right + '/biblioa.do';
				params = 'method=biblioMain_biblio&key=' + applno;
			}
			break;
		case 'abdg' : // 해외디자인
			reqUrl = '/' + right + '/biblioa.do';
			masterKey = applno.split(',');
			let ret = '';
			if (masterKey[3] == 'DC') {
				ret = 'DC';
			} else {
				ret = masterKey[3].substr(0, 2);
			}
			params = 'method=biblioMain_biblio&next=biblioViewSub01&publ_key=' + applno + '&cntry=' + ret;
			break;
		case 'kdg' : // 국내디자인
			reqUrl = '/kdtj/biblioDynapatha.do';
			if (mode == 'HAENGJEONG') {
				params = 'method=biblioDGMain_biblio&masterKey=' + applno + '&getType=' + mode + '&rights=DG&index=0';
			} else {
				params = 'method=biblioDGMain_biblio&masterKey=' + applno + '&rights=DG&index=0';
			}
			dpCnf.ctx = '/kdtj';
			break;
		case 'ktm' :
			reqUrl = '/kdtj/biblioDynapatha.do';
			if (mode == 'HAENGJEONG') {
				params = 'method=biblioTMMain_biblio&masterKey=' + applno + '&getType=' + mode + '&rights=TM&index=0&link=N';
			} else {
				params = 'method=biblioTMMain_biblio&masterKey=' + applno + '&rights=TM&index=0&link=N';
			}
			dpCnf.ctx = '/kdtj';
			break;
		case 'abtm' : // 해외상표
			reqUrl = '/' + right + '/FT_biblioMain.do';
			params = 'ltrtno=' + applno;
			break;
		case 'jg' : // 심판
			reqUrl = '/kdtj/biblioDynapatha.do';
			params = 'method=biblioJMMain_biblio&masterKey=' + applno + '&index=0';
			dpCnf.ctx = '/kdtj';
			break;
		case 'ipNaviConflict' : // ipNaviConflict
			reqUrl = '';
			break;
		case 'ipNaviPrcdn' : // ipNaviPrcdn
			reqUrl = '';
			break;
		case 'cntst' : // 아이디어공모전
			reqUrl = '/etc/cntst/biblioa.do';
			params = 'method=biblioMain&applno=' + applno;
			break;
		case 'cyber' : // 인터넷기술공지
			reqUrl = '/etc/cyber/biblioa.do';
			params = 'method=biblioMain&applno=' + applno;
			break;
	}
	
	var option = {
			async: false,
			type: 'POST',
			url: reqUrl,
			data: params,
			dataType: 'json',
			success: function(data)
			{
				// 상세정보 서비스 유무 확인(국내 디상심)
				if (right == 'kdg' || right == 'ktm' || right == 'jg') {
					if (data.service_yn == 'N') {
						alert('서비스 제공 대상이 아닙니다.');
						// 새창 유무에 따른 후속 처리
						if (el != undefined) {
							searchPageModule.toggleResultFilter(true, true); 
							toggleLoadingDialog(loadingDialogTarget, false);
							return false;
						} else {
							toggleLoadingDialog(loadingDialogTarget, false);
							window.close();
							return false;
						}
					}
				}

				if (mode == 'HAENGJEONG') {
					getTemplate(right, 'detail', 'viewSubHaengjeong', 'HAENGJEONG', data);
				} else if (mode == 'RGSTFEE') {
					getTemplate(right, 'detail', 'viewSubRgstFee', 'RGSTFEE', data);
				} else if (mode == 'P' || mode == 'R' || mode == 'C') {	// 지식재산처 링크()
					getTemplate(right, 'detail', 'view', mode , data);
				} else {
					if (right == 'abpatTrans') {
						binderBiblioData(applno, data, mode);
					}

					// 통계_출원번호별 상세정보 조회  2026-06
					let classcode = null;					
					if (right == 'kpat') {						
						classcode = data?.ipclist?.[0]?.clss_cd ?? null; //특실 코드
						recordStatRdnoData(right, applno, classcode);
					}else if (right == 'ktm') {
						classcode = data?.tb_KT15List[0]?.[0] ?? null; //상표 코드
						recordStatRdnoData(right, applno, classcode);
					}else if (right == 'kdg') {
						classcode = data?.lcClcd?.trim() || null; //디자인 코드
						recordStatRdnoData(right, applno, classcode);
					}   

					// 김성준 주무관님 요청_팜헌응옥(620250070627)주소 예외 처리_(김철, 250327)
					if (right == 'ktm') {
						$.each(data.apnlist, function(idx, item){
							if (item[3] == '620250070627') {
								item[1] = '호주 프레스턴 빅토리아...';
							} 
						});
						$.each(data.trhlist, function(idx, item){
							if (item[6] == '620250070627') {
								item[3] = '호주 프레스턴 빅토리아...';
							} 
						});
					}
					//getTemplate(right, 'detail', 'view', 'openDetail', data); // 중복 호출 제거			
					
					//발명의날 60주년 검색마라톤 이벤트 by.20250515 OHR
					if (applno.substr(0, 11) == '10202590000') {
						getTemplate('kpat', 'detail', 'view' + applno.substr(11, 2), 'openDetail');
					} else {
						getTemplate(right, 'detail', 'view', 'openDetail', data);
					}
				}
			},
			error: function(xhr, status, error)
			{
				toggleLoadingDialog(loadingDialogTarget, false);
			}	
	};
	
	if (right == 'kpat' || right == 'abpat' || right == 'kdg' || right == 'ktm' || right == 'jg' || right == 'abpatTrans') {	// 상세정보 스크래핑 적용 권리일 경우
		ajaxResult = typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);
	} else {
		ajaxResult = $.ajax(option);
	}
	
	//발명의날 60주년 검색마라톤 이벤트 by.20250515 OHR
	if(applno.substr(0, 11)=='10202590000'){
		ajaxResult = getTemplate('kpat', 'detail', 'view'+applno.substr(11, 2), 'openDetail');	
	}	
	
	return ajaxResult;
}

function doSpecializationSearch(mode, params)
{
	let $SpecializationForm = '';
	if (mode == 'main') {
		// 폼 셋팅
		$SpecializationForm = $('<form>', {
			id: '$SpecializationForm',
			name: '$SpecializationForm',
			method: 'POST',
			action: '/khome/search/searchResult.do'
		});
		
		$.each(params, function(key, val) {
			$SpecializationForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
		});
		
		$SpecializationForm.appendTo('body');
		$SpecializationForm.submit();
	} /*else {
		doSearch('specialization', 'specializationSearch');
	}*/
}

// 결과 내 재검색 버튼 처리
let tempQuery;
function toggleReSearch(obj) {
	// 통계_결과 내 재검색
	recordServiceStats('KHOME', 'OPSVC', 'RESC');
	let $targetObj = $('#queryText');
	if ($(obj).prop('checked')) {
		tempQuery = $('#queryText').val();
		$('#queryText').val('');
		$('#queryText').focus();
	} else {
		$('#queryText').val(tempQuery);
	}
}

// 결과의 코드 및 출원인 포함 검색
function reSearchInResult(field, keyword1, keyword2) {
	// 통계_검색결과 내 항목별 재검색
	recordServiceStats(currentTab2, 'OPSVC', 'SR' + field);
	
	let confirmText = '';
	let keyword = '';
	if (keyword2 != undefined && keyword2 != '') {
		confirmText = '\'' + keyword1 + '(' + keyword2 + ')\'를 포함하여 다시 검색하시겠습니까?';
		keyword = keyword2;
	} else {
		confirmText = '\'' + keyword1 + '\'를 포함하여 다시 검색하시겠습니까?';
		keyword = keyword1;
	}
	
	let result = confirm(confirmText);
	if (result) {
		rightTotalSearch(field + '=[' + keyword.replace(/[,^!+*\(\)\[\]]/gi, '') + ']');
	}
}

//번역
function renderTranslate(right, data, template)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data.result);
	resultHTML = updateContent(resultHTML);
	$("#container-translate").html(resultHTML);
	machineTranslate.init();
}

//오늘의 공보
function renderInfoData(right, data, template)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);	
	resultHTML = updateContent(resultHTML);
	$('#today-list-section').html(resultHTML);
	$('.bod-def-list caption').text('');
	let textTitle = $('.title.bul.abs').text();
	if(right == 'kpat') {
		$('.bod-def-list caption').text(textTitle + '. 순번, 출원번호, 출원일자, 공개일자, 발명의명칭, 발명의명칭, IPC 항목으로 구성되어 있습니다.');
	} else if(right == 'kdg') {
		$('.bod-def-list caption').text(textTitle + '. 순번, 출원번호, 출원일자, 공개일자, 디자인명칭, 국제분류 항목으로 구성되어 있습니다.');
	} else if(right == 'ktm') {
		$('.bod-def-list caption').text(textTitle + '. 순번, 출원번호, 출원일자, 등록공고일자, 상품분류, 상표명칭 항목으로 구성되어 있습니다.');
	}
}	

//소멸 공보
function renderExtinctData(right, data, template)
{
	// 권리별 템플릿 랜더링
	let bindTemplate = Handlebars.compile(template);
	let resultHTML = bindTemplate(data);
	resultHTML = updateContent(resultHTML);
	$('#extinction-detail-list').html(resultHTML);
}
	
function searchKeywordView(params) {
/*	let tempQuery = $('#sd010201_g02_text_04').val();
	if (tempQuery == undefined || tempQuery == '') {
		alert('검색키워드를 입력해주세요.');
		return false;
	}*/
	let tempQuery = '';
	let tempStrstat = '';
	toggleLoadingDialog('#container', true);
	
	let $tempForm = $('<form>', {
		id: 'tempForm',
		name: 'tempForm',
		method: 'POST',
		//target: right,
		action: '/kdc/docresult.do'
	});
	
	params['searchKeywordViewYn'] = 'Y';
	$.each(params, function(key, val) {
		$tempForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
		if (key == 'strstat') {
			tempStrstat = val;
		} else if (key == 'query') {
			tempQuery = val;
		}
	});
	
	$.ajax({
		type: 'POST',
		url: '/kdc/docresult.do',
		data: $tempForm.serialize(),
		dataType: 'json',
		success: function(data)
		{
			data.queryBak = tempQuery;
			data.strstat = tempStrstat;
			getTemplate('kdc', 'search', 'keyword', 'searchKeywordWeight', data);
			
			modal.open('#modalSearchKeyword');
		},
		error: function(xhr, status, error)
		{
			
		},
		complete: function()
		{
			toggleLoadingDialog('#container', false);
		}
	});
}

let initialWeightValues = {}; // 검색키워드 가중치 초기값
function initSearchKeywordWeight(mode)
{
	let $searchWeightDataObj = $('input[id^=skc]');
	
	// 검색키워드 가중치 초기화
	if (mode == 'init') {
		$.each($searchWeightDataObj, function(idx, item){
			initialWeightValues[idx] = $(item).val();
		});	
	} else if (mode == 'initialize') {
		$.each($searchWeightDataObj, function(idx, item){
			$(item).val(initialWeightValues[idx]);
		});
	}
}

// 검색결과 인쇄
function printResult()
{
	//2025.09.18 특화검색의 경우 상세정보 클릭 시 currentTab이 kpat으로 되기때문에
	if($('#searchKind').val() == 'specializationSearch') currentTab2 = $('#searchRight').val();

	if (ResultData.getData(currentTab2) == undefined || dataNotFound) {
		alert('검색 결과가 존재하지 않습니다.');
		return false;
	} else {
		openWindow('printResult', {target: 'printResult'});
	}
}

// 해외특허 한글검색용 binder
function binderBiblioData(key, data, mode)
{
	let resultList;
	if (mode == 'openWindow'){
		resultList = opener.ResultData.getData('abpatTrans').resultList;
	} else if (mode == 'openWindowForMyfolder') {
		resultList = myFolderResultData.resultList;
	} else {
		resultList = ResultData.getData('abpatTrans').resultList;
	}
	if (resultList != undefined && resultList.length > 0) {
		$.each(resultList, function(idx, item) {
			let itemKey = item.VdkVgwKey.replaceAll(',','');
			let tempKey = key.replaceAll(',','');
			if (itemKey == tempKey) {
				data.invnt_ttl = item.TL;
				data.invnt_ttl_kr = item.TLK;
				data.abstractTextKr = item.AB;
				data.claimText = item.CL;
			}
		});
	}
}

function doStatResearch(key, value, type)
{
	let query = key + '=[' + value + ']';
	if (type == 'date') {
		query = key + '=[' + value + '0101~' + value + '1231' + ']';
	}
	let $targetForm = $('#' + currentTab2 + 'SearchForm');
	let beforeExpression = $targetForm.find('input[name=expression]').val();
	//$targetForm.find('input[name=beforeExpression]').val(beforeExpression);
	$targetForm.find('input[name=queryText]').val(beforeExpression + '*' + query);
	$targetForm.find('input[name=expression]').val(beforeExpression + '*' + query);
	modal.close('#modalStatistics');
	doSearch(currentTab2, 'statResearch');
}

function filterHangjungToggle(right) {
	if (!/kpat|kdg|ktm/.test(right)) return false;
	
	let inputName = right == 'kpat' ? 'leftHangjung' : 'measure';
	let tmpBtn = $('#mainResultFilter').find('.btnToggleStatus');
	
	if (!$('#mainResultFilter').find("input[data-check-all=" + inputName + "]").is(':checked')) {
		if (tmpBtn.attr('aria-expanded') === 'false') {
			tmpBtn.click();
		}
	} else {
		if (tmpBtn.attr('aria-expanded') === 'true') {
			tmpBtn.click();
		}
	}
}

function detailHangjungToggle(right) {
	if (!/kpat|kdg|ktm/.test(right)) return false;
	
	let inputName = right == 'kpat' ? 'sd01_ck03' : right == 'kdg' ? 'sd010201_g02' : 'sd010301_g03';
	
	let $tmpInput = $('#sd01Pannel').find("input[data-check-all=" + inputName + "]");
	let $tmpBtn = $tmpInput.closest('.ck-list').find('.btnToggleStatus');
	
	if (!$tmpInput.is(':checked')) {
		if ($tmpBtn.attr('aria-expanded') === 'false') {
			$tmpBtn.click();
		}
	} else {
		if ($tmpBtn.attr('aria-expanded') === 'true') {
			$tmpBtn.click();
		}
	}
}

// 상세정보의 IPC 입력 도우미 jstree Tab 활성화 함수
function applyTabindex(container) {
	$('#jstreeIPC, #jstreeCPC, #jstreeEPC, #jstreeFI, #jstreeFC, #jstreeLC, #jstreeDR').attr('tabindex', '-1');
    $(container).find('.jstree-container-ul').attr('tabindex', '-1');
    $(container).find('.jstree-container-ul i, .jstree-container-ul span').attr('tabindex', '0');
}
function syncAllCheckboxes(container) {
    $(container).find('.jstree-node').each(function() {
        const $node = $(this);
        const $anchor = $node.find('.jstree-anchor');
        const $checkbox = $node.find('.jstree-checkbox');
        const $themeicon = $node.find('.jstree-themeicon');
        
        // 1. 모든 요소에서 불필요한 role 제거 ( presentation 포함 )
        $node.find('[role]').removeAttr('role');
        
        if ($checkbox.length) {
            const isSelected = $anchor.attr('aria-selected') === 'true';
            let nodeText = "";
            
            $anchor.contents().each(function(){
            	if(this.nodeType === 3) {
            		nodeText += $(this).text();
            	}
            	if(nodeText.trim().length > 0) return false;
            })
            
            if(nodeText.trim() === "") {
            	nodeText = $anchor.find('.description').first().text();
            }
            nodeText = nodeText.trim();
            // 2. 체크박스에만 명확한 역할 부여
            $checkbox.attr({
                'aria-label': isSelected ? nodeText + ' 체크됨' : '체크 해제'
            });
            $themeicon.attr({
                'aria-label': '클릭 시 앞의 체크박스 선택 또는 해제'
            });
            
            // 3. 앵커는 트리 항목(treeitem) 역할만 수행
            $anchor.attr('role', 'treeitem');
        }
    });
}

/**
 * 기술분류정보 셀렉트 박스 텍스트
 */

function changeLGCLSCol(el) {
	let selectedId = '';
	if(el == undefined || el == null) {
		selectedId = 'tech_1'; 
	} else {
		selectedId = el.value;
	}
	const config = techDepthConfig[selectedId] || { depth: 2 };
    const $container = $('#miller-container');

    $container.removeClass('depth-2 depth-3').addClass('depth-' + config.depth);
    config.depth === 3 ? $('#col-sub').show() : $('#col-sub').hide();
	
    $('#techDesc').text(techDataTitle[selectedId]);
    $('#techInfoDisplay').show();
 
    // 첫 컬럼 데이터 로드 (대분류)
    $('#col-mid ul, #col-sub ul').empty();
    loadTechData(selectedId, '#col-large');
}

function loadTechData(parentId, targetColId) {
    // 로딩 시작
    const $target = $(targetColId);
    const currentType = $('input[name="sd0205_g00"]:checked').val();
    $target.prepend('<div class="loading-mask"><div class="spinner"></div></div>');

    $.ajax({
        type: 'POST',
        url: '/khome/search/SearchTechFld.do',
        data: { value: parentId, kind:currentType},
        success: function(data) {
            renderColumn(data.resultList, targetColId);
        },
        complete: function() {
            $target.find('.loading-mask').remove();
        }
    });
}

function renderColumn(data, colId) {
	const $ul = $(colId).find('ul').empty();
	const currentType = $('input[name="sd0205_g00"]:checked').val();
	const isLastStep = (currentType !== 'tech_3' && colId === '#col-mid') || (colId === '#col-sub');

    data.forEach(item => {
        const $li = $('<li>')
            .attr('tabindex', '0') // 키보드 포커스 가능하게 설정
            .append($('<span class="text-part">').text(item.text))
            .attr('title', item.text) // 초기 툴팁
            .data('id', item.id)
            .data('originalText', item.text); // 원래 텍스트 보관

        if (isLastStep) {
            $li.addClass('no-arrow');
        }

        const selectItem = function($el) {
            if ($el.hasClass('active')) return;
            $el.parent().find('li').removeClass('active').attr('title', function() { return $(this).data('originalText'); });
            $el.addClass('active').attr('title', "(선택됨) " + $el.data('originalText'));

            if (colId === '#col-large') {
                $('#col-mid ul').empty(); 
                // tech_3가 아니면 col-sub를 비울 필요 없음 (이미 숨겨져 있음)
                if (currentType === 'tech_3') $('#col-sub ul').empty();
                loadTechData($el.data('id'), '#col-mid');
            } else if (colId === '#col-mid' && currentType === 'tech_3') {
                $('#col-sub ul').empty();
                loadTechData($el.data('id'), '#col-sub');
            }
        };

        $li.on('click', function() { selectItem($(this)); });
        $li.on('keydown', function(e) { if (e.key === 'Enter') selectItem($(this)); });
        $ul.append($li);
    });
}

function getIPCQuery() {
	const $activeItems = $('.m-col li.active');
	const $lastActive = $activeItems.last();
	const id = $lastActive.data('id');
	let resultQuery = '';
	
	if(id == null || id == undefined) {
		return null;
	} else {
		$.ajax({
	        type: 'POST',
	        url: '/khome/search/getTechFldQuery.do',
	        data: { value: id},
	        success: function(data) {
	        	if(data.resultList[0].REMRK != null || data.resultList[0].REMRK != undefined) {
	        		resultQuery = data.resultList[0].SRFRM_CONT + data.resultList[0].REMRK;
	        	} else {
	        		resultQuery = data.resultList[0].SRFRM_CONT;
	        	}
	        	if (window.location.pathname.indexOf('/main.do') > -1) {
	        		$('#searchKind').val('detailSearch');
	        		$('#searchRight').val('kpat');
	        		$('#queryTextTop').val(resultQuery);
	        		$('#queryText').val(resultQuery);
	        		$('#expression').val(resultQuery);
	        		$('#pageLanguage').val(i18next.language);
	        		$('#searchInTrans').val('N');
	        		$('#searchInComplate').val('N');
	        		$('#indtechSearchFlag').val('Y');
	        		window.sessionStorage.setItem('queryText', resultQuery);
	        		window.sessionStorage.setItem('expression', resultQuery);
	        		$('#mainSearchForm').submit();
	        	} else if (window.location.pathname.indexOf('/searchResult.do') > -1) {
	        		let targetFormId = '#kpatSearchForm';
	        		$(targetFormId).find('input[name=queryText]').val(resultQuery);
	        		$(targetFormId).find('input[name=expression]').val(resultQuery);
	        		$(targetFormId).find('input[name=pageLanguage]').val(i18next.language);	// 한-영 변역검색 페이지 언어 처리
	        		$(targetFormId).find('input[name=searchInTrans]').val('N');
	        		$(targetFormId).find('input[name=searchInComplate]').val('N');
	        		$('#indtechSearchFlag').val('Y');
	        		checkRequest();
	        		initDataForDetailSearch('kpat');
	        		initChangeViewBtn('kpat');
	        		$('#searchKind').val('detailSearch');
	        		doSearch('kpat', 'detailSearch');
	        		$('#queryText').val(resultQuery);
	        		initSortOption('detailSearch');	
	        		const activTapMap = {
	        				IPC: "기술분야 검색"
	        		};
	        		document.title = "홈 > 지식재산정보검색 > " + activTapMap['IPC'] + " (검색어: " + resultQuery + ")";
	        	}
	        	recordServiceStats('KHOME', 'SMART', 'INDSR');
	        },
	        error: function() {

	        }
	    });
	}
}