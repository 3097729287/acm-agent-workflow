import { useCallback, useEffect, useState } from 'react';
import { Bell, Play, Target } from 'lucide-react';
import '@/pages/GoalsPanel.css';

function useGoals(api) {
  const [data,setData]=useState({goals:[]}),[error,setError]=useState('');
  const reload=useCallback(()=>api('goals').then(value=>{setData(value);setError('');}).catch(issue=>setError(issue.message)),[api]);
  useEffect(()=>{reload();const timer=setInterval(reload,60000);const visible=()=>{if(!document.hidden)reload();};document.addEventListener('visibilitychange',visible);return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',visible);};},[reload]);
  return {data,setData,error,setError,reload};
}

export function GoalReminder({api,onOpen}) {
  const {data}=useGoals(api);
  const incomplete=data.goals.filter(goal=>!goal.workloadCompleted&&(!goal.dailyTask.completed||goal.warnings.length));
  return incomplete.length>0&&<button className="goal-reminder" aria-label="目标任务提醒" onClick={onOpen}><Bell size={15}/><span>{incomplete.length} 个目标待推进</span></button>;
}

const blank=()=>({title:'CF 2200',kind:'cf',deadline:'',currentRating:1000,targetRating:2200,dailyMinutes:90,totalProblems:100});
export default function GoalsPanel({api,onTrain,dailyOnly=false}) {
  const {data,setData,error,setError,reload}=useGoals(api);
  const [form,setForm]=useState(blank),[busy,setBusy]=useState(false),[confirm,setConfirm]=useState(null);
  const change=patch=>setForm(value=>({...value,...patch}));
  async function save(event){event.preventDefault();setBusy(true);try{setData(await api('goals/save',form));setForm(blank());setError('');}catch(issue){setError(issue.message);}finally{setBusy(false);}}
  async function archive(){setBusy(true);try{setData(await api('goals/archive',{id:confirm.id}));setConfirm(null);}catch(issue){setError(issue.message);}finally{setBusy(false);}}
  return <div className={'goals-page'+(dailyOnly?' goals-daily':'')} aria-label={dailyOnly?'目标每日任务':'目标计划'}>
    <div className="progress-section-heading"><h2><Target size={18}/>{dailyOnly?'目标每日任务':'目标与截止日期'}</h2><button className="text-button" onClick={reload}>刷新进度</button></div>
    {!dailyOnly&&<form className="goal-form" onSubmit={save}>
      <label>目标类型<select aria-label="目标类型" value={form.kind} onChange={event=>{const kind=event.target.value;change({kind,title:{cf:'CF 2200',xcpc:'区域赛银牌',lanqiao:'蓝桥杯国一',custom:''}[kind],targetRating:{cf:2200,xcpc:2000,lanqiao:1800,custom:1800}[kind]});}}><option value="cf">Codeforces 评级</option><option value="xcpc">XCPC 区域赛</option><option value="lanqiao">蓝桥杯</option><option value="custom">自定义目标</option></select></label>
      <label>具体目标<input aria-label="具体目标" value={form.title} onChange={event=>change({title:event.target.value})} maxLength={160} required/></label>
      <label>截止日期<input aria-label="目标截止日期" type="date" value={form.deadline} onChange={event=>change({deadline:event.target.value})} required/></label>
      <label>当前能力参考值<input aria-label="当前能力参考值" type="number" min={0} max={4000} value={form.currentRating} onChange={event=>change({currentRating:event.target.value})} required/></label>
      {form.kind==='custom'?<label>计划新题总数<input aria-label="目标新题总数" type="number" min={1} max={10000} value={form.totalProblems} onChange={event=>change({totalProblems:event.target.value})} required/></label>:<label>{form.kind==='cf'?'目标 CF 评级':'训练能力参考值'}<input aria-label="目标能力参考值" type="number" min={200} max={4000} value={form.targetRating} onChange={event=>change({targetRating:event.target.value})} required/></label>}
      <label>每日可用时间（分钟）<input aria-label="每日可用分钟" type="number" min={15} max={720} value={form.dailyMinutes} onChange={event=>change({dailyMinutes:event.target.value})} required/></label>
      <p className="progress-small">起点和奖项目标的能力参考值由你填写，可按近期独立做题调整；银牌、国一参考值仅用于安排题量。预留 30% 时间参赛和复盘。</p>
      <div className="progress-actions"><button className="primary" type="submit" disabled={busy}>{form.id?'保存目标调整':'生成目标计划'}</button>{form.id&&<button className="secondary" type="button" onClick={()=>setForm(blank())}>取消编辑</button>}</div>
    </form>}
    {error&&<p className="inline-error" role="alert">{error}</p>}
    {confirm&&<div className="goal-archive-confirm" role="alertdialog" aria-label="归档目标确认"><p>归档“{confirm.title}”后停止每日提醒，保留计划和训练记录。</p><button className="secondary" disabled={busy} onClick={()=>setConfirm(null)}>取消</button><button className="primary" disabled={busy} onClick={archive}>确认归档</button></div>}
    {!data.goals.length&&<p className="progress-muted">还没有目标。在成长与能力的“目标计划”中填写目标和截止日期。</p>}
    {data.goals.map(goal=><section className="goal-card" key={goal.id}>
      <div className="progress-section-heading"><h3>{goal.title}</h3><span>截止 {goal.deadline}</span></div>
      <p>新题进度 <b>{goal.progress}/{goal.totalProblems}</b> · 剩余 {goal.remainingDays} 天 · 本周安排 <b>{goal.weeklyTarget}</b> 题{goal.workloadCompleted&&' · 训练题量已完成，目标结果需另行核验'}</p>
      {goal.warnings.map(warning=><p key={warning} className="goal-pressure" role="alert">{warning}</p>)}
      <div className="goal-daily-task"><strong>{goal.dailyTask.date} · 今日目标任务</strong><span>{goal.dailyTask.progress}/{goal.dailyTask.target} 道新题通过 · {goal.dailyTask.completed?'今日已完成':'尚未完成，请安排训练时间'}</span></div>
      <div className="goal-problems">{!goal.dailyTask.completed&&goal.dailyTask.problems.map(problem=><button className="secondary" key={problem.id} onClick={()=>onTrain(problem.id)}><Play size={13}/>{problem.title}<small>{problem.difficulty??'未评级'}</small></button>)}</div>
      {!dailyOnly&&<><p className="progress-small">{goal.assumption}每题按 {goal.minutesPerProblem} 分钟估算；剩余时间预计容纳 {goal.capacity} 题。只计目标创建后首次通过的新题，本地审核 AC 与可靠官方 AC 均可计入；样例通过不计入。目标任务不额外发放经验。</p><details><summary>每周计划</summary><div className="goal-week-plan">{goal.weeklyPlan.map(week=><div key={week.start}><span>{week.start} — {week.end}</span><b>{week.target} 题</b></div>)}</div></details><p className="progress-small">{goal.disclaimer}</p><div className="progress-actions"><button className="text-button" onClick={()=>{setForm(goal);setConfirm(null);}}>调整目标</button><button className="text-button" onClick={()=>setConfirm(goal)}>归档目标</button></div></>}
    </section>)}
  </div>;
}
