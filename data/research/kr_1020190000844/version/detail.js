// (abpat) 전문보기
function goFullText(publ_key, cntry, patno_fg, download, fulltext_fg, trans_yn)
{
	// 통계_전문조회
	if (trans_yn == 'Y'){
		if (patno_fg == 'OPN') {
			recordServiceStats('ABPTR', 'BIBLO', 'PFLT', cntry);
		} else {
			recordServiceStats('ABPTR', 'BIBLO', 'RFLT', cntry);
		}
	} else {
		if (patno_fg == 'OPN') {
			recordServiceStats('ABPAT', 'BIBLO', 'PFLT', cntry);
		} else {
			recordServiceStats('ABPAT', 'BIBLO', 'RFLT', cntry);
		}
	}
	
	var viewerId = '#pdfViewer01';
	var tempFg = patno_fg;
	
	// 대만일 경우
	if (cntry == 'TA') {
		// 공개, 등록 구분
		if (patno_fg == 'OPN') {
			// TIFF 존재 여부
			if ($('#facsimileUnExFg').val() == 'Y') {
				$('#report0101').parent().show();
				$('#report0101').prop('checked', true);
				tempFg = 'TWTIFF';
				viewerId = '#imgViewer01';
			} else {
				$('#report0101').parent().hide();
			}
			
			// PDF 존재 여부
			if ($('#unexaminedFullTextFg').val() == 'Y') {
				$('#report0102').parent().show();
				if (tempFg != 'TWTIFF') {
					$('#report0102').prop('checked', true);
					tempFg = 'TWPDF';
				}
			} else {
				$('#report0102').parent().hide();
			}
		} else if (patno_fg == 'PAN') {
			viewerId = '#pdfViewer02';
			// TIFF 존재 여부
			if ($('#facsimileExFg').val() == 'Y') {
				$('#report0101').parent().show();
				$('#report0101').prop('checked', true);
				tempFg = 'TWTIFF';
				viewerId = '#imgViewer02';
			} else {
				$('#report0101').parent().hide();
			}
			// PDF 존재 여부
			if ($('#examinedFullTextFg').val() == 'Y') {
				$('#report0102').parent().show();
				if (tempFg != 'TWTIFF') {
					$('#report0102').prop('checked', true);
					tempFg = 'TWPDF';
				}
			} else {
				$('#report0102').parent().hide();
			}
		} else if (patno_fg == 'TWTIFF' || patno_fg == 'TWPDF') {
			if(publ_key.slice(-2, -1) == 'B'){
				if (patno_fg == 'TWPDF') {
					viewerId = '#pdfViewer02';
				} else {
					viewerId = '#imgViewer02';
				}
			} else {
				if (patno_fg == 'TWPDF') {
					viewerId = '#pdfViewer01';
				} else {
					viewerId = '#imgViewer01';
				}
			}
		}
		
		if (viewerId.indexOf('img') > -1) {
			if (viewerId == '#imgViewer01') {
				$('#pdfViewer01').hide();
				$('#imgViewer01').show();
			} else if (viewerId == '#imgViewer02') {
				$('#pdfViewer02').hide();
				$('#imgViewer02').show();
			}
		} else {
			if (viewerId == '#pdfViewer01') {
				$('#imgViewer01').hide();
				$('#pdfViewer01').show();
			} else if (viewerId == '#pdfViewer02') {
				$('#imgViewer02').hide();
				$('#pdfViewer02').show();
			}
		}
	} else {
		if (patno_fg == 'OPN') {
			viewerId = '#pdfViewer01';
			if($('#facsimileUnExFg').val() == 'Y') {
				$('#pdfViewer01').hide();
				$('#imgViewer01').show();
				viewerId = '#imgViewer01';
			}
		} else {
			viewerId = '#pdfViewer02';
			if($('#facsimileExFg').val() == 'Y') {
				$('#pdfViewer02').hide();
				$('#imgViewer02').show();
				viewerId = '#imgViewer02';
			}
		}
	} 
	
	if (viewerId.indexOf('img') > -1) {
		if (fulltext_fg == 'N') {
			imgFullTextAjax(viewerId, '/abpat/fulltexta.do', {method: 'fullText', publ_key: publ_key, cntry: cntry, patno_fg: tempFg, download: download});
		} else {
			imgFullTextAjax(viewerId, '/abpat/fulltexta.do', {method: 'fullText', publ_key: fulltext_fg, cntry: cntry, patno_fg: tempFg, download: download});
		}
	} else {
		if (fulltext_fg == 'N') {
			fullTextAjax(viewerId, '/abpat/fulltexta.do', {method: 'fullText', publ_key: publ_key, cntry: cntry, patno_fg: tempFg}, publ_key + ".pdf", download);
		}
		else {
			fullTextAjax(viewerId, '/abpat/fulltexta.do', {method: 'fullText', publ_key: fulltext_fg, cntry: cntry, patno_fg: tempFg}, fulltext_fg + ".pdf", download);
		}
	}	
}
//(abpat) 전문보기 초기화
function initFulltextabpat() {
	$('.pdf-container .tab-section-01').removeClass('hidden');
	$('#pdfViewer03').html('');
	$('#imgViewer03').hide();
}
//(abpat) 정정공고 전문보기
function goCorrectionFulltextabpat(applno, correction_Ltrtno, file_cd, trans_yn) {
	// 통계_전문조회
	if (trans_yn == 'Y') {
		recordServiceStats('ABPTR', 'BIBLO', 'CFLT', correction_Ltrtno.slice(0, 2));
	} else {
		recordServiceStats('ABPAT', 'BIBLO', 'CFLT', correction_Ltrtno.slice(0, 2));
	}
	
	$('.pdf-container.active .tab-section-01').addClass('hidden')
	
	if (file_cd == 'S10201') {
		$('#imgViewer03').hide();
		$('#pdfViewer03').show();
		fullTextAjax('#pdfViewer03', '/abpat/fulltexta.do', {method: 'correctionFulltext', applno: applno, publ_key: correction_Ltrtno}, correction_Ltrtno + ".pdf");
	} else {
		$('#pdfViewer03').hide();
		$('#imgViewer03').show();
		imgFullTextAjax('#imgViewer03', '/abpat/fulltexta.do', {method: 'correctionFulltext', applno: applno, publ_key: correction_Ltrtno});
	}
}
//(ktm) 전문보기
function goFullTextKtm(publ_key, pub_reg, download) {
	// 통계_전문조회
	if (pub_reg == 'R') {
		recordServiceStats('KTM', 'BIBLO', 'RFLT');
	} else {
		recordServiceStats('KTM', 'BIBLO', 'PFLT');
	}
	
	var viewerId = '#pdfViewer01';
	var method = 'fullTextTM';
	var flag = '';
	// 다운로드일 경우에는 바로 호출
	if (download != 'Y') {
		if(pub_reg == 'R') {
			viewerId = '#pdfViewer02';
		}
	}
	
	if (pub_reg == 'R') {
		flag = 'B1';
	}
	else if (pub_reg == 'P') {
		flag = '';
	}
	fullTextAjax(viewerId, '/kdtj/fullText.do', {method: method, applno: publ_key, pub_reg: pub_reg, rights: 'TM'}, publ_key + flag + ".pdf", download);
}

//(jg) 전문보기
function goFullTextJg(trlno, pub_reg, download) {
	// 통계_전문조회
	if (pub_reg == 'A') {
		recordServiceStats('KJM', 'BIBLO', 'JFLT');
	} else {
		recordServiceStats('KJM', 'BIBLO', 'CFLT');
	}
	
	var viewerId = '#pdfViewer01';
	var method = 'fullTextJM';
	var flag = '';
	// 다운로드일 경우에는 바로 호출
	if (download != 'Y') {
		if(pub_reg == 'B') {
			viewerId = '#pdfViewer02';
		}
	}
	
	if (pub_reg == 'A') {
		flag = 'A';
	}
	else if (pub_reg == 'B') {
		flag = 'B';
	}
	fullTextAjax(viewerId, '/kdtj/fullText.do', {method: method, applno: trlno, pub_reg: pub_reg}, trlno + flag + ".pdf", download);
}

