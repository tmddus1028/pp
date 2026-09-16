// This zero-height Streamlit helper observes presentation only, never source text/state.
window.observeReadableOverflow = (doc) => {
  const selector = '.readable-panel:has(>.readable-toggle), .readable-panel:has(>.source-toggle)';
  const observed = new Set();
  let frame = 0;
  function measure() {
    frame = 0;
    const panels = new Set(doc.querySelectorAll(selector));
    for (const panel of observed) {
      if (!panels.has(panel)) { resize.unobserve(panel); observed.delete(panel); }
    }
    for (const panel of panels) {
      if (!observed.has(panel)) { observed.add(panel); resize.observe(panel); }
      const content = panel.querySelector('.readable-text-content');
      const toggle = panel.querySelector(':scope > .readable-toggle, :scope > .source-toggle');
      if (!content || !content.getBoundingClientRect().width) continue;
      const lines = Number(doc.defaultView.getComputedStyle(panel).getPropertyValue('--readable-lines')) || 5;
      const lineHeight = parseFloat(doc.defaultView.getComputedStyle(content).lineHeight);
      const overflowing = content.scrollHeight > lines * lineHeight + 1;
      toggle.hidden = !overflowing;
      if (!overflowing) {
        if (toggle.tagName === 'DETAILS') toggle.open = false;
        else {
          content.parentElement.classList.add('preview');
          toggle.setAttribute('aria-expanded', 'false');
          if (toggle.textContent !== '원문 더 보기') toggle.textContent = '원문 더 보기';
        }
      }
    }
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(measure); }
  const resize = new ResizeObserver(schedule);
  const mutations = new MutationObserver(schedule);
  mutations.observe(doc.body, {childList:true, subtree:true, characterData:true});
  doc.fonts?.ready.then(schedule);
  schedule();
  window.addEventListener('unload', () => {
    resize.disconnect(); mutations.disconnect(); cancelAnimationFrame(frame);
  });
};
