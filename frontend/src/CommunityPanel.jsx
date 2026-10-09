import { useCallback, useEffect, useState } from 'react';
import { Check, Copy, RefreshCw, Trophy, UserRound } from 'lucide-react';

export function ProfileSettings({ api, onError, onChanged }) {
  const [snapshot, setSnapshot] = useState(null), [nickname, setNickname] = useState(''), [endpoint, setEndpoint] = useState('');
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  useEffect(() => { let alive = true; api('profile').then(value => { if (!alive) return; setSnapshot(value); setNickname(value.profile?.nickname || ''); setEndpoint(value.leaderboard?.endpoint || ''); }).catch(issue => { if (alive) setError(issue.message); }); return () => { alive = false; }; }, [api]);
  async function save(event) {
    event.preventDefault(); if (busy) return; setBusy(true); setError(''); setMessage('');
    try { const value = await api('profile', { nickname: nickname.trim(), endpoint: endpoint.trim() }); setSnapshot(value); setNickname(value.profile?.nickname || ''); setEndpoint(value.leaderboard?.endpoint || ''); setMessage('昵称与排行榜连接已保存。'); onChanged?.(value); }
    catch (issue) { setError(issue.message); onError?.(issue.message); } finally { setBusy(false); }
  }
  return <section className="profile-settings" aria-label="用户身份与排行榜连接"><div className="progress-section-heading"><h2><UserRound size={18} />用户身份</h2><span>{snapshot?.leaderboard?.configured ? '排行榜已连接' : '本地身份'}</span></div>
    {snapshot?.profile && <div className="profile-identity"><strong>{snapshot.profile.nickname || '用户'}</strong><code className="copyable-id">#{snapshot.profile.userId}</code><button className="text-button" aria-label="复制用户 ID" onClick={() => navigator.clipboard.writeText(snapshot.profile.userId).then(() => setMessage('用户 ID 已复制。')).catch(() => setError('请选中 ID 后按 Ctrl+C 复制。'))}><Copy size={14} /></button></div>}
    <p className="progress-small">ID 是你的固定标识，修改昵称后保留。连接共享服务后，排行榜显示昵称和 ID。</p>
    <form onSubmit={save} className="profile-form"><label>昵称<input aria-label="用户昵称" maxLength={24} value={nickname} onChange={event => setNickname(event.target.value)} placeholder="设置你的昵称" required /></label><label>排行榜服务地址<input aria-label="排行榜服务地址" type="url" value={endpoint} onChange={event => setEndpoint(event.target.value)} placeholder="https://your-service.example" /></label><button className="progress-button progress-primary" disabled={busy || !snapshot}><Check size={14} />保存身份</button></form>
    <p className="progress-small">{snapshot?.leaderboard?.notice || '共享排行榜尚未连接。连接后同步 ID、昵称与过题统计。'}</p>{error && <p className="connection-error" role="alert">{error}</p>}{message && <p className="connection-message" role="status">{message}</p>}
  </section>;
}

export default function RankingsPage({ api, onConfigure, onError }) {
  const [period, setPeriod] = useState('daily'), [snapshot, setSnapshot] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const load = useCallback(async () => { setBusy(true); setError(''); try { setSnapshot(await api('leaderboard?period=' + period)); } catch (issue) { setError(issue.message); onError?.(issue.message); } finally { setBusy(false); } }, [api, period]);
  useEffect(() => { let alive = true; setBusy(true); setError(''); api('leaderboard?period=' + period).then(value => { if (alive) setSnapshot(value); }).catch(issue => { if (alive) setError(issue.message); }).finally(() => { if (alive) setBusy(false); }); return () => { alive = false; }; }, [api, period]);
  async function sync() { if (busy) return; setBusy(true); setError(''); try { await api('leaderboard/sync', {}); await load(); } catch (issue) { setError(issue.message); onError?.(issue.message); setBusy(false); } }
  useEffect(() => {
    if (!snapshot?.configured || snapshot.status !== 'syncing') return;
    const timer = setTimeout(() => { api('leaderboard?period=' + period).then(setSnapshot).catch(issue => setError(issue.message)); }, 1000);
    return () => clearTimeout(timer);
  }, [api, period, snapshot]);
  const entries = Array.isArray(snapshot?.entries) ? snapshot.entries : [];
  return <div className="rankings-page scroll-panel" aria-label="用户过题排行榜"><section className="progress-section">
    <div className="progress-section-heading"><h2><Trophy size={20} />过题排行榜</h2><button className="progress-button" onClick={snapshot?.configured ? sync : load} disabled={busy}><RefreshCw size={14} className={busy ? 'spin' : ''} />{snapshot?.configured ? '同步与刷新' : '刷新'}</button></div>
    <div className="ranking-tabs" role="tablist" aria-label="排行榜时间范围">{[['daily', '每日过题'], ['weekly', '本周过题'], ['total', '累计过题']].map(([value, label]) => <button role="tab" aria-selected={period === value} className={period === value ? 'active' : ''} key={value} onClick={() => setPeriod(value)}>{label}</button>)}</div>
    <p className="progress-small">按不同题目的首次通过数排名。{snapshot?.date ? `统计日期：${snapshot.date}。` : ''}</p>
    {error ? <p className="connection-error" role="alert">{error}</p> : !snapshot ? <p className="progress-muted" role="status">正在读取排行榜…</p> : !snapshot.configured || snapshot.status === 'offline' || snapshot.status === 'error' && !entries.length ? <div className="ranking-empty"><Trophy size={32} /><h3>{snapshot.configured ? '排行榜暂时无法连接' : '共享排行榜尚未连接'}</h3><p>{snapshot.error || snapshot.notice || '在偏好设置中填写排行榜服务地址，连接后查看所有用户的排名。'}</p><button className="progress-button progress-primary" onClick={onConfigure}>设置昵称与连接</button></div> : entries.length ? <div className="progress-table-scroll"><table className="ranking-table"><thead><tr><th>排名</th><th>用户 · ID</th><th>过题数</th></tr></thead><tbody>{entries.map(item => <tr key={item.userId} className={snapshot.self?.userId === item.userId ? 'ranking-self' : ''}><td>{item.rank}</td><td><strong>{item.nickname || item.displayName || '用户'}</strong><code className="copyable-id">{item.userId}</code>{snapshot.self?.userId === item.userId && <span className="tag">我</span>}</td><td><b>{item.count}</b></td></tr>)}</tbody></table></div> : <div className="ranking-empty" role="status">{snapshot.status === 'syncing' ? <p><RefreshCw size={18} className="spin" />正在同步过题记录…</p> : <><h3>服务已连接</h3><p>这个统计周期还没有首次审核通过记录。</p>{snapshot.self && <p>我的过题数：{snapshot.self.count || 0}</p>}</>}</div>}
  </section></div>;
}