//(kdg) 전문보기
function goFullTextKdg(applno, pub_reg, download) {
//	goFullTextKdg('{{applno}}', 'R', 'N')"
	
	// 통계_전문조회
	if (pub_reg == 'R') {
		recordServiceStats('KDG', 'BIBLO', 'RFLT');
	} else if (pub_reg == 'P') {
		recordServiceStats('KDG', 'BIBLO', 'PFLT');
	} else if (pub_reg == 'B') {
		recordServiceStats('KDG', 'BIBLO', 'CPFLT');
	}
	
	var viewerId = '#pdfViewer01';
	var method = 'fullText';
	// applno => applno,ds_seq
	var publ_key = applno;
	var flag = '';
	// 다운로드일 경우에는 바로 호출
	if (download != 'Y') {
		if (pub_reg == 'R') {
			viewerId = '#pdfViewer03';
		}
		else if (pub_reg == 'B') {
			method = 'facsimileDG';
			viewerId = '#pdfViewer02';
			publ_key = applno;
		}
	}
	
	if (pub_reg == 'R') {
		flag = 'B1';
	}
	else if (pub_reg == 'P') {
		flag = 'A';
	}
	fullTextAjax(viewerId, '/kdtj/fullText.do', {method: method, applno: publ_key, pub_reg: pub_reg, rights: 'DG'}, applno + flag + '.pdf', download);
}

//(ktm) 정정공보 전문보기
function goCorrectionFulltextKtm(publ_key, ver, stat) {
	// 통계_전문조회
	recordServiceStats('KTM', 'BIBLO', 'CFLT');
	
	$('.pdf-container.active .tab-section-01').addClass('hidden');
	$('.pdf-container.active .title-box').addClass('hidden');
	checkInfoBox('detail04');
	var viewerId = '#pdfViewer03';
	var pub_reg = 'c';
	var method = 'correctionFulltextTM';
	
	fullTextAjax(viewerId, '/kdtj/fullText.do', {method: method, applno: publ_key, pub_reg: pub_reg, rights: 'TM', ver: ver, stat: stat}, publ_key + 'C.pdf');
}

//(kdg) 정정공보 전문보기
function goCorrectionFulltextKdg(applno, ver) {
	// 통계_전문조회
	recordServiceStats('KDG', 'BIBLO', 'CFLT');
	
	$('.pdf-container.active .tab-section-01').addClass('hidden');
	$('.pdf-container.active .title-box').addClass('hidden');
	checkInfoBox('detail05');
	var viewerId = '#pdfViewer04';
	var method = 'correctionFulltext';
	
	//var publ_key = applno + ',M01';//재 분석 M01 파라미터
	var publ_key = applno;
	
	var pub_reg = 'c';

	fullTextAjax(viewerId, '/kdtj/fullText.do', {method: method, applno: publ_key, pub_reg: pub_reg, ver: ver, rights: 'DG'}, applno + 'C.pdf');
}

//(kdg+ktm) 전문보기 초기화
function initFulltextKdtj() {
	$('.pdf-container .tab-section-01').removeClass('hidden');
	$('.pdf-container .title-box').removeClass('hidden');
	$('.pdf-container .info-box').remove();
	$('#pdfViewer03').html('');
	$('#pdfViewer04').html('');
}

//(abdg) 전문보기
function goFullTextAbdg(publ_key, cntry, dsImgTpcd, Ltrtno, downYn) {
	// 통계_전문조회
	recordServiceStats('ADG', 'BIBLO', 'RFLT');
	
	var viewerId = '#pdfViewer01';
	var method = 'fullText';
	
	var pub_reg ='R';
	var ver = null;
	var rights = 'DG';
	var ltrtno  = publ_key.split(',');
	//fullTextAjax('#pdfViewer01','/abdg/remoteFile.do', {method: 'fullText', publ_key: 'US,2024D1020560,usp', cntry :'US', dsImgTpcd : 'uspat'}, "dddddddddd.pdf");
	if (cntry == 'JP' || cntry == 'WO') {
		fullTextAjax('#pdfViewer01','/abdg/remoteFile.do', {method: 'fullText', publ_key: publ_key, cntry : cntry, dsImgTpcd : dsImgTpcd, downYn : downYn}, Ltrtno.trim()+".pdf");
	} else {
		fullTextAjax('#pdfViewer01','/abdg/remoteFile.do', {method: 'fullText', publ_key: publ_key, cntry : cntry, dsImgTpcd : dsImgTpcd, downYn : downYn}, Ltrtno[1]+".pdf");
	}
	
}

//(특실) 대표도면 다운로드 by.20251202 OHR
function openDown(applno)
{
	toggleLoadingDialog('#mainResultDetail div.body', true);
	
	var option = {
			url: '/kpat/fullText.do',
			type: 'POST',
			data:  {
                method: "downloadImage",
                applno: applno,
                frontYn: "Y",
                downYn: "Y"
			},
			xhrFields: {responseType: 'blob'},
	        success: function (blob, status, xhr) {

	            //파일명(Content-Disposition)
	            const disposition = xhr.getResponseHeader("Content-Disposition");
	            let fileName = applno + ".jpg";

	            if (disposition && disposition.indexOf("filename=") > -1) {
	                fileName = disposition
	                    .split("filename=")[1]
	                    .replace(/"/g, "")
	                    .trim();
	            }

	            //실제 타입 사용
	            const contentType = xhr.getResponseHeader("Content-Type") || "application/octet-stream";

	            const fileBlob = new Blob([blob], { type: contentType });
	            const url = URL.createObjectURL(fileBlob);

	            // 다운로드 링크
	            const link = document.createElement('a');
	            link.href = url;
	            link.download = fileName;
	            document.body.appendChild(link);
	            link.click();

	            URL.revokeObjectURL(url);
	            link.remove();
	        },

			error: function(jqXHR, textStatus, errorThrown) {
				console.error('Error : ', textStatus, errorThrown);
			},
			complete: function() {
				toggleLoadingDialog('#mainResultDetail div.body', false);
			}
	};

		dpCnf.ctx = '/kpat';
		typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);

}


// (공통) 전문 호출부 함수
function fullTextAjax(viewerId, url, parameterData, fileName, download)
{
	toggleLoadingDialog('#mainResultDetail div.body', true);
	
	var option = {
			url: url,
			type: 'POST',
			data: parameterData,
			xhrFields: {responseType: 'blob'},
			success: function(response) {
				let blob = new Blob([response], {type: 'application/pdf'});
				let url = URL.createObjectURL(blob);
				url += '#sidebarView=0';
				
				if (download == 'Y') {
					let link = document.createElement('a');
					link.href = url;
					link.download = fileName;
					link.click();
					$(link).remove();
					// 파일다운로드 관련 GTM 이벤트 호출 추가
					callDownloadTagEvent(fileName);
				} else {
					pdfViewer.init(viewerId, url, fileName);
				}
			},
			error: function(jqXHR, textStatus, errorThrown) {
				console.error('Error : ', textStatus, errorThrown);
			},
			complete: function() {
				toggleLoadingDialog('#mainResultDetail div.body', false);
			}
	};
	if(url.indexOf('abdg') > -1) {	// 해외디자인 전문 dynapath 미적용
		$.ajax(option);
	} else {
		dpCnf.ctx = url.substring(0, url.indexOf('/', 1));
		typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);
	}
}
// kpat
//(kpat) 공보다운
function GoDownFullText(params){
	/*let $tempForm = $('<form>', {
		id: 'tempForm',
		name: 'tempForm',
		method: 'POST',
		target: '',
		action: '/kpat/fullText.do?method=fullText'
	});
	params['download'] = 'Y';
	
	//applno, pub_reg
	$.each(params, function(key, val) {
		$tempForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
	});
	$tempForm.appendTo('body');
	$tempForm.submit();*/
	var temp_applno = params['applno'].substring(0,2);
	var flag = '';
	if (temp_applno == '10') {
		if (params['pub_reg'] == 'P') {
			flag = 'A';
		}
		else {
			flag = 'B1';
		}
	}
	else {
		if (params['pub_reg'] == 'P') {
			flag = 'U';
		}
		else {
			flag = 'Y1';
		}
	}
	fullTextAjax('', '/kpat/fullText.do', {method: 'fullText', applno: params['applno'], pub_reg: params['pub_reg']}, params['applno'] + flag + ".pdf", 'Y');
}

