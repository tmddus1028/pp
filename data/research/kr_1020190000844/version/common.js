/**
 * 공통 스크립트 파일
 */

let pageLang = $('input[name=pageLanguage]').val();
const supportLngs = ['ko', 'en'];  // 지원 언어 목록
const isValidLang = supportLngs.includes(pageLang);
	
		
i18next
	.use(i18nextHttpBackend)
	.use(i18nextBrowserLanguageDetector)
	.init({
		debug: false,
		fallbackLng: 'en', // 기본 대체 언어
		lng : isValidLang ? pageLang : undefined, //파라미터 값이 유효하면 설정, 아니면 ①브라우저 감지 ②fallbackLng
		supportedLngs: supportLngs, // 지원 언어 목록
		load: 'languageOnly', // 언어 코드만 사용
		backend: {
			loadPath: '/khome/locales/{{lng}}/translation.json'
		}
	}, function(err, t) {
		if (err) {
			console.error('i18next initialization error', err);
			return;
		}
		
		reqLogin();
		addDataLangId();
		updateContent();
		updateHtmlLang(i18next.language);
	});

function updateContent(targetHtml)
{
	if (location.pathname.indexOf('/main.do') > -1) {
		$('#fp-nav .fp-tooltip').each(function(idx, item) {
			if (i18next.language == 'ko') {
				switch ($(item).text()) {
					case 'Search' : $(item).text('검색'); break;
					case 'Info' : $(item).text('정보'); break;
					case 'Link' : $(item).text('연계'); break;
				}
			} else if (i18next.language == 'en') {
				switch ($(item).text()) {
					case '검색' : $(item).text('Search'); break;
					case '정보' : $(item).text('Info'); break;
					case '연계' : $(item).text('Link'); break;
				}
			}
		});
	} 
	
	// 영문페이지 일부 권리 한글-영어 검색 숨기기
	if (i18next.language == 'en') {
		$('.h-check').css('display', 'none');
	} else if (i18next.language == 'ko'){
		if($('.h-check').css('display') == 'none'){
			$('.h-check').css('display', 'block');
		}
	}
	
	let target;
	if (targetHtml != undefined) {
		target = document.createElement('div');
		target.innerHTML = targetHtml;
	} else {
		target = document;
	}
	
	target.querySelectorAll('[data-lang-id]').forEach(element => {
		const langKey = element.getAttribute('data-lang-id');
		const langType = element.getAttribute('data-lang-type');
		if (langType == "title") {
			let newtitle = i18next.t(langKey, {defaultValue: element.getAttribute("title")});
			element.setAttribute("title", newtitle);
		} else if (langType == "placeholder") {
			let newplaceholder = i18next.t(langKey, {defaultValue: element.getAttribute("placeholder")});
			element.setAttribute("placeholder", newplaceholder);
		} else {
			element.innerHTML = i18next.t(langKey, {defaultValue: element.innerHTML});
		}
	});
	
	if (targetHtml != undefined) {
		return target.innerHTML;
	}
}

function updateHtmlLang(lng)
{
	document.documentElement.setAttribute('lang', lng);
}

function changeLanguage(obj) {
	let lng = '';
	let curLng = i18next.language;
	if (curLng == 'ko') {
		lng = 'en';
	} else {
		lng = 'ko';
	}
	const kpaTitle = document.getElementById('KPA_title');
	const kpaAbs = document.getElementById('kpa-content');
	const kpaAll = document.getElementById('kpa_all');
	const sumAll = document.getElementById('sum_all');
	if(sumAll != undefined) {
		if(lng == 'en' && kpaTitle != undefined && kpaAbs != undefined) {
			kpaAll.style.display = 'block';
			sumAll.style.display = 'none';
		} else if(lng == 'en' && (kpaTitle != undefined || kpaAbs != undefined)) {
			kpaAll.style.display = 'none';
			sumAll.style.display = 'block';
		} else if(lng == 'ko') {
			kpaAll.style.display = 'none';
			sumAll.style.display = 'block';
		}
	}
	i18next.changeLanguage(lng).then(() => {
	    updateContent();

	    setTimeout(() => {
	        document.querySelectorAll(
	            'label[data-tooltip-id][data-tooltip-type="icon"], ' +
	            'em[data-tooltip-id][data-tooltip-type="icon"], ' +
	            'button[data-tooltip-id][data-tooltip-type="icon"]'
	        ).forEach(el => {
	            const icon = el.querySelector('.help-tip');
	            if (icon) icon.remove();
	            el.dataset.tooltipInit = '';
	        });
	        window.reInitTooltips();
	    }, 0);
	    updateHtmlLang(lng);
	});
	
	// 통계_페이지 한영전환
	recordServiceStats('KHOME', 'OPSVC', 'PGKE');
}

let urlParams = new URLSearchParams(window.location.search);
function reqLogin() {
	if (urlParams.has('reqLogin') && urlParams.get('reqLogin') == 'Y') {
		alert(i18next.t('lgin.aflogin'));
		modal.open('#modalLogin');
	}
}

//로딩화면 셋팅 타겟
let loadingDialogTarget = '';

let surveyLastChecked = null;

$(document).ready(function() {
	// 상세검색 enter 이벤트
	$('#modalSearchDetail').find('input[type=text], textarea').on('keydown', function(event) {
		handleEnter(event, doDetailSearch);
	});
	
	// 입력도우미 초기화
	$('.modal-support button.btn-close, .modal-support button[type=submit]').not('.btn-reset').on('click', function() {
		initModalSupport($(this).parents('.modal-support').data('modal').replace('support', ''));
	});
	
	// 최근검색어 초기화
	if ($('.search-recent').length != 0) {
		initRecentKeyword();
	}
	
	// 저장된 아이디 셋팅
	if (localStorage.getItem('saveId')) {
		$('#modalLogin #loginId').val(localStorage.getItem('saveId'));
		$('#saveId').prop('checked', true);
	}
	
	$('select[name=sd010301_g01_category_01]').change(function(){
		let selectedValue = $(this).val(); 
		$('#sd010301_g01_category_01 option').prop('selected', false);
		$('#sd010301_g01_category_01 option[value=' + selectedValue + ']').prop('selected', true);
	});
	
	// 문장검색 글자 수 제한(20,000자)
	$(document).on('input', 'textarea[data-limit-id=Y]', function(){
		let maxLength = 20000;
		let currentLength = $(this).val().length;
		
		if (currentLength > maxLength) {
			alert(i18next.t('cmn.txt16'));
			$(this).val($(this).val().substring(0, maxLength));
		}
	});
	
	// 통계_헤더 지식재산권 검색 권리별
    $('.patentMenu').on('click', function() {
    	recordServiceStats('KHOME', 'HEAD', 'PAT');
    });
    $('.designMenu').on('click', function() {
    	recordServiceStats('KHOME', 'HEAD', 'DG');
    });
    $('.trademarkMenu').on('click', function() {
    	recordServiceStats('KHOME', 'HEAD', 'TM');
    });
    $('.judgementMenu').on('click', function() {
    	recordServiceStats('KHOME', 'HEAD', 'JM');
    });
    $('.etcMenu').on('click', function() {
    	recordServiceStats('KHOME', 'HEAD', 'OTHER');
    });	
    
    // 라디오 버튼 클릭 이벤트 (토글 로직)
    $('input[name="rating"]').on('click', function() {
      const $this = $(this);
      const $parent = $this.closest('.rating-item');
      const $panel = $('#feedbackPanel');

      if (this === surveyLastChecked) {
        // 이미 선택된 것을 다시 클릭한 경우 -> 초기화
        $this.prop('checked', false);
        $parent.removeClass('active');
        surveyLastChecked = null;
        $panel.removeClass('is-open');
        setTimeout(() => {
            $('#surveyComment').val('');
            $('#current-count').text('0');
            $panel.hide();
          }, 400);
      } else {
        // 새로운 선택
    	$this.prop('checked', true);
        $('.rating-item').removeClass('active');
        $parent.addClass('active');
        surveyLastChecked = this;
        $panel.show();
        $panel.addClass('is-open');
      }
    });

    // 글자수 카운팅
    $('#surveyComment').on('input', function() {
    	const len = $(this).val().length;
      $('#current-count').text(len);
    });
    
    // 페이지 로드 시 참여 여부 체크
    checkSurveyStatus();
    
    $('#btnSurveySubmit').on('click', function() {
    	let surveyData = {
                'pageId': $('#surveyPageId').val(),
                'rating': $('input[name="rating"]:checked').val(),
                'comment': $('#surveyComment').val()
            };
    	
    	// 검색결과페이지일 경우 권리 저장
    	if($('#surveyPageId').val() == 'S01') {	
    		surveyData.sub_clcd = currentTab2;
    	}

        if (!surveyData.rating) { 
        	alert("평점을 선택해주세요."); return; 
        }
        
        $.ajax({
            type: 'POST',
            url: '/khome/common/insertSurvey.do',
            data: surveyData,
            success: function() {
                $('#feedbackPanel').removeClass('is-open');
                setTimeout(function() {
                    $('#surveyForm').fadeOut(200, function() {
                        setCookie($('#surveyPageId').val(), 'Y', 1);
                        $('#completedTitle').hide();
                        $('#completedDesc').hide();
                        $('#completedTitleSuccess').show();
                        $('#completedDescSuccess').show();
                        $('#completedIcon').text("✅");
                        $('#surveyCompleted').fadeIn(200);
                    });
                }, 400);
                $('#surveyCompleted').focus();
            },
            error: function(xhr, status, error)
    		{
    			console.log('insertSurvey error');
    		}
        });
    });
    
    // 쿠키 생성 함수
    function setCookie(name, value, days) {
      const d = new Date();
      d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
      let expires = "expires=" + d.toUTCString();
      document.cookie = name + "=" + value + ";" + expires + ";path=/";
    }
    
    // 쿠키 가져오기 함수
    function getCookie(name) {
      let nameArr = name + "=";
      let decodedCookie = decodeURIComponent(document.cookie);
      let ca = decodedCookie.split(';');
      for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1);
        if (c.indexOf(nameArr) == 0) return c.substring(nameArr.length, c.length);
      }
      return "";
    }
    
    // 초기 로드 시 체크 함수
    function checkSurveyStatus() {
    	const surveyPageId = $('#surveyPageId').val();
    	if (getCookie(surveyPageId) === 'Y') {
    		// 이미 참여 후 재방문 시 문구 설정
    		$('#completedTitleSuccess').hide();
            $('#completedDescSuccess').hide();
            $('#completedTitle').show();
            $('#completedDesc').show();
            /*$('#completedIcon').text("ℹ️");*/
			$('#surveyCompleted').show();
	    } else {
	    	$('#surveyForm').show();
	    }
		$('#surveyContainer').show();
    }
    
    // 상세정보 내 전문검색 입력란 확장
    var $wrapper = $('#searchWrapper');
    var $textarea = $('#sd01_g01_text');
    var $expandBtn = $('#btnInputExpand');

    $textarea.on('input keydown click', function(e) {
    	if (e.key === 'Enter' || this.scrollHeight > 32) {
    		if(!$wrapper.hasClass('is-expanded')){
    			$expandBtn.trigger('click');
    		}
    	}
    });
    
    // 1. 확장/축소 토글 버튼 클릭
    $expandBtn.on('click', function(e) {
        e.stopPropagation(); 
        
        var isExpanded = $wrapper.toggleClass('is-expanded').hasClass('is-expanded');
        
        if (isExpanded) {
            $expandBtn.attr({'aria-label': '입력창 축소', 'title': '입력창 축소'});
            setTimeout(function() {
                $textarea.trigger('focus');
            }, 50);
            
        } else {
            $expandBtn.attr({'aria-label': '입력창 확대', 'title': '입력창 확대'});
            // 접힐 때 내부 스크롤을 맨 위로 리셋
            setTimeout(function() {
            	$textarea.scrollTop(0);
            }, 50);
        }
    });

    // 2. 외부 영역 클릭 시 자동으로 닫히는 기능
    $(document).on('click', function(e) {
        if ($wrapper.hasClass('is-expanded') && !$wrapper.has(e.target).length && !$wrapper.is(e.target)) {
            $wrapper.removeClass('is-expanded');
            $expandBtn.attr({'aria-label': '입력창 확대', 'title': '입력창 확대'});
            $textarea.scrollTop(0);
        }
    });
});

