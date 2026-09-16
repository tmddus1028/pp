'use strict';
const $ = id => document.getElementById(id);
const send = (type, extra={}) => window.parent.postMessage({isStreamlitMessage:true,type,...extra},'*');
const el = (tag,cls,text) => {const node=document.createElement(tag);if(cls)node.className=cls;if(tag==='p')node.classList.add('readable-text');if(text!==undefined)node.textContent=text;return node;};
const labels={direct_rejection:'직접 지적',dependency:'종속 영향',citation:'인용 문헌',specification:'관련 설명',rejection:'거절 사유',unaddressed:'추출된 지적 없음',allowed:'허용',withdrawn:'심사 대상 제외',canceled:'취소됨',pending:'계류 중'};
const groundLabel=r=>r.action_type==='objection'?'Objection':r.statute;
const citationRoleLabels={relied_upon:'거절 근거'};
const citationRoleHelp={citation:'심사관이 실제 거절 논리에 사용한 선행기술'};
const itemLabel=item=>item.kind==='claim'&&item.status==='objected'&&!item.direct.length?'Objection · 추가 검토':labels[role(item)];
let model, state, currentPage, initialized=false, searchHits=[], searchIndex=-1, timer, pendingScroll=false, pendingSearch=false, serverNavigation=-1;
const itemById = id => model.items.find(item=>item.id===id);
const docById = id => model.documents.find(doc=>doc.id===id);
const visibleScope = item => state.scope==='all'||item.rejection_ids.includes(state.scope);
function role(item,scope=state.scope){
  if(item.kind==='citation'){
    const roles=(item.occurrences||[]).filter(e=>scope==='all'||e.rejection_id===scope).map(e=>e.role);
    const type=roles.includes('relied_upon')?'relied_upon':roles.includes('supporting_evidence')?'supporting_evidence':item.citation_role||'relied_upon';
    return type==='relied_upon'?'citation':type;
  }
  if(item.kind==='claim'){
    if(['allowed','withdrawn','canceled'].includes(item.status))return item.status;
    if(item.direct.some(r=>scope==='all'||r===scope))return 'direct_rejection';
    if([...item.indirect,...(item.objected||[])].some(r=>scope==='all'||r===scope)||item.status==='objected'&&scope==='all')return 'dependency';
    if(item.status==='pending')return 'pending';
    return 'unaddressed';
  }
  return item.kind==='rejection'&&item.action_type==='objection'?'dependency':item.kind;
}
// Presentation only: retain all documents/relations in model, display relied-upon citations.
const presented=item=>Boolean(item)&&(item.kind!=='citation'||role(item)==='citation');
const presentedAnnotation=a=>itemById(a.item_id)?.kind!=='citation'||a.type==='citation';
function eligible(item){return presented(item)&&(state.scope==='all'||visibleScope(item))&&(state.filter==='all'||role(item)===state.filter);}
// Rejection scope is shared by summary and list; point-type filtering applies only to the list.
function scopedPoints(){return model.items.filter(i=>i.kind!=='rejection'&&presented(i)&&visibleScope(i));}
function emit(){clearTimeout(timer);timer=setTimeout(()=>send('streamlit:setComponentValue',{value:{nonce:Date.now()+Math.random(),navigation:serverNavigation,ui:state},dataType:'json'}),90);}
function button(text,callback,cls){const b=el('button',cls,text);b.type='button';b.addEventListener('click',callback);return b;}
function jump(documentId,number){
  const doc=docById(documentId);if(!doc)return;
  state.document=documentId;state.page=Math.max(1,Math.min(doc.pages.length,Number(number)||1));
  pendingScroll=true;draw();emit();
}
function selectItem(id,fromPDF=false,expand=true){
  const item=itemById(id);if(!item)return;
  // PDF evidence navigation must not replace the Claim being reviewed.
  state.viewer_evidence=id;
  state.active_rejection=item.kind==='rejection'?item.rejection_ids[0]:null;
  if(item.kind!=='rejection'){state.selected=id;state.expanded=expand?id:null;}
  pendingSearch=false;
  if(item.kind!=='rejection'&&!eligible(item)){state.filter='all';if(!visibleScope(item))state.scope='all';}
  const candidates=model.annotations.filter(a=>a.item_id===id&&presentedAnnotation(a)&&(item.kind==='rejection'||state.scope==='all'||!a.linked_rejection_id||a.linked_rejection_id===state.scope));
  const anchor=(fromPDF?candidates.find(a=>a.document_id===state.document&&a.page===state.page):null)||candidates[0];
  if(anchor){if(state.document!==anchor.document_id){state.search='';searchHits=[];searchIndex=-1;}state.document=anchor.document_id;state.page=anchor.page;}
  pendingScroll=!fromPDF;draw();emit();
  requestAnimationFrame(()=>{
    const card=document.querySelector('.review-card.active'),list=$('review-list');
    if(card)list.scrollTo({top:list.scrollTop+card.getBoundingClientRect().top-list.getBoundingClientRect().top,behavior:'instant'});
  });
}
function toggleCard(id){
  selectItem(id,false,state.expanded!==id);
  document.querySelector('.review-card.active .card-select')?.focus({preventScroll:true});
}
function setFilter(value){
  state.filter=value;
  // List filtering never changes Claim/rejection selection or PDF evidence focus.
  drawToolbar();drawPanel();$('review-list').scrollTop=0;emit();
}
function annotations(){
  return model.annotations.filter(a=>{
    const item=itemById(a.item_id);
    const focused=a.item_id===state.viewer_evidence;
    return presentedAnnotation(a)&&a.document_id===state.document&&a.page===state.page&&(focused||visibleScope(item))&&
      (focused||state.scope==='all'||!a.linked_rejection_id||a.linked_rejection_id===state.scope);
  });
}
function drawToolbar(){
  const doc=docById(state.document);
  $('document').replaceChildren(...model.documents.map(d=>{const o=el('option','',(d.kind==='patent'?'Patent · ':'Office Action · ')+d.filename);o.value=d.id;return o;}));
  $('document').value=state.document;$('page-number').value=state.page;$('page-number').max=doc.pages.length;$('page-total').textContent='/ '+doc.pages.length;
  $('prev').disabled=state.page<=1;$('next').disabled=state.page>=doc.pages.length;
  $('search').value=state.search||'';
  const download=$('download');download.hidden=!doc.pdf_download;
  if(doc.pdf_download){download.href='data:application/pdf;base64,'+doc.pdf_download;download.download=doc.filename;}
  $('scope').replaceChildren(el('option','','전체 거절 사유'));
  $('scope').firstChild.value='all';
  for(const rejection of model.rejections){const option=el('option','',rejection.rejection_id+' · '+groundLabel(rejection));option.value=rejection.rejection_id;$('scope').append(option);}
  $('scope').value=state.scope;
  document.querySelectorAll('#legend-filters button, #point-filters button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter)));
  $('fit-width').setAttribute('aria-pressed',String(state.fit==='width'));
  $('fit-page').setAttribute('aria-pressed',String(state.fit==='page'));
  const current=itemById(state.selected),mini=$('relationship-mini');mini.replaceChildren();
  if(presented(current)){
    mini.append(el('strong','',current.title));
    if(current.kind==='claim'){
      const parents=current.depends_on.map(n=>'Claim '+n).join(', ')||'독립항';
      const children=current.children.map(n=>'Claim '+n).join(', ')||'직접 종속항 없음';
      mini.append(el('span','',parents+' → '+current.title+' → '+children));
    }else mini.append(el('span','',current.rejection_ids.join(' · ')));
  }
}
function resizePaper(){
  if(!currentPage)return;
  const available=$('pdf-scroll').clientWidth-40;
  const fullWidth=currentPage.width*96/72;
  let width=fullWidth*state.zoom/100;
  if(state.fit==='width')width=available;
  if(state.fit==='page')width=Math.min(available,($('pdf-scroll').clientHeight-40)*currentPage.width/currentPage.height);
  $('paper').style.width=Math.max(150,width)+'px';
  $('zoom-label').textContent=Math.round(width/fullWidth*100)+'%';
  placeClaimBadges();
}
function drawPage(){
  const ready=currentPage&&currentPage.document===state.document&&currentPage.number===state.page;
  $('loading').hidden=ready;$('paper').style.visibility=ready?'visible':'hidden';
  if(!ready){$('page-status').textContent='원본 페이지를 불러오는 중…';return;}
  const doc=docById(state.document), ann=annotations();
  let status=doc.kind==='patent'?'Patent 원문':'Office Action 원문';
  status+=' · p. '+state.page;
  if(doc.ocr_pages.includes(state.page))status+=' · OCR 위치';
  if(searchHits.length&&state.search)status+=' · 검색 '+(searchIndex+1)+' / '+searchHits.length;
  const unlocated=ann.filter(a=>a.location_method==='page_only');
  if(currentPage.error)status+=' · '+currentPage.error;
  else if(!doc.pdf_download)status+=' · 텍스트 입력 문서';
  else if(unlocated.length)status+=' · 일부 정확한 위치를 찾지 못해 페이지 근거를 표시합니다';
  $('page-status').textContent=status;
  const img=$('page-image'), text=$('text-page');
  img.hidden=!currentPage.image;img.style.display=currentPage.image?'block':'none';
  text.style.display=currentPage.image?'none':'block';
  if(currentPage.image){if(img.src!==currentPage.image)img.src=currentPage.image;img.alt=doc.filename+' 원본 '+state.page+'페이지';drawOverlays(ann);}
  else {drawTextPage(ann);$('overlays').replaceChildren();}
  resizePaper();
  if(pendingScroll){requestAnimationFrame(()=>scrollToSelection());}
}
function drawOverlays(ann){
  const overlay=$('overlays');overlay.replaceChildren();
  const badges=el('div','claim-badge-layer');
  const geometry=window.PatentAnnotationGeometry;
  const pageClaimBoxes=model.annotations.filter(a=>a.document_id===state.document&&a.page===state.page&&itemById(a.item_id).kind==='claim').flatMap(a=>a.boxes);
  for(const a of geometry.groupAnnotations(ann)){
    const item=itemById(a.item_id), type=role(item), selected=state.viewer_evidence===item.id;
    if(['unaddressed','allowed','withdrawn','canceled','pending'].includes(type)&&!selected)continue;
    const region=item.kind==='claim'||item.kind==='rejection';
    const boxes=region?geometry.claimRegions(a.boxes,item.kind==='claim'?pageClaimBoxes:a.boxes):a.boxes;
    for(const [index,box] of boxes.entries()){
      const node=button('',()=>selectItem(item.id,true),'annotation '+type+(region?' region':'')+(selected?' selected pulse':' dimmed'));
      node.dataset.annotation=a.id;node.dataset.itemId=item.id;
      node.dataset.box=JSON.stringify(box);
      node.setAttribute('aria-label',item.title+' '+labels[type]+' · p. '+a.page+' · 구간 '+(index+1));
      node.title=item.title+' · '+labels[type];
      const padding=region?3:1;
      Object.assign(node.style,{left:`calc(${box[0]*100}% - ${padding}px)`,top:`calc(${box[1]*100}% - ${padding}px)`,width:`calc(${(box[2]-box[0])*100}% + ${padding*2}px)`,height:`calc(${(box[3]-box[1])*100}% + ${padding*2}px)`});
      if(item.kind==='claim'){
        const badge=el('span','claim-number-badge '+type+(selected?' selected':''),String(item.claim_number));
        badge.setAttribute('aria-hidden','true');badge.dataset.itemId=item.id;
        badge.dataset.box=JSON.stringify(box);badges.append(badge);
      }
      overlay.append(node);
    }
  }
  for(const box of (currentPage.search_boxes||[])){
    const node=el('span','annotation search-hit');
    Object.assign(node.style,{left:box[0]*100+'%',top:box[1]*100+'%',width:(box[2]-box[0])*100+'%',height:(box[3]-box[1])*100+'%'});overlay.append(node);
  }
  overlay.append(badges);
}
function placeClaimBadges(){
  const paper=$('paper'),width=paper.clientWidth,height=paper.clientHeight;
  if(!width||!height||!model)return;
  const badges=[...document.querySelectorAll('.claim-number-badge')];
  const occupied=model.annotations.filter(a=>a.document_id===state.document&&a.page===state.page).flatMap(a=>a.boxes).map(b=>[b[0]*width,b[1]*height,b[2]*width,b[3]*height]);
  // One size and placement rule for every Claim on the page, including both columns.
  const digits=Math.max(2,...badges.map(b=>b.textContent.length)),badgeWidth=digits*5+6,badgeHeight=12;
  const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
  for(const badge of badges){
    const box=JSON.parse(badge.dataset.box),left=box[0]*width,top=box[1]*height;
    const y=clamp(top-3,1,height-badgeHeight-1);
    let x=clamp(left-3-2-badgeWidth,1,width-badgeWidth-1),placement='outside';
    // Shift only as far as needed to clear the previous column's text. A badge
    // may meet the border or use the first-line indentation instead of disappearing.
    const row=occupied.filter(b=>y<b[3]+1&&y+badgeHeight>b[1]-1);
    for(const b of row.sort((a,b)=>a[0]-b[0])){
      if(x<b[2]+1&&x+badgeWidth>b[0]-1)x=b[2]+1;
    }
    if(x>left+3||x+badgeWidth>width-1){
      // At very low zoom or a tight page edge, retain EVERY badge at the same
      // safe inner corner. Never hide a subset or change source annotation boxes.
      x=clamp(left+1,1,width-badgeWidth-1);placement='inside';
    }else if(x>left-3-2-badgeWidth){placement='adjusted';}
    badge.dataset.placement=placement;
    Object.assign(badge.style,{left:x+'px',top:y+'px',width:badgeWidth+'px',height:badgeHeight+'px'});
  }
}
function drawTextPage(ann){
  const text=currentPage.text, root=$('text-page');root.replaceChildren();
  const boundaries=[...new Set([0,text.length,...ann.flatMap(a=>[a.start,a.end])])].sort((a,b)=>a-b);
  for(let i=0;i<boundaries.length-1;i++){
    const start=boundaries[i],end=boundaries[i+1];
    const a=ann.filter(a=>a.start<=start&&a.end>=end).sort((a,b)=>(b.item_id===state.viewer_evidence)-(a.item_id===state.viewer_evidence)||(b.type==='citation')-(a.type==='citation'))[0];
    if(!a){root.append(document.createTextNode(text.slice(start,end)));continue;}
    const node=el('mark','text-highlight '+role(itemById(a.item_id))+(a.item_id===state.viewer_evidence?' selected':''),text.slice(start,end));
    node.dataset.itemId=a.item_id;node.setAttribute('role','button');node.tabIndex=0;
    node.addEventListener('click',()=>selectItem(a.item_id,true));
    node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectItem(a.item_id,true);}});
    root.append(node);
  }
}
function scrollToSelection(){
  if(currentPage?.image&&!$('page-image').complete)return;
  if(pendingSearch&&currentPage.search_query!==state.search)return;
  const targets=pendingSearch?[...document.querySelectorAll('.search-hit')]:[...document.querySelectorAll('#overlays [data-item-id], #text-page [data-item-id]')].filter(n=>n.dataset.itemId===state.viewer_evidence);
  const node=targets[0];
  if(node){
    const scroll=$('pdf-scroll'),outer=scroll.getBoundingClientRect(),box=node.getBoundingClientRect();
    scroll.scrollTo({top:scroll.scrollTop+box.top-outer.top-65,left:Math.max(0,scroll.scrollLeft+box.left-outer.left-35),behavior:'smooth'});
  }else $('pdf-scroll').scrollTo({top:0,left:0});
  pendingScroll=false;
  pendingSearch=false;
}
function evidenceSection(body,evidence,caption){
  body.append(el('div','source-caption',caption+' · p. '+evidence.page_numbers.join(', ')));
  body.append(el('div','evidence readable-text',evidence.text));
}
function chips(body,values){const row=el('div','chips');values.forEach(([label,id])=>row.append(button(label,()=>selectItem(id))));body.append(row);}
function details(item,body){
  const rids=item.rejection_ids.filter(r=>(state.scope==='all'||state.scope===r)&&(item.kind!=='citation'||!item.occurrences||item.occurrences.some(e=>e.rejection_id===r&&e.role==='relied_upon')));
  if(item.kind==='claim'){
    const active=model.rejections.find(r=>r.rejection_id===state.active_rejection&&item.rejection_ids.includes(r.rejection_id));
    if(active&&active.evidence.document_id===state.document&&active.evidence.page_numbers.includes(state.page)){
      const current=el('div','current-evidence');current.dataset.rejectionId=active.rejection_id;
      current.append(el('h4','','현재 보고 있는 근거'),el('strong','',active.rejection_id+' · '+groundLabel(active)));
      current.append(el('div','source-caption','Office Action p. '+state.page));
      const actions=el('div','chips');
      actions.append(button('청구항 원문 보기',()=>selectItem(item.id)));
      for(const rid of rids.filter(r=>r!==active.rejection_id))actions.append(button(rid+' 근거 보기',()=>selectItem('rejection-'+rid)));
      current.append(actions);body.append(current);
    }
    body.append(el('h4','','분석 설명'));
    if(item.status_evidence){
      body.append(el('p','',itemLabel(item)+(item.conditional_allowance?' · 독립항으로 재작성하는 조건의 허용 가능성 언급':'')));
      const statusDetail=el('details');statusDetail.append(el('summary','','Office Action 청구항 상태 근거'));evidenceSection(statusDetail,item.status_evidence,'상태 원문');body.append(statusDetail);
    }
    if(role(item)==='dependency'&&item.status!=='objected')body.append(el('p','',item.title+'은 Claim '+item.depends_on.join(', ')+'에 종속됩니다. 선택한 거절 사유의 상위 청구항과 함께 검토할 대상으로 연결되었습니다.'));
    else if(!rids.length&&!item.status_evidence)body.append(el('p','','이 청구항에 연결된 명시적 지적을 추출하지 못했습니다. 허용 여부를 뜻하지 않습니다.'));
    for(const rid of rids){const r=model.rejections.find(r=>r.rejection_id===rid);body.append(el('p','',r.reason_summary));}
    const own=el('details');own.append(el('summary','','Claim 원문'));evidenceSection(own,item.evidence,'Patent');body.append(own);
    body.append(el('h4','','종속 관계'));
    if(!item.depends_on.length)body.append(el('p','','독립항'));
    else chips(body,item.depends_on.map(n=>['상위 Claim '+n,'claim-'+n]));
    if(item.children.length)chips(body,item.children.map(n=>['종속 Claim '+n,'claim-'+n]));
  }else if(item.kind==='citation'){
    const ref=item.reference;
    if(ref.title)body.append(el('p','',ref.title));
    if(ref.doi)body.append(el('p','','DOI: '+ref.doi));
    body.append(el('h4','',ref.type==='npl'?'NPL · 비특허 문헌':ref.type==='patent'?'Patent · 특허 문헌':'문헌 유형 미확인'));
    body.append(el('p','',ref.publication_number||[ref.publication,ref.year].filter(Boolean).join(' · ')||'원문에 표시된 문헌'));
    body.append(el('p','','심사관이 인용한 문헌의 Office Action 내 위치입니다.'));
    const firstOccurrence=(item.occurrences||[]).find(e=>e.role==='relied_upon'&&rids.includes(e.rejection_id));
    evidenceSection(body,firstOccurrence?.evidence||item.evidence,'Office Action 인용 원문');
    for(const occurrence of item.occurrences||[]){
      if(occurrence.role!=='relied_upon'||state.scope!=='all'&&occurrence.rejection_id!==state.scope)continue;
      const entry=el('details','citation-occurrence');
      entry.dataset.rejectionId=occurrence.rejection_id||'';
      entry.append(el('summary','',(occurrence.rejection_id||'기록')+' · '+citationRoleLabels[occurrence.role]+' · p. '+occurrence.evidence.page_numbers.join(', ')));
      evidenceSection(entry,occurrence.evidence,'해당 문헌을 사용한 원문');
      entry.append(button((occurrence.rejection_id||'기록')+' 인용 원문 보기',()=>{
        state.scope=occurrence.rejection_id||'all';state.filter='all';selectItem(item.id);
      }));body.append(entry);
    }
    body.append(el('h4','','연결된 거절 · 법조항'));
    chips(body,rids.map(rid=>[rid+' · '+model.rejections.find(r=>r.rejection_id===rid).statute,'rejection-'+rid]));
    const numbers=[...new Set(model.rejections.filter(r=>rids.includes(r.rejection_id)).flatMap(r=>r.claims))].sort((a,b)=>a-b);
    body.append(el('h4','','관련 Claim · 같은 거절에 연결된 청구항'));
    chips(body,numbers.map(n=>['Claim '+n,'claim-'+n]));
    body.append(el('p','notice','거절 사유 단위의 연결이며, 문헌별로 각 Claim 구성을 개시한다는 판단을 새로 생성하지 않습니다.'));
  }else if(item.kind==='specification'){
    body.append(el('p','','Office Action이 명시적으로 언급한 원문 위치입니다. 이 연결 자체가 명세서의 뒷받침 여부를 판단하지는 않습니다.'));
    evidenceSection(body,item.evidence,'Patent');
  }else {body.append(el('p','',item.text));evidenceSection(body,item.evidence,'Office Action');}
  for(const rid of rids){
    const rejection=model.rejections.find(r=>r.rejection_id===rid);
    const detail=el('details');detail.dataset.rejectionId=rid;
    detail.open=item.kind==='claim'&&(state.active_rejection?state.active_rejection===rid:rids.length===1);
    detail.append(el('summary','',rid+' · '+groundLabel(rejection)+' · Office Action 원문 근거'));
    evidenceSection(detail,rejection.evidence,'심사관 원문');
    detail.append(button('OA p. '+rejection.evidence.page_numbers[0]+'에서 보기',()=>selectItem('rejection-'+rid)));
    if(item.kind==='rejection')chips(detail,rejection.claims.map(n=>['Claim '+n,'claim-'+n]));
    body.append(detail);
  }
  const references=[...new Map(model.rejections.filter(r=>rids.includes(r.rejection_id)).flatMap(r=>r.cited_references).filter(ref=>(ref.citation_role||'relied_upon')==='relied_upon').map(ref=>[ref.citation_id,ref])).values()];
  if(references.length&&item.kind!=='citation'){body.append(el('h4','','관련 인용문헌 · '+references.length+'개'));chips(body,references.map(ref=>[ref.name||ref.publication_number,'citation-'+ref.citation_id]));}
  if(item.kind==='claim'){
    body.append(el('h4','','관련 specification / drawing'));
    const links=(item.support_ids||[]).map(itemById).filter(i=>visibleScope(i));
    if(links.length)chips(body,links.map(i=>[i.title,i.id]));
    else body.append(el('p','notice','원문에서 확인된 명시적 명세서·도면 연결이 없습니다.'));
  }
  const checklist=model.impacts.filter(i=>rids.includes(i.rejection_id)).flatMap(i=>i.review_items||[]);
  if(checklist.length){
    body.append(el('h4','','검토 체크리스트'));
    for(const entry of checklist){
      const row=el('label','check-item'),input=el('input');input.type='checkbox';input.checked=Boolean(state.checked[entry.item_id]);
      input.addEventListener('change',()=>{state.checked[entry.item_id]=input.checked;emit();});
      row.append(input,el('span','',entry.text));body.append(row);
    }
  }
  const anchors=model.annotations.filter(a=>a.item_id===item.id&&a.document_id===state.document);
  if(anchors.some(a=>a.location_method==='page_only'))body.append(el('p','notice','정확한 좌표를 확인하지 못한 구간은 하이라이트 없이 페이지와 원문 근거로 표시합니다.'));
  if(item.kind==='claim'){
    body.append(button('PDF에서 보기',()=>selectItem(item.id),'claim-pdf-link'));
    body.append(button('근거 비교',()=>{
      clearTimeout(timer);
      send('streamlit:setComponentValue',{value:{nonce:Date.now()+Math.random(),navigation:serverNavigation,ui:state,action:'open_comparison'},dataType:'json'});
    },'claim-pdf-link'));
  }
}
function drawPanel(){
  $('provider').textContent=model.provider==='local'?'LOCAL 분석':model.provider.toUpperCase()+' 분석';
  const root=$('summary');root.replaceChildren();
  const scoped=scopedPoints();
  // Claim selection and evidence focus do not change the review scope or these counts.
  for(const [type,label] of [['direct_rejection','직접 지적'],['dependency','종속 영향 / Objection'],['allowed','허용'],['citation','인용 문헌']]){
    const count=scoped.filter(i=>role(i)===type).length;
    const card=button('',()=>setFilter(type),type);card.setAttribute('aria-label',label+' '+count);card.setAttribute('aria-pressed',String(state.filter===type));
    if(citationRoleHelp[type])card.title=citationRoleHelp[type];
    card.append(el('small','',label),el('strong','',String(count)));root.append(card);
  }
  $('rejection-links').replaceChildren(...model.rejections.map(r=>button(r.rejection_id+' · '+groundLabel(r),()=>selectItem('rejection-'+r.rejection_id))));
  const list=$('review-list'),scroll=list.scrollTop;list.replaceChildren();
  const points=scoped.filter(i=>state.filter==='all'||role(i)===state.filter);
  $('point-count').textContent=points.length+'개';
  if(!points.length)list.append(el('div','empty','해당 유형의 검토 포인트가 없습니다. 모든 청구항이 직접 지적되면 종속항도 빨강으로 표시됩니다. 거절 사유별 범위에서 종속 영향을 확인할 수 있습니다.'));
  points.forEach((item,index)=>{
    const active=item.id===state.selected,expanded=item.id===state.expanded,type=role(item),card=el('article','review-card'+(active?' active':'')+(expanded?' expanded':''));card.dataset.reviewId=item.id;
    const select=button('',()=>toggleCard(item.id),'card-select');select.setAttribute('aria-label',item.title+' · '+itemLabel(item));select.setAttribute('aria-expanded',String(expanded));
    select.append(el('span','card-index',String(item.claim_number??index+1)));
    const heading=el('div','readable-panel'),title=el('div','card-title readable-text',item.title);
    const badgeText=item.kind==='citation'?'거절 근거':itemLabel(item);
    const roleBadge=el('span','badge '+type+(item.kind==='citation'?' citation-role-badge':''),badgeText);
    if(item.kind==='citation')roleBadge.title=citationRoleHelp.citation;
    title.append(roleBadge);heading.append(title);
    const statutes=item.rejection_ids.filter(r=>state.scope==='all'||state.scope===r).map(r=>groundLabel(model.rejections.find(rej=>rej.rejection_id===r)));
    heading.append(el('div','card-meta',[...new Set(statutes)].join(' · ')||(item.kind==='citation'?'Office Action 기록':'Patent 원문')));
    if(item.kind==='citation'){
      const badges=el('div','citation-rejection-badges');
      item.rejection_ids.filter(rid=>!item.occurrences||item.occurrences.some(e=>e.rejection_id===rid&&e.role==='relied_upon')).forEach(rid=>{const badge=el('span','badge',rid);badge.dataset.rejectionId=rid;badges.append(badge);});
      heading.append(badges);
    }
    const chevron=el('span','card-chevron',expanded?'⌃':'⌄');chevron.setAttribute('aria-hidden','true');
    select.append(heading,chevron);card.append(select);
    if(expanded){const body=el('div','card-body readable-panel');body.id='detail-'+item.id;select.setAttribute('aria-controls',body.id);details(item,body);card.append(body);}
    list.append(card);
  });list.scrollTop=scroll;
}
function draw(){if(!model)return;drawToolbar();drawPanel();drawPage();}
function normalize(s){return s.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');}
function searchNext(){
  const query=$('search').value.trim().slice(0,300);
  if(query!==state.search){searchIndex=-1;state.search=query;}
  const doc=docById(state.document),needle=normalize(query);searchHits=[];
  if(needle.length>=2)for(const page of doc.pages){if(normalize(page.text).includes(needle))searchHits.push(page.number);}
  if(searchHits.length){searchIndex=(searchIndex+1)%searchHits.length;pendingSearch=true;jump(state.document,searchHits[searchIndex]);}
  else {$('page-status').textContent=needle.length<2?'검색어를 두 글자 이상 입력하세요.':'검색 결과가 없습니다.';emit();}
}
function frameSize(){
  let height=760;try{height=window.parent.innerHeight;}catch(_error){}
  const narrow=window.innerWidth<=880, panelHeight=Math.max(580,Math.min(870,height-145));
  document.documentElement.style.setProperty('--height',panelHeight+'px');
  send('streamlit:setFrameHeight',{height:narrow?1260:panelHeight+2});resizePaper();
}
$('document').addEventListener('change',e=>{state.search='';searchHits=[];jump(e.target.value,1);});
$('prev').onclick=()=>jump(state.document,state.page-1);$('next').onclick=()=>jump(state.document,state.page+1);
$('page-number').addEventListener('change',e=>jump(state.document,e.target.value));
$('page-number').addEventListener('keydown',e=>{if(e.key==='Enter')jump(state.document,e.target.value);});
for(const [id,difference] of [['zoom-out',-15],['zoom-in',15]])$(id).onclick=()=>{state.zoom=Math.max(35,Math.min(250,parseInt($('zoom-label').textContent)+difference));state.fit='manual';resizePaper();drawToolbar();emit();};
$('fit-width').onclick=()=>{state.fit='width';resizePaper();drawToolbar();emit();};$('fit-page').onclick=()=>{state.fit='page';resizePaper();drawToolbar();emit();};
$('search-next').onclick=searchNext;$('search').addEventListener('keydown',e=>{if(e.key==='Enter')searchNext();});
$('scope').onchange=e=>{state.scope=e.target.value;setFilter('all');drawPage();};
document.querySelectorAll('#legend-filters button, #point-filters button').forEach(b=>{b.onclick=()=>setFilter(b.dataset.filter);if(citationRoleHelp[b.dataset.filter])b.title=citationRoleHelp[b.dataset.filter];});
$('page-image').onload=()=>{resizePaper();if(pendingScroll)scrollToSelection();};
$('open-map').onclick=()=>{clearTimeout(timer);send('streamlit:setComponentValue',{value:{nonce:Date.now()+Math.random(),navigation:serverNavigation,ui:state,action:'open_map'},dataType:'json'});};
window.addEventListener('resize',frameSize);
window.addEventListener('message',event=>{
  if(event.source!==window.parent||event.data.type!=='streamlit:render')return;
  const args=event.data.args;
  let typography=$('readable-text-styles');
  if(!typography){typography=el('style');typography.id='readable-text-styles';document.head.append(typography);}
  if(typography.textContent!==args.readable_css)typography.textContent=args.readable_css||'';
  if(!initialized||model.analysis_id!==args.model.analysis_id||serverNavigation!==args.navigation){state={...args.ui,filter:'all'};initialized=true;pendingScroll=true;serverNavigation=args.navigation;}
  model=args.model;
  if(args.page.document===state.document&&args.page.number===state.page)currentPage=args.page;
  draw();frameSize();
});
send('streamlit:componentReady',{apiVersion:1});send('streamlit:setFrameHeight',{height:650});