//(kpat) 공보다운
function downloadTiff(params)
{
	/*let $tempForm = $('<form>', {
		id: 'tempForm',
		name: 'tempForm',
		method: 'POST',
		target: '',
		action: '/kpat/fullText.do?method=facsimile'
	});
	params['next'] = 'downloadTiff';
	
	//applno, pub_reg
	$.each(params, function(key, val) {
		$tempForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
	});
	$tempForm.appendTo('body');
	$tempForm.submit();*/
	var temp_applno = params['applno'].substring(0,2);
	var flag = '';
	if (temp_applno == '10') {
		if (params['pub_reg'] == 'P') {
			flag = 'A';
		}
		else {
			flag = 'B1';
		}
	}
	else {
		if (params['pub_reg'] == 'P') {
			flag = 'U';
		}
		else {
			flag = 'Y1';
		}
	}
	fullTextAjax('', '/kpat/fullText.do', {method: 'fullText', applno: params['applno'], pub_reg: params['pub_reg']}, params['applno'] + flag + ".pdf", 'Y');
}

//(kpat) 정정공고 전문보기
function goCorrectionFulltextKpat(applno, correctionSeq) {
	// 통계_전문조회
	recordServiceStats('KPAT', 'BIBLO', 'CFLT');
	
	$('.pdf-container.active .tab-section-01').addClass('hidden');
	$('.pdf-container.active .title-box').addClass('hidden');
	checkInfoBox('detail04');
	var viewerId = '#pdfViewer03';
	fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'correctionFulltext', applno: applno, correctionSeq: correctionSeq}, applno + ".pdf");
}

//(kpat) 존속기간연장공보 전문보기
function goExFulltextKpat(applno, correctionSeq) {
	$('.pdf-container.active .tab-section-01').addClass('hidden');
	$('.pdf-container.active .title-box').addClass('hidden');
	checkInfoBox('detail05');
	var viewerId = '#pdfViewer04';
	fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'EXFulltext', applno: applno, correctionSeq: correctionSeq}, applno + ".pdf");
}

//(kpat) 전문보기 초기화
function initFulltextKpat() {
	$('.pdf-container .tab-section-01').removeClass('hidden');
	$('.pdf-container .title-box').removeClass('hidden');
	$('.pdf-container .info-box').remove();
	$('#pdfViewer03').html('');
	$('#pdfViewer04').html('');
}

//(kpat) 중간서류철 원문보기
function openDocument(applno, rgno, rsDocCd, docpath)
{
	//통계_거절정보제공 익명
	recordServiceStats(currentTab2, 'OPSVC', 'OPDV');
	
	let $tempForm = $('<form>', {
		id: 'tempForm',
		name: 'tempForm',
		method: 'POST',
		target: rgno,
		action: '/khome/detail/document.do'
	});
	
	$tempForm.append($('<input/>', {type: 'hidden', name: 'applno', value: applno}));
	$tempForm.append($('<input/>', {type: 'hidden', name: 'rsno', value: rgno}));
	$tempForm.append($('<input/>', {type: 'hidden', name: 'rsDocCd', value: rsDocCd}));
	$tempForm.append($('<input/>', {type: 'hidden', name: 'docPath', value: docpath}));
	
	$tempForm.appendTo('body');
	
	window.open('', rgno, 'width=' + screen.width + ', height=' + screen.height + ', menubar=no, toolbar=no, location=no, status=no, fullscreen=yes');
	
	$tempForm.submit();
	$tempForm.remove();
}
//(kpat) 도면 일괄보기(html load)
function changeImageMain()
{
	var applList = [];
	
 	$(ResultData.getData('kpat').resultList).each(function(idx, item){
		applList[idx] = item.DOCID;
	});
 	
	$.ajax({
		url : '/kpat/AllImgList.do?method=allImgListInResult',
		type : 'post',
		traditional : true,
		data : {applList : applList}, 
		async : true,
		cache : true,
		datatype: 'json',
	    success : function(data)
	    {
	    	ResultData.setAllImageData('kpat', data);
	    	getTemplate(currentTab2, 'search', 'allList', 'changeView');
	    },
	    error : function(request, status, error)
	    {
	        // alert('code::' + request.status + '\n' + 'message;' + request.responseText + '\n' + 'error:' + error);
	    }
	});
}

function changeImageMain2()
{
	let $targetForm = $('#kpatSearchForm');
	
	$targetForm.find('input[name=viewMode]').val('All');
	$targetForm.find('input[name=numPerPage]').val('10');
	
	let ajaxResult = $.ajax({
		async: false,
		type: 'POST',
		url: $targetForm.attr('action'),
		data: $targetForm.serialize(),
		dataType: 'json',
		success: function(data)
		{
			ResultData.setData('kpat', data);
			getTemplate('kpat', 'search', 'allList', '', '');
		},
		error: function(xhr, status, error)
		{
			alert('통신 중 오류가 발생하였습니다.');
		},
		complete: function()
		{
			$('input[name=viewMode]').val('');
			$('input[name=numPerPage]').val('30');
		}
	});
}

/*function changeImageMain3()
{
	let $targetForm = $('#kdgSearchForm');
	
	$targetForm.find('input[name=viewMode]').val('All');
	
	let ajaxResult = $.ajax({
		async: false,
		type: 'POST',
		url: $targetForm.attr('action'),
		data: $targetForm.serialize(),
		dataType: 'json',
		success: function(data)
		{
			ResultData.setData('kdg', data);
			getTemplate('kdg', 'search', 'allList', '', '');
		},
		error: function(xhr, status, error)
		{
			alert('통신 중 오류가 발생하였습니다.');
		},
		complete: function()
		{
			$('input[name=viewMode]').val('');
			$('input[name=numPerPage]').val('30');
		}
	});
}*/

//(kpat) 도면 일괄보기(image load)
function imageLoadMain(mode, btnObj)
{
	let $target;
	
	if (mode == 'hidden' && btnObj != undefined) {
		$target = $(btnObj).parents('.thumb-wrap');
	} else {
		$target = $('.thumb-wrap');
	}
	
	$target.each(function(i, t) {
		let loaded = $(this).data('loaded');
		
		if (isElementInViewport(this) && (loaded != 'Y' || mode == 'hidden')){
			let targetObj, count;
			
			if (mode == 'hidden') {
				targetObj = $(t).find('.sub-item-list.hidden');
				count = 5;
			} else {
				targetObj = $(t).find('.sub-item-list').not('.hidden');
				count = 0;
			}
			
			targetObj.each(function(idx, item) {
				applno = $(item).data('applno');
				imgPath = $(item).data('path');
				imgName = $(item).find('input[name=xmlImgFileName' + (count + idx) + ']').val();
				imgFullPath = imgPath + imgName;
				
				let parameters = 'applno=' + applno + '&imgFileList=' + imgFullPath + '&imgName=' + imgName;
				let imgObj = $(item).find('img');
			
				$.ajax({
			        url : '/kpat/AllImgList.do?method=thumImgDrawSingle',
			        type : 'post',
			        data : parameters,
			        async : false,
			        cache : true,
			        datatype: 'json',
			        success : function(data)
			        {
			        	var strArray=data[1].split('/'); // 실환경용
						//var strArray=data[1].split('\\'); // 로컬 테스트용
						$(imgObj).attr('src', '/kpat/remoteFile.do?method=tiffImageDraw&applno='+applno+'&fileNm='+strArray[strArray.length-1]);
			        },
			        error : function(request, status, error)
			        {
			        	alert('code::' + request.status + '\n' + 'message;' + request.responseText + '\n' + 'error:' + error);
			        }
				});
			});
			
			if (mode == 'hidden') {
				targetObj.removeClass('hidden');
				$(btnObj).parents('li').remove();
			}
			
			$(this).attr('data-loaded', 'Y');
		}
	});
}
// (kpat) 화면 변화 감지 (element가 화면상에 노출이 되어있는지 확인)
function isElementInViewport(el) 
{
    var rect = el.getBoundingClientRect();
    //alert(rect.top + "::" + rect.left + "::" + $(window).height() + "::" + $(window).width());
    return (rect.top >= 0 && rect.left >=0 && rect.top <= $(window).height() && rect.left <= $(window).width());
}
// (kpat) 화면 일괄보기 이미지 로드(초기 셋팅)
var waiting = false, endScrollHandle;  