function goMenu(menu, sub)
{
	let url;
	let statCode = null;
	
	switch(menu) {
		case 'home' : url = '/khome/main.do'; break;
		case 'join' : url = '/khome/member/join/agreement.do'; break;
		case 'updateEmail' : url = '/khome/member/update/cert.do'; break;
		case 'updatePassword' : url = '/khome/member/update/form.do?type=password'; break;
		case 'findId' : url = '/khome/member/find/findId.do'; break;
		case 'findPassword' : url = '/khome/member/find/findPassword.do'; break;
		case 'notice' : url = '/khome/board/notice/list.do'; break;
		case 'faq' : url = '/khome/board/faq.do'; break;
		case 'voc' : url = '/khome/board/voc/cert.do'; break;
		case 'rgstVoc' : url = '/khome/board/voc/regist.do'; break;
		case 'vocList' : url = '/khome/board/voc/list.do'; break;
		case 'detailVoc' : url = '/khome/board/voc/detail.do'; break;
		case 'inactive' : url = '/khome/member/update/inactive.do'; break;
		case 'basicHelp' : url = '/khome/board/help/introduce.do'; break;
		//통계_검색도움말-권리별검색
        case 'srchRightsHelp' :
            url = '/khome/board/help/searchByRights.do?tab=' + sub;

            switch(sub) {
                case 'patent':
                    recordServiceStats('KHOME', 'OPSVC', 'PTDOM');
                    break;
                case 'design':
                    recordServiceStats('KHOME', 'OPSVC', 'DSDOM');
                    break;
                case 'trademark':
                    recordServiceStats('KHOME', 'OPSVC', 'TMDOM');
                    break;
                case 'judgement':
                    recordServiceStats('KHOME', 'OPSVC', 'JUDGE');
                    break;
                case 'etc':
                    recordServiceStats('KHOME', 'OPSVC', 'OTHER');
                    break;
            }
            break;
		//통계_검색도움말-특화검색
        case 'spcSrchHelp' :
            url = '/khome/board/help/specialSearch.do?tab=' + sub;

            switch(sub) {
                case 'similar':
                    recordServiceStats('KHOME', 'OPSVC', 'SIMIL');
                    break;
                case 'national':
                    recordServiceStats('KHOME', 'OPSVC', 'NATRL');
                    break;
                case 'product':
                    recordServiceStats('KHOME', 'OPSVC', 'PRDCT');
                    break;
                case 'micro':
                    recordServiceStats('KHOME', 'OPSVC', 'MDEPO');
                    break;
            }
            break;


		case 'myNoticeList' : url = '/khome/myKipris/myNotice/list.do'; break;
		default : url = '/khome/main.do'; break;
	}
	
	if (sub == 'openPopup') {
		// window.open(url, menu, 'width=' + screen.width/2 + ', height=' + screen.availHeight + ', menubar=no, toolbar=no, location=no, status=no, fullscreen=yes');
		window.open(url, '_blank');
	} else {
		location.href = url;
	}
}

function openLoginBox(nextUrl)
{
	if (nextUrl != undefined && nextUrl != '') {
		$('#nextUrl').val(nextUrl);
	}
	modal.open('#modalLogin');
}

let loginCheckId = false, loginCheckPw = false, fiveTimesError = false;
let loginErrDtm = '';
function login()
{
	if (loginCheckId && loginCheckPw && !fiveTimesError) {
		toggleLoadingDialog('#modalLogin .modal-con', true);
		let inptId = $('#loginId').val();
		let inptPwd = $('#loginPw').val();

		$.ajax({
			async: true,
			type: 'POST',
			url: '/khome/member/loginProc.do',
			data: {userid: inptId, password: inptPwd},
			dataType: 'json',
			success: function(data)
			{
				let result = data.resultCode;
				
				// 회원 방문자 관련 GTM 이벤트 호출 추가
				if (result == 3 || result == 6) {
					window.dataLayer = window.dataLayer || [];
					window.dataLayer.push({
						event: 'kipris_login_success',
						_TRK_SX: 'U',
						_TRK_PI: 'LIR'
					});
				}
				
				switch (result) {
					case 0 :
						$('#loginId').addClass('error');
						$('#errMsgId').html(i18next.t('lgin.idnotexist'));
						$('#errMsgId').removeClass('hidden');
						$('#loginId').focus();
						break;
					case 1 :
						$('#loginPw').addClass('error');
						$('#errMsgPw').html(i18next.t('lgin.incopw') + data.pwdErrTms + i18next.t('lgin.incopwcnt'));
						$('#errMsgPw').removeClass('hidden');
						$('#loginPw').focus();
						break;
					case 3 :
						// 로그인 성공 (로그인 부분 UI 변경 스크립트 추가 예정, 모바일도 같이 변경해야됨)
						$('#header').find('.before-login').addClass('hidden');
						$('#header').find('.after-login').removeClass('hidden');
						
						let nextUrl = $('#nextUrl').val();
						if (urlParams.has('reqLogin') && urlParams.get('reqLogin') == 'Y') {
							location.href = $('#orgReqUrl').val();
						} else if (nextUrl != '') {
							if (nextUrl == 'reload') {
								location.reload();
							} else {
								location.href = nextUrl;
							}
						}
						// 아이디 저장
						if ($('#saveId').prop('checked')) {
							if (localStorage.getItem('saveId') != inptId) {
								localStorage.setItem('saveId', inptId);
							}
						} else {
							localStorage.removeItem('saveId');
						}
						// modal 창 종료
						$('button.btn-close[data-modal-close=modalLogin]').trigger('click');
						
						/*
						 * 개인화_김철(설정 불러오기)
						 */
						loadPersonalizeSetting();
						
						break;
					case 4 :
						$('#loginPw').addClass('error');
						$('#errMsgPw').html(i18next.t('lgin.fvwrpw'));
						$('#remainMinute').text(data.remainMinute);
						$('#errMsgPw').removeClass('hidden');
						fiveTimesError = true;
						loginErrDtm = data.pwdErrDtm;
						break;
					case 5 :
						// 휴면계정 해제 절차 필요
						$('button.btn-close[data-modal-close=modalLogin]').trigger('click');
						$('#header').find('.before-login').removeClass('hidden');
						$('#header').find('.after-login').addClass('hidden');
						inactive_user(data.value1, data.value2, data.value3, data.value4, data.value5);
						break;
					case 6 :
						// 비밀번호 변경 절차 필요
						$('#header').find('.before-login').addClass('hidden');
						$('#header').find('.after-login').removeClass('hidden');
						alert(i18next.t('cmn.txt17'));
						goMenu('updatePassword');
						break;
					default :
						alert(i18next.t('ms.join.txt21'));
						break;
				}
			},
			error: function(xhr, status, error)
			{
				alert(i18next.t('ms.join.txt53'));
			},
			complete: function() {
				toggleLoadingDialog(loadingDialogTarget, false);
			}
		});
	} else {
		if (fiveTimesError) {
			var remainMinute = calcRetryMinute(loginErrDtm);
			if (remainMinute == 0) {
				fiveTimesError = false;
				loginIdCheck();
				loginPasswordCheck();
			} else {
				$('#loginPw').addClass('error');
				$('#errMsgPw').html(i18next.t('lgin.fvwrpw'));
				$('#remainMinute').text(remainMinute);
				$('#errMsgPw').removeClass('hidden');
			}
		} else {
			loginIdCheck();
			loginPasswordCheck();
		}
	}
}

function loginIdCheck()
{
	let $inptObj = $('#loginId');
	let $msgObj = $('#errMsgId');
	
	if ($inptObj.val() == '') {
		$inptObj.addClass('error');
		$msgObj.html(i18next.t('lgin.enid'));
		$msgObj.removeClass('hidden');
		loginCheckId = false;
	} else {
		if ($inptObj.hasClass('error')) {
			$inptObj.removeClass('error');
			$msgObj.addClass('hidden');
		}
		loginCheckId = true;
	}
	
	if (event.key == 'Enter' || event.keyCode == 13) {
		login();
	}
}

function loginPasswordCheck()
{
	let $inptObj = $('#loginPw');
	let $msgObj = $('#errMsgPw');
	if ($inptObj.val() == '') {
		$inptObj.addClass('error');
		$msgObj.html(i18next.t('lgin.pwnotexist'));
		$msgObj.removeClass('hidden');
		loginCheckPw = false;
	} else if ($inptObj.val().length < 8) {
		$inptObj.addClass('error');
		$msgObj.html(i18next.t('lgin.pweight'));
		$msgObj.removeClass('hidden');
		loginCheckPw = false;
	} else {
		if ($inptObj.hasClass('error')) {
			$inptObj.removeClass('error');
			$msgObj.addClass('hidden');
		}
		loginCheckPw = true;
	}
	
	if (event.key == 'Enter' || event.keyCode == 13) {
		login();
	}
}

function logout()
{
	$.ajax({
		async: true,
		type: 'POST',
		url: '/khome/member/logoutProc.do',
		dataType: 'json',
		success: function(data)
		{
			if (data.resultCode == '00') {
				$('#header').find('.before-login').removeClass('hidden');
				$('#header').find('.after-login').addClass('hidden');
				$('#loginPw').val('');
				
				if (location.href.indexOf('/member/') > -1) {
					goMenu('home');
				}
				
				// 개인화 설정 초기화_김철
				removePersonalizeCookie();
			}
		},
		error: function(xhr, status, error)
		{
			alert(i18next.t('ms.join.txt53'));
		},
	});
}

function loginCheck(mode)
{
	let loginYn = 'N';
	$.ajax({
		async: false,
		type: 'POST',
		url: '/khome/member/checkSession.do',
		dataType: 'json',
		success: function(data)
		{
			if (data.result == 'SESSION_VALID') {
				loginYn = 'Y';
			}
		},
		error: function(xhr, status, error)
		{
			alert(i18next.t('ms.join.txt7'));
		},
	});
	
	if (loginYn == 'Y') {
		return true;
	} else {
		if (mode != 'noAlert') {
			alert(i18next.t('cmn.txt1'));
			openLoginBox();
		}
		return false;
	}
}

// 로그인 오류 시간 카운트 다운
function calcRetryMinute(errDtm) {
	if (errDtm.length != 14) {
		throw new Error('유효하지 않은 입력 값입니다.');
	}
	
	const errYear = parseInt(errDtm.substring(0, 4));
	const errMonth = parseInt(errDtm.substring(4, 6));
	const errDay = parseInt(errDtm.substring(6, 8));
	const errHour = parseInt(errDtm.substring(8, 10));
	const errMin = parseInt(errDtm.substring(10, 12));
	const errSec = parseInt(errDtm.substring(12, 14));
	
	const errDate = new Date(errYear, errMonth-1, errDay, errHour, errMin, errSec);
	
	if (isNaN(errDate.getTime())) {
		throw new Error('유효하지 않은 날짜 문자열 형식입니다.');
	}
	
	const targetTime = errDate.getTime() + (30 * 60 * 1000);
	const targetDate = new Date(targetTime);
	
	const nowDate = new Date();
	const diffTime = targetDate.getTime() - nowDate.getTime();
	
	var diffMinute = 0;
	if (diffTime > 0) {
		diffMinute = Math.floor(diffTime / (60 * 1000));
	}
	
	return diffMinute;
}

//한글-영어 변역 검색 체크
function searchTransCheck(right) 
{
	let $targetForm = '';
	
	if (window.location.pathname.indexOf('/main.do') > -1){
		$targetForm = $('#mainSearchForm');
	} else {
		$targetForm = $('#' + right + 'SearchForm');
	}

	if ($('#' + right + 'SearchInTrans').prop('checked')) {
		$targetForm.find('input[name=searchInTrans]').val('Y');
		//접근성 속성 추가(checkbox, label)
		$('#' + right + 'SearchInTrans').attr({
			'title':'선택됨',
			'aria-checked':'true'
		});
		$('label[for="' + right + 'SearchInTrans').attr('title','선택됨');
	} else {
		$targetForm.find('input[name=searchInTrans]').val('N');
		//접근성 속성 추가(checkbox, label)
		$('#' + right + 'SearchInTrans').removeAttr('title').attr('aria-checked','false');
		$('label[for="' + right + 'SearchInTrans').removeAttr('title');
	}
}

