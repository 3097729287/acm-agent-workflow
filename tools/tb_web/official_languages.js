// The displayed language may name a C++ standard, a compiler release, or both.
// We only select values in actual language controls, never arbitrary page text.
function compilerCandidate(text, code = '') {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  if (!/(?:c\+\+|g\+\+|gnu\+\+|clang\+\+)/i.test(value) || /(?:c#|objective)/i.test(value)) return null;
  let required = /(?:std::(?:print|println|expected)|#\s*include\s*<\s*(?:print|expected)\s*>)/.test(code) ? 23
    : /(?:std::(?:ranges|span)|#\s*include\s*<\s*(?:ranges|span|concepts|coroutine)\s*>|\b(?:concept|co_await|co_return|requires)\b)/.test(code) ? 20 : 17;
  let explicit = value.match(/(?:c\+\+|g\+\+|gnu\+\+)\s*(?:std\s*)?(11|14|17|20|23|26|0x|1y|1z|2a|2b|2c)\b(?!\.\d)/i);
  if (explicit && /g\+\+/i.test(explicit[0]) && value.lastIndexOf('(', explicit.index) > value.lastIndexOf(')', explicit.index)) explicit = null;
  const aliases = {'0x':11,'1y':14,'1z':17,'2a':20,'2b':23,'2c':26};
  const standard = explicit ? (aliases[explicit[1].toLowerCase()] || Number(explicit[1])) : null;
  const compiler = value.match(/(?:gcc|g\+\+|clang)\s*[-:]?\s*(\d{1,2})(?:\.\d+)?/i);
  const version = compiler ? Number(compiler[1]) : null;
  if (standard !== null && standard < required) return null;
  // GCC 11+ defaults to GNU++17; GCC 8+ implements C++17 but an unnamed
  // site choice does not prove that it actually enables that standard.
  if (standard === null && required > 17) return null;
  if (standard === null && version !== null && /gcc|g\+\+/i.test(value) && version < 11) return null;
  return {label:value, standard:standard || 17, compilerVersion:version,
    score:standard !== null ? standard - required : version !== null ? 40 - Math.min(version,30) : 45};
}

async function selectOfficialCompiler(code) {
  const selectors = '.ivu-select-selected-value,.el-select__selected-item,.ant-select-selection-item,[role=combobox],.language-select .selected,.lang-select .selected';
  const visible = node => node && node.getClientRects().length > 0;
  const candidates = values => values.map(node => ({node, candidate:compilerCandidate(node.textContent || node.value, code)}))
    .filter(item => item.candidate && !item.node.disabled).sort((a,b)=>a.candidate.score-b.candidate.score);
  for (const select of document.querySelectorAll('select')) {
    if (!/language|programtype|compiler|lang(?:uage)?id/i.test(select.name || select.id || '')) continue;
    const item = candidates([...select.options])[0];
    if (!item) continue;
    select.value = item.node.value;
    select.dispatchEvent(new Event('input', {bubbles:true}));
    select.dispatchEvent(new Event('change', {bubbles:true}));
    return item.candidate;
  }
  const selected = [...document.querySelectorAll(selectors)].filter(visible);
  const current = candidates(selected)[0];
  if (current) return current.candidate;
  // Only open a real combobox or a known component whose label identifies
  // language/compiler selection. The currently selected Java is insufficient.
  for (const control of selected) {
    const parent = control.closest('.ivu-select,.el-select,.ant-select,.language-select,.lang-select') || control;
    const hint = [parent.className, parent.getAttribute('aria-label'), parent.getAttribute('data-field'), parent.id].join(' ');
    if (!/language|compiler|lang-select|programtype/i.test(hint) && selected.length > 1) continue;
    control.click();
    for (let attempt = 0; attempt < 6; attempt++) {
      await new Promise(resolve => setTimeout(resolve,50));
      const options = [...document.querySelectorAll('[role=option],.ivu-select-item,.el-select-dropdown__item,.ant-select-item-option')].filter(visible);
      const chosen = candidates(options)[0];
      if (!chosen) continue;
      chosen.node.click();
      await new Promise(resolve => setTimeout(resolve,50));
      const confirmed = candidates([...document.querySelectorAll(selectors)].filter(visible))[0];
      if (confirmed) return confirmed.candidate;
    }
  }
  return null;
}
