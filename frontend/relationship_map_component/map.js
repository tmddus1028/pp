'use strict';
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const el = (tag, cls, text) => {const n=document.createElement(tag);if(cls)n.className=cls;if(tag==='p'||cls==='detail-title')n.classList.add('readable-text');if(text!==undefined)n.textContent=text;return n;};
const svgEl = (tag, attrs={}, text) => {const n=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n;};
const send = (type, extra={}) => window.parent.postMessage({isStreamlitMessage:true,type,...extra},'*');
let model, state, navigation=-1, hovered=null, visibleEdges=[];
const nodeById = id => model.nodes.find(n=>n.id===id);
const itemFor = node => model.items.find(i=>i.id===node?.item_id);
const edgeKey = edge => JSON.stringify([edge.source,edge.target,edge.relation]);
const relevantRejections = node => {
  if(!node||node.kind==='office_action')return model.rejections.map(r=>r.rejection_id);
  if(node.kind==='rejection')return [node.id];
  return itemFor(node)?.rejection_ids||model.edges.filter(e=>e.target===node.id&&e.relation==='directly_addresses').map(e=>e.source);
};
const scopedRejections = () => model.rejections.filter(r=>state.scope==='all'||r.rejection_id===state.scope);
const statusOf = node => {
  if(node.kind==='citation'){
    const roles=(itemFor(node)?.occurrences||[]).filter(e=>state.scope==='all'||e.rejection_id===state.scope).map(e=>e.role);
    if(!roles.includes('relied_upon')&&roles.includes('supporting_evidence'))return 'supporting_evidence';
  }
  if(node.kind!=='claim')return node.kind==='office_action'?'root':node.kind;
  const item=itemFor(node);if(!item)return node.status;
  if(['allowed','withdrawn','canceled'].includes(item.status))return item.status;
  if(item.direct.some(r=>state.scope==='all'||state.scope===r))return 'direct';
  if((item.objected||[]).some(r=>state.scope==='all'||state.scope===r)||item.status==='objected'&&state.scope==='all')return 'objected';
  if(item.indirect.some(r=>state.scope==='all'||state.scope===r))return 'impacted';
  return 'unaddressed';
};
const statusLabels = {direct:'직접 지적',objected:'Objection',allowed:'허용',withdrawn:'심사 대상 제외',impacted:'종속 영향',unaddressed:'추출된 지적 없음',missing:'원문 없음',canceled:'취소됨',rejection:'거절 / 지적 사유',citation:'인용 문헌',root:'Office Action'};
statusLabels.supporting_evidence='보조 증거';
const makeButton = (text, callback, cls) => {const n=el('button',cls,text);n.type='button';n.onclick=callback;return n;};
const citationType = ref => ref?.type==='npl'?'NPL · 비특허 문헌':ref?.type==='patent'?'Patent · 특허 문헌':'문헌 유형 미확인';
function emit(action){send('streamlit:setComponentValue',{value:{nonce:Date.now()+Math.random(),ui:state,action},dataType:'json'});}
function selectNode(id){
  const node=nodeById(id);if(!node)return;
  state.selected=id;hovered=null;
  if(state.scope!=='all'&&!relevantRejections(node).includes(state.scope))state.scope='all';
  if(node.kind==='claim'){
    if(!['all','claim','dependency'].includes(state.filter))state.filter='all';
    state.dependencies=true;
    if(statusOf(node)!=='direct')state.direct_only=false;
  }
  if(node.kind==='citation'){state.citations=true;if(!['all','citation'].includes(state.filter))state.filter='all';}
  draw();emit();
  requestAnimationFrame(()=>{
    const selected=$('map').querySelector('.node.selected');if(!selected)return;
    const scroll=$('map-scroll'),a=selected.getBoundingClientRect(),b=scroll.getBoundingClientRect();
    if(a.top<b.top||a.bottom>b.bottom)scroll.scrollTop+=a.top-b.top-30;
  });
}
function graphView(){
  const rejections=scopedRejections(),rids=new Set(rejections.map(r=>r.rejection_id));
  const selected=nodeById(state.selected),primary=new Set(rejections.flatMap(r=>r.primary_claims||[]).map(n=>'CL'+n));
  const allowed=node=>{
    if(node.kind!=='claim')return false;
    if(state.direct_only&&statusOf(node)!=='direct')return false;
    return state.scope==='all'||relevantRejections(node).some(r=>rids.has(r));
  };
  const claims=new Set(primary),neighbors=new Set(),children=new Set();
  rejections.filter(r=>state.expanded.includes(r.rejection_id)).forEach(r=>r.claims.forEach(n=>claims.add('CL'+n)));
  if(selected?.kind==='claim'){
    claims.add(selected.id);
    if(state.dependencies)for(const edge of model.edges.filter(e=>e.relation==='depends_on')){
      if(edge.source===selected.id||edge.target===selected.id){
        neighbors.add(edge.source);neighbors.add(edge.target);claims.add(edge.source);claims.add(edge.target);
        if(edge.source===selected.id)children.add(edge.target);
      }
    }
  }
  if(state.filter==='dependency'){
    for(const id of [...claims])if(id!==selected?.id&&!neighbors.has(id))claims.delete(id);
  }
  const nodes=model.nodes.filter(n=>{
    if(n.kind==='office_action')return true;
    if(n.kind==='rejection')return rids.has(n.id);
    if(n.kind==='claim')return ['all','claim','dependency'].includes(state.filter)&&claims.has(n.id)&&allowed(n);
    return ['all','citation'].includes(state.filter)&&state.citations&&model.edges.some(e=>e.relation==='cites'&&e.target===n.id&&rids.has(e.source));
  });
  const ids=new Set(nodes.map(n=>n.id));
  const edges=model.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)&&
    (e.relation!=='depends_on'||state.dependencies&&(e.source===selected?.id||e.target===selected?.id)));
  return {nodes,edges,children};
}
function drawControls(){
  document.querySelectorAll('#filters button').forEach(b=>b.setAttribute('aria-pressed',String(state.filter===b.dataset.filter)));
  $('direct-only').checked=state.direct_only;$('dependencies').checked=state.dependencies;$('citations').checked=state.citations;
  $('scope').replaceChildren(new Option('전체 거절 사유','all'),...model.rejections.map(r=>new Option(r.rejection_id+' · '+r.statute,r.rejection_id)));
  $('scope').value=state.scope;
  $('claim-picker').replaceChildren(new Option('Claim 선택',''),...model.nodes.filter(n=>n.kind==='claim').map(n=>new Option(n.label,n.id)));
  $('claim-picker').value=nodeById(state.selected)?.kind==='claim'?state.selected:'';
  $('branches').replaceChildren();
  if(['all','claim'].includes(state.filter))for(const r of scopedRejections()){
    const expanded=state.expanded.includes(r.rejection_id);
    const b=makeButton(r.rejection_id+' · 청구항 '+r.claims.length+'개 '+(expanded?'접기':'펼치기'),()=>{
      state.expanded=expanded?state.expanded.filter(id=>id!==r.rejection_id):[...state.expanded,r.rejection_id];draw();emit();
    });
    b.setAttribute('aria-expanded',String(expanded));$('branches').append(b);
  }
}
function drawGraph(){
  const view=graphView(),svg=$('map');svg.replaceChildren();visibleEdges=view.edges;
  const defs=svgEl('defs'),marker=svgEl('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto'});
  marker.append(svgEl('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#91a99e'}));defs.append(marker);svg.append(defs);
  const positions=new Map(),leafNodes=view.nodes.filter(n=>['claim','citation'].includes(n.kind)&&!view.children.has(n.id));
  leafNodes.sort((a,b)=>(a.kind==='citation')-(b.kind==='citation')||(a.claim_number||0)-(b.claim_number||0));
  leafNodes.forEach((n,i)=>positions.set(n.id,{x:420,y:55+i*64,w:200}));
  const anchor=positions.get(state.selected)?.y||55;
  view.nodes.filter(n=>view.children.has(n.id)).forEach((n,i)=>positions.set(n.id,{x:650,y:anchor+i*64,w:170}));
  view.nodes.filter(n=>n.kind==='rejection').forEach((n,i)=>positions.set(n.id,{x:198,y:65+i*100,w:180}));
  view.nodes.filter(n=>n.kind==='office_action').forEach(n=>positions.set(n.id,{x:24,y:65,w:140}));
  const height=Math.max(310,...[...positions.values()].map(p=>p.y+80)),width=view.nodes.some(n=>view.children.has(n.id))?846:650;
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('height',height);svg.setAttribute('width','100%');
  for(const [x,text] of [[24,'OFFICE ACTION'],[198,'거절 사유'],[420,'주요 CLAIM / 인용문헌'],[650,'선택 CLAIM의 종속항']]){
    if(x<width-40)svg.append(svgEl('text',{x,y:26,class:'lane-label'},text));
  }
  for(const edge of view.edges){
    const a=positions.get(edge.source),b=positions.get(edge.target);let path;
    if(a.x===b.x){const x=a.x+a.w+9;path=`M ${a.x+a.w} ${a.y+25} C ${x+17} ${a.y+25}, ${x+17} ${b.y+25}, ${b.x+b.w} ${b.y+25}`;}
    else path=`M ${a.x+a.w} ${a.y+25} C ${a.x+a.w+24} ${a.y+25}, ${b.x-24} ${b.y+25}, ${b.x-3} ${b.y+25}`;
    svg.append(svgEl('path',{d:path,class:'edge '+edge.relation,'data-key':edgeKey(edge),'data-source':edge.source,'data-target':edge.target,'data-relation':edge.relation,'marker-end':'url(#arrow)'}));
  }
  for(const node of view.nodes){
    const p=positions.get(node.id),status=statusOf(node),item=itemFor(node),g=svgEl('g',{class:'node '+status+(node.id===state.selected?' selected':''),transform:`translate(${p.x},${p.y})`,tabindex:0,role:'button','aria-label':node.label+' 관계 보기','aria-pressed':String(node.id===state.selected),'data-node-id':node.id});
    g.append(svgEl('rect',{width:p.w,height:50,rx:8}));
    const title=node.kind==='citation'?(item?.title||node.label):node.label;
    const subtitle=node.kind==='citation'?(item?.reference.publication_number||citationType(item?.reference)):node.kind==='claim'?statusLabels[status]:node.kind==='rejection'?'직접 지적 '+model.rejections.find(r=>r.rejection_id===node.id).claims.length+'개':'심사 의견서';
    const shorten=(s,n)=>s.length>n?s.slice(0,n-1)+'…':s;
    g.append(svgEl('text',{x:10,y:21},shorten(title,Math.floor(p.w/7))));g.append(svgEl('text',{x:10,y:39,class:'subtitle'},shorten(subtitle,Math.floor(p.w/6))));g.append(svgEl('title',{},node.label+' · '+subtitle));
    g.onclick=()=>selectNode(node.id);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectNode(node.id);}};
    g.onmouseenter=()=>{hovered=node.id;highlight();};g.onmouseleave=()=>{hovered=null;highlight();};g.onfocus=()=>{hovered=node.id;highlight();};g.onblur=()=>{hovered=null;highlight();};svg.append(g);
  }
  highlight();$('map-status').textContent=`${view.nodes.length}개 노드 · ${view.edges.length}개 연결 · 접힌 Claim은 펼치기 또는 Claim 찾기로 확인하세요.`;
}
function highlight(){
  const id=hovered||state.selected,node=nodeById(id),keys=new Set(),ids=new Set(id?[id]:[]);
  if(node){
    const rids=new Set(relevantRejections(node));
    for(const edge of visibleEdges){
      const linked=hovered?(edge.source===id||edge.target===id):
        node.kind==='office_action'||
        edge.relation==='contains'&&rids.has(edge.target)||
        edge.relation==='cites'&&rids.has(edge.source)&&(node.kind!=='citation'||edge.target===id)||
        edge.relation==='directly_addresses'&&rids.has(edge.source)&&(node.kind!=='claim'||edge.target===id||visibleEdges.some(d=>d.relation==='depends_on'&&d.source===edge.target&&d.target===id))||
        edge.relation==='depends_on'&&(edge.source===id||edge.target===id);
      if(linked){keys.add(edgeKey(edge));ids.add(edge.source);ids.add(edge.target);}
    }
  }
  document.querySelectorAll('.edge').forEach(e=>{e.classList.toggle('dimmed',Boolean(node)&&!keys.has(e.dataset.key));e.classList.toggle('highlight',Boolean(node)&&keys.has(e.dataset.key));});
  document.querySelectorAll('.node').forEach(n=>n.classList.toggle('dimmed',Boolean(node)&&!ids.has(n.dataset.nodeId)));
}
function chips(root, nodes){
  const row=el('div','chips');for(const node of nodes)row.append(makeButton(node.kind==='citation'?(itemFor(node)?.title||node.label):node.label,()=>selectNode(node.id)));root.append(row);
}
function label(root,text){root.append(el('h4','detail-label',text));}
function source(root,evidence,caption='Office Action'){
  const card=el('div','source-card readable-panel'),text=el('div','source preview readable-text');
  text.append(el('span','readable-text-content',evidence.text));
  card.append(el('p','detail-note',caption+' p. '+evidence.page_numbers.join(', ')),text);
  const toggle=makeButton('원문 더 보기',()=>{
    const expanded=text.classList.toggle('preview')===false;
    toggle.textContent=expanded?'접기':'원문 더 보기';toggle.setAttribute('aria-expanded',String(expanded));
  },'source-toggle');
  toggle.setAttribute('aria-expanded','false');card.append(toggle);root.append(card);
}
function drawDetail(){
  const root=$('map-detail'),node=nodeById(state.selected);root.replaceChildren();
  if(!node){root.append(el('span','eyebrow','관계 상세'),el('h3','','관계를 선택하세요'),el('p','detail-note','처음에는 주요 Claim과 인용문헌만 표시합니다. 노드를 선택하면 관련 경로와 원문 연결을 확인할 수 있습니다.'));return;}
  const item=itemFor(node),rids=relevantRejections(node).filter(r=>state.scope==='all'||r===state.scope),rejections=model.rejections.filter(r=>rids.includes(r.rejection_id));
  root.append(el('div','detail-type '+statusOf(node),statusLabels[statusOf(node)]),el('h3','detail-title',node.kind==='citation'?(item?.title||node.label):node.label));
  const actions=el('div','detail-actions');
  if(item){const b=makeButton(node.kind==='claim'?'PDF에서 보기':'Office Action 근거 보기',()=>emit('open_pdf'),'source-button');b.id='open-source';actions.append(b);}
  if(item&&node.kind==='claim')actions.append(makeButton('근거 비교',()=>emit('open_comparison'),'source-button'));
  if(node.kind==='citation'&&item){
    label(root,'문헌 역할');root.append(el('p','detail-text',statusOf(node)==='supporting_evidence'?'보조 증거':'거절 인용문헌'));
    label(root,'문헌 종류');root.append(el('p','detail-text',citationType(item.reference)));
    label(root,'Publication');root.append(el('p','detail-text',item.reference.publication_number||[item.reference.publication,item.reference.year].filter(Boolean).join(' · ')||'원문 참조'));
  }
  label(root,'연결된 거절 · 법조항');chips(root,rejections.map(r=>nodeById(r.rejection_id)));
  if(node.kind==='claim'||node.kind==='rejection'){
    const refs=new Set(model.edges.filter(e=>e.relation==='cites'&&rids.includes(e.source)).map(e=>e.target));
    label(root,'관련 인용문헌 · '+refs.size+'개');chips(root,[...refs].map(nodeById));
  }
  if(['citation','rejection'].includes(node.kind)){
    label(root,'관련 Claim · 같은 거절에 연결된 청구항');const numbers=new Set(rejections.flatMap(r=>r.claims));chips(root,model.nodes.filter(n=>n.kind==='claim'&&numbers.has(n.claim_number)));
    if(node.kind==='citation')root.append(el('p','detail-note','거절 사유 단위의 연결입니다. 각 문헌이 모든 Claim 구성을 개별적으로 개시한다는 판단은 아닙니다.'));
  }
  if(item){label(root,node.kind==='claim'?'Claim 원문':'Office Action 원문 근거');source(root,item.evidence,node.kind==='claim'?'Patent':'Office Action');root.append(actions);}
  for(const r of rejections){const details=el('details','rejection-source');details.dataset.rejectionId=r.rejection_id;details.append(el('summary','',r.rejection_id+' · '+r.statute+' 원문'));source(details,r.evidence);root.append(details);}
  if(node.kind==='claim'){
    label(root,'상위 Claim');const parents=model.edges.filter(e=>e.relation==='depends_on'&&e.target===node.id).map(e=>nodeById(e.source));if(parents.length)chips(root,parents);else root.append(el('p','detail-note','독립항'));
    label(root,'종속 Claim');const children=model.edges.filter(e=>e.relation==='depends_on'&&e.source===node.id).map(e=>nodeById(e.target));if(children.length)chips(root,children);else root.append(el('p','detail-note','직접 종속항 없음'));
    if(!item)root.append(el('p','detail-note','분석 결과에 언급된 번호이지만 Claim 원문이 없어 PDF로 이동할 수 없습니다.'));
  }
  if(node.kind==='office_action'){root.append(el('p','detail-note',model.documents.find(d=>d.kind==='office_action')?.filename||'Office Action'));}
  root.scrollTop=0;
}
function draw(){if(!model)return;drawControls();drawGraph();drawDetail();}
function reset(){state={selected:null,filter:'all',scope:'all',direct_only:false,dependencies:false,citations:true,expanded:[]};hovered=null;draw();emit();}
function frameSize(){let height=768;try{height=window.parent.innerHeight;}catch(_error){}const h=Math.max(610,Math.min(860,height-145));document.documentElement.style.setProperty('--height',h+'px');send('streamlit:setFrameHeight',{height:window.innerWidth<=880?1230:h+2});}
document.querySelectorAll('#filters button').forEach(b=>b.onclick=()=>{
  state.filter=b.dataset.filter;
  if(state.filter==='dependency'){
    state.dependencies=true;
    if(nodeById(state.selected)?.kind!=='claim')state.selected='CL'+scopedRejections().flatMap(r=>r.primary_claims||[])[0];
    if(!nodeById(state.selected))state.selected=null;
  }else if(state.filter==='citation'){state.citations=true;state.selected=null;}else state.selected=null;
  hovered=null;draw();emit();
});
$('scope').onchange=e=>{state.scope=e.target.value;state.selected=null;hovered=null;draw();emit();};
$('claim-picker').onchange=e=>{if(e.target.value)selectNode(e.target.value);};
for(const [id,key] of [['direct-only','direct_only'],['dependencies','dependencies'],['citations','citations']])$(id).onchange=e=>{state[key]=e.target.checked;hovered=null;draw();emit();};
$('reset').onclick=reset;
window.addEventListener('resize',frameSize);
window.addEventListener('message',event=>{
  if(event.source!==window.parent||event.data.type!=='streamlit:render')return;
  const args=event.data.args;
  let typography=$('readable-text-styles');
  if(!typography){typography=el('style');typography.id='readable-text-styles';document.head.append(typography);}
  if(typography.textContent!==args.readable_css)typography.textContent=args.readable_css||'';
  if(!model||model.analysis_id!==args.model.analysis_id||navigation!==args.navigation){state={...args.ui};navigation=args.navigation;hovered=null;}
  model=args.model;draw();frameSize();
});
send('streamlit:componentReady',{apiVersion:1});send('streamlit:setFrameHeight',{height:640});