function exactMatchCheck(right) 
{
	let $targetForm = '';
	
	if (window.location.pathname.indexOf('/main.do') > -1){
		$targetForm = $('#mainSearchForm');
	} else {
		$targetForm = $('#' + right + 'SearchForm');
	}

	if ($('#' + right + 'ExactMatch').prop('checked')) {
		$targetForm.find('input[name=searchInComplate]').val('Y');
		//접근성 속성 추가(checkbox, label)
		$('#' + right + 'ExactMatch').attr({
			'title':'선택됨',
			'aria-checked':'true'
		});
		$('label[for="' + right + 'ExactMatch').attr('title','선택됨');
	} else {
		$targetForm.find('input[name=searchInComplate]').val('N');
		//접근성 속성 추가(checkbox, label)
		$('#' + right + 'ExactMatch').removeAttr('title').attr('aria-checked','false');
		$('label[for="' + right + 'ExactMatch').removeAttr('title');
	}
}
//btn hover 시 선택됨 title 추가 _20250415 웹접근성을 위한 기능
function onBtnHover(el){
	if(el.classList.contains('active') || el.classList.contains('on')){
		el.setAttribute('title','선택됨');
		el.setAttribute('aria-selected','true');
	}
	else{
		el.setAttribute('title','선택되지 않음');
		el.setAttribute('aria-selected','false');
	}
}
// 상세검색
function doDetailSearch(mode)
{
	/* 상세검색의 권리별 탭 ID
	 * sd01 : 권리별검색, sd02 : 특화검색 */
	let tabId = $('#modalSearchDetail').find('.btn-tab.active').data('tab-id');
	
	/* 상세검색의 두번째 탭 정보
	 * [권리별검색] sd01_01 : 특실, sd01_02 : 디자인, sd01_03 : 상표, sd01_04 : 심판, sd01_05 : 기타문헌
	 * [특화검색] sd02_01 : 유사특허, sd02_02 : 국유특허, sd02_03 : 물질특허, sd02_04 : 미생물 */
	let sTabId = $('#modalSearchDetail').find('.tab-con.active').find('.btn-category.active').data('visible-control');
	
	// 두번째 탭 선택에 따른 활성화 div 추출
	let $activeDiv1 = $('#modalSearchDetail').find('.tab-con.active > .tab-con-body').find('div[data-visible-target=' + sTabId + ']');
	
	// 상표와 심판은 두번째 탭이 존재하지 않음으로 별도 처리
	/*if ($activeDiv1.length == 0) {
		$activeDiv1 = $('#modalSearchDetail').find('.tab-con.active > .tab-con-body > .search-detail-form.active');
	}*/
	
	// 상세검색의 검색유형 값 (검색유형이 없는 권리는 존재하지 않음)
	// Radio버튼이 존재하지 경우(심판)예외처리_특화검색 제외
	// 산업기술분류정보는 국내특실고정
	let srchKind = '';
	if ($activeDiv1.find('input[type=radio]:checked').val() == undefined && tabId == 'sd01') {
		srchKind = 'jg';
	} else if(tabId == 'sd02' && sTabId == 'sd02_05'){
		srchKind = 'kpat'
	} else {
		srchKind = $activeDiv1.find('input[type=radio]:checked').val();
	}
	// 상세검색의 검색유형 선택시 활성화 div id값
	let targetId = $activeDiv1.find('input[type=radio]:checked').data('visible-control');
	// 상세검색의 검색유형 선택에 따른 active div 추출
	let $activeDiv2 = $('#modalSearchDetail').find('.tab-con.active > .tab-con-body').find('div[data-visible-target=' + targetId + ']');
	
	// 검색유형 선택항목이 존재하지 않는 경우
	if ($activeDiv2.length == 0) {
		$activeDiv2 = $activeDiv1;
	}
	
	// 추출한 div의 checkbox 요소 추출
	// 한글-영어 번역 체크 제외
	let $elsCheck = $activeDiv2.find('input[type=checkbox]').not('[data-filter-id=searchInTransCk]').not('[data-filter-id=exactMatchCk]');
	if (srchKind == 'abpatTrans') {
		$elsCheck = $activeDiv2.find('input[type=radio]');
	}
	// 추출한 div의 text 요소 추출 
	let $elsInput = $activeDiv2.find('input[type=text], textarea');
	
	// 초기화 버튼 클릭시
	if (mode == 'init') {
		// 체크박스 초기화
		if (srchKind == 'abpat') {
			$.each($elsCheck, function(idx, item) {
				if ('US|EP|WO|JP|CN'.indexOf($(item).data('filter-id')) > -1) {
					$(item).prop('checked', true);
				} else {
					$(item).prop('checked', false);
				}
			});
		} else if (srchKind == 'abpatTrans') {
			$.each($elsCheck, function(idx, item) {
				if ('US'.indexOf($(item).data('filter-id')) > -1) {
					$(item).prop('checked', true);
				} else {
					$(item).prop('checked', false);
				}
			});
		} else if (srchKind == 'abdg' || srchKind == 'abtm') {
			$.each($elsCheck, function(idx, item) {
				if ('US|JP'.indexOf($(item).data('filter-id')) > -1) {
					$(item).prop('checked', true);
				} else {
					$(item).prop('checked', false);
				}
			});
		} else {
			$elsCheck.prop('checked', true);
		}
		// 입력 텍스트 초기화
		$elsInput.val('');
		// 추가된 항목 초기화
		$activeDiv2.find('.sdf-grid.active:not(:first-child) .btn-control-item').click();
		/*
		 * 2026.06.09 OJE
		 * 초기화 시 추가한 검색항목도 제거하도록 처리
		 */ 
		var activeTabId = $('#modalSearchDetail .btn-category.active').attr('data-visible-control');
		$('#modalSearchDetail').find('[data-visible-target="' + activeTabId + '"]').find('[data-sdf-extra-control].active').trigger('click');
		// 첫번째 항목 select 초기화 
		$activeDiv2.find('.sdf-grid.active:first-child select option:first-child').prop('selected', true);
		$activeDiv2.find('.sdf-grid.active:first-child select').trigger('change');

		// 특화검색일때 select 초기화 (tab이 active이고, grid는 active 아님)
		$activeDiv1.find('.sdf-grid:first-child select option:first-child').prop('selected', true);
		$activeDiv1.find('.sdf-grid:first-child select option:first-child').trigger('change');

		// 검색항목 설정 초기화
		$('#modalSearchDetail .tab-con.active .tab-con-foot.active div.active button.active').click();
		// 한글-영어 번역 검색 설정 초기화
		$activeDiv2.find('input[name='+ srchKind +'SearchInTrans]').prop('checked', false);
		$activeDiv2.find('input[name='+ srchKind +'ExactMatch]').prop('checked', false);
		
		if(tabId == 'sd02' && sTabId == 'sd02_05') {
			 $('#modalSearchDetail #sd0205_g00_0001').click();
		}
	} else {
		// 입력값 Validation
		if (tabId == 'sd02') { // 특화검색
			if (sTabId == 'sd02_01') { // 유사특허
				if (mode == undefined) {
			    	let $essentialInput = $elsInput.filter(function(){
			    		return $(this).attr('id').indexOf('text') !== -1;
			    	});
			    	
			    	let validInputTxt = true;
			    	$essentialInput.each(function(idx, item){
			    		if ($(item).val().trim() != '') {
			    			validInputTxt = false;
			    		}
			    	});
			    	
		    		if (validInputTxt) {
		    			alert(i18next.t('cmn.txt2'));
		    			return false;
		    		}
				} else {
					if (mode != 'weightSearch') {
						if ($('#sd020101_g02_text_04').val() == '') {
							alert(i18next.t('cmn.txt3'));
							return false;
						}
					}
				}
		    } else if (sTabId == 'sd02_02') { // 국유특허
		    	let $dateInput = $elsInput.filter(function(){
		    		return $(this).attr('id').indexOf('text') == -1;
		    	});

		    	let validInputTxtCount = 0;
		    	$dateInput.each(function(idx, item){
		    		let tempValue = $(item).val().trim();
		    		if (tempValue == '') {
		    			validInputTxtCount++;
		    		}
		    	});
		    	
	    		if (validInputTxtCount == 1) {
	    			alert(i18next.t('cmn.txt4'));
		            return false;
		        }
		    } else if (sTabId == 'sd02_03') { // 물질특허
		    	let $dateInput = $elsInput.filter(function(){
		    		return $(this).attr('id').indexOf('text') == -1;
		    	});
		    	
		    	let validInputTxtCount = 0;
		    	$dateInput.each(function(idx, item){
		    		let tempValue = $(item).val().trim();
		    		if (tempValue == '') {
		    			validInputTxtCount++;
		    		}
		    	});
		    	
		    	if (validInputTxtCount == 1) {
	    			alert(i18next.t('cmn.txt4'));
	    			return false;
	    		}
		    } else if (sTabId == 'sd02_04') { // 미생물 기탁,분양정보
		    	
		    } else if (sTabId == 'sd02_05') {
		    	if ($('#miller-container').find('.active').length < 1) {
	    			alert(i18next.t('cmn.txt2'));
	    			return false;
	    		}
		    }
		} else {
	        if (!filterValidation('detailSearch', srchKind, $activeDiv2.find('[data-type=checkbox]'))) {
	            return;
	        }
	    	// checkbox 값 셋팅
	    	setFilterValues('detailSearch', srchKind, $elsCheck);
	    }

		let query = '';
		let dateQuery = {};
		let tempStrstat = '';
		let jgLawQuery = '';
		
		$.each($elsInput, function(idx, item) {
	        let tempValue = $.trim($(item).val());
	        if (tempValue != '') {
	            let inputKind = $(item).data('kind');
	            let fieldName = $(item).data('field');
	            let operator = $(item).parents('.fg-body').find('select[data-operator=' + fieldName + ']').val();
	            
	            if (inputKind == 'date') {
	                let dateValue = tempValue.replace(/[^\d]/g, '');
	                
	                if (dateValue.length > 8) {
	                    alert(i18next.t('cmn.txt5'));
	                    return false;
	                }
	                
	                if ($(item).data('sdf-support-date') == 'start') {
	                	// 시작일자만 입력한 경우 구분(해당 일자로만 검색하도록)
	                	if ($(item).closest('div').siblings().find('input').val() == '') {
	                		dateQuery[fieldName] = dateValue;
	                		query += fieldName + '=[' + dateQuery[fieldName] + '~' + dateQuery[fieldName] + ']';
	                		if (operator == 'AND') {
		                        query += '*';
		                    } else if (operator == 'OR') {
		                        query += '+';
		                    }
	                	} else {
	                		dateQuery[fieldName] = dateValue;
	                	}
	                } else if ($(item).data('sdf-support-date') == 'end') {
	                	// 종료일자만 입력한 경우 구분(해당 일자로만 검색하도록)
	                	if (tabId == 'sd01') {
	                		if (dateQuery[fieldName] == '' || dateQuery[fieldName] == undefined) {
	                			dateQuery[fieldName] = dateValue;
	                		} 
	                		query += fieldName + '=[' + dateQuery[fieldName] + '~' + dateValue + ']';
	                	} else {
	                		dateQuery[fieldName] = dateValue;
	                	}
	                    
	                    if (operator == 'AND') {
	                        query += '*';
	                    } else if (operator == 'OR') {
	                        query += '+';
	                    }
	                }
	            } else {
	                if (fieldName == 'KW') {
	                    query += tempValue;
	                } else {
	                	// 문장검색(유사특허) 구분
	                	if (tabId == 'sd02' && sTabId == 'sd02_01') {
	                		query = tempValue;
	                		tempStrstat = 'SMART|' + fieldName + '|';
	                		
	                		//다음 옵션 선택 시, 다른 옵션 입력 값 초기화, 퍼블리셔 요청 필요?
	                		$(item).val('');
	                	} else if (tabId == 'sd01' && fieldName == 'LL') { // 심판 법조항
	                		if (jgLawQuery == '') {
	                			let lawKind = $(item).parents('.fg-body').find('select.column-category').val();
		                		jgLawQuery += lawKind;
		                		
		                		$(item).parents('.fg-body').find('input[type=text]').each(function(i, t) {
		                			if ($(t).val() != '') {
		                				switch ($(t).data('order')) {
				                			case 1 : jgLawQuery += $(t).val() + '조'; break;
				                			case 2 : jgLawQuery += $(t).val() + '항'; break;
				                			case 3 : jgLawQuery += $(t).val() + '호'; break;
				                		}
		                			}
		                		});
		                		
		                		let matchedSearch = $(item).parents('.fg-body').find('input[type=checkbox]').prop('checked');
	            				if (matchedSearch) jgLawQuery = '"' + jgLawQuery + '"';
	            				query += fieldName + '=[' + jgLawQuery + ']';
	            				
	            				// 완전일치검색 여부 셋팅
	            				let targetFormId = '#' + srchKind + 'SearchForm';
	            				if ($('#sd0104_g08_ck').prop('checked')) {
	            					$(targetFormId).find('input[name=searchInComplate]').val('Y');
	            				} else {
	            					$(targetFormId).find('input[name=searchInComplate]').val('N');
	            				}
	                		} else {
	                			return false;
	                		}
	                	} else {
	                		if (fieldName == 'TN' && $('#' + srchKind + 'ExactMatch').prop('checked')) {
	                			fieldName = 'TNM';
	                		}
	                		query += fieldName + '=[' + tempValue + ']';
	                	}
	                }
	                
	                if (operator == 'AND') {
	                    query += '*';
	                } else if (operator == 'OR') {
	                    query += '+';
	                }
	            }
	            // 통계_스마트검색
	            let statFieldName = fieldName.toUpperCase();
	            if (srchKind == 'kdg' || srchKind == 'ktm') {
	            	if (fieldName == 'PRD') {
	            		statFieldName = 'UD';
		            } else if (fieldName == 'PRN') {
		            	statFieldName = 'UN';
		            } 
	            	let regExphgcs = /^(?!\s*$)[ㄱ-ㅎ\s]*$/;
	            	if (srchKind == 'ktm' && regExphgcs.test(tempValue)) {
	            		recordServiceStats(srchKind, 'SMART', 'TNCH');
	            	}
	            } else if (srchKind == 'kpat') {
	            	if (fieldName == 'IAN') { 
	            		statFieldName = 'FN';
	            	} else if (fieldName == 'ION') {
	            		statFieldName = 'FON';
	            	}
	            } else if (srchKind == 'kdc') {
	            	if (inputKind == 'date') {	// 유사검색 일자 제외처리
	            		statFieldName = '';
	            	} else {
	            		let kdcTarget = $(item).parents().find('div[data-visible-group="sd0201"].active').attr('data-visible-target');
		            	if (kdcTarget == 'sd0201_01') {
		            		statFieldName = 'K' + statFieldName;
		            	} else if (kdcTarget == 'sd0201_02') {
		            		statFieldName = 'J' + statFieldName;
		            	} else if (kdcTarget == 'sd0201_03') {
		            		statFieldName = 'I' + statFieldName;
		            	}
	            	}
	            }
	            recordServiceStats(srchKind, 'SMART', statFieldName);
	        }
	    });

		if (tabId == 'sd01') { // 권리별 검색
			// 항목 값이 없는지 체크
			if (query == '' && mode != 'weightSearch') {
				alert(i18next.t('cmn.txt6'));
				return;
			}
			// 마지막 연산자 버리기
			query = query.slice(0, -1);
		} else { // 특화검색
			query = query;
		}
		
		let queryTextTop = query; // 상단 입력란에 기입될 검색식
		try {
			if (isKeywordValidation(query)) {
				//By J.H.S 20130813 국문 메인홈페이지에서 검색 할 때 출원번호, 등록번호 - 형식으로 입력시 "" 치환하여 검색식 입력하도록 개선함. 
				//입력된 숫자가 등록번호형식일 경우 "10-0000123" 대쉬 제거 by lhy 2013.03.19
				var regExpRegNum1 = /^\d{2}-\d{7}$/;
				if(regExpRegNum1.test(query)){
					query = query.replace("-","");
				}

				//입력된 숫자가 등록번호형식일 경우 "10-0000123-0000" 대쉬 제거 by lhy 2013.03.19
				var regExpRegNum2 = /^\d{2}-\d{7}-\d{4}$/;
				if(regExpRegNum2.test(query)){
					query = query.replace(/-/gi,"");
				}

				//입력된 숫자가 출원번호형식일 경우 "40-2003-0048429" 대쉬 제거 by lhy 2013.03.19
				var regExpRegNum3 = /^\d{2}-\d{4}-\d{7}$/;
				if(regExpRegNum3.test(query)){
					query = query.replace(/-/gi,"");
				}
				
				//인명정보 Validation(하이픈[-]제거)
				query = bioInfoValidation(query);
				
				//독일어 특수문자 치환
				query = convertGermanEntities(query);
				
				if (tabId != 'sd02') {
					query = removeOperatorBlank(query);
				}
			}
		} catch (e) {
			alert(e);
			return false;
		}
		
		if (tabId == 'sd01' || (tabId == 'sd02' && sTabId == 'sd02_05') ) { // 권리별검색
			/*
			 * 2026.06.09 OJE
			 * 아이디어공모전 상세검색 시 기술분류(TCC)가 적용되지 않는 문제를 개선하기 위해
			 * 선택한 TCC 값을 expression에 포함하여 전달하도록 수정
			 */
			expression = query;

			// 아이디어 공모전 - 기술분류
			if(srchKind == 'cntst') {
			    let tempTcc = '';

			    $.each($elsCheck, function(idx, item) {
			        if($(item).attr('name') == 'sd010502_g01' && !$(item).is('[data-check-all]') && $(item).is(':checked')) {
			            if(tempTcc != '') {
			                tempTcc += ',';
			            }
			            tempTcc += $(item).val();
			        }
			    });

			    if(tempTcc != '') {
			    	expression += '*(TCC=[' + tempTcc + '])';
			    }
			}

			// 메인화면
			if ((window.location.pathname.indexOf('/main.do') > -1) && sTabId != 'sd02_05') {
				$('#searchKind').val('detailSearch');
				$('#searchRight').val(srchKind);
				$('#queryTextTop').val(queryTextTop);
				$('#queryText').val(query);
				$('#expression').val(expression);
				$('#pageLanguage').val(i18next.language);	// 한-영 변역검색 페이지 언어 처리
				if ($('#' + srchKind + 'SearchInTrans').prop('checked')) {
					$('#searchInTrans').val('Y');
				} else {
					$('#searchInTrans').val('N');
				}
				if ($('#' + srchKind + 'ExactMatch').prop('checked')) {
					$('#searchInComplate').val('Y');
				} else {
					$('#searchInComplate').val('N');
				}
				
				window.sessionStorage.setItem('queryText', query);
				window.sessionStorage.setItem('expression', expression);
				
				$('#mainSearchForm').submit();
			}
			// 검색결과
			else if ((window.location.pathname.indexOf('/searchResult.do') > -1) && sTabId != 'sd02_05') {
				// 해당 권리의 form 값 셋팅
				let targetFormId = '#' + srchKind + 'SearchForm';
				$(targetFormId).find('input[name=queryText]').val(query);
				$(targetFormId).find('input[name=expression]').val(expression);
				$(targetFormId).find('input[name=pageLanguage]').val(i18next.language);	// 한-영 변역검색 페이지 언어 처리
				if ($('#' + srchKind + 'SearchInTrans').prop('checked')) {
					$(targetFormId).find('input[name=searchInTrans]').val('Y');
				} else {
					$(targetFormId).find('input[name=searchInTrans]').val('N');
				}
				if ($('#' + srchKind + 'ExactMatch').prop('checked')) {
					$(targetFormId).find('input[name=searchInComplate]').val('Y');
				} else {
					$(targetFormId).find('input[name=searchInComplate]').val('N');
				}
				$('#indtechSearchFlag').val('N');
				checkRequest();
				
				initDataForDetailSearch(srchKind);
				initChangeViewBtn(srchKind);
				
				$('#searchKind').val('detailSearch');
				
				doSearch(srchKind, 'detailSearch');
				//$('#queryText').val(query);
				$('#queryText').val(queryTextTop);
				initSortOption('detailSearch');	
				////(웹접근성) 상세검색 권리별  title 설정하기
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
						cyber: "인터넷기술공지 검색",
						cntst: "아이디어공모전 검색",
						arti: "논문 검색"
				};
				//웹접근성 권리별 title 검색 설정
				document.title = "홈 > 지식재산정보검색 > " + activTapMap[srchKind] + " (검색어: " + queryTextTop + ")";
			}
			else if(sTabId == 'sd02_05') {
				getIPCQuery();
			}
		} else { // 특화검색
			// 유사특허
			if (sTabId == 'sd02_01') {
				let $checkedInput = $activeDiv1.find('input[type=checkbox]:checked').not(':disabled');
				var tempCollection = '';
				var tempNext = '';
				if (targetId == 'sd0201_01') {
					tempCollection = 'kr';
					tempNext = 'SimpleList';
					if ($checkedInput.length > 1) {
						tempCollection += '+pat++sil+';
					} else {
						tempCollection += '+' + $checkedInput.val() + '+';
					}
				} else if (targetId == 'sd0201_02') {
					tempCollection = 'jp';
					tempNext = 'jpList';
					if ($checkedInput.length > 1) {
						tempCollection += '+pat++sil+';
					} else {
						tempCollection += '+' + $checkedInput.val() + '+';
					}
				} else if (targetId == 'sd0201_03') {
					tempCollection = 'IDEA';
					tempNext = 'ideaList';
				}
				
				// 검색키워드 가중치 조절 query 셋팅
				let $targetWeightObj1 = $('span[id^=weightKeyword]');
				let $targetWeightObj2 = $('input[id^=skc]');
				let weightQuery = '';
				let total_score = 0;
				let total_score_per = 0;
				let query_ori = '';
				let query_ori_s = '';
				let flag_keyword = 'N';
				// 검색키워드 가중치 조절 파라미터 셋팅
				if (mode == 'weightSearch') {
					$.each($targetWeightObj1, function(i, t){
						if(parseInt($targetWeightObj2.eq(i).val()) > 100) {
							flag_keyword = 'Y1';
						}
						if(typeof parseInt($targetWeightObj2.eq(i).val()) === 'number' && Number.isFinite(parseInt($targetWeightObj2.eq(i).val())) && parseInt($targetWeightObj2.eq(i).val()) !== 0) {		
							weightQuery += $(t).text() + '^' + $targetWeightObj2.eq(i).val() + ' ';
							total_score_per += parseInt($targetWeightObj2.eq(i).val());
						} else {
							
						}
						
					});
					if (total_score_per == 0) {
						flag_keyword = 'Y2';
					}
					dateQuery['weightQuery'] = weightQuery;
					tempStrstat = $('input[name=strstatBak]').val();
					total_score = $('input[name=total_score]').val();
					query_ori = $('input[name=query_ori]').val();
					query_ori_s = $('input[name=query_ori_s]').val();
					query = $('input[name=queryBak]').val();
					dateQuery['searchKeywordWeightYn'] = 'Y';
				}
				
				dateQuery['query'] = query;
				dateQuery['collection'] = tempCollection;
				dateQuery['next'] = tempNext;
				dateQuery['strstat'] = tempStrstat;
				dateQuery['total_score'] = total_score;
				dateQuery['query_ori'] = query_ori;
				dateQuery['query_ori_s'] = query_ori_s;
				
				if (mode == 'weightView') {
					searchKeywordView(dateQuery);
				} else {
					if(flag_keyword == 'N') {
						// 유사특허 검색 통계
						recordServiceStats('KHOME', 'SMART', 'SIMSR');
						openWindow('special', dateQuery);
					} else {
						if(flag_keyword == 'Y1'){
							alert("키워드별 가중치 점수는 100점을 초과할 수 없습니다.\n값을 조정하여 다시 검색해주세요.");
						} else if (flag_keyword == 'Y2') {
							alert("모든 키워드별 가중치 점수가 0점 또는 공백입니다.\n하나 이상의 값을 입력 후 검색해주세요.");
						}
						return false;
					}
					
				}
			} else {
				// 국유특허
				if (sTabId == 'sd02_02') {
					// 권리구분 셋팅
					dateQuery['pat_tpcd'] = srchKind;
					
					// 실시료 구분 셋팅
					dateQuery['pay_tpcd'] = $activeDiv1.find('#sd0202_g02_01').prop('checked') ? '전체' : $activeDiv1.find('input[name=sd0202_g02]:checked').val();
					
					// 발명기관 셋팅
					dateQuery['invnt_instn_nm'] = $activeDiv1.find('#sd020201_g01_category_01').val();
					
					// 발명의명칭, 등록번호, 등록일자 셋팅
					let regEx = /(\w+)=\[(.*?)\]/g;
					let match;
					while ((match = regEx.exec(query)) !== null) {
						const [_, key, value] = match;
						dateQuery[key] = value;
					}
					
					// 모드
					dateQuery['mode'] = 'natlPat';
					dateQuery['sortField'] = 'RGSTNO';
					dateQuery['sortState'] = 'DESC';
					//웹접근성 국유특허 검색 title 수정
					document.title = "홈 > 지식재산정보검색 > 국유특허 검색" ;
				}
				// 물질특허
				else if (sTabId == 'sd02_03') {
					// 발명연도 셋팅
					dateQuery['publicYear'] = $activeDiv1.find('#sd0203_g01').val();
					
					// 제품유형 셋팅
					dateQuery['patentType'] = $activeDiv1.find('#sd0203_g03').val();
					
					// 번호 형태 셋팅
					dateQuery['numberType'] = $activeDiv1.find('#sd0203_g04_category_01').val();
					
					// 만료예정일, 번호, 명칭 셋팅
					let regEx = /(\w+)=\[(.*?)\]/g;
					let match;
					while ((match = regEx.exec(query)) !== null) {
						const [_, key, value] = match;
						dateQuery[key] = value;
					}
					
					// 모드
					dateQuery['mode'] = 'mPat';
					dateQuery['sortField'] = 'APPLNO';
					dateQuery['sortState'] = 'DESC';
					//웹접근성 물질특허 검색 title 수정
					document.title = "홈 > 지식재산정보검색 > 물질특허 검색" ;
				}
				// 미생물 기탁ㆍ분양정보
				else if (tabId == 'sd02' && sTabId == 'sd02_04') {
					// 기탁기관 셋팅
					dateQuery['micgmDpathNm'] = $activeDiv1.find('#sd0204_g01').val();
					
					// 국내외기탁 셋팅 
					dateQuery['mofmcDmstcYn'] = $activeDiv1.find('#sd0204_g02_01').prop('checked') ? 'A' : $activeDiv1.find('input[name=sd0204_g02]:checked').val();
					
					//분양이력 여부 셋팅
					dateQuery['mcdtbYn'] = $activeDiv1.find('#sd0204_g10_01').prop('checked') ? 'A' : $activeDiv1.find('input[name=sd0204_g10]:checked').val();
					
					// 나머지 셋팅
					let regEx = /(\w+)=\[(.*?)\]/g;
					let match;
					while ((match = regEx.exec(query)) !== null) {
						const [_, key, value] = match;
						dateQuery[key] = value;
					}
					
					// 모드
					dateQuery['mode'] = 'etcPat';
					dateQuery['sortField'] = 'APPLNO';
					dateQuery['sortState'] = 'DESC';
					//웹접근성 물질특허 검색 title 수정
					document.title = "홈 > 지식재산정보검색 > 미생물 기탁ㆍ분양정보 검색" ;
				}
				
				dateQuery['currentPage'] = '1';
				dateQuery['numPerPage'] = '30';
				dateQuery['searchKind'] = 'specializationSearch';
				dateQuery['searchRight'] = dateQuery.mode;
				
				// 메인
				if (window.location.pathname.indexOf('/main.do') > -1) {
					doSpecializationSearch('main', dateQuery);
				}
				// 검색결과
				else if (window.location.pathname.indexOf('/searchResult.do') > -1) {
					let $targetFrm = $('#' + dateQuery.mode + 'SearchForm');
					$.each($targetFrm.find('input[type=hidden]'), function(idx, item) {
						let itemName = $(item).attr('name');
						if (dateQuery[itemName] != undefined) {
							$(item).val(dateQuery[itemName]);
						} else {
							$(item).val('');
						}
					});
					
					$('#searchKind').val('specializationSearch');
					$('#searchRight').val(dateQuery.mode);
					initDataForDetailSearch(dateQuery.mode);
					doSearch(dateQuery.mode, 'specialization');
				}
			}
			// 특화검색 통계 추가
			const spSearchMap = {
					sd02_02:"NATSR", sd02_03:"PRDSR", sd02_04:"MICSR"
    		};
			recordServiceStats('KHOME', 'SMART', spSearchMap[sTabId]);
		}
		/*
		 * 2026.06.11 OJE
		 * 상세검색 시 선택보기를 초기화하도록  doDetailSearch() 마지막에 initSelectView() 호출
		 */
		// 선택보기 초기화
		initSelectView();
		
		// 모달창 닫기
		if (mode != 'weightView' && mode != 'weightSearch') {
		    $('button[data-modal-close=modalSearchDetail]').trigger('click');
		}
	}
}

