




function setDocListBiblio(docdbNum, area_id) {
	$.ajax({
		url: '/kipi/getDocList2.do',
		type: 'POST',
		data:{
			docdbNum : docdbNum
		},
		beforeSend:function(x) {
			$('#' + area_id).html('<div style="width:100%;text-align:center;"><br /><img src="/images/ico_loading.gif" /></div>');
		},
		cache:false,
		
		success:function(result) {
			
			if(result.result == 'success') {
				var html = '<div class="title1">' + getFlag(docdbNum) + docdbNum + '</div>';
				html += 	'<div>';
				html += 		'<table class="tb02" cellspacing="1" style="background-color:white;">';
				html += 			'<colgroup>';
				html += 				'<col style="width:15%;"/>';
				html += 				'<col style="width:85%;"/>';
				html += 			'</colgroup>';
				html += 			'<tbody>';
				html += 				'<tr>';
				html += 					'<th>발명의 명칭</th>';
				html += 					'<td align="center">'+(result.inventTitle == null ? '' : result.inventTitle)+'</td>';
				html += 				'</tr>';
				html += 				'<tr>';
				html += 					'<th>출원인</th>';
				html += 					'<td align="center">'+(result.applicant == null ? '' : result.applicant)+'</td>';
				html += 				'</tr>';
				html += 			'</tbody>';
				html += 		'</table>';
				html += 	'</div>';
				$('#' + area_id).html(html);
				
				//setDocListContent(docdbNum, area_id);
			} else {
				$('#' + area_id).html(result.result);
			}
		},
		error:function(xhr, status, error) {
			alert('setDocListBiblio error');
		}
	});
}

