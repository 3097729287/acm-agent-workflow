import { useMemo, useRef, useState } from 'react';
import { Clock, Flag, LoaderCircle, Play, RefreshCw } from 'lucide-react';

export default function MockSetup({ api, onStarted, onError, activeContest, onResume, categories = [], platforms = [] }) {
  const [config, setConfig] = useState({ mode: 'comprehensive', count: 6, duration: 120, min: 1000, max: 2100, tags: [], platform: '', excludeSolved: true, reviewedOnly: false });
  const [plan, setPlan] = useState(null), [busy, setBusy] = useState(false), [name, setName] = useState(''), [error, setError] = useState(''), [topic, setTopic] = useState('');
  const sequence = useRef(0);
  const topics = useMemo(() => { const result = []; const walk = (nodes, depth = 0) => nodes.forEach(node => { result.push({ ...node, depth }); walk(node.children || [], depth + 1); }); walk(categories); return result; }, [categories]);
  const change = patch => { setConfig(previous => ({ ...previous, ...patch })); setPlan(null); setError(''); sequence.current++; };
  const valid = [config.min, config.max, config.duration].every(value => String(value).trim() !== '' && Number.isFinite(Number(value))) && Number(config.min) <= Number(config.max) && Number(config.duration) >= 10 && Number(config.duration) <= 360 && (config.mode !== 'topic' || config.tags.length > 0);
  async function generate() {
    const seq = ++sequence.current; setBusy(true); setError('');
    try { const result = await api('contests/preview', { ...config, count: config.mode === 'single' ? 1 : Number(config.count), duration: Number(config.duration), min: Number(config.min), max: Number(config.max), tags: config.mode === 'topic' ? config.tags : [] }); if (sequence.current === seq) setPlan(result.plan); }
    catch (issue) { if (sequence.current === seq) setError(issue.message); }
    finally { if (sequence.current === seq) setBusy(false); }
  }
  async function start() {
    if (!plan || busy) return; setBusy(true); setError('');
    try { const result = await api('contests/start', { previewId: plan.previewId, ids: plan.slots.map(slot => slot.id), duration: Number(config.duration), name: name.trim() || plan.name }); onStarted(result); }
    catch (issue) { setError(issue.message); onError?.(issue.message, 'error'); setBusy(false); }
  }
  return <div className="mock-create"><section className="create-main">
    <div className="section-title"><Flag size={22} /><div><h2>按目标组成一套训练</h2><p>选择综合练习、专项训练或随机单题，完成后解锁题解与考点。</p></div></div>
    {activeContest && <div className="active-notice"><Clock size={17} /><span>你有一场进行中的模拟赛</span><button className="primary" onClick={onResume}>继续比赛</button></div>}
    <div className="mock-config">
      <div className="mock-mode-options" role="group" aria-label="组题方式">{[['comprehensive', '综合训练', '多种知识点，逐步增加难度'], ['topic', '专项训练', '指定某个领域或知识点'], ['single', '随机单题', '抽取一道适合难度的题']].map(([mode, title, description]) => <button key={mode} aria-pressed={config.mode === mode} className={config.mode === mode ? 'active' : ''} disabled={busy} onClick={() => change({ mode })}><strong>{title}</strong><span>{description}</span></button>)}</div>
      <div className="mock-name-fields"><label>试卷名称<input aria-label="试卷名称" placeholder="例如：周四晚间训练" value={name} onChange={event => setName(event.target.value)} maxLength={80} disabled={busy} /></label><label>平台<select aria-label="组题平台" value={config.platform} disabled={busy} onChange={event => change({ platform: event.target.value })}><option value="">全部平台</option>{platforms.map(platform => <option key={platform}>{platform}</option>)}</select></label></div>
      {config.mode === 'topic' && <label className="mock-topic-picker">训练知识点 / 类别<select aria-label="专项训练知识点" value={topic} disabled={busy} onChange={event => { setTopic(event.target.value); change({ tags: topics.find(item => item.name === event.target.value)?.tags || [] }); }}><option value="">选择类别或知识点</option>{topics.map((item, index) => <option key={item.name + index} value={item.name}>{'　'.repeat(item.depth)}{item.name}</option>)}</select></label>}
      <div className="field-grid"><label>题目数<select aria-label="模拟赛题目数" value={config.mode === 'single' ? 1 : config.count} disabled={busy || config.mode === 'single'} onChange={event => change({ count: Number(event.target.value) })}>{[1, 3, 4, 6, 8, 10].map(count => <option key={count} value={count}>{count} 题</option>)}</select></label><label>时长（分钟）<input aria-label="模拟赛时长" type="number" min={10} max={360} step={10} value={config.duration} disabled={busy} onChange={event => change({ duration: event.target.value })} /></label><label>最低难度<input aria-label="模拟赛最低难度" type="number" min={600} max={3500} step={50} value={config.min} disabled={busy} onChange={event => change({ min: event.target.value })} /></label><label>最高难度<input aria-label="模拟赛最高难度" type="number" min={600} max={3500} step={50} value={config.max} disabled={busy} onChange={event => change({ max: event.target.value })} /></label></div>
      <div className="presets"><span>难度范围</span>{[{ name: '循序起步', min: 1000, max: 1600 }, { name: '综合练习', min: 1000, max: 2100 }, { name: '挑战进阶', min: 1500, max: 2100 }].map(preset => <button key={preset.name} disabled={busy} className={Number(config.min) === preset.min && Number(config.max) === preset.max ? 'active' : ''} onClick={() => change({ min: preset.min, max: preset.max })}>{preset.name}</button>)}</div>
      <div className="mock-extra-options"><label><input type="checkbox" aria-label="排除已通过题目" checked={config.excludeSolved} disabled={busy} onChange={event => change({ excludeSolved: event.target.checked })} />排除已通过题目</label><label><input type="checkbox" aria-label="只选本地完整评测题" checked={config.reviewedOnly} disabled={busy} onChange={event => change({ reviewedOnly: event.target.checked })} />只选本地完整评测题</label></div>
    </div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <div className="create-buttons"><button className={plan ? 'secondary' : 'primary'} onClick={generate} disabled={busy || !!activeContest || !valid}>{busy ? <LoaderCircle size={16} className="spin" /> : <RefreshCw size={16} />}{plan ? '重新组题' : config.mode === 'single' ? '抽取单题' : '生成试卷'}</button>{plan && <button className="primary" onClick={start} disabled={busy || !!activeContest}><Play size={16} />开始 {config.duration} 分钟训练</button>}</div>
    {plan && <div className="paper-preview" aria-label="训练试卷预览"><div className="paper-preview-title"><span>{config.mode === 'topic' ? `专项训练 · ${topic}` : config.mode === 'single' ? '随机单题' : '综合训练'}</span><span>{plan.slots.length} 题 · {config.duration} 分钟</span></div>{plan.slots.map((slot, index) => <div className="paper-slot" key={slot.id}><strong>{slot.letter || String.fromCharCode(65 + index)}</strong><div><span>{slot.judgeScope === 'local' ? '本地完整评测' : '官方样例评测'}</span><small>考点在训练结束后显示</small></div></div>)}<p>代码按题自动保存；离开页面后倒计时继续。</p></div>}
    <details className="mock-guide"><summary>计时、评测与复盘规则</summary><p>组题预览不计入训练，开始后按题保存代码。赛中隐藏题解、考点与原题链接；结束后可查看复盘，未完成的题进入待办。</p><p>完整审核测试通过计为本地 AC，样例通过单独统计。可以在模拟赛记录中重练与补题。</p></details>
  </section></div>;
}