// (kpat) 화면 일괄보기 이미지 로드(상시)
var imgLoadEvent = function(){   // 스크롤에 의한 부하를 줄이기 위한 지연시간
        if(waiting){ // waiting(전역) 중에는 이벤트 발생 금지
            return;
        }
        waiting = true; // 이벤트 발생 시 waiting (1000ms 안에는 연속적으로 발생 못 하도록)
        clearTimeout(endScrollHandle); // endScrollHandle을 clear
        imageLoadMain();
        
        setTimeout(function(){ // 1000ms Timeout 생성
            waiting = false;
        }, 1000);
        endScrollHandle = setTimeout(function(){ // 1000ms Timeout 생성 -- 이벤트 실행 중 다시 이벤트 발생
            imageLoadMain();
        }, 1000);
}
// (kpat) 도면 전체보기(html load)
function changeImage(applno, mode)
{
	//통계_상세정보 도면 전체보기
	recordServiceStats('KPAT', 'OPSVC', 'ALIMG');
	
	if (mode == 'newWindow'){
		getTemplate('kpat', 'detail', 'imagePop', 'openAllimgPop', window.opener.ImageData.getData('kpat'));
	} else {
		if ($('#mainResultDetailArea .sub-item-list').length == 0){
			toggleLoadingDialog('#mainResultDetail', true);
			$.ajax({
				url : '/kpat/AllImgList.do?method=allImgListInDetail',
				type : 'post',
				data : 'applno=' + applno,
				async : true,
				cache : true,
				datatype: 'json',
			    success : function(data)
			    {
			    	ImageData.setData('kpat', data);
		    		$('#detailBPArea').scrollTop(0);
				    getTemplate('kpat', 'detail', 'image', 'openAllimg', data);
				    //$('.main-item').hide();
			    },
			    error : function(request, status, error)
			    {
			    	alert('code::' + request.status + '\n' + 'message;' + request.responseText + '\n' + 'error:' + error);
			    }
			});
		} else {
			return 0;
		}
	}
}
//(kpat) 도면 전체보기(image load)
function imageLoad(mode, resizeYn)
{
	var applno = '';
	var imgName = '';
	var imgPath = '';
	var imgFullPath = '';
	/*var imgTl = '';
	var imgTle = '';*/
	var obj = '';
	var imgObj = '';
	
	if (mode == 'hidden'){
		obj = $('.bp-list .hidden').slice(0,5);
		var startIdx = $('.bp-list li').not('.hidden').length;
	} else {
		obj = $('.bp-list li').not('.hidden');
		var startIdx = 0;
	}
	
	$(obj).each(function(idx, item){
		$(this).removeClass('hidden');
		/*imgTl = $('.head-title .title').text();
		imgTle = $('.head-title .eng').text();*/
		applno = $('#applno').val();
		imgName = $('#xmlImgFileName_'+ (startIdx + idx)).val();
		imgPath = $('#imgFilePath_'+ (startIdx + idx)).val();
		imgFullPath = imgPath + imgName;
		
		if (resizeYn != undefined) {
			var parameters = 'applno=' + applno + '&imgFileList=' + imgFullPath + '&imgName=' + imgName + '&resizeYn=' + resizeYn;
		} else {
			var parameters = 'applno=' + applno + '&imgFileList=' + imgFullPath + '&imgName=' + imgName;
		}
		
		
		var imgObj = $(item).find('img');
		
		$.ajax({
            url : '/kpat/AllImgList.do?method=thumImgDrawSingle',
            type : 'post',
            data : parameters,
            async : true,
            cache : true,
            datatype: 'json',
            success : function(data)
            {
				var strArray=data[1].split('/'); // 실환경용
				//var strArray=data[1].split('\\'); // 로컬 테스트용
				$(imgObj).attr('src', '/kpat/remoteFile.do?method=tiffImageDraw&applno='+applno+'&fileNm='+strArray[strArray.length-1]);
            },
            error : function(request, status, error)
            {
            	alert('code::' + request.status + '\n' + 'message;' + request.responseText + '\n' + 'error:' + error);
            }
		});
	});
}

//(kpat) 공개, 공고 전문 이동
function goFullTextKpat(applno, pub_reg) {
	// 통계_전문조회
	if (pub_reg == 'P') {
		recordServiceStats('KPAT', 'BIBLO', 'PFLT');
	} else {
		recordServiceStats('KPAT', 'BIBLO', 'RFLT');
	}
	
	$('#pub_reg').val(pub_reg); // 공개/등록 구분값 셋팅
	
	var caseNo = '';
	if (pub_reg == 'P') {
		caseNo = $('#unexCaseNo').val(); // 공개 경우의수
	} else {
		caseNo = $('#exCaseNo').val();// 공고 경우의 수
	}
	
	if (caseNo == 4 || caseNo == 7) {
		searchCommonModule.toggleVisible('deu01', 'deu0102', false);
		goRefactory(applno);
	} else {
		searchCommonModule.toggleVisible('deu01', 'deu0102', true);
		if (caseNo == 3) {
			// 표준화공보 탭 비활성화, 체크 및 책자 호출 로직
			$('#report0101').prop('disabled', true);
			$('#report0102').prop('checked', true);
			goOrgFullText(applno);
		} else {
			// 표준화공보 호출 로직
			// SR000098790 : 원본공보를 디폴트로, 표준화공보를 선택사항으로 변경
			$('#report0101').prop('disabled', false);
			$('#report0101').prop('checked', true);
			goOrgFullText(applno);
		}
	}
};
// (kpat) 표준화공보 처리
function goRefactory(applno, download){
	var pub_reg = $('#pub_reg').val();//공개, 공고 전문 구별
	var viewerId = '';
	
	if (pub_reg == 'P') {
		viewerId = '#pdfViewer01';
	} else {
		viewerId = '#pdfViewer02';
	}
	var temp_applno = String(applno).substring(0,2);
	var flag = '';
	if (temp_applno == '10') {
		if (pub_reg == 'P') {
			flag = 'A';
		}
		else {
			flag = 'B1';
		}
	}
	else {
		if (pub_reg == 'P') {
			flag = 'U';
		}
		else {
			flag = 'Y1';
		}
	}
	//pdfViewer.init(viewerId, '/kpat/remoteFile.do?method=fullText&applno=' + applno + '&pub_reg=' + pub_reg, applno + ".pdf");
	fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'fullText', applno: applno, pub_reg: pub_reg}, applno + flag +".pdf", download);
	
}
// (kpat) 원본공보 처리
function goOrgFullText(applno){
	// 통계_전문조회
	recordServiceStats('KPAT', 'BIBLO', 'CPFLT');
	
	var pub_reg = $('#pub_reg').val();//공개, 공고 전문 구별
	var caseNo = '';//전문별 caseno
	var viewerId = '';
	var temp_applno = String(applno).substring(0,2);
	var flag = '';
	if (temp_applno == '10') {
		if (pub_reg == 'P') {
			flag = 'A';
		}
		else {
			flag = 'B1';
		}
	}
	else {
		if (pub_reg == 'P') {
			flag = 'U';
		}
		else {
			flag = 'Y1';
		}
	}
	switch(pub_reg){
		case 'P' :
			caseNo = $('#unexCaseNo').val();
			viewerId = '#pdfViewer01';
			if (caseNo == 2) {
				//pdfViewer.init('#pdfViewer01', '/kpat/remoteFile.do?method=fullText&applno=' + applno + '&pub_reg=' + pub_reg + '&fileKind=org', applno + ".pdf");
				fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'fullText', applno: applno, pub_reg: pub_reg, fileKind: 'org'}, applno + flag +".pdf");
			} else {
				//pdfViewer.init('#pdfViewer01', '/kpat/remoteFile.do?method=facsimile&applno=' + applno + '&pub_reg=' + pub_reg, applno + ".pdf");
				fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'facsimile', applno: applno, pub_reg: pub_reg}, applno + flag +".pdf");
			}
			break;
		case 'R' :
			caseNo = $('#exCaseNo').val();
			viewerId = '#pdfViewer02';
			if (caseNo == 2) {
				//pdfViewer.init('#pdfViewer02', '/kpat/remoteFile.do?method=fullText&applno=' + applno + '&pub_reg=' + pub_reg + '&fileKind=org', applno + ".pdf");
				fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'fullText', applno: applno, pub_reg: pub_reg, fileKind: 'org'}, applno + flag +".pdf");
			} else {
				//pdfViewer.init('#pdfViewer02', '/kpat/remoteFile.do?method=facsimile&applno=' + applno + '&pub_reg=' + pub_reg, applno + ".pdf");
				fullTextAjax(viewerId, '/kpat/fullText.do', {method: 'facsimile', applno: applno, pub_reg: pub_reg}, applno + flag +".pdf");
			}
			break;
	}
}

