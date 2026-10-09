import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { ArrowRight, BookOpen, Layers3, RefreshCw, Sparkles, Target, X } from 'lucide-react';
import { STATE_CLASS, STATES } from './model.js';
import { buildPlan } from './planner.js';
import './PracticePlanner.css';

export { buildPlan } from './planner.js';

export default function PracticePlanner({ rows = [], onClose, onSelect, onStart }) {
  const [min, setMin] = useState('1300');
  const [max, setMax] = useState('2100');
  const [count, setCount] = useState(6);
  const [seed, setSeed] = useState(0);
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const titleId = useId(), detailId = useId();
  const validRange = min !== '' && max !== '' && Number.isFinite(Number(min)) && Number.isFinite(Number(max)) && Number(min) >= 0 && Number(min) <= Number(max);
  const plan = useMemo(() => buildPlan(rows, { min, max, count, seed }), [rows, min, max, count, seed]);
  const coverage = useMemo(() => new Set(plan.flatMap(item => item.newTags)).size, [plan]);
  const priorityCount = plan.filter(item => [STATES[1], STATES[2]].includes(item.row.status)).length;

  useEffect(() => {
    const previousFocus = document.activeElement;
    dialogRef.current?.querySelector('[data-planner-focus]')?.focus();
    function keydown(event) {
      event.stopPropagation();
      if (event.key === 'Escape') {
        event.preventDefault();
        closeRef.current?.();
        return;
      }
      if (event.key !== 'Tab') return;
      const targets = [...(dialogRef.current?.querySelectorAll('button:not(:disabled), input:not(:disabled), [tabindex="0"]') || [])].filter(el => el.getClientRects().length);
      const first = targets[0], last = targets.at(-1);
      if (!first) {
        event.preventDefault();
        dialogRef.current?.focus();
      } else if (event.shiftKey && (document.activeElement === first || !dialogRef.current?.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialogRef.current?.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener('keydown', keydown, true);
    return () => {
      document.removeEventListener('keydown', keydown, true);
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus();
    };
  }, []);

  return <div className="modal-backdrop planner-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose?.(); }}>
    <section className="practice-planner" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={detailId} ref={dialogRef} tabIndex={-1}>
      <header className="planner-heading">
        <div className="planner-symbol"><Sparkles size={22} /></div>
        <div className="planner-heading-copy"><div className="eyebrow">A LITTLE BETTER, EVERY DAY</div><h2 id={titleId}>安排一组训练</h2></div>
        <button className="icon-button planner-close" aria-label="关闭训练推荐" title="关闭 · Esc" onClick={onClose}><X size={19} /></button>
      </header>
      <p className="planner-description" id={detailId}>根据当前状态、难度范围和知识点覆盖选择；题解可按需展开。</p>
      <div className="planner-controls">
        <fieldset className="planner-difficulty"><legend><Target size={13} />难度范围</legend><div>
          <label><span className="planner-sr-only">最低难度</span><input data-planner-focus type="number" inputMode="numeric" min="0" step="100" value={min} onChange={event => setMin(event.target.value)} aria-invalid={!validRange} /></label>
          <span className="planner-range-divider">至</span>
          <label><span className="planner-sr-only">最高难度</span><input type="number" inputMode="numeric" min="0" step="100" value={max} onChange={event => setMax(event.target.value)} aria-invalid={!validRange} /></label>
        </div></fieldset>
        <fieldset className="planner-count"><legend>本组目标题数</legend><div className="segmented">{[3, 6, 10].map(value => <button key={value} type="button" className={count === value ? 'active' : ''} aria-pressed={count === value} onClick={() => setCount(value)}>{value} 题</button>)}</div></fieldset>
      </div>
      {!validRange && <p className="planner-validation" role="alert">请输入有效的难度范围，最低难度应不大于最高难度。</p>}
      <div className="planner-list-heading"><span><Layers3 size={14} />推荐 <strong>{plan.length}</strong> 题<span className="planner-heading-separator">/</span>覆盖 <strong>{coverage}</strong> 个知识点</span><button className="text-button planner-refresh" onClick={() => setSeed(value => value + 1)} disabled={!plan.length} title="在同等条件的题目之间重新挑选"><RefreshCw size={12} key={seed} className={seed ? 'planner-refresh-icon' : ''} />换一组</button></div>
      <div className="planner-list" aria-live="polite" aria-atomic="true">
        {plan.length ? <ol>{plan.map((item, index) => <li className="planner-item" key={item.row.id}>
          <span className="planner-order">{String(index + 1).padStart(2, '0')}</span>
          <div className="planner-item-content"><div className="planner-title-line"><h3>{item.row.title}</h3><span className="difficulty">{item.row.difficulty}</span></div>
            <div className="planner-item-meta"><span>{item.row.contest} · {item.row.problem}</span><span className={'state-badge ' + (STATE_CLASS[STATES.indexOf(item.row.status)] || '')}><span />{item.row.status}</span></div>
            <p className={index < priorityCount ? 'planner-reason priority-reason' : 'planner-reason'}>{item.reason}</p>
          </div>
          <button className="button planner-select" onClick={() => onSelect?.(item.row)} disabled={!onSelect} aria-label={`选择 ${item.row.title}`}><BookOpen size={13} /><span>选择这题</span></button>
        </li>)}</ol> : <div className="planner-empty"><Target size={28} /><h3>{validRange ? '这个难度范围暂时没有待练题目' : '先设置一个有效的难度范围'}</h3><p>{validRange ? '试着扩大范围。已 AC 或巩固的题目留在复习队列中。' : '填写上下限后，推荐会自动更新。'}</p></div>}
      </div>
      <footer className="planner-footer"><div><strong>{priorityCount ? `优先处理 ${priorityCount} 道待重写 / 待补题` : '从覆盖更多知识点的题目开始'}</strong><span>{plan.length && plan.length < count ? `范围内有 ${plan.length} 道可练题，已全部列出。` : '按自己的节奏练习，随时可以调整这一组。'}</span></div><button className="button primary planner-start" disabled={!plan.length || !onStart} onClick={() => onStart?.(plan[0].row)}>开始第一题<ArrowRight size={15} /></button></footer>
    </section>
  </div>;
}