function isKeywordValidation(S)
{
	let tabId = $('#modalSearchDetail').find('.btn-tab.active').data('tab-id');
	let tab_details = $('#modalSearchDetail').find('.tab-con.active').find('.btn-category.active').data('visible-control');
	const modal_active = $('#modalSearchDetail.modal').hasClass('active') ? 'Y' : 'N';
	
	if (tabId != 'sd02' || (tab_details == 'sd02_05' && modal_active == 'N')) {
		if (S == void 0 || S == "" || S.length == 0) {
			throw (i18next.t('cmn.txt7'));
		}
	}
	
	S = S.replace(/\r\n/g, "");

	if (checkValid(S) && checkValidation(S)) {
		return (DelSpecialChar(S) != "");
	}

	return true;
}

function checkValid(V)
{
	if (V == void 0 || V == "" || V.length == 0)
		return false;

	if (!CompareCountChar(V, '(', ')')) {
		throw (i18next.t('cmn.txt8'));
	}

	if (!CompareCountChar(V, '[', ']')) {
		throw (i18next.t('cmn.txt9'));
	}

	var quoteCnt = 0;

	if (V.indexOf("\"") > -1) {
		for (var i = 0; i < V.length; i++) {
			if (V.charAt(i) == '\"')
				quoteCnt++;
		}
	}

	if ((quoteCnt % 2) != 0) {
		throw (i18next.t('cmn.txt10'));
	}

	return true;
}