function setDocListContent(docdbNum, area_id) {
	$.ajax({
		url: '/kipi/getDocList2.do',
		type: 'POST',
		data:{
			docdbNum : docdbNum
		},
		beforeSend:function(x) {
			$('#' + area_id).html('<div style="width:100%;text-align:center;"><br /><img src="/images/ico_loading.gif" /></div>');
		},
		cache:false,
		
		success:function(result) {
			
			if(result.result == 'success') {
				//일반적인 리스트, 다운로드를 위한 상세화면, 2개의 PDF 비교화면 모두 공유
				var listType = 'normal';
				if(area_id.indexOf('Detail') > 0) {
					listType = 'detail';
				} else if(area_id.indexOf('2pdf') > 0) {
					listType = '2pdf';
				}
				
				var newTotal = 0;
				
				var html = '';
				//html += 	'<div id="' + area_id + '_list" class="table_wrap02">';
				html += 	'<div style="padding-top:7px;">';
				html += 		'<table class="tb02" style="background-color:white;" cellSpacing="0">';
				
				if(listType == 'detail') {
					
					html += 			'<colgroup>';
					html += 				'<col style="width:10%;" />';
					html += 				'<col style="width:40%;" />';
					html += 				'<col style="width:30%;" />';
					html += 				'<col style="width:20%;" />';
					html += 			'</colgroup>';
					html += 			'<thead>';
					html += 				'<tr>';
					html += 					'<th>제출일</th>';
					html += 					'<th>문서</th>';
					html += 					'<th>문서그룹</th>';
					html += 					'<th>문서 <input type="checkbox" onclick="javascript:checkAll(this);" /> <a class="btn_style01" href="javascript:download();"><span>다운로드</span></a></th>';
					html += 				'</tr>';
					html += 			'</thead>';
					
				} else if(listType == '2pdf') {
					
					html += 			'<colgroup>';
					html += 				'<col style="width:15%;" />';
					html += 				'<col style="width:43%;" />';
					html += 				'<col style="width:16%;" />';
					html += 				'<col style="width:16%;" />';
					html += 			'</colgroup>';
					html += 			'<thead>';
					html += 				'<tr>';
					html += 					'<th>제출일</th>';
					html += 					'<th>문서</th>';
					html += 					'<th>문서보기(좌)</th>';
					html += 					'<th>문서보기(우)</th>';
					html += 				'</tr>';
					html += 			'</thead>';
					
					
				} else {
					
					html += 			'<colgroup>';
					html += 				'<col style="width:23%;" />';
					html += 				'<col style="width:53%;" />';
					html += 				'<col style="width:24%;" />';
					html += 			'</colgroup>';
					html += 			'<thead>';
					html += 				'<tr>';
					html += 					'<th>제출일</th>';
					html += 					'<th>문서</th>';
					html += 					'<th>문서보기</th>';
					html += 				'</tr>';
					html += 			'</thead>';
				}
				html += 			'<tbody>';
				
				
				for(var i = 0; i < result.doclist.length; i++) {
					
					//강조표시
					var bgColor = '';
					if(result.doclist[i].highlight == 'L') {
						bgColor = 'bgc_blue';
					} else if(result.doclist[i].highlight == 'B') {
						bgColor = 'bgc_pink';
					} else if(result.doclist[i].highlight == 'Y') {
						bgColor = 'bgc_yellow';
					} else {
						bgColor = 'bgc_else';
					}
					html += '<tr class="' + bgColor + ' colorFilter">';
					
					//제출일
					html += '<td class="txa_c txt_gray dateFilter">' + result.doclist[i].rs_dt + '</td>';

					html += '<td class="txa_l">';
					
					//심판아이콘
					if(result.doclist[i].trlno != null && result.doclist[i].trlno == 'Y') {
						html += '<img src="/images/icon_judge.png" complete="complete"/>';
					}
					
					//문서명
					var docName = '';
					var isWipo = new RegExp('W$');
					
					if(docdbNum.substring(0,2) == 'KR' && !isWipo.test(docdbNum)) {
						docName = result.doclist[i].rs_doc_nm2;
					} else {
						docName = result.doclist[i].rs_doc_nm;
					}
					html += docName;

					// new icon
					/*var newIconTarget = 'NOTICE_' + docdbNum;
					var minDate = getCookie(newIconTarget);
					
					if (minDate == '' || minDate == undefined) {
						minDate = getCookie('*' + newIconTarget);
					}
					
					if (minDate != '' && minDate != undefined) {
						minDate = minDate.split('|')[1];
						var yyyy = minDate.substring(0,4);
						var mm = minDate.substring(4,6);
						var dd = minDate.substring(6,8);
						minDate = new Date(yyyy + '/' + mm + '/' + dd);
						
						var targetDate = result.doclist[i].rs_dt;
						targetDate = targetDate.replace(/\./gi, '/');
						targetDate = new Date(targetDate);
						if (minDate <= targetDate) {
							html += ' <img src="/image/ico-new.gif" alt="" />';
							newTotal += 1;
//							$('#noticePopup').removeClass('hide');
						}
					}*/
					
					html += '</td>';
					
					//그룹
					if(listType == 'detail') {
						html += '<td>' + result.doclist[i].docgroup_kr + '</td>';
					}
					
					for(var k=1;k<=2;k++) {//2pdf화면일 경우 버튼 2쌍 생성을 위해 반복
						
						var docContentAreaID = 'docContentArea';
						
						if(listType == '2pdf') {
							docContentAreaID = 'docContentArea' + k;
						}
						
						//열람제한
						html += '<td class="txa_c">';
						if(result.doclist[i].acss_cp_rst_tpcd != null && result.doclist[i].acss_cp_rst_tpcd != '') {
							html += '<span style="color:gray;">열람제한</span>';
						}
						
						
						//문서 보기 버튼
						if(result.doclist[i].docid != null && result.doclist[i].docid != '-') {
							html += '<a class="btn_05 txt_gray" href="javascript:viewDocContent(\'' + docdbNum + '\',\'' + result.doclist[i].docid + '\',\'' + result.doclist[i].docformat + '\',\'' + docName.replace('\'','&rsquo;') + '\',\'' + result.doclist[i].rs_dt + '\',\'' + result.doclist[i].numberOfPage + '\',\'' + docContentAreaID + '\');"><span>원문</span></a>';
							
							if(listType == 'detail') {//다운로드용 체크박스
								html += ' <input type="checkbox" name="check" value="' + result.doclist[i].docid + '!@#' + result.doclist[i].numberOfPage + '!@#' + result.doclist[i].docformat + '!@#' + result.doclist[i].rs_dt + '!@#' + docName + '" />';
							}
						}								
						
						if(docdbNum.substring(0,2) != 'KR' && result.doclist[i].docid2 != null && result.doclist[i].docid2 != '') {
						//if(result.doclist[i].docid2 != null && result.doclist[i].docid2 != '') {
							html += '<br /><a class="btn_05 txt_gray" href="javascript:viewDocContent(\'' + docdbNum + '\',\'' + result.doclist[i].docid2 + '\',\'' + result.doclist[i].docformat + '\',\'' + docName.replace('\'','&rsquo;') + '\',\'' + result.doclist[i].rs_dt + '\',\'' + result.doclist[i].numberOfPage + '\',\'' + docContentAreaID + '\');"><span>영문</span></a>';
							
							if(listType == 'detail') {//다운로드용 체크박스
								html += ' <input type="checkbox" name="check" value="' + result.doclist[i].docid2 + '!@#' + result.doclist[i].numberOfPage + '!@#' + result.doclist[i].docformat + '!@#' + result.doclist[i].rs_dt + '!@#' + docName + '" />';
							}
						}
						
						
						html += '</td>';
						
						if(listType != '2pdf') {
							break;
						}
					}
					
					html += '</tr>';
				}
				
				html += 			'</tbody>';
				html += 		'</table>';
				html += 	'</div>';
				html += 	'<input type="hidden" id="' + docdbNum + '_new" name="new_total" value="' + newTotal + '" />';
				
				$('#'+area_id).html(html);
//				$('#'+area_id).html(html);
				
				
				
				//서지 영역과 리스트영역이 하나의 DIV에 있을 경우 높이 조절
				if($('#'+area_id+'_biblio').length > 0 && $('#'+area_id+'_number').length > 0) {
					$('#'+area_id+'_list').height($('#' + area_id).height() - $('#'+area_id+'_number').height() - $('#'+area_id+'_biblio').height() - 10);
				}
				
			} else {
				$('#' + area_id).html(result.result);
			}
			
			//unmask();
		},
		error:function(xhr, status, error) {
			alert('setDocListContent error');
			//unmask();
		}
	});
}

