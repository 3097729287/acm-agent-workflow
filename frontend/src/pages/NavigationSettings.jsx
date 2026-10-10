import { useState } from 'react';
import { ArrowDown, ArrowUp, BookmarkPlus, Layers, RotateCcw, X } from 'lucide-react';

export function orderedPages(pages, preferences) {
  const order = Array.isArray(preferences.navOrder) ? preferences.navOrder : [];
  return [...pages].sort((left, right) => {
    const a = order.indexOf(left.id), b = order.indexOf(right.id);
    return (a < 0 ? 100 + pages.indexOf(left) : a) - (b < 0 ? 100 + pages.indexOf(right) : b);
  }).map(page => ({ ...page, label: preferences.navLabels?.[page.id]?.trim() || page.label, group: preferences.navGroups?.[page.id]?.trim() || '' }));
}

export default function NavigationSettings({ pages, prefs, setPrefs, onOpen }) {
  const [bookmarkPage, setBookmarkPage] = useState('mine'), [bookmarkName, setBookmarkName] = useState('');
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
    <div className="settings-bookmarks"><h3><BookmarkPlus size={17} />书签与常用筛选</h3>
      <form className="bookmark-add" onSubmit={event => { event.preventDefault(); const item = ordered.find(page => page.id === bookmarkPage); setPrefs(previous => ({ ...previous, pageBookmarks: [...(previous.pageBookmarks || []), { id: crypto.randomUUID(), page: bookmarkPage, name: bookmarkName.trim() || item.label }] })); setBookmarkName(''); }}>
        <select aria-label="书签页面" value={bookmarkPage} onChange={event => setBookmarkPage(event.target.value)}>{ordered.map(page => <option key={page.id} value={page.id}>{page.label}</option>)}</select><input aria-label="新书签名称" placeholder="书签名称" maxLength={24} value={bookmarkName} onChange={event => setBookmarkName(event.target.value)} /><button className="secondary" type="submit"><BookmarkPlus size={14} />添加书签</button>
      </form>
      {(prefs.pageBookmarks || []).map(item => <div className="bookmark-editor-row" key={item.id}><input aria-label={`书签名称 ${item.id}`} value={item.name} maxLength={24} onChange={event => setPrefs(previous => ({ ...previous, pageBookmarks: previous.pageBookmarks.map(bookmark => bookmark.id === item.id ? { ...bookmark, name: event.target.value } : bookmark) }))} /><button className="text-button" onClick={() => onOpen(item.page)}>打开</button><button aria-label={`删除书签 ${item.name}`} onClick={() => setPrefs(previous => ({ ...previous, pageBookmarks: previous.pageBookmarks.filter(bookmark => bookmark.id !== item.id) }))}><X size={15} /></button></div>)}
      {(prefs.views || []).map(item => <div className="bookmark-editor-row" key={item.id}><input aria-label={`筛选书签名称 ${item.id}`} value={item.name} maxLength={24} onChange={event => setPrefs(previous => ({ ...previous, views: previous.views.map(view => view.id === item.id ? { ...view, name: event.target.value } : view) }))} /><span className="progress-small">已保存筛选</span><button aria-label={`删除筛选 ${item.name}`} onClick={() => setPrefs(previous => ({ ...previous, views: previous.views.filter(view => view.id !== item.id) }))}><X size={15} /></button></div>)}
    </div>
  </section>;
}
