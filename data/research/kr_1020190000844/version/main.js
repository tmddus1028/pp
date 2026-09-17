// 메인화면 전체검색
function doMainSearch()
{
	let inputQuery = $('#inputQuery').val();
	
	try
	{
		if (inputQuery != '')
		{
			if (isKeywordValidation(inputQuery))
			{
				var searchKeyword = $.trim(inputQuery);

				/* By J.H.S 20130813 국문 메인홈페이지에서 검색 할 때 출원번호, 등록번호 - 형식으로 입력시 "" 치환하여 검색식 입력하도록 개선함. */
				//입력된 숫자가 등록번호형식일 경우 "10-0000123" 대쉬 제거 by lhy 2013.03.19
				var regExpRegNum1 = /^\d{2}-\d{7}$/;
				if (regExpRegNum1.test(searchKeyword)) {
					searchKeyword = searchKeyword.replace("-","");
				}

				//입력된 숫자가 등록번호형식일 경우 "10-0000123-0000" 대쉬 제거 by lhy 2013.03.19
				var regExpRegNum2 = /^\d{2}-\d{7}-\d{4}$/;
				if (regExpRegNum2.test(searchKeyword)) {
					searchKeyword = searchKeyword.replace(/-/gi,"");
				}

				//입력된 숫자가 출원번호형식일 경우 "40-2003-0048429" 대쉬 제거 by lhy 2013.03.19
				var regExpRegNum3 = /^\d{2}-\d{4}-\d{7}$/;
				if (regExpRegNum3.test(searchKeyword)) {
					searchKeyword = searchKeyword.replace(/-/gi,"");
				}
				
				let searchKeywordTop = searchKeyword;
				//인명정보 Validation(하이픈[-]제거)
				searchKeyword = bioInfoValidation(searchKeyword);
				
				//독일어 특수문자 치환
				searchKeyword = convertGermanEntities(searchKeyword);

				var expression = DelSpecialChar(searchKeyword);
				expression = removeOperatorBlank(expression);
				
				$('#searchKind').val('totalSearch');
				$('#queryText').val(searchKeyword);
				$('#queryTextTop').val(searchKeywordTop);
				$("#expression").val(expression);
				
				sessionStorage.setItem('queryText', searchKeyword);
				sessionStorage.setItem('expression', expression);
				sessionStorage.setItem('filterData', null);
				
				$('#mainSearchForm').submit();
			}
		} else {
			alert('검색어를 입력해 주십시오.');
		}
	}
	catch (e)
	{
		alert(e);
		return false;
	}
}

//(국내상표)25.10.30 지정상품 명칭 및 유사군코드 일부 변경 알림 팝업 띄우기
function openModalSimilarCodeNotice() {
	modal.open('#modalSimilarCodeNotice');
}