function checkValidation(V)
{
	V = DelSpecialChar(V);

	if (V.indexOf('!') > -1) {
		if (V.indexOf(' ') == -1 && V.indexOf('*') == -1) {
			throw (i18next.t('cmn.txt11'));
		}
	}

	return checkSpecialChar(V);
}

function checkSpecialChar(V)
{
	var str = V;
	str = str.replace(/ /g, '');

	var specialchar = /\&\#|\<|\|\>|\(\?\!\)/g;

	if (specialchar.test(str)) {
		throw (i18next.t('cmn.txt12') + str.match(specialchar) + " ]");
	}

	return true;
}

function removeOperatorBlank(V)
{
	var isStr = false;
	var resultStr = "";
	var ch_prev_prev = "";
	var ch_prev = "";
	var ch_now = "";
	var ch_next = "";

	for (var i = 0; i < V.length; i++) {
		if (i >= 2) {
			ch_prev_prev = V.charAt(i - 2);
		} else {
			ch_prev_prev = "";
		}

		if (i >= 1) {
			ch_prev = V.charAt(i - 1);
		} else {
			ch_prev = "";
		}

		ch_now = V.charAt(i);

		if (i < V.length - 1) {
			ch_next = V.charAt(i + 1);
		} else {
			ch_next = "";
		}

		if (ch_now == "\"") {
			isStr = !isStr;
		}

		if (!isStr && ch_now == " " && ch_next != " " && !(ch_next == "*" || ch_next == "+" || ch_next == "!" || ch_next == "^") && !(ch_prev == "*" || ch_prev == "+" || ch_prev == "!" || ch_prev == "^") && !(ch_prev_prev == "^" && (ch_prev == "1" || ch_prev == "2" || ch_prev == "3"))) {
			resultStr += "*";
			continue;
		}

		if (!isStr && ch_now == " " && (ch_next == "*" || ch_next == "+" || ch_next == "^")) {
			continue;
		}

		if (!isStr && ch_now == " " && (ch_prev == "*" || ch_prev == "+" || ch_prev == "!" || ch_prev_prev != "^" && (ch_prev == "1" || ch_prev == "2" || ch_prev == "3"))) {
			continue;
		}
		if (!isStr && ch_now == " ") {
			continue;
		}
		resultStr += ch_now;
	}

	resultStr = resultStr.replace(/\*\*/g, "*");
	resultStr = resultStr.replace(/!\*/g, "!");
	resultStr = resultStr.replace(/\^\*/g, "^");
	resultStr = resultStr.replace(/\^1\*/g, "^1");
	resultStr = resultStr.replace(/\^2\*/g, "^2");
	resultStr = resultStr.replace(/\^3\*/g, "^3");

	return resultStr;
}

function CountChar(S, C)
{
	var count = 0;
	for (var i = 0; i <= S.length; i++) {
		if (S.charAt(i) == C)
			count++;
	}
	return count;
}

function CompareCountChar(S, C1, C2)
{
	return (CountChar(S, C1) == CountChar(S, C2));
}

function DelSpecialChar(V)
{
	var str = V;
	str = str.replace(/[\r\n]/g, '')

	while (1) {
		if (str.substring(str.length - 1, str.length) == ' ' || str.substring(str.length - 1, str.length) == '+' || str.substring(str.length - 1, str.length) == '*' || str.substring(str.length - 1, str.length) == '!')
			str = str.substring(0, str.length - 1)
		else
			break;
	}

	str = str.replace(/\*\*/g, '*');
	str = str.replace(/\+\+/g, '+');
	str = str.replace(/\*\+/g, '*');
	str = str.replace(/\+\*/g, '*');
	str = str.replace(/  /g, ' ');

	return str;
}