//(kpa)등록사항 등록료 조회
function goRgstFeeInfo(rgstno, btnObj)
{
	toggleLoadingDialog('#mainResultDetail div.body', true);
	
	let targetTabId = $(btnObj).data('tab-id');
	
	$.ajax({
		async: true,
		type: 'POST',
		url: '/kpa/rgin1000a.do',
		data: {rgstno: rgstno, lang: 'eng'},
		dataType: 'html',
		success: function(data)
		{
			$('#mainResultDetailArea').find('div[data-tab-id=' + targetTabId + ']').html(data);
		},
		error: function(xhr, status, error)
		{
			alert('통신 중 오류가 발생하였습니다.');
			
		},
		complete: function() {
			toggleLoadingDialog(loadingDialogTarget, false);
		}
	});
}
//OPD 심사정보 링크
function showOPD(gubun, cntry, key)
{
	// 통계_행정진행정보
	recordServiceStats(currentTab2, 'BIBLO', 'LGST');
    // gubun : A - 전체 조회, U - 국가별 조회
	let openUrl = '';
	// 문헌코드 : (국내)A - 특허, U - 실용신안
	let code = '';
	if (cntry == 'WO') {
		openUrl = 'https://patentscope.wipo.int/search/en/detail.jsf?docId=' + key + '#detailMainForm:MyTabViewId:PCTDOCUMENTS';
	} else if (gubun == 'A') {
		if (cntry !='KR') {
			let parts = key.split('.');
			cntry = parts[0];
			key = parts[1];
			code = parts[2];
			openUrl = 'https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=' + cntry + '&appno=' + key + '&code=' + code + '&docgrp=ALL&from=K';
		}
		else{
			if(key.slice(0,2) == '10') {
				code = 'A';
			}
			else {
				code = 'U';
			}
			key = key.slice(2);
			openUrl = 'https://kopd.kipo.go.kr:8888/viewFamilySearchResult.do?paramType=A&cntry=' + cntry + '&appno=' + key + '&code=' + code + '&docgrp=ALL&from=K';
		}
    	
    } else if (gubun == 'U') {
    	openUrl = 'https://kopd.kipo.go.kr:8888/docContent/openDocContentPopupOne.do?docdbnum=' + key;
    } else {
        alert ('관리자에게 연락 바랍니다.');
        return false;
    }
    
    window.open(openUrl, '_blank', 'width=' + screen.width + ', height=' + screen.height + ', menubar=no, toolbar=no, location=no, status=no, fullscreen=yes');
}
//(kdg) 상세정보 선택에 따른 도면보여주기
function openKdgImgList(){
	$('#optionImgTxt').html($('#bpSelect').val());
	$('#bpSelect option').each(function(){
		if($(this).prop('selected')){
			$('#optionImg'+$(this).val()).css('display','block');
		}else{
			$('#optionImg'+$(this).val()).css('display','none');
		}
	});
}
//(abdg) 상세정보 선택에 따른 도면보여주기
function openAbdgImgList(){
	$('#optionImgAbdgTxt').text('['+$('#bpSelectAbdg').val()+']');
	$('#bpSelectAbdg option').each(function(){
		if($(this).prop('selected')){
			$('#optionAbdgImg'+$(this).val()).css('display','block');
		}else{
			$('#optionAbdgImg'+$(this).val()).css('display','none');
		}
	});
}
//DOI 복사
function copyUrl(right, applno, ds_seq, intnl_rgstno){
	recordServiceStats(right, 'OPSVC', 'OPDOI');
	var baseURL = "https://doi.org/10.8080/";
	var URL = "";
	if (right == "KTM" || right == "KPAT") {
		URL = baseURL + applno;
	} else {
		if (intnl_rgstno == "") {
			URL = baseURL + applno + "." + ds_seq;
		} else {
			// 국제디자인일 경우
			URL = baseURL + intnl_rgstno + "." + ds_seq;
		}
	}
	core.copyToClipboard(URL);
}

// 지정상품 보기 토글 버튼 (true: 보기, false: 닫기)
function toggleGoodsList(flag) {
	if (flag) {
		$('#goodsList').find('tr.hidden').removeClass('hidden');
	} else {
		$.each($('#goodsList tbody tr'), function(idx, item) {
			if (idx >= 30) {
				$(item).addClass('hidden');
			}
		});
	}
}

// 상세보기 인쇄
function printDetail()
{
	let $activeDiv = $('#mainResultDetailArea').find('.detail-tab-body .tab-con.active');
	if ($activeDiv.hasClass('pdf-container')) {
		let viewerWindow = $activeDiv.find('iframe')[0].contentWindow;
		viewerWindow.PDFViewerApplication.triggerPrinting();
	} else {
		//통계_상세정보 전체 인쇄하기
		recordServiceStats(currentTab2, 'OPSVC', 'ALPRT');
		openWindow('printDetail', {target: 'printDetail', right: currentTab2});
	}
}

// 거절정보제공 실명제공 및 익명제공
function doProvideRefusal(mode, tpcd, applno)
{
	/*
	[거절정보제공 버튼 생성] 20210331 J
	- 특허실용신안 및 디자인의 공개공고, 상표의 서지정보 및 출원공고 내 '거절정보제공' 서비스 연계
	(공개 또는 공고되어 제3자가 정보제공할 수 있는 상태에 놓인 건만 서비스 제공)
	정보시스템과 전자출원,수수료 담당 이동욱B 주무관 요청			
	 */
	if (mode == 'init') {
		//통계_거절정보제공(전문) 버튼
		if(currentTab2 == 'kpat' || currentTab2 == 'kdg'){	// 상표는 서지정보, 출원공고 view에서 호출
			recordServiceStats(currentTab2, 'OPSVC', 'PRINF');
		}
		$('#modalProvideRefusal').find('input[name=applno]').val(applno);
		$('#modalProvideRefusal').find('input[name=tpcd]').val(tpcd);
		modal.open('#modalProvideRefusal');
	} else if (mode == 'silmyeong') {
		//통계_거절정보제공 실명
		recordServiceStats(currentTab2, 'OPSVC', 'SIOFR');
		let silmyeongHref = '';
		let tempApplno = $('#modalProvideRefusal').find('input[name=applno]').val();
		let tempApplnoSub = tempApplno.substring(0, 2);
		
		if (tempApplnoSub == '10') { // 마드리드건 출원번호때문에 TPCD 추가
			silmyeongHref = "https://www.patent.go.kr/smart/kiponet3/apl/sg/ap/renew/main/DrawApplication.do?frmCd=103050&rgTp=10";
		} else if (tempApplnoSub == '20') {
			silmyeongHref = "https://www.patent.go.kr/smart/kiponet3/apl/sg/ap/renew/main/DrawApplication.do?frmCd=203050&rgTp=20";
		} else if (tempApplnoSub == '30') {
			silmyeongHref = "https://www.patent.go.kr/smart/kiponet3/apl/sg/ap/renew/main/DrawApplication.do?frmCd=303050&rgTp=30";
		} else {
			silmyeongHref = "https://www.patent.go.kr/smart/kiponet3/apl/sg/ap/renew/main/DrawApplication.do?frmCd=403020&rgTp=40";
		}
		
		window.open(silmyeongHref, '_blank');
	} else if (mode == 'ikmyeong') {
		//통계_거절정보제공 익명
		recordServiceStats(currentTab2, 'OPSVC', 'IKOFR');
		let ikmyeongHref = '';
		let tempApplno = $('#modalProvideRefusal').find('input[name=applno]').val();
		let tempTpcd = $('#modalProvideRefusal').find('input[name=tpcd]').val();
		
		if (tempTpcd == '1') {
			ikmyeongHref ='https://www.patent.go.kr/smart/jsp/kiponet/mp/sbmtinfo/SbmtInfoAnomsForm.do?madridNo=' + tempApplno;		
		} else {
			ikmyeongHref ='https://www.patent.go.kr/smart/jsp/kiponet/mp/sbmtinfo/SbmtInfoAnomsForm.do?applNo=' + tempApplno;
		}
		
		window.open(ikmyeongHref, '_blank');
	}
}

