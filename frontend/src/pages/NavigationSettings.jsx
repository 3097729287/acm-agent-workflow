import { ArrowDown, ArrowUp, Layers, RotateCcw } from 'lucide-react';

export function orderedPages(pages, preferences) {
  const order = Array.isArray(preferences.navOrder) ? preferences.navOrder : [];
  const groups={...(preferences.navGroups||{})};
  for(const [ids,fallback] of [[['mine','today'],'训练与待办'],[['growth','activity','goals'],'成长与能力']]) {
    const group=ids.map(id=>groups[id]?.trim()).find(Boolean)||fallback;
    ids.forEach(id=>{groups[id]=group;});
  }
  return [...pages].sort((left, right) => {
    const a = order.indexOf(left.id), b = order.indexOf(right.id);
    return (a < 0 ? 100 + pages.indexOf(left) : a) - (b < 0 ? 100 + pages.indexOf(right) : b);
  }).map(page => ({ ...page, label: preferences.navLabels?.[page.id]?.trim() || page.label, group: groups[page.id]?.trim() || '' }));
}

export default function NavigationSettings({ pages, prefs, setPrefs }) {
  const ordered = orderedPages(pages, prefs);
  const move = (id, direction) => {
    const next = ordered.map(page => page.id), index = next.indexOf(id), target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setPrefs(previous => ({ ...previous, navOrder: next }));
  };
  const rename = (field, id, value) => setPrefs(previous => ({ ...previous, [field]: { ...previous[field], [id]: value } }));
  return <section className="settings-navigation">
    <div className="progress-section-heading"><h2><Layers size={18} />导航与页面组合</h2><button className="text-button" onClick={() => setPrefs(previous => ({ ...previous, navOrder: [], navLabels: {}, navGroups: {} }))}><RotateCcw size={14} />恢复默认</button></div>
    <p className="progress-small">修改名称与顺序；填写相同组合名称，将页面合并到一个导航入口，使用页内标签切换。键盘快捷键保留。</p>
    <div className="navigation-editor" aria-label="自定义导航栏">
      <div className="navigation-editor-heading"><span>页面名称</span><span>页面组合（可选）</span><span>顺序</span></div>
      {ordered.map((page, index) => <div className="navigation-editor-row" key={page.id}>
        <label><page.icon size={16} /><input aria-label={`导航名称 ${page.id}`} value={prefs.navLabels?.[page.id] ?? pages.find(item => item.id === page.id).label} maxLength={18} onChange={event => rename('navLabels', page.id, event.target.value)} /></label>
        <input aria-label={`页面组合 ${page.id}`} value={prefs.navGroups?.[page.id] || ''} maxLength={18} placeholder="例如：学习记录" onChange={event => rename('navGroups', page.id, event.target.value)} />
        <span className="navigation-reorder"><button aria-label={`上移 ${page.label}`} disabled={index === 0} onClick={() => move(page.id, -1)}><ArrowUp size={16} /></button><button aria-label={`下移 ${page.label}`} disabled={index === ordered.length - 1} onClick={() => move(page.id, 1)}><ArrowDown size={16} /></button></span>
      </div>)}
    </div>
  </section>;
}