function addComma(value)
{
	return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function changeDateFormat(value)
{
	if (value.length == 8)
		return String(value).replace(/(\d{4})(\d{2})(\d{2})/g, '$1.$2.$3');
	else if (value.length == 6)
		return String(value).replace(/(\d{4})(\d{2})/g, '$1.$2');
	else
		return value;
}

function maxLengthCheck(object)
{
	if (object.name == 'numberInput') {
		object.value = object.value.replace(/[^0-9\+\?]/g, '');
	}

	if (object.value.length > object.maxLength) {
		object.value = object.value.slice(0, object.max.length);
	}
}

function inputCheck(object)
{
	object.value = object.value.replace(/[\#\$\%\&\<\>\+\?\=\"\'\{\}]/g, '');

	if (object.value.length > object.maxLength) {
		object.value = object.value.slice(0, object.max.length);
	}
}

function getContextPath()
{
	return sessionStorage.getItem("contextpath");
}

function getCookieOption()
{
	var opt = {};
	opt.domain = "kipris.or.kr";
	opt.path = "/";
	opt.expires = 7;
	return opt;
}

function mergeCount(kind)
{
	var checker = $.cookie('MOBILE_KIPRIS_TODAY_CNT');

	if (checker != "CHECKED") {
		var cookieOption = getCookieOption();
		var newExpireTime = new Date();
		newExpireTime.setSeconds(newExpireTime.getSeconds() + 3);
		cookieOption.expires = newExpireTime;

		$.cookie('MOBILE_KIPRIS_TODAY_CNT', "CHECKED", cookieOption);
		$.post(getContextPath() + '/mbl/cmm/mergeWebCount.mdo', 'kind=' + kind);
	}
}

function getCurrentDateTime(format)
{
	let now = new Date();
	let year = now.getFullYear();
	let month = ('0' + (now.getMonth() + 1)).slice(-2);
	let day = ('0' + now.getDate()).slice(-2);
	let hours = ('0' + now.getHours()).slice(-2);
	let minutes = ('0' + now.getMinutes()).slice(-2);
	let seconds = ('0' + now.getSeconds()).slice(-2);
	
	let dateTimeStr = year + month + day + hours + minutes + seconds;
	
	// format = 'yyyy년 mm월 dd일'
	if (format != undefined) {
		dateTimeStr = format.replace('yyyy', year);
		dateTimeStr = dateTimeStr.replace('mm', month);
		dateTimeStr = dateTimeStr.replace('dd', day);
	}
	
	return dateTimeStr;
}

// 인명정보 검증 및 가공 함수
function bioInfoValidation(Str)
{
	let regex = /([\w()+]+)=\[(.*?)\]/g; 	// '='과 '[]'를 기준으로 (key,value)구분하는 정규식
	let matches = [];						// 검색식 저장 배열
	let hash = {};							// 파싱 해쉬
	
	// 검색식 파싱(문자열->해쉬)및 검색식 순서 저장
	let modifiedStr = Str.replace(regex, function(match, key, value){
		if ('AP|IN|IV|AG|RG|EL|NL|TRH|TR|DP|DG|PP|PG'.indexOf(key) >= 0) {
			if (!hash[key]) {
				hash[key] = [];
			}
			hash[key].push(value);
		}
		
		matches.push({key:key, value:value, match:match});
		return "{" + (matches.length - 1) + "}";
	});
	
	// 해쉬 데이터 가공
	for (var key in hash) {
		if (hash.hasOwnProperty(key)) {
			for (var i = 0; i < hash[key].length; i++) {
				hash[key][i] = hash[key][i].replaceAll('-', '');
			}
		}
	}
	
	// 검색식 순서에 맞게 다시 기입
	var finalStr = modifiedStr.replace(/{(\d+)}/g, function(match, index) {
		var original = matches[parseInt(index, 10)];
		
		if (hash[original.key]) {
			return original.key + "=[" + hash[original.key].shift() + "]";
		} else {
			return original.match;
		}
	});
	
	// 최종 검색식 반환
	return finalStr;
}

function openWindow(mode, params)
{
	let actionUrl = '';
	if (mode == 'detail') {
		// 통계_새창열기
		recordServiceStats(currentTab2, 'VIEW', 'NEWV');
		actionUrl = '/khome/detail/newWindow.do';
	} else if (mode == 'similar') {
		if (Object.keys(params)[0] == 'collection') {
			actionUrl = '/khome/search/searchResultSimilarTemp.do';
		} else {
			if (currentTab2 == 'kpat') {
				// 통계_검색결과 유사특허
				recordServiceStats(currentTab2, 'OPSVC', 'SRSI');
			}
			actionUrl = '/khome/search/searchResultSimilar.do';
		}
	} else if (mode == 'intnl') {
		let translateOption = '';
		if (/KR/i.test(params.docId)) {
			translateOption = '&translateOption=kipo';
		}
		actionUrl = 'https://patentscope.wipo.int/search/en/detail.jsf?docId=' + params.docNum + translateOption;
	} else if (mode == 'imageBig' || mode == 'imageTotal') {
		// 통계_대표도면 확대보기
		recordServiceStats(currentTab2, 'OPSVC', 'IMZM');
		let imgParams = '';
		actionUrl = '/khome/detail/' + mode + '.do';
		
		$.each(Object.keys(params), function(idx, key) {
			if (idx > 0) {
				if (imgParams == '') {
					imgParams += '?';
				} else {
					imgParams += '&';
				}
				imgParams += key + '=' + params[key];
			}
		});
		
		params['applno']= params.applno;
		params['imgUrl'] = '/' + params.right + '/remoteFile.do' + imgParams;
		params['tl'] = $('.head-title .title').text();
		params['tle'] = $('.head-title .eng').text();
	} else if (mode == 'translate'){
		// 통계_기계번역
		if (currentTab2 == 'kpat') {
			recordServiceStats(currentTab2, 'TRANS', 'KR');
		} else if (currentTab2 == 'abpat' || currentTab2 == 'abpatTrans') {
			if(params.applno != '' && params.applno != undefined) {
				let cntry = params.applno.slice(0, 2);
				if ('US|EP|WO|JP|CN'.indexOf(cntry) >= 0){
					recordServiceStats(currentTab2, 'TRANS', cntry);
				}
			}
		}
		actionUrl = '/khome/detail/translate.do';
	} else if (mode == 'special'){
		actionUrl = '/khome/search/searchResultSpecial.do';
	} else if (mode == 'printResult') {
		actionUrl = '/khome/search/printResult.do';
	} else if (mode == 'printDetail') {
		actionUrl = '/khome/detail/printDetail.do';
	} else if (mode == 'suggestSearch') {
		// 통계_추천검색식
		recordServiceStats('KHOME', 'OPSVC', 'REEX');
		actionUrl = '/khome/search/suggestSearch.do';
	} else if (mode == 'giSearch') {
		// 통계_지리적표시 보기
		recordServiceStats('KTM', 'OPSVC', 'OGI');
		actionUrl = '/khome/search/searchResultGi.do';
	}
	
	//Key값별 서로 다른 창을 띄우기 위한 target설정
	let targetKey = '';
	if (mode == 'imageBig' || mode == 'imageTotal') {
		targetKey = params[Object.keys(params)[2]];
	} else if (mode == 'detail') {
		targetKey = params[Object.keys(params)[0]] + ',' + params[Object.keys(params)[1]];
	} else {
		targetKey = params[Object.keys(params)[0]];
	}
	if (mode != 'intnl'){
		let $tempForm = $('<form>', {
			id: 'tempForm',
			name: 'tempForm',
			method: 'POST',
			target: targetKey,
			action: actionUrl
		});
		
		$.each(params, function(key, val) {
			$tempForm.append($('<input/>', {type: 'hidden', name: key, value: val}));
		});
		
		$tempForm.appendTo('body');
		window.open('', targetKey, 'width=' + screen.width + ', height=' + '1000' + ', menubar=no, toolbar=no, location=no, status=no, fullscreen=yes');
		$tempForm.submit();
		$tempForm.remove();
	} else {
		window.open(actionUrl, targetKey, 'width=' + screen.width + ', height=' + '1000' + ', menubar=no, toolbar=no, location=no, status=no, fullscreen=yes');
	}
}

// 부분 로딩바 toggle
function toggleLoadingDialog(target, visibility)
{
	if ($(target).length == 0) {
		target = 'body';
	}
	
	if (visibility) {
		if ($(target).find('.loading-dialog').length == 0) {
			let rect = $(target)[0].getBoundingClientRect();
			let scrollTop = $(window).scrollTop();
			let scrollLeft = $(window).scrollLeft();
			let top = rect.top < 0 ? scrollTop : rect.top + scrollTop;
			let left = rect.left + scrollLeft;
			let offsetWidth = target.indexOf('modal') > -1 ? 0 : 20;
			
			if ($(target).css('position') != 'static') {
				let offset = $(target).offset();
				top -= offset.top;
				left -= offset.left;
			}
			let visibleHeight = Math.min(rect.height, window.innerHeight - rect.top, window.innerHeight);
			let wrapStyle = 'position: absolute; top: ' + top + 'px; left: ' + left + 'px; width: ' + (rect.width + offsetWidth) + 'px; height: ' + visibleHeight + 'px;';
			
			let $wrapDiv = $('<div>', {'style': wrapStyle});
			let $loadingDiv = $('<div>', {'class': 'loading-dialog active', 'data-s-type': 'local', 'data-size': 'xs'});
			let $textBox = $('<strong>', {'class': 'dialog-box'});
			//$textBox.append(i18next.t('cmn.txt13'));
			$textBox.append('정보를 불러오고 있습니다.');
			
			$loadingDiv.append($textBox);
			$wrapDiv.append($loadingDiv);
			$(target).append($wrapDiv);
		}
		$('body').attr('data-prevent-scroll', 'on');
	} else {
		$(target).find('.loading-dialog').parent().remove();
		if (target.indexOf('modal') < 0) {
			$('body').attr('data-prevent-scroll', 'off');
		}
	}
	
	loadingDialogTarget = target;
}

// 등록사항 조회 초기화(국내상표 분할등록 한정)
let rgstListHtml = '';
function initRgstInfo(rgstno, btnObj, rgstList)
{
	// 분할등록 리스트 존재하지 않을 경우, 일반 등록사항 호출
	if (rgstList == '') { 
		goRgstInfo(rgstno, btnObj);
	} 
	// 분할등록 리스트 존재할 경우, 리스트 html을 전역변수에 저장하고 리스트 출력
	else {
		if (rgstListHtml != '') {
			$('.tab-con[data-tab-id=detail05]').html(rgstListHtml);
		} else {
			rgstListHtml = $('.tab-con[data-tab-id=detail05]').html();
		}
	}
}

// 등록사항 조회(새창포함)
function goRgstInfo(rgstno, btnObj)
{
	toggleLoadingDialog('#mainResultDetail div.body', true);
	
	// (btnObj == undefined) : 새창
	let targetTabId = '';
	if (btnObj != undefined) {
		targetTabId = $(btnObj).data('tab-id');
	}
	
	// 통계_상세정보 등록사항
	recordServiceStats(currentTab2, 'BIBLO', 'RGST');
	
	$.ajax({
		async: true,
		type: 'POST',
		url: '/khome/biblio/rgstInfo.do',
		data: {rgstno: rgstno},
		dataType: 'html',
		success: function(data)
		{
			if (btnObj != undefined) {
				$('#mainResultDetailArea').find('div[data-tab-id=' + targetTabId + ']').html(data);
			} else {
				$('#wrap').html(data);
			}
			
		},
		error: function(xhr, status, error)
		{
			alert(i18next.t('ms.join.txt7'));
			
		},
		complete: function() {
			toggleLoadingDialog(loadingDialogTarget, false);
		}
	});
}

// 입력 도우미 체크박스 콜백
let supportCheckArray = [];
function supportCheckValue(obj, target)
{
	let checkedValue = '';
	if ($(obj).attr('type') == 'checkbox') {
		let objVal = $(obj).val().replace(/\s/g, '');
		if ($(obj).prop('checked') == true) {
			supportCheckArray.push(objVal);
		} else {
			let tempNewArray = [];
			$.each(supportCheckArray, function(idx, item) {
				if (objVal != item) {
					tempNewArray.push(item);
				}
			});
			supportCheckArray = tempNewArray;
		}
	} else if ($(obj).attr('type') == 'button'){
		let objVal = $(obj).data('value').toString().replace(/\s/g, '');
		let findIndex = supportCheckArray.indexOf(objVal);
		if (findIndex > -1) {
			supportCheckArray.splice(findIndex, 1);
		} else {
			supportCheckArray.push(objVal);
		}
	} else {
		supportCheckArray = obj;
	}
	
	// 체크값 생성
	$.each(supportCheckArray, function(idx, item) {
		if (checkedValue != '') {
			checkedValue += '+';
		}
		checkedValue += item;
	});
	
	$(target).val(checkedValue);
}

// 최근검색어 저장
function saveRecentKeyword(keyword)
{
	let tempKeyword = keyword.trim();
	if (tempKeyword == '') {
		return;
	}
	
	if (tempKeyword.length > 2000) {
		tempKeyword = tempKeyword.substring(0, 1997) + '...';
	}
	
	// xss 필터링
	keyword = encodeURIComponent(sanitizeInput(tempKeyword));
	
	$.ajax({
		async: false,
		type: 'POST',
		url: '/khome/myKipris/mngtQryPatentChange.do',
		data: 'mode=recentInsert' + '&querys=' + keyword,
		dataType: 'json',
		error: function(xhr, status, error)
		{
			console.log('최근검색어 저장 중 오류 발생');
		},
	});
	
	let recentKeywordArray = JSON.parse(localStorage.getItem('recentKeyword'));
	if (recentKeywordArray == null) {
		recentKeywordArray = [];
	} else {
		// 50개가 넘어가면 마지막 요소 삭제
		if (recentKeywordArray.length >= 50) {
			recentKeywordArray.pop();
		}
		// 동일 키워드가 존재하면 기존건 삭제
		let findIndex = recentKeywordArray.indexOf(keyword);
		if (findIndex > -1) {
			recentKeywordArray.splice(findIndex, 1);
			$('.search-recent .list li').eq(findIndex).find('button.btn-remove').click();
		}
	}
	
	recentKeywordArray.unshift(keyword);
	localStorage.setItem('recentKeyword', JSON.stringify(recentKeywordArray));
	
	let templateHtml = makeRecentHtml([keyword]);
	
	$('.search-recent .list').prepend(templateHtml);
}

// 최근검색어 삭제
function removeRecentKeyword(keyword, allRemove)
{
	if (allRemove) {
		localStorage.removeItem('recentKeyword');
	} else {
		let recentKeywordArray = JSON.parse(localStorage.getItem('recentKeyword'));
		if (recentKeywordArray != undefined && recentKeywordArray.length != 0) {
			let findIndex = recentKeywordArray.indexOf(keyword);
			if (findIndex > -1) {
				recentKeywordArray.splice(findIndex, 1);
				localStorage.setItem('recentKeyword', JSON.stringify(recentKeywordArray));
			}
		}
	}
}

// 최근검색어 초기화
function initRecentKeyword()
{
	let recentKeywordArray = JSON.parse(localStorage.getItem('recentKeyword'));
	let templateHtml = makeRecentHtml(recentKeywordArray);
	$('.search-recent .list').html(templateHtml);
}

// 최근검색어 템플릿 생성
function makeRecentHtml(recentKeywordArray)
{
	let templateHtml = '';
	$.each(recentKeywordArray, function(idx, item) {
		templateHtml += '<li class="item">';
		templateHtml += '<button type="button" class="btn-recent" onclick="searchCommonModule.applyRecent(\'' + item + '\',this)">' + decodeURIComponent(item) + '</button>';
		templateHtml += '<button type="button" class="btn-remove btn-close" onclick="searchCommonModule.removeRecent(this); removeRecentKeyword(\'' + item + '\', false);" title="검색히스토리 \''+ decodeURIComponent(item) +'\' 선택삭제">';
		templateHtml += '<span class="blind" alt="">검색히스토리 선택삭제</span>';
		templateHtml += '</button>';
		templateHtml += '</li>';
	});
	return templateHtml;
}

// XSS 차단
function sanitizeInput(input) {
    // 1. 악의적인 패턴 제거
    const filteredInput = input
        // Remove script-like tags
        .replace(/<script.*?>.*?<\/script>/gi, '')
        .replace(/<style.*?>.*?<\/style>/gi, '')
        .replace(/<iframe.*?>.*?<\/iframe>/gi, '')
        .replace(/<object.*?>.*?<\/object>/gi, '')
        .replace(/<embed.*?>.*?<\/embed>/gi, '')
        .replace(/<link.*?>/gi, '')
        
        // Remove inline event handlers
        .replace(/\son\w+="[^"]*"/gi, '')  // e.g., onclick="..."
        .replace(/\son\w+='[^']*'/gi, '')  // e.g., onclick='...'
        .replace(/\son\w+=\w+/gi, '')      // e.g., onclick=value
        
        // Prevent javascript: and data: URLs
        .replace(/javascript:/gi, '')
        .replace(/data:/gi, '')
        
        // Remove unnecessary tags (e.g., `<img>`, `<video>` without proper context)
        .replace(/<img.*?>/gi, '')
        .replace(/<video.*?>.*?<\/video>/gi, '')
        .replace(/<audio.*?>.*?<\/audio>/gi, '')
        
        // custom
        .replace(/\'/g, '');
    
    // 2. 기본 HTML 엔티티 이스케이프 처리
    const element = document.createElement('div');
    element.textContent = filteredInput;
    const escapedInput = element.innerHTML;
    
    return escapedInput;
}

// enter 입력 감지 및 콜백 함수 호출
function handleEnter(event, callback, args)
{
	if (event.key == 'Enter' || event.keyCode == 13) {
		event.preventDefault();
		if (args != undefined) {
			callback(...args);
		} else {
			callback();
		}
	}
}

//페이징 생성
function generatePagingHtml(currentPage, numPerPage, totalCount, wrap, caller)
{
	if (totalCount != undefined && totalCount != 0) {
		let totalPage = 0;
		if ((totalCount % numPerPage) == 0) {
			totalPage = totalCount / numPerPage;
		} else {
			totalPage = Math.floor(totalCount / numPerPage + 1);
		}
		
		/*let rangeStart = 1;
		if (currentPage - 2 > 1) {
			rangeStart = currentPage - 2;
		}
		
		let rangeEnd = 5;
		if (currentPage + 2 > totalPage) {
			rangeEnd = totalPage;
		} else if (currentPage + 2 > 5) {
			rangeEnd = currentPage + 2;
		}*/
		
		let pageRange = 2;
		let rangeStart = currentPage - pageRange;
		let rangeEnd = currentPage + pageRange;
		
		if (rangeEnd > totalPage) {
			rangeEnd = totalPage;
			rangeStart = totalPage - pageRange * 2;
			rangeStart = rangeStart < 1 ? 1 : rangeStart;
		}
		
		if (rangeStart <= 1) {
			rangeStart = 1;
			rangeEnd = Math.min(pageRange * 2 + 1, totalPage);
		}
		
		let tempHtml = '';
		tempHtml += '<a class="btn-navi prev"' + (currentPage > 1 ? 'href="javascript:goPage(' + (currentPage - 1) + ', \'' + caller + '\');"' : '') + 'data-lang-id="srlt.prv">이전</a>';
		tempHtml += '<div class="page-links">';
		
		if (rangeStart <= 3) {
			for (let i = 1; i < rangeStart; i++) {
				if (i == currentPage) {
					tempHtml += '<a class="active" title="'+i+' 페이지 선택됨">' + i + '</a>';
				} else {
					tempHtml += '<a href="javascript:goPage(' + i + ', \'' + caller + '\');">' + i + '</a>';
				}
			}
		} else {
			tempHtml += '<a href="javascript:goPage(1, \'' + caller + '\');">1</a>';
			tempHtml += '<span class="skip"></span>';
		}

		for (let i = rangeStart; i <= rangeEnd; i++) {
			if (i == currentPage) {
				tempHtml += '<a class="active" title="'+i+' 페이지 선택됨">' + i + '</a>';
			} else {
				tempHtml += '<a href="javascript:goPage(' + i + ', \'' + caller + '\');">' + i + '</a>';
			}
		}

		if (rangeEnd >= totalPage - 2) {
			for (let i = rangeEnd + 1; i <= totalPage; i++) {
				tempHtml += '<a href="javascript:goPage(' + i + ', \'' + caller + '\');">' + i.toLocaleString() + '</a>';
			}
		} else {
			tempHtml += '<span class="skip"></span>';
			tempHtml += '<a href="javascript:goPage(' + totalPage + ', \'' + caller + '\');">' + totalPage.toLocaleString() + '</a>';
		}
		
		tempHtml += '</div>';
		tempHtml += '<a class="btn-navi next"' + (currentPage < totalPage ? 'href="javascript:goPage(' + (currentPage + 1) + ', \'' + caller + '\');"' : '') + 'data-lang-id="srlt.nxt">다음</a>';
		
		let $target = wrap.find('.pagination');
		let tempHtml2 = updateContent(tempHtml);
		$target.html(tempHtml2);
		
		if (wrap.find('.pagination-jump').length != 0) {
			wrap.find('.pagination-jump .totalPage').text(totalPage.toLocaleString());
			wrap.find('.pagination-jump .paginationNum').val(currentPage);
		}
		
		wrap.removeClass('hidden');
	} else {
		let $target = wrap.find('.pagination');
		$target.html('');
	}
}

// 일반 페이지 이동
function goPage(pageNum, caller)
{
	window.scroll({
		top: 0,
		left: 0
	});
	
	if (caller == 'searchResult') {
		/*window.scroll({
			top: 0,
			left: 0,
			// behavior: 'smooth'
		});*/
		let targetFormId = '#' + currentTab2 + 'SearchForm';
		
		// 심판(판례,분쟁)별도 처리
		if (currentTab2 == 'ipNaviConflict' || currentTab2 == 'ipNaviPrcdn') {
			$(targetFormId).find('input[name=pageNum]').val(pageNum);
		} else {
			$(targetFormId).find('input[name=currentPage]').val(pageNum);
		}
		
		doSearch(currentTab2, 'paging');
	} else if(caller == 'list') {
		$('#listSearchForm').find('input[name="currentPage"]').val(pageNum);
		$('#listSearchForm').submit();
	} else if (caller == 'myFolderForm') {
		$('#currentMyFolderPage').val(pageNum);
		doResultSearch(resultCountForPaging, folderIdForPaging, natlCdForPaging);
	} else if (caller == 'myFolderForm_search') {
		$('#currentMyFolderPage').val(pageNum);
		$('#currentMyFolderPageSrch').val(pageNum);
		if(pageNum > 1 && natlCdForPaging == 'TM') {
			doResultSearchTM(resultCountForPaging, folderIdForPaging, natlCdForPaging, 'search_TM');
		} else {
			doResultSearch(resultCountForPaging, folderIdForPaging, natlCdForPaging, 'search');
		}
	} else if (caller == 'mngtQryForm') {
		$('#currentMngtQryPage').val(pageNum);
		getResultList(modeForPaging, resultCountForPaging, folderIdForPaging, natlCdForPaging);
	} else if (caller == 'infoStatis') {
		$('#infoStatisPage').val(pageNum);
		doInfoSearch($('#infoViewRight').val(), $('#infoViewType').val(), 'paging');
	} else if (caller == 'infoExtinct') {
		$('#infoExtinctPage').val(pageNum);
		fnCntPage();
	} else if (caller == 'infoDetailExtinct') {
		$('#infoExtinctDetailPage').val(pageNum);
		fnDetailData($("#date").val(),$("#infoExtinctDetailTotalPage").val());
	} else if (caller == 'myInterestForm') {
		$('#currentMyInterestPage').val(pageNum);
		doNewDataSearch(queryForMyInterestPage, tpcdForMyInterestPage, cntForMyInterestPage, dtForMyInterestPage, dt_fgForMyInterestPage, term_fgForMyInterestPage);
	} else if (caller == 'specializationForm') {
		$('#' + currentTab2 + 'SearchForm').find('input[name=currentPage]').val(pageNum);
		doSearch(currentTab2, 'specialization');
	} else if (caller == 'vocList') {
		$('#pageNum').val(pageNum);
		$('#vocSearchForm').submit();
	} else if (caller == 'giSearchResult') {
		/*window.scroll({
			top: 0,
			left: 0,
			// behavior: 'smooth'
		});*/
		$('#giSearchForm').find('input[name=currentPage]').val(pageNum);
		openPopGiSearch('gi', 'search');
	} else if (caller == 'mediaList') {
		$('#pageNum').val(pageNum);
		$('#mediaSearchForm').submit();
	} else {
		let right = '';
		let $target;
		let modeForPaging;
		if(caller.indexOf('exp') > 0) {
			$target = $('#' + caller.replace('exp', ''));
			right = caller.replace('support', '').replace('exp', '');
			modeForPaging = 'pagingexp';
		} else {
			$target = $('#' + caller);
			right = caller.replace('support', '');
			modeForPaging = 'paging';
		}
		if ($target.length == 0 && right == 'CRM') {
			$target = $('.search-service-list');
		}
		$target.find('input[name=pageNum]').val(pageNum);
		doCodeSearch(right, modeForPaging);
		$target.find('.con-body').scrollTop(0);
	}
}

//페이지 점프 이동
function goJumpPage(obj)
{
	let mode = $(obj).data('mode');
	let targetPage = $(obj).parent().find('input[type=text]').val();
	
	if (mode != undefined) {
		if (mode == 'myFolder') {
			$('#currentMyFolderPage').val(targetPage);
			doResultSearch(resultCountForPaging, folderIdForPaging, natlCdForPaging, 'search');
		} else if (mode == 'mngtQry') {
			$('#currentMngtQryPage').val(targetPage);
			getResultList(modeForPaging, resultCountForPaging, folderIdForPaging, natlCdForPaging);
		} else if (mode == 'myInterest') {
			$('#currentMyInterestPage').val(targetPage);
			doNewDataSearch(queryForMyInterestPage, tpcdForMyInterestPage, cntForMyInterestPage, dtForMyInterestPage ,dt_fgForMyInterestPage, term_fgForMyInterestPage);
		} else if (mode == 'vocList') {
			$('#pageNum').val(targetPage);
			$('#vocSearchForm').submit();
		} else if (mode == 'mediaList') {
			$('#pageNum').val(targetPage);
			$('#mediaSearchForm').submit();
		} else if (mode == 'infoExtinctCnt') {
			$('#infoExtinctPage').val(targetPage);
			fnCntPage();
		} else if (mode == 'infoExtinctDetail') {
			$('#infoExtinctDetailPage').val(targetPage);
			fnDetailData($("#date").val(),$("#infoExtinctDetailTotalPage").val());
		} 
	} else {
		if ($('#searchKind').val() == 'specializationSearch') {
			window.scroll({
				top: 0,
				left: 0,
				// behavior: 'smooth'
			});
			let targetFormId = '#' + currentTab2 + 'SearchForm';
			$(targetFormId).find('input[name=currentPage]').val(targetPage);
			doSearch(currentTab2, 'specialization');
		} else {
			window.scroll({
				top: 0,
				left: 0,
				// behavior: 'smooth'
			});
			let targetFormId = '#' + currentTab2 + 'SearchForm';
			$(targetFormId).find('input[name=currentPage]').val(targetPage);
			doSearch(currentTab2, 'paging');
		}
	}
}

function refreshCaptcha()
{
	$('#captchaImage').attr('src', '/khome/captcha/image.do?type=reload&timestamp=' + new Date().getTime());
	$('#captchaImage').ready(function(){
		$('#captchaAudio').attr('src', '/khome/captcha/audio.do?timestamp=' + new Date().getTime());
	});
	$('#captchaStr').val('');
}

function viewDetail(from, seq) {
    var form = document.createElement("form");
    form.setAttribute("method", "post");
    
    if (from == 'notice') {
    	form.setAttribute("action", "/khome/board/notice/detail.do");
    } else {
    	form.setAttribute("action", "/khome/info/pr/webzineRWD.do");
    }

    var hiddenField = document.createElement("input");
    hiddenField.setAttribute("type", "hidden");
    hiddenField.setAttribute("value", seq);
    
    if (from == 'notice') {
    	hiddenField.setAttribute("name", "seq");
    } else {
    	hiddenField.setAttribute("name", "wzver");
    }

    form.appendChild(hiddenField);
    document.body.appendChild(form);
    form.submit();
}

function playAudio(obj)
{
	obj.disabled = true;
	
	let audio = document.querySelector('#captchaAudio');
	audio.play().then(() => {
		obj.disabled = false;
	}).catch(error => {
		obj.disabled = false;
	});
}

function serviceNotReady()
{
	alert(i18next.t('cmn.txt14'));
	return false;
}

function serviceNotReady2()
{
	alert(i18next.t('cmn.txt15'));
	return false;
}

function addDataLangId()
{
	var $spanElements = $(".add_data_lang");
	$spanElements.each(function(index, element) {
        var $spanElement = $(element); 
        var resultValue = $spanElement.text(); 

        if ($spanElement.attr("data-lang-id")) {
        	return;
        }
        if (resultValue == "서비스 점검/중단") {
            $spanElement.attr("data-lang-id", "list.interruption");
        } else if (resultValue == "행사안내") {
            $spanElement.attr("data-lang-id", "list.eventinfor");
        } else if (resultValue == "교육/세미나") {
            $spanElement.attr("data-lang-id", "list.edu");
        } else if (resultValue == "설문/이벤트") {
            $spanElement.attr("data-lang-id", "list.survey");
        } else if (resultValue == "알림/소식") {
            $spanElement.attr("data-lang-id", "list.news");
        } else {
            $spanElement.attr("data-lang-id", "list.imp");
        }
    });	
}

function getNatlDesc(code) {
	let codeDesc = '';
	if (i18next.language == 'ko') {
		switch (code.toLowerCase()) {
			case 'us' : codeDesc = '미국'; break;
			case 'ep' : codeDesc = '유럽'; break;
			case 'jp' : codeDesc = '일본'; break;
		}
	} else if (i18next.language == 'en') {
		switch (code.toLowerCase()) {
			case 'us' : codeDesc = 'USA';
			case 'ep' : codeDesc = 'EU';
			case 'jp' : codeDesc = 'Japan';
		}
	}
	
	return codeDesc;
}

function insertQueryLog(right, mode, query) {
	
	let u_nation = 'TOT', u_flag = '1';
	
	if (mode == 'detailSearch' || mode == 'specialization') {
		switch(right) {
			case 'abdg' : u_nation = 'FDG'; break;
			case 'abpat' : u_nation = 'KAB'; break;
			case 'abpatTrans' : u_nation = 'ABT'; break;
			case 'abtm' : u_nation = 'FTM'; break;
			case 'arti' : u_nation = 'ART'; break;
			case 'cntst' : u_nation = 'CNT'; break;
			case 'cyber' : u_nation = 'CBY'; break;
			case 'ipNaviConflict' : u_nation = 'INC'; break;
			case 'ipNaviPrcdn' : u_nation = 'INP'; break;
			case 'jg' : u_nation = 'KJD'; break;
			case 'kdg' : u_nation = 'KDG'; break;
			case 'kpa' : u_nation = 'KPA'; break;
			case 'kpat' : u_nation = 'KPT'; break;
			case 'ktm' : u_nation = 'KTM'; break;
			case 'natlPat' : u_nation = 'NTP'; break;
			case 'mPat' : u_nation = 'MPT'; break;
			case 'etcPat' : u_nation = 'ETP'; break;
			default : u_nation = 'NON'; break;
		}
		u_flag = '2';
	}
	
	// query 길이 제한 추가
	let total = 0;
	let maxBytes = 4000;
	let u_query = '';
	for (const ch of query) {
		const chByte = new Blob([ch]).size;
		if (total + chByte > maxBytes) break;
		u_query += ch;
		total += chByte;
	}
	
	if (u_query == '') {
		return;
	}
	
	let params = {
		'u_query': u_query,
		'u_nation': u_nation,
		'u_flag': u_flag,
		'srch_rslt_cnt': ResultData.getData(right).countInfo.totalcount
	};
	
	$.ajax({
		type: 'POST',
		url: '/khome/common/insertQueryLog.do',
		data: params,
		error: function(xhr, status, error)
		{
			console.log('insert query log error');
		},
	});
}

function decodeHtmlEntities(str) {
    // HTML엔티티,10진수,16진수  목록을 정의한 객체
	const htmlEntities = {	
	    "&quot;": "\"", "&#34;": "\"", "&#x22;": "\"",
	    "&apos;": "'", "&#39;": "'", "&#x27;": "'",
	    "&amp;": "&", "&#38;": "&", "&#x26;": "&",
	    "&lt;": "<", "&#60;": "<", "&#x3C;": "<",
	    "&gt;": ">", "&#62;": ">", "&#x3E;": ">",
	    "&nbsp;": " ", "&#160;": " ", "&#xA0;": " ",
	    "&commat;": "@", "&#64;": "@", "&#x40;": "@",
	    "&num;": "#", "&#35;": "#", "&#x23;": "#",
	    "&dollar;": "$", "&#36;": "$", "&#x24;": "$",
	    "&percnt;": "%", "&#37;": "%", "&#x25;": "%",
	    "&plus;": "+", "&#43;": "+", "&#x2B;": "+",
	    "&minus;": "-", "&#45;": "-", "&#x2D;": "-",
	    "&ast;": "*", "&#42;": "*", "&#x2A;": "*",
	    "&sol;": "/", "&#47;": "/", "&#x2F;": "/",
	    "&bsol;": "\\", "&#92;": "\\", "&#x5C;": "\\",
	    "&vert;": "|", "&#124;": "|", "&#x7C;": "|",
	    "&excl;": "!", "&#33;": "!", "&#x21;": "!",
	    "&quest;": "?", "&#63;": "?", "&#x3F;": "?",
	    "&colon;": ":", "&#58;": ":", "&#x3A;": ":",
	    "&semi;": ";", "&#59;": ";", "&#x3B;": ";",
	    "&equals;": "=", "&#61;": "=", "&#x3D;": "=",
	    "&lpar;": "(", "&#40;": "(", "&#x28;": "(",
	    "&rpar;": ")", "&#41;": ")", "&#x29;": ")",
	    "&lbrack;": "[", "&#91;": "[", "&#x5B;": "[",
	    "&rbrack;": "]", "&#93;": "]", "&#x5D;": "]",
	    "&lbrace;": "{", "&#123;": "{", "&#x7B;": "{",
	    "&rbrace;": "}", "&#125;": "}", "&#x7D;": "}",
	    "&comma;": ",", "&#44;": ",", "&#x2C;": ",",
	    "&period;": ".", "&#46;": ".", "&#x2E;": ".",
	    "&lowbar;": "_", "&#95;": "_", "&#x5F;": "_"
	};
    return str.replace(/&[^;]+;/g, (match) => htmlEntities[match] || match);
}

function printDiv() {
	var hidden_divTag = document.getElementById('print_hidden');
	hidden_divTag.style.display = 'none';
	
    html2canvas(document.getElementById('stat_print')).then(function(canvas) {
    	hidden_divTag.style.display = 'block';
        var imgData = canvas.toDataURL();  
        
        var iframe = document.createElement('iframe');
        iframe.style.position = 'absolute';
        iframe.style.width = '0px';
        iframe.style.height = '0px';
        iframe.style.border = 'none';
        document.body.appendChild(iframe);
		
        var iframeDoc = iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write('<img src="' + imgData + '" style="width:100%;" />');
        iframeDoc.close();
        
        iframe.contentWindow.onload = function() {
            iframe.contentWindow.print(); 
            document.body.removeChild(iframe);  
        };
    });
}

function isMobile() {
	const userAgent = navigator.userAgent || navigator.vendor || window.opera;
	const isMobileUA = /Mobi|Android|iPhone|iPad|iPod|Tablet/i.test(userAgent);
	const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
	const isSmallScreen = window.matchMedia('(max-width: 1024px)').matches;
	
	return isMobileUA || (isTouchDevice && isSmallScreen);
}

function recordServiceStats(svc, loctn, itm, cntry = 'KR') {
	
	let svc_tpcd;
	if (svc == 'jg') {
		svc_tpcd = 'KJM';
	} else if (svc == 'abdg') {
		svc_tpcd = 'ADG';
	} else if (svc == 'abpatTrans') {
		svc_tpcd = 'ABPTR';
	} else if (svc == 'ipNaviPrcdn') {
		svc_tpcd = 'IPPRC';
	} else if (svc == 'ipNaviConflict') {
		svc_tpcd = 'IPCFT';
	} else {
		if (svc == undefined || svc == '') {
			return;
		} else {
			svc_tpcd = svc.toUpperCase();
		}
	}
	
	let loctn_tpcd;
	if (loctn == undefined || loctn == '') {
		return;
	} else {
		loctn_tpcd = loctn.toUpperCase();
	}
	
	let itm_tpcd;
	if (itm == 'jg') {
		itm_tpcd = 'KJM';
	} else if (itm == 'abdg') {
		itm_tpcd = 'ADG';
	} else if (itm == 'abpatTrans') {
		itm_tpcd = 'ABPTR';
	} else if (itm == 'ipNaviPrcdn') {
		itm_tpcd = 'IPPRC';
	} else if (itm == 'ipNaviConflict') {
		itm_tpcd = 'IPCFT';
	}  else {
		if (itm == undefined || itm == '') {
			return;
		} else {
			itm_tpcd = itm.toUpperCase();
		}
	}
	
	let lang_tpcd = i18next.language.includes('ko') ? 'KR' : 'EN';
	
	let params = {
		'lang_tpcd': lang_tpcd,	// 언어
		'svc_tpcd': svc_tpcd,	// 서비스
		'loctn_tpcd': loctn_tpcd,	//위치
		'itm_tpcd': itm_tpcd,	// 항목
		'cntry_cd': cntry	// 국가코드
	};
	
	//---------- GTM 설정 추가 [START] ------------- 
	window.dataLayer = window.dataLayer || [];
	
	window.dataLayer.push({
		event: 'kipris_tab_view',
		lang_tpcd: lang_tpcd,
		svc_tpcd: svc_tpcd,
		loctn_tpcd: loctn_tpcd,
		itm_tpcd: itm_tpcd,
		cntry_cd: cntry
	});
	//---------- GTM 설정 추가 [END] ---------------
	
	$.ajax({
		type: 'POST',
		url: '/khome/common/recordServiceStats.do',
		data: params,
		error: function(xhr, status, error)
		{
			console.log('recordServiceStats error');
		},
	});
}

function inactive_user(val_1, val_2, val_3, val_4, val_5){
	const oldForm = document.getElementById("inactiveForm");
    if (oldForm) {
        oldForm.remove();
    }

    const form = document.createElement("form");
    form.setAttribute("id", "inactiveForm");
    form.setAttribute("method", "post");
    form.setAttribute("action", "/khome/member/update/inactive.do");

    const Input_1 = document.createElement("input");
    Input_1.setAttribute("type", "hidden");
    Input_1.setAttribute("name", "userid");
    Input_1.setAttribute("value", val_1);
    form.appendChild(Input_1);

    const Input_2 = document.createElement("input");
    Input_2.setAttribute("type", "hidden");
    Input_2.setAttribute("name", "password");
    Input_2.setAttribute("value", val_2);
    form.appendChild(Input_2);
    
    const Input_3 = document.createElement("input");
    Input_3.setAttribute("type", "hidden");
    Input_3.setAttribute("name", "year");
    Input_3.setAttribute("value", val_3);
    form.appendChild(Input_3);
    
    const Input_4 = document.createElement("input");
    Input_4.setAttribute("type", "hidden");
    Input_4.setAttribute("name", "month");
    Input_4.setAttribute("value", val_4);
    form.appendChild(Input_4);
    
    const Input_5 = document.createElement("input");
    Input_5.setAttribute("type", "hidden");
    Input_5.setAttribute("name", "day");
    Input_5.setAttribute("value", val_5);
    form.appendChild(Input_5);

    document.body.appendChild(form);
    form.submit();
}

function inactive_proc(val_1, val_2){
	$.ajax({
		async: true,
		type: 'POST',
		url: '/khome/member/update/inactiveUser.do',
		data: {value_1: val_1, value_2: val_2},
		dataType: 'json',
		success: function(data){
			if (data.result == true) {
				alert("휴면계정에서 일반계정으로 정상적으로 전환 되었습니다.\n메인화면에서 재로그인 후 서비스를 이용하시기 바랍니다.");
			} else {
				alert("휴면계정의 정보가 삭제되는중 문제가 발생했습니다.");
			}
			goMenu('home');
		},
		error: function(xhr, status, error)
		{
			alert(i18next.t('ms.join.txt53'));
		},
	});
}

function convertGermanEntities(str) {
	return str.replace(/[ÄäÖöÜüß]/g, function(match) {
		return '&#' + match.charCodeAt(0) + ';';
	});
}

//통계_출원번호별 상세정보 조회  2026-06
function recordStatRdnoData(svc, readno, relclcd) {
	
	let svc_tpcd;
	if (svc == undefined || svc == '') {
			return;
	} else {
		svc_tpcd = svc.toUpperCase();
	}
	
	let rel_clcd = null;
	
	if (!(relclcd == undefined || relclcd == '' || relclcd == null)) {		
		rel_clcd = relclcd.toUpperCase();
	}
	
	let lang_tpcd = i18next.language.includes('ko') ? 'KR' : 'EN';
	let read_no = String(readno || "").split(",")[0].trim();
	
	let params = {
		'lang_tpcd': lang_tpcd,	// 언어
		'svc_tpcd': svc_tpcd,	// 서비스
		'read_no': read_no,		// 출원번호
		'rel_clcd': rel_clcd 	// 분류
	};
	
	fetch('/khome/common/recordStatRdnoData.do', {
		method: 'POST',
		headers:{'Content-Type':'application/x-www-form-urlencoded'},
		body: new URLSearchParams(params)		
	})
	.then(function(res){return res.text();})
	.catch(error => console.log('recordStatRdnoData error'));
}

function closeHeadBanner() {
	$('#mainResultListArea .head-banner').slideUp(400, function() {
        $(this).remove();
    });
	sessionStorage.setItem("HeadBannerClosed", "true");
}

function checkHeadBanner(tab) {
	const $headBanner = $('#mainResultListArea .head-banner');
	if (tab == 'kpat' && sessionStorage.getItem("HeadBannerClosed") != "true") {
		$headBanner.show();
    } else {
    	$headBanner.hide();
    }
}

function openIndstTechClss() {
	const $mBtn = $('#modalSearchDetail #sd02');
	$mBtn.click();
	
	const $sBtn = $('#modalSearchDetail .tab-con.active button[data-visible-control=sd02_05]');
	$sBtn.click();
	
	modal.open('#modalSearchDetail', $sBtn);
}