// 데이터 오류 신고
function sendErrorReport(key)
{	
	//통계_거절정보제공 익명
	recordServiceStats(currentTab2, 'OPSVC', 'OCV');
	
	let $form = $('<form>', {method: 'post', target: '_blank', action: '/khome/board/voc/regist.do'});
	$form.append($('<input>', {type: 'hidden', name: 'key', value: key}));
	$('body').append($form);
	$form.submit();
}

// (국내상표)지정상품 전체보기
function doExpandDesignatedGoods(mode)
{
	// 상세보기 지정상품 표, 이벤트 제외하고 가져오기
	if (mode == 'origin') {
		$('#totalGoodsList').html($('#goodsList')[0].outerHTML);
	} else {
		$('#totalGoodsList').html($('#goodsListSub')[0].outerHTML);
	}
	
	// 모달 오픈
	modal.open('#modalProduct');
}

// (국내상표)지정상품 더보기 토글 버튼 
function toggleExpandGoodsList(element) {
	let $el = $(element);
	let tempText = $el.text().substring(1);
	
	if ($el.attr('aria-expanded') == 'true') {
		$el.text('▽' + tempText);
	} else {
		$el.text('△' + tempText);
	}
}

// (국내상표)마드리드 상표 거절결정서에 대한 국제사무국 전송정보 확인
function openWipoSendInfo(docNum, sendDt) {
	$('#rejDocNum').text(docNum);
	$('#wipoSendDt').text(sendDt);
	modal.open('#modalWipoSendInfo');
}

//(국내상표)25.10.30 지정상품 명칭 및 유사군코드 일부 변경 알림 팝업 띄우기
function openModalSimilarCodeNotice() {
	modal.open('#modalSimilarCodeNotice');
}