function viewDocContent(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, area_id) {
	/*if(typeof window['setCurrentStatus'] == 'function') {
		setCurrentStatus(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, 'N');
	}*/
	
	//if($('#' + area_id).length > 0) {
	if(document.getElementById(area_id)) {
		$.ajax({
			url: '/docContent/doDocContent.do',
			type: 'POST',
			data:{
				id : docid,
				num : docdbnum.substring(3),
				type : docformat,
				cn : docdbnum.substring(0, 2),
				numberOfPage : numberOfPage
			},
			beforeSend:function(x) {
				$('#' + area_id).html('');
				
				mask();
			},
			cache:false,
			success:function(result) {
				
				if(result.result == 'success') {
					/*var html = '';
					html += '<div id="div_doccontent_title" class="title1">' + getDocContentTitle(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, area_id, result.path) + '</div>';
					html += '<div id="div_doccontent_content" style="overflow:auto;font-size:15px;">';
					html += 	'<iframe src="/docContent/getDocContent.do?path='+result.path+'" width="100%" height="100%" />';
					html += '</div>';
					
					$('#' + area_id).html(html);
					$('#div_doccontent_content').height($('#' + area_id).height() - $('#div_doccontent_title').height());*/
					
					var html = '';
					html += '<div style="height:4%" class="title1">' + getDocContentTitle(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, area_id, result.path, '') + '</div>';
					html += '<div style="height:96%;overflow:auto;font-size:15px;">';
					html += 	'<iframe src="/docContent/getDocContent.do?path='+result.path+'" width="100%" height="100%" />';
					html += '</div>';
					
					$('#' + area_id).html(html);

				} else if(result.result == 'goCaptcha') {
					var option = "width=300,height=300,toolbar=no, menubar=no, scrollbars=yes, resizable=yes, location=no";
					//함수와 파라미터를 캡차화면에 넘겨주고 캡차 성공 후 캡차화면에서 viewDocContent를 호출
					var param = '?cb_fn=viewDocContent&cb_p_cnt=7&cb_p1=' + docdbnum + '&cb_p2=' + docid + '&cb_p3=' + docformat + '&cb_p4=' + rs_doc_nm + '&cb_p5=' + rs_dt + '&cb_p6=' + numberOfPage + '&cb_p7=' + area_id;
					var captchaPopup = window.open('/captcha/openCaptchaPage.do' + param, 'captchaPopup', option);
				} else {
					// [SR000117707, JJI] 데이터 오류 방지 및 안내 화면 도입
					var errorHtml = '';
					errorHtml += '<div style="height:96%;overflow:auto;font-size:15px;">';
					errorHtml += 	'<iframe src="/docContent/getDocContent.do?path='+result.path+'" width="100%" height="100%" />';
					$('#' + area_id).html(errorHtml);
					//$('#' + area_id).html(result.result);
				}
				unmask();
			},
			error:function(xhr, status, error) {
				unmask();
				// [SR000117707, JJI] 데이터 오류 방지 및 안내 화면 도입
				// [SR000121046, JJI] OPD_대민 심사문서 조회 기능 개선 (SR000117707 추가건)
				var errorHtml = '';
				var errorPdf = 'DocContent_SoapError_Public.pdf';
				errorHtml += '<div style="height:96%;overflow:auto;font-size:15px;">';
				errorHtml += '<iframe src="/docContent/getDocContent.do?path='+errorPdf+'" width="100%" height="100%" />';
				$('#' + area_id).html(errorHtml);
			}
		});
	} else {
		openPopup(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, '');
	}
	
	
	
	
	/*if($('#docListArea').html() == '') {
		viewDocList(docdbnum);
	}*/
	
}

