/* Only generated labels opt in. Never walk dynamic evidence, filenames or citations. */
window.PatentTerminology = (() => {
  let terms = {}, pattern = null;
  const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const text = value => typeof value === 'string' && pattern ? value.replace(pattern, match => terms[match]) : value;
  const originals = [];
  function configure(values) {
    terms = values || {};
    const keys = Object.keys(terms).sort((a,b)=>b.length-a.length);
    pattern = keys.length ? new RegExp(keys.map(key =>
      (/^[A-Za-z]/.test(key)?'(?<![A-Za-z])':'') + escape(key) + (/[A-Za-z]$/.test(key)?'(?![A-Za-z])':'')
    ).join('|'), 'g') : null;
    if (!originals.length) {
      // Only explicitly marked, static HTML labels/attributes are eligible.
      document.querySelectorAll('[data-terminology]').forEach(node => {
        for (const child of node.childNodes) if(child.nodeType === Node.TEXT_NODE) originals.push([child, null, child.textContent]);
      });
      document.querySelectorAll('[data-terminology-attrs]').forEach(node => {
        for(const attr of node.dataset.terminologyAttrs.split(' ')) originals.push([node, attr, node.getAttribute(attr)]);
      });
    }
    for(const [node, attr, original] of originals) {
      if(attr) node.setAttribute(attr,text(original)); else node.textContent=text(original);
    }
  }
  function checklist(value) {
    const direct=value.match(/^(Claim \d+: )(.*)( 지적 사유와 OA 근거를 대조하세요\.)$/);
    if(direct) return text(direct[1])+direct[2]+text(direct[3]);
    const dependent=value.match(/^(종속 Claim [\d, ]+: )(상위 청구항과 연결된 추가 검토 범위를 확인하세요\.)$/);
    if(dependent) return text(dependent[1])+dependent[2];
    if(value==='OA가 지적한 청구항 일부가 입력에 없습니다. OA 당시의 청구항 버전을 확인하세요.') return text(value);
    return value;
  }
  return {configure, text, checklist};
})();