function moreFamilyList(applno, mode, cnt) {
	let perPage = 30;
	let currentPage = mode == 'OPFAMILY' ? parseInt($('#opFamilyPage').val()) : parseInt($('#docFamilyPage').val());
	let nextPage = currentPage + 1;
	let totalPage = (parseInt(cnt) % perPage) == 0 ? Math.floor(parseInt(cnt) / perPage) : Math.floor(parseInt(cnt) / perPage) + 1;
	let reqUrl = '';
	if(currentTab2 == 'abpatTrans') {
		reqUrl = '/abpat/biblioDynapatha.do';
	} else {
		reqUrl = '/' + currentTab2 + '/biblioDynapatha.do';
	}
	let params = 'method=biblioMain_Family&applno=' + applno + '&page=' + nextPage + '&mode=' + mode + '&per=' + perPage;
	
	var opOption = {
			async: false,
			type: 'POST',
			url: reqUrl,
			data: params,
			dataType: 'json',
			success: function(data)
			{
				let tbody = $('#opFamilyTable');
				let count = ((currentPage) * 30) + 1;
				let listSource = ``;
				if(currentTab2 == 'kpat') {
					listSource = `<tr>
						<td><em class="th" data-lang-id="dtvw.patent.ordrno">순번</em>{{index}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.fno">패밀리번호</em>
						{{#iif fmly_cntry_cd 'KR' '=='}}
							<a href="#" onclick="openWindow('detail', {applno:'{{applno}}', right:'{{toRight fmly_cntry_cd}}'}); return false;" class="btn-blank" title="새 창, 상세정보" data-lang-id="title.newwin" data-lang-type="title">
								{{fmly_pubno_epo}}
							</a>
						{{else}}
							{{#iif 'Y' fmly_link_yn '=='}}
								<a href="#" onclick="openWindow('detail', {applno:'{{toFormatKeyV2 ltrtno}}', right:'{{toRight fmly_cntry_cd}}'}); return false;" class="btn-blank" title="새 창, 상세정보" data-lang-id="title.newwin" data-lang-type="title">
									{{fmly_pubno_epo}}
								</a>
							{{else}}
								{{fmly_pubno_epo}}
							{{/iif}}
						{{/iif}}
						{{#isChkIp5 fmly_cntry_cd appl_dt}}
							{{#iif '\S' docdbnum}}
								<a href="#" onclick="showOPD('U', '{{fmly_cntry_cd}}', '{{docdbnum}}'); return false;" class="btn-blank" title="새 창, OPD 심사정보" target="_blank" data-lang-id="title.opopd" data-lang-type="title"><span data-lang-id="dtvw.patent.ei">심사정보</span></a>
							{{/iif}}
						{{/isChkIp5}}
						</td>
						<td><em class="th" data-lang-id="dtvw.patent.adt">출원일자</em>{{toDateFormat appl_dt}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.cntrc">국가코드</em>{{fmly_cntry_cd}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.cntr2">국가명</em>{{nationNameKor}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.tp">종류</em>{{pat_tpcd}}</td>
					</tr>`;
				} else {
					listSource = `<tr>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.num">순번</em>{{index}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.fn">패밀리번호</em>
						{{#iif 'KR' tbkind '=='}}
							<a href="#" onclick="openWindow('detail', {applno:'{{fmly_applno}}', right:'kpat'}); return false;" title="새 창, 상세정보" class="btn-blank">{{fmly_pubno_epo}}</a>
							{{#if docdbnum}}
								<a href="#" data-lang-id="dtvw.{{lang}}.ei" onclick="showOPD('U', '{{fmly_cntry_cd}}', '{{docdbnum}}'); return false;" class="btn-blank" title="새 창, OPD 심사정보" data-lang-id="title.opopd" data-lang-type="title"><span data-lang-id="dtvw.patent.ei">심사정보</span></a>
							{{/if}}
						{{else}}
							{{#iif 'Y' fmly_link_yn '=='}}
								<a href="#" onclick="openWindow('detail', {applno:'{{publ_key_link}}', right:'abpat'}); return false;" title="새 창, 상세정보" class="btn-blank">{{fmly_pubno_epo}}</a>
							{{else}}
								{{fmly_pubno_epo}}
							{{/iif}}
							{{#isShowOpd fmly_cntry_cd fmly_appl_dt}}
								{{#if docdbnum}}
									<a href="#" data-lang-id="dtvw.{{lang}}.ei" onclick="showOPD('U', '{{fmly_cntry_cd}}', '{{docdbnum}}'); return false;" class="btn-blank" title="새 창, OPD 심사정보" data-lang-id="title.opopd" data-lang-type="title"><span data-lang-id="dtvw.patent.ei">심사정보</span></a>
								{{/if}}
							{{/isShowOpd}}
						{{/iif}}
						</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.adt">출원일자</em>{{toDateFormat fmly_appl_dt}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.cc">국가코드</em>{{fmly_cntry_cd}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.ct">국가명</em>{{nationNameKor}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.tp">종류</em>{{pat_tpcd}}</td>
					</tr>`;
				}
						
				let listTemplate = Handlebars.compile(listSource);
				
				$('#moreOpFamilyList').remove();
				
				data.forEach(function(item){
					let listVar = {};
					if(currentTab2 == 'kpat') {
						listVar = {
							index: count++,
							fmly_cntry_cd: item.fmly_cntry_cd,
							applno: item.applno,
							fmly_pubno_epo: item.fmly_pubno_epo,
							fmly_link_yn: item.fmly_link_yn,
							ltrtno: item.ltrtno,
							appl_dt: item.appl_dt,
							docdbnum: item.docdbnum,
							nationNameKor: item.nationNameKor,
							pat_tpcd: item.pat_tpcd
						};
					} else {
						listVar = {
							index: count++,
							tbkind: item.tbkind,
							fmly_applno: item.fmly_applno,
							fmly_pubno_epo: item.fmly_pubno_epo,
							docdbnum: item.docdbnum,
							fmly_cntry_cd: item.fmly_cntry_cd,
							fmly_link_yn: item.fmly_link_yn,
							publ_key_link: item.publ_key_link,
							fmly_appl_dt: item.fmly_appl_dt,
							nationNameKor: item.nationNameKor,
							pat_tpcd: item.pat_tpcd	
						};
						if(currentTab2 == 'abpat') {
							listVar["lang"] = "abpat";
						} else {
							listVar["lang"] = "abpatKr";
						}
					}
					let tempHtml = listTemplate(listVar);
					$('#opFamilyTable').append(tempHtml);
				});
				
				if(nextPage < totalPage) {
					let moreSource = `<tr id="moreOpFamilyList">
						<input type="hidden" id="opFamilyPage" value="{{nextPage}}"></input>  
						<td colspan="6" style="padding-bottom:5px; padding-top:5px; background-color:#EDF1F5;">
							<button class="badge" style="width:100%; padding:0;" onclick="moreFamilyList('{{applno}}', '{{mode}}', '{{opFamilyCnt}}')">
								<span data-lang-id="dtvw.patent.fpmore">더보기</span>({{nextPage}}/{{#familyListPage opFamilyCnt}}{{/familyListPage}})
							</button>
						</td>
					</tr>`;
					let moreTemplate = Handlebars.compile(moreSource);
					let tempHtml = moreTemplate({
							nextPage: nextPage,
							applno: applno,
							mode: mode,
							opFamilyCnt: cnt	
						});
					
					$('#opFamilyTable').append(tempHtml);
				}
			},
			error: function(xhr, status, error)
			{
				toggleLoadingDialog(loadingDialogTarget, false);
			},
			complete: function() {
				toggleLoadingDialog(loadingDialogTarget, false);
			}	
	};
	
	var docOption =  {
			async: false,
			type: 'POST',
			url: reqUrl,
			data: params,
			dataType: 'json',
			success: function(data)
			{
				let tbody = $('#docFamilyTable');
				let count = ((currentPage) * 30) + 1;
				let listSource = ``;
				if(currentTab2 == 'kpat') {
					listSource = `<tr>
						<td><em class="th" data-lang-id="dtvw.patent.ordrno">순번</em>{{index}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.fno">패밀리번호</em>
						{{#iif 'Y' fmly_link_yn '=='}}
							{{#iif fmly_cntry_cd 'KR' '=='}}
								<a href="#" onclick="openWindow('detail', {applno:'{{applno}}', right:'{{toRight fmly_cntry_cd}}'}); return false;" class="btn-blank" title="새 창, 상세정보" data-lang-id="title.newwin" data-lang-type="title">
									{{fmly_pubno_epo}}
								</a>
							{{else}}
								<a href="#" onclick="openWindow('detail', {applno:'{{toFormatKeyV2 ltrtno}}', right:'{{toRight fmly_cntry_cd}}'}); return false;" class="btn-blank" title="새 창, 상세정보" data-lang-id="title.newwin" data-lang-type="title">
									{{fmly_pubno_epo}}
								</a>
							{{/iif}}
						{{else}}
							{{fmly_pubno_epo}}
						{{/iif}}
						</td>
						<td><em class="th" data-lang-id="dtvw.patent.adt">출원일자</em>{{toDateFormat appl_dt}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.cntrc">국가코드</em>{{fmly_cntry_cd}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.cntr2">국가명</em>{{nationNameKor}}</td>
						<td><em class="th" data-lang-id="dtvw.patent.tp">종류</em>{{pat_tpcd}}</td>
					</tr>`;
				} else {
					listSource = `<tr>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.num">순번</em>{{index}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.fn">패밀리번호</em>
						{{#iif 'Y' fmly_link_yn '=='}}
							{{#iif 'KR' fmly_cntry_cd}}
								<a href="#" onclick="openWindow('detail', {applno:'{{fmly_docdb_kr_applno}}', right:'kpat'}); return false;" class="btn-blank">{{fmly_pubno_epo}}</a>
							{{else}}
								<a href="#" onclick="openWindow('detail', {applno:'{{publ_key_link}}', right:'abpat'}); return false;" class="btn-blank">{{fmly_pubno_epo}}</a>
							{{/iif}}
						{{else}}
							{{fmly_pubno_epo}}
						{{/iif}}
						</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.adt">출원일자</em>{{toDateFormat fmly_appl_dt}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.cc">국가코드</em>{{fmly_cntry_cd}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.ct">국가명</em>{{nationNameKor}}</td>
						<td><em class="th" data-lang-id="dtvw.{{lang}}.tp">종류</em>{{pat_tpcd}}</td>
					</tr>`;
				}
				let listTemplate = Handlebars.compile(listSource);
				
				$('#moreDocFamilyList').remove();
				
				data.forEach(function(item){
					let listVar = {};
					if(currentTab2 == 'kpat') {
						listVar = {
							index: count++,
							fmly_link_yn: item.fmly_link_yn,
							fmly_cntry_cd: item.fmly_cntry_cd,
							applno: item.applno, 
							fmly_pubno_epo: item.fmly_pubno_epo,
							ltrtno: item.ltrtno,
							appl_dt: item.appl_dt,
							nationNameKor: item.nationNameKor,
							pat_tpcd: item.pat_tpcd
						};
					} else {
						listVar = {
							index: count++,
							fmly_link_yn: item.fmly_link_yn,
							fmly_cntry_cd: item.fmly_cntry_cd,
							fmly_docdb_kr_applno: item.fmly_docdb_kr_applno,
							fmly_pubno_epo: item.fmly_pubno_epo,
							publ_key_link: item.publ_key_link,
							fmly_appl_dt: item.fmly_appl_dt,
							nationNameKor: item.nationNameKor,
							pat_tpcd: item.pat_tpcd	
						};
						if(currentTab2 == 'abpat'){
							listVar["lang"] = "abpat";
						} else {
							listVar["lang"] = "abpatKr";
						}
					}
				
					let tempHtml = listTemplate(listVar);
					$('#docFamilyTable').append(tempHtml);
				});
				
				if(nextPage < totalPage) {
					let moreSource = `<tr id="moreDocFamilyList">
						<input type="hidden" id="docFamilyPage" value="{{nextPage}}"></input>
						<td colspan="6" style="padding-bottom:5px; padding-top:5px; background-color:#EDF1F5;">
							<button class="badge" style="width:100%; padding:0;" onclick="moreFamilyList('{{applno}}', '{{mode}}', '{{docFamilyCnt}}')">
								<span data-lang-id="dtvw.patent.fpmore">더보기</span>({{nextPage}}/{{#familyListPage docFamilyCnt}}{{/familyListPage}})
							</button>
						</td>
					</tr>`;
					let moreTemplate = Handlebars.compile(moreSource);
					let tempHtml = moreTemplate({
							nextPage: nextPage,
							applno: applno,
							mode: mode,
							docFamilyCnt: cnt	
						});
					$('#docFamilyTable').append(tempHtml);
				}
			},
			error: function(xhr, status, error)
			{
				toggleLoadingDialog(loadingDialogTarget, false);
			},
			complete: function() {
				toggleLoadingDialog(loadingDialogTarget, false);
			}	
	};
	
	var option = mode == 'OPFAMILY' ? opOption : docOption;
	ajaxResult = typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);
}
						