/*function getDocContentTitle(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, path) {
	var html = '';
	
	var patt = new RegExp('W$');
	if(patt.test(docdbnum)) {
		html += '<img src="/common/images/flag_wo.gif" />&nbsp;';
	} else {
		html += '<img src="/common/images/flag_' + docdbnum.substring(0, 2).toLowerCase() + '.gif" />&nbsp;';
	}
	
	html += rs_doc_nm + ' (' + rs_dt + ')';
	
	if(path != '') {
		html += ' <a href="/docContent/getDocContent.do?path='+path+'" target="_blank" class="btn_style01"><span>새창</span></a>';
	}
	
	return html;
}*/


function getDocContentTitle(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, area_id, path, transYN) {
	var html = '';
	
	var patt = new RegExp('W$');
	if(patt.test(docdbnum)) {
		html += '<img src="/images/flag_wo.gif" />&nbsp;';
	} else {
		html += '<img src="/images/flag_' + docdbnum.substring(0, 2).toLowerCase() + '.gif" />&nbsp;';
	}
	
	html += rs_doc_nm + ' (' + rs_dt + ')';
	
	/*if(path != '') {
		if(docdbnum.substring(0, 2) == 'EP') {
			html += '<a class="btn_style01" href="javascript:doTransEP(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';	
		} else if(docdbnum.substring(0, 2) == 'CN') {
			html += '<a class="btn_style01" href="javascript:doTransCN(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';
		} else if(docdbnum.substring(0, 2) == 'JP') {
			html += '<a class="btn_style01" href="javascript:doTransJP(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';
		} else if(docdbnum.substring(0, 2) == 'US') {
			html += '<a class="btn_style01" href="javascript:doTransUS(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';
		}
		
		html += '<a href="/docContent/getDocContent.do?path='+path+'" target="_blank" class="btn_style01"><span>새창</span></a>';
		
	} else {
		html += '<a class="btn_style01" href="javascript:viewDocContent(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>원문</span></a>';
		html += '<a class="btn_style01" href="javascript:print();"><span>인쇄</span></a>';
	}*/
	
	/*if(transYN == 'Y') {
		html += '<a href="/docContent/getDocContent.do?path='+path+'" target="_blank" class="btn_style01"><span>원문</span></a>';
		html += '<a class="btn_style01" href="javascript:print();"><span>인쇄</span></a>';
	} else {
		if(docdbnum.substring(0, 2) == 'EP') {
			html += '<a class="btn_style01" href="javascript:doTransEP(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';	
		} else if(docdbnum.substring(0, 2) == 'CN') {
			html += '<a class="btn_style01" href="javascript:doTransCN(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';
		} else if(docdbnum.substring(0, 2) == 'JP') {
			html += '<a class="btn_style01" href="javascript:doTransJP(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';
		} else if(docdbnum.substring(0, 2) == 'US') {
			html += '<a class="btn_style01" href="javascript:doTransUS(\'' + docdbnum + '\',\'' + docid + '\',\'' + docformat + '\',\'' + rs_doc_nm.replace('\'','&rsquo;') + '\',\'' + rs_dt + '\',\'' + numberOfPage + '\',\'' + area_id + '\');"><span>번역</span></a>';
		}
		html += '<a href="/docContent/getDocContent.do?path='+path+'" target="_blank" class="btn_style01"><span>새창</span></a>';
	}*/
	html += '<a href="/docContent/getDocContent.do?path='+path+'" target="_blank" class="btn_style01"><span>새창</span></a>';
	
	
	
	
	
	return html;
}