let fullTextSwiper = null;				
function swiperFullTextImg(response, cntry, viewerId) {
	let list = response.imgList;
	let multi = response.isMultiTiff;
	let totalSlides = list.length;
	let virtualSlidesData = Array.from({ length: totalSlides });
	let targetId = '#swiper-' + viewerId.slice(viewerId.indexOf('#') + 1);
	let pageInput = $(targetId + '-page-input');
    let jumpButton = $(targetId + '-jump-button');
    let totalPages = $(targetId + '-total-pages');
    
	// Swiper 초기화
    if (fullTextSwiper) {	
    	fullTextSwiper.destroy();
    	fullTextSwiper = null;
    	$(targetId).find('.swiper-wrapper').html('');
    	jumpButton.off('click');
        pageInput.off('keydown');
    	pageInput.val(1);
    }
    
	// EP 책자공보 임시 블라인드
    if (list[0] == 'EP') {	
    	return;
    }
    
    // 총 페이지 수 ,input max 설정
    totalPages.text(totalSlides);
    pageInput.attr('max', totalSlides);
    
    // Swiper 설정
    fullTextSwiper = new Swiper(targetId, {
      virtual: {
        slides: virtualSlidesData,
        renderSlide: function(slideData, index) {
          return `
            <div class="swiper-slide" data-slide-index="${index}">
              <img src="" class="swiper-lazy">
              <div class="swiper-lazy-preloader"></div>
            </div>
          `;
        }
      },
      slidesPerView: 1,
      slidesPerGroup: 1,
      addSlidesBefore: 2,
      addSlidesAfter: 2,
      navigation: {
        nextEl: ".swiper-detail-next",
        prevEl: ".swiper-detail-prev",
      },
      keyboard: { enabled: true },
      touchReleaseOnEdges: true,
      on: {
    	  slideChange: function(swiper) {
    		  generateImgFullText('/abpat/fulltexta.do', {method: 'generateImgFullText', cntry: cntry, imgPath: list[swiper.activeIndex], multi: multi, idx: swiper.activeIndex}, targetId);
    		  pageInput.val(swiper.activeIndex + 1);
    	  },
    	  afterInit: function(swiper) {
    		  setTimeout(() => {
    			  generateImgFullText('/abpat/fulltexta.do', {method: 'generateImgFullText', cntry: cntry, imgPath: list[swiper.activeIndex], multi: multi, idx: swiper.activeIndex}, targetId);
    		  }, 0);
    	  }
      }
    });

    function swiperGoToSlide() {
        let pageNumber = parseInt(pageInput.val(), 10);
        if (isNaN(pageNumber) || pageNumber < 1 || pageNumber > totalSlides) {
			alert(`1부터 ${totalSlides} 사이의 숫자를 입력해주세요.`);
			pageInput.val('');
			pageInput.focus();
			return;
        }
        fullTextSwiper.slideTo(pageNumber - 1);
    }
    
    // 페이지 이동(enter, 버튼) 
    jumpButton.on('click', swiperGoToSlide);
    pageInput.on('keydown', (event) => {
      if (event.key === 'Enter') {
    	  swiperGoToSlide();
      }
    });
}

// Swiper 이미지 조회
function generateImgFullText(url, parameterData, targetId) {
	var option = {
			url: url,
			type: 'POST',
			data: parameterData,
			xhrFields: {responseType: 'blob'},
			success: function(data, textStatus, jqXHR) {
				let contentType = jqXHR.getResponseHeader('Content-Type');
				let blob = new Blob([data], {type: contentType});
				let imgUrl = URL.createObjectURL(blob);
				if (targetId == 'download') {
					let link = document.createElement('a');
					contentType = contentType.split(';')[0];
					let filename = parameterData.publ_key + '.' + contentType.substring(contentType.lastIndexOf('/') + 1);;
					let disposition = jqXHR.getResponseHeader('Content-Disposition');
					if (disposition && disposition.indexOf('attachment') !== -1) {
					    let filenameMatch = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
					    if (filenameMatch != null && filenameMatch[1]) {
					        filename = filenameMatch[1].replace(/['"]/g, '');
					    }
					}
					link.href = imgUrl;
					link.download = filename;
					link.click();
					$(link).remove();
					// 파일다운로드 관련 GTM 이벤트 호출 추가
					callDownloadTagEvent(filename);
				} else {
					let targetSlide = $(targetId).find('.swiper-slide-active img');
					targetSlide.attr('src', imgUrl);
				}
			},
			error: function(jqXHR, textStatus, errorThrown) {
				console.error('Error : ', textStatus, errorThrown);
			},
			complete: function() {
				toggleLoadingDialog('#mainResultDetail div.body', false);
			}
	};
	dpCnf.ctx = url.substring(0, url.indexOf('/', 1));
	typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);
}

// 이미지전문 list 조회
function imgFullTextAjax(viewerId, url, parameterData) {
	toggleLoadingDialog('#mainResultDetail div.body', true);
	if (parameterData.download == 'Y') {
		generateImgFullText(url, parameterData, 'download');
	} else {
		toggleLoadingDialog('#mainResultDetail div.body', true);
		var option = {
				url: url,
				type: 'POST',
				data: parameterData,
				success: function(response) {
					swiperFullTextImg(response, parameterData.cntry, viewerId);
				},
				error: function(jqXHR, textStatus, errorThrown) {
					console.error('Error : ', textStatus, errorThrown);
				},
				complete: function() {
					toggleLoadingDialog('#mainResultDetail div.body', false);
				}
		};
		dpCnf.ctx = url.substring(0, url.indexOf('/', 1));
		typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);
	}
}

// KPA, 요약 선택보기 위한 함수
function showContent(contentType) {
    const kpaContent = document.getElementById('kpa-content');
    const summaryContent = document.getElementById('summary-content');
    const tabButtons = document.querySelectorAll('.tab-section-02 .title-box');

    if (contentType === 'kpa') {
        kpaContent.style.display = 'block'; // KPA 보이기
        summaryContent.style.display = 'none'; // 요약  숨기기
    } else if (contentType === 'summary') {
        kpaContent.style.display = 'none'; // KPA 숨기기
        summaryContent.style.display = 'block'; // 요약  보이기
    }

    tabButtons.forEach(button => {
    	const h5element = button.querySelector('h5');
        const buttonAction = button.getAttribute('onclick');
        if (buttonAction && buttonAction.includes("'" + contentType + "'")) {
        	h5element.classList.add('active-abs');
        } else {
        	h5element.classList.remove('active-abs'); 
        }
    });
}

function checkInfoBox(viewerId) {
	const $viewerId = $('div[data-tab-id=' + viewerId + ']');
	if (sessionStorage.getItem("pdfInfoClosed") === "true") {
		if ($viewerId.find('.info-box').length !== 0) {
			$viewerId.find('.info-box').remove();
		}
    } else {
    	if ($viewerId.find('.info-box').length === 0) {
            const boxHtml = $('#infoBoxTemplate').html();
            $viewerId.prepend(boxHtml); // 상단에 삽입
        }
    }
}

function closeInfoBox() {
	$('.pdf-container.active .info-box').slideUp(400, function() {
        $(this).remove();
    });
	sessionStorage.setItem("pdfInfoClosed", "true");
}

function openVisualize(applno, btn) {

	recordServiceStats('KPAT', 'BIBLO', 'PTVW');
	
	const modalElement = document.querySelector('#modalVisualize');

	const observer = new MutationObserver((mutations) => {
		mutations.forEach((mutation) => {
			if (mutation.attributeName === 'aria-hidden') {
				const isHidden = modalElement.getAttribute('aria-hidden') === 'true';

				if (isHidden) {
					//console.log('modal--close--event');
					closeVisualModal();
					observer.disconnect();
				}
			}
		});
	});

	observer.observe(modalElement, { attributes: true });

	modal.open('#modalVisualize', document.querySelector('#visualize_btn'));

	var reqUrl = '/kpat/biblioDynapatha.do';
	var params = 'method=biblioMain_biblio&getType=visualize&applno=' + applno;
	var option = {
		async: false,
		type: 'POST',
		url: reqUrl,
		data: params,
		dataType: 'json',
		success: function(data)
		{
			//console.log(data);
			renderTimelineTotal(data);
		},
		error: function(xhr, status, error)
		{
			toggleLoadingDialog(loadingDialogTarget, false);
		}
	};

	dpCnf.ctx = '/kpat';
    let ajaxResult = typeof dp !== 'undefined' ? dp.$.ajax($, option) : $.ajax(option);
}

//파일다운로드 관련 GTM 이벤트 호출 추가
function callDownloadTagEvent(fileName) {
	window.dataLayer = window.dataLayer || [];
	window.dataLayer.push({
		event: 'kipris_file_download',
		downName: fileName
	});
}