// 심사문서 조회
function openPopup(docdbnum, docid, docformat, rs_doc_nm, rs_dt, numberOfPage, transYN) {
	var url = "/docContent/openDocContentPopup.do";
//	url += "?docdbNum="+docdbnum;
//	url += "&docid="+docid;
//	url += "&docformat="+docformat;
//	url += "&rs_doc_nm="+rs_doc_nm;
//	url += "&rs_dt="+rs_dt;
//	url += "&numberOfPage="+numberOfPage;
//	url += "&transYN="+transYN;
	
	url = encodeURI(url, 'UTF-8');
	
	var option = "width=1480,height=960,top="+ (screen.availHeight - 960) / 2 +", left=" + (screen.availWidth - 1480) / 2 + ", toolbar=no, menubar=no, scrollbars=yes, resizable=yes, location=no";
	
	var $frm = $('<form action="' + url + '" method="post" target="' + docid + '"></form>');
	$frm.append('<input type="hidden" name="docdbNum" value="' + docdbnum + '"/>');
	$frm.append('<input type="hidden" name="docid" value="' + docid + '"/>');
	$frm.append('<input type="hidden" name="docformat" value="' + docformat + '"/>');
	$frm.append('<input type="hidden" name="rs_doc_nm" value="' + rs_doc_nm  + '"/>');
	$frm.append('<input type="hidden" name="rs_dt" value="' + rs_dt + '"/>');
	$frm.append('<input type="hidden" name="numberOfPage" value="' + numberOfPage + '"/>');
	$frm.append('<input type="hidden" name="transYN" value="' + transYN + '"/>');
	
	$(document.body).append($frm);
	
	var documentPop = window.open(url, docid, option);
	documentPop.focus();
	
	$frm.submit();
}

function getFlag(docdbNum) {
	var flag = '<img src="/images/flag_' + docdbNum.substring(0, 2).toLowerCase() + '.gif" alt="" />&nbsp;';
	var patt = new RegExp('W$');
	if(patt.test(docdbNum)) {
		flag = '<img src="/images/flag_wo.gif" alt="" />';
	}
	
	return flag;
}

/*function clickLine(e) {
	//$(e).siblings().css('background-color','');
	//$(e).css('background-color','#EAEAEA');
	
	$(e).siblings().children('td').css('background-color','');
	$(e).children('td').css('background-color','#EAEAEA');
}*/

/*function mask() {
    if($('#mask').length == 0) {
    	$('body').append('<div id="mask" style="position:absolute; z-index:9000; background-color:#000000; display:none; left:0; top:0;"></div>');
    	$('#mask').css({'width' : '100%','height': '100%','opacity' :'0.3'});
    }
  
    $('#mask').fadeIn('fast');  
}

function unmask() {
	$('#mask').fadeOut('fast');
}*/

function print() {
	var newWin = window.open('', 'printPage', 'toolbar=no, directories=no, scrollbars=yes, resizable=yes, status=no, menubar=no, width=1500, height=1200, top=0, left=20');
	newWin.document.open();
	newWin.document.write('<html><head><title>print area</title><script>function init(){window.print();window.close();}<\/script></head><body onload="javascript:init();">' + $('#printArea').html() + '</body></html>');
	newWin.document.close();
	
}