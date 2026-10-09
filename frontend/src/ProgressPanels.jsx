import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Award, BookOpen, CalendarDays, Check, ChevronRight, ExternalLink, Flag, Github, LoaderCircle, RefreshCw, Search, Target, TrendingUp, Trophy, UserRound } from 'lucide-react';
import { compareContestNewest, contestTime, difficultyBand } from './practiceMetadata.js';
import './ProgressPanels.css';

const PLATFORMS = [
  ['codeforces', 'Codeforces', 'Handle'], ['atcoder', 'AtCoder', '用户名'],
  ['nowcoder', '牛客', '公开用户 ID'], ['luogu', '洛谷', '公开用户 ID'],
];
const LABELS = Object.fromEntries(PLATFORMS.map(([key, name]) => [key, name]));
const number = value => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('zh-CN') : '—';
const list = value => Array.isArray(value) ? value : [];
const confidence = value => ({ none: '证据不足', low: '证据较少', medium: '中等可信', high: '证据充分' }[value] || '证据不足');
const STAGES = { foundation: '基础起步', consolidate: '巩固练习', stretch: '逐步挑战', retry: '复习与补题' };
const PROJECT_URL = 'https://github.com/3097729287/acm-agent-workflow';
const contestDateLabel = row => {
  const time = contestTime(row);
  return time == null ? '日期待同步' : new Date(time).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
};
const dateLabel = value => {
  if (!value) return '尚未更新';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
};
const clamp = (value, max = 100) => Math.max(0, Math.min(max, Number(value) || 0));
function Loading({ text = '正在读取记录' }) { return <div className="progress-empty" role="status"><LoaderCircle size={21} className="progress-spin" /><span>{text}</span></div>; }
function Empty({ children }) { return <div className="progress-empty">{children}</div>; }
function Meter({ value, label }) { return <span className="progress-meter" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={clamp(value)}><i style={{ width: `${clamp(value)}%` }} /></span>; }

export function AchievementPanel({ achievements = [] }) {
  const [filter, setFilter] = useState('all');
  const items = list(achievements).filter(item => filter === 'all' || (filter === 'unlocked' ? item.unlocked : !item.unlocked)).slice().sort((left, right) => Number(right.unlocked) - Number(left.unlocked));
  return <div className="achievement-panel"><div className="ranking-tabs" role="group" aria-label="成就筛选">{[['all', '全部成就'], ['unlocked', '已达成'], ['pending', '待达成']].map(([value, label]) => <button className={filter === value ? 'active' : ''} aria-pressed={filter === value} key={value} onClick={() => setFilter(value)}>{label}</button>)}</div><div className="progress-achievements">{items.map(item => <div className={`progress-achievement${item.unlocked ? ' progress-unlocked' : ''}`} key={item.id}><Award size={21} /><div><strong>{item.name}</strong><p>{item.description}</p>{!item.unlocked && <Meter value={item.target ? item.progress / item.target * 100 : 0} label={`${item.name}完成进度`} />}<span>{item.unlocked ? `已达成${item.unlockedAt ? ' · ' + dateLabel(item.unlockedAt) : ''}` : `${number(item.progress)} / ${number(item.target)}`}</span></div></div>)}</div>{!items.length && <p className="progress-muted">这一组暂时没有成就记录。</p>}</div>;
}
function DailyTasks({ dailyTasks, onClaim }) {
  const [claiming, setClaiming] = useState(null), [error, setError] = useState('');
  const tasks = list(dailyTasks?.tasks);
  async function claim(task) { if (claiming || !task.completed || task.claimed) return; setClaiming(task.id); setError(''); try { await onClaim?.(task.id, dailyTasks.date); } catch (issue) { setError(issue.message); } finally { setClaiming(null); } }
  return <section className="progress-section daily-tasks" aria-label="每日任务"><div className="progress-section-heading"><h2><CalendarDays size={18} />每日任务</h2><span>{dailyTasks?.date || '每日更新'} · {tasks.filter(task => task.claimed).length}/{tasks.length}</span></div><p className="progress-small">完成任务获得经验；更高难度的挑战获得更多经验。每天按北京时间刷新。</p><div className="daily-task-grid">{tasks.map(task => <article className={`daily-task${task.claimed ? ' daily-task-claimed' : ''}`} key={task.id}><div className="daily-task-main"><div><strong>{task.title}</strong><span className="daily-task-xp">+{number(task.xp)} XP</span></div><p>{task.description}</p><div className="daily-task-progress"><Meter value={task.target ? task.progress / task.target * 100 : 0} label={`${task.title}任务进度`} /><span>{number(task.progress)}/{number(task.target)}</span></div></div><button className={'progress-button ' + (task.completed && !task.claimed ? 'progress-primary' : '')} disabled={!task.completed || task.claimed || !!claiming || !onClaim} onClick={() => claim(task)}>{claiming === task.id ? <LoaderCircle size={13} className="spin" /> : task.claimed ? <Check size={13} /> : null}{task.claimed ? '已领取' : task.completed ? '领取经验' : '进行中'}</button></article>)}</div>{!tasks.length && <p className="progress-muted">每日任务正在准备。完成训练后，任务进度会自动更新。</p>}{error && <p role="alert" className="connection-error">{error}</p>}</section>;
}

export function GrowthPage({ insights, hub, onTrain, onTopic, onSync, onAccounts, onClaimTask, onAchievements }) {
  const [gapsOnly, setGapsOnly] = useState(false);
  const [moreRecommendations, setMoreRecommendations] = useState(false);
  if (!insights) return <Loading />;
  const summary = insights.summary || {}, growth = insights.growth || {}, assessment = insights.assessment || {};
  const recommendations = list(insights.recommendations);
  const topics = list(insights.knowledge).filter(topic => !gapsOnly || topic.due > 0 || topic.failures > 0)
    .slice().sort((a, b) => (b.priority || 0) - (a.priority || 0));
  const trend = list(assessment.trend).filter(item => typeof item.value === 'number');
  const min = Math.min(...trend.map(item => item.value)), max = Math.max(...trend.map(item => item.value));
  const points = trend.map((item, index) => `${trend.length === 1 ? 150 : index / (trend.length - 1) * 300},${42 - (item.value - min) / (max - min || 1) * 32}`).join(' ');
  return <div className="progress-page" aria-label="成长与能力">
    <div className="progress-level-strip">
      <span className="progress-level-badge"><Award size={22} /><b>Lv.{growth.level ?? '—'}</b></span>
      <div className="progress-level-main"><strong>{growth.levelName || '从第一步开始'}</strong><span>{number(growth.currentLevelXp)} / {number(growth.nextLevelXp)} XP · 累计 {number(growth.totalXp ?? growth.xp)} XP</span><Meter value={growth.nextLevelXp ? growth.currentLevelXp / growth.nextLevelXp * 100 : 0} label="本级经验进度" /></div>
      {growth.nextMilestone && <span className="progress-milestone">{typeof growth.nextMilestone === 'string' ? growth.nextMilestone : growth.nextMilestone.name || growth.nextMilestone.label}</span>}
    </div>
    <div className="progress-stat-line">
      <span><b>{number(summary.localAccepted)}</b> 本地通过</span><span><b>{number(summary.officialSolved)}</b> 库内官方通过</span><span><b>{number(summary.submissions)}</b> 次提交</span><span><b>{number(summary.activeDays)}</b> 个活跃日</span><span><b>{number(summary.streak)}</b> 天连续训练</span><span><b>{number(summary.completedContests)}</b> 场模拟赛</span>
    </div>
    <div className="progress-growth-columns">
      <div className="progress-growth-left">
      <section className="progress-section progress-assessment">
        <div className="progress-section-heading"><h2><TrendingUp size={17} />能力参考</h2><span>{confidence(assessment.confidence)}</span></div>
        <div className="progress-estimate"><strong>{assessment.rating == null ? '积累独立通过记录' : number(assessment.rating)}</strong><span>{assessment.label || '训练难度估算'}</span></div>
        <p className="progress-muted">{assessment.explanation || '更多独立完成的题目，才能提供可信的能力参考。'}</p>
        {assessment.evidenceCount != null && <p className="progress-small">独立通过证据：{number(assessment.evidenceCount)} 题</p>}
        {trend.length > 1 && <div className="progress-trend"><svg viewBox="0 0 300 50" role="img" aria-label={`训练参考值变化，${number(min)} 至 ${number(max)}`}><polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" /></svg><details><summary>查看参考值明细</summary><table><thead><tr><th>日期</th><th>训练参考值</th></tr></thead><tbody>{trend.map((item, index) => <tr key={index}><td>{item.date}</td><td>{number(item.value)}</td></tr>)}</tbody></table></details></div>}
        <div className="progress-platform-scores">{list(assessment.platforms).map(item => <div key={item.platform}><span>{LABELS[item.platform] || item.platform}</span><b>{number(item.rating)}</b><span className="progress-small">最高 {number(item.maxRating)}</span></div>)}</div>
        <div className="progress-actions"><button type="button" className="progress-button" onClick={() => onAccounts?.()}><UserRound size={14} />{list(hub?.accounts).some(account => account.handle) ? '管理公开账号' : '连接公开账号'}</button>{onSync && <button type="button" className="progress-text-button" disabled={hub?.sync?.busy} onClick={() => onSync()}><RefreshCw size={13} />刷新</button>}</div>
      </section>
      {onAchievements && <button className="growth-achievement-link" onClick={onAchievements}><Trophy size={17} /><span>查看成就</span><small>{list(insights.achievements).filter(item => item.unlocked).length}/{list(insights.achievements).length}</small><ArrowRight size={14} /></button>}
      </div>
      <section className="progress-section progress-recommendations">
        <div className="progress-section-heading"><h2><Target size={17} />下一步练什么</h2><span>按实际记录推荐</span></div>
        {assessment.recommendationLevel != null && <p className="progress-small">建议练习参考：<b>{number(assessment.recommendationLevel)}</b>{assessment.recommendationBasis ? ` · ${assessment.recommendationBasis}` : ''}</p>}
        {recommendations.length ? <div id="growth-recommendations-list">{recommendations.slice(0, moreRecommendations ? recommendations.length : 4).map((item, index) => {
          const question = item.problem, identity = question?.id || item.ids?.[0];
          const completed = question?.accepted || question?.officialAccepted || question?.completed;
          return <div className="progress-recommendation" key={identity || index}><div><div className="progress-recommendation-title"><strong>{question?.title || '推荐练习'}</strong>{question && <Difficulty row={question} />}</div><span className="progress-recommendation-stage">{STAGES[item.stage] || '推荐练习'}{question?.contest ? ` · ${question.contest}` : ''}</span><p>{completed ? item.reason : `${question?.difficulty != null ? '难度 ' + question.difficulty + ' 在当前训练范围内。' : '适合当前训练阶段。'}完成后显示知识点。`}</p></div>{identity && onTrain && <button type="button" className="progress-button" onClick={() => onTrain(identity)}>练习<ArrowRight size={13} /></button>}</div>;
        })}</div> : <p className="progress-muted">先选择题目完成一次提交，建议会根据真实结果更新。</p>}
        {recommendations.length > 4 && <button type="button" className="progress-text-button recommendation-more" aria-expanded={moreRecommendations} aria-controls="growth-recommendations-list" onClick={() => setMoreRecommendations(value => !value)}>{moreRecommendations ? '收起推荐' : `查看其余 ${recommendations.length - 4} 题`}<ChevronRight size={13} /></button>}
      </section>
    </div>
      <DailyTasks dailyTasks={insights.dailyTasks} onClaim={onClaimTask} />
    <section className="progress-section">
      <div className="progress-section-heading"><h2><BookOpen size={17} />知识掌握与缺口</h2><label className="progress-check"><input type="checkbox" checked={gapsOnly} onChange={event => setGapsOnly(event.target.checked)} />只看待加强</label></div>
      <div className="progress-table-scroll"><table className="progress-knowledge-table"><thead><tr><th>知识领域</th><th>参与 / 可用</th><th>本地 / 官方通过</th><th>通过覆盖率</th><th>待办</th><th>下一步</th></tr></thead><tbody>{topics.map(topic => <tr key={topic.name}>
        <td><button type="button" className="progress-topic" onClick={() => onTopic?.(topic)}>{topic.name}<ChevronRight size={13} /></button><small>{topic.reason || topic.label}</small></td>
        <td>{number(topic.participated)} / {number(topic.available)}</td><td>{number(topic.localAccepted)} / {number(topic.officialAccepted)}</td>
        <td>{topic.mastery == null ? <span className="progress-muted">待积累</span> : <div className="progress-mastery"><Meter value={topic.mastery} label={`${topic.name}通过覆盖率`} /><span>{Math.round(topic.mastery)}%</span></div>}<small>{confidence(topic.confidence)}</small></td>
        <td>{number(topic.due)}</td><td>{topic.suggestedIds?.length > 0 && onTrain ? <button type="button" className="progress-text-button" onClick={() => onTrain(topic.suggestedIds[0])}>练习<ArrowRight size={13} /></button> : '—'}</td>
      </tr>)}</tbody></table></div>
      {!topics.length && <p className="progress-muted">这一组暂时没有需要加强的记录。</p>}
    </section>
  </div>;
}

const dayKey = date => date.toISOString().slice(0, 10);
export function ActivityPage({ insights, onTrain }) {
  const today = new Date();
  const todayKey = dayKey(new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())));
  const [year, setYear] = useState(today.getFullYear());
  const [selected, setSelected] = useState(todayKey);
  const [focused, setFocused] = useState(todayKey);
  const focusRef = useRef(todayKey), buttons = useRef(new Map());
  const activity = useMemo(() => new Map(list(insights?.activity).map(item => [item.date, item])), [insights?.activity]);
  const days = useMemo(() => {
    const result = [], begin = new Date(Date.UTC(year, 0, 1)), stop = new Date(Date.UTC(year + 1, 0, 1));
    for (let date = begin; date < stop && dayKey(date) <= todayKey; date = new Date(+date + 86400000)) result.push(dayKey(date));
    return result;
  }, [year, todayKey]);
  const years = [...new Set([today.getFullYear(), ...list(insights?.activity).map(item => Number(String(item.date).slice(0, 4))).filter(value => Number.isFinite(value) && value <= today.getFullYear())])].sort((a, b) => b - a).slice(0, 6);
  const offset = (new Date(Date.UTC(year, 0, 1)).getUTCDay() + 6) % 7;
  useEffect(() => {
    const next = days.includes(selected) ? selected : days[days.length - 1];
    setSelected(next); setFocused(next); focusRef.current = next;
  }, [year, days]);
  if (!insights) return <Loading />;
  const selectedData = activity.get(selected) || { date: selected, submissions: 0, accepted: 0, officialAccepted: 0 };
  const focusedData = activity.get(focused) || { submissions: 0, accepted: 0, officialAccepted: 0 };
  const selectedDays = days.filter(key => activity.has(key));
  const totals = days.reduce((value, key) => {
    const item = activity.get(key); if (item) { value.submissions += item.submissions || 0; value.accepted += item.accepted || 0; value.official += item.officialAccepted || 0; }
    return value;
  }, { submissions: 0, accepted: 0, official: 0 });
  const focusDay = key => { focusRef.current = key; setFocused(key); buttons.current.get(key)?.focus(); };
  const handleKey = event => {
    const index = days.indexOf(focusRef.current);
    let next;
    if (event.key === 'ArrowLeft') next = index - 7;
    else if (event.key === 'ArrowRight') next = index + 7;
    else if (event.key === 'ArrowUp') next = index - 1;
    else if (event.key === 'ArrowDown') next = index + 1;
    else if (event.key === 'Home') next = event.ctrlKey ? 0 : index - ((index + offset) % 7);
    else if (event.key === 'End') next = event.ctrlKey ? days.length - 1 : index + 6 - ((index + offset) % 7);
    if (next != null) { event.preventDefault(); event.stopPropagation(); focusDay(days[clamp(next, days.length - 1)]); }
  };
  return <div className="activity-page" aria-label="训练活动">
    <section className="progress-section"><div className="progress-section-heading"><h2><CalendarDays size={17} />训练日历</h2><label className="activity-year">年份<select aria-label="活动年份" value={year} onChange={event => setYear(Number(event.target.value))}>{years.map(value => <option key={value}>{value}</option>)}</select></label></div>
      <div className="progress-stat-line activity-stats"><span><b>{number(totals.submissions)}</b> 次提交</span><span><b>{number(totals.accepted)}</b> 次首次本地通过</span><span><b>{number(totals.official)}</b> 次官方通过</span><span><b>{number(insights.summary?.longestStreak)}</b> 天最长连续</span></div>
      <div className="activity-calendar-scroll"><div className="activity-calendar" role="grid" aria-label={`${year}年训练热力图，方向键移动，Enter查看日期`} onKeyDown={handleKey}>
        {Array.from({ length: offset }, (_, index) => <span className="activity-day activity-padding" role="presentation" key={'pad' + index} />)}
        {days.map(key => {
          const item = activity.get(key), amount = (item?.submissions || 0) + (item?.officialAccepted || 0);
          const level = amount === 0 ? 0 : amount < 3 ? 1 : amount < 6 ? 2 : amount < 10 ? 3 : 4;
          const description = `${key}，${item?.submissions || 0} 次提交，${item?.accepted || 0} 次本地通过，${item?.officialAccepted || 0} 次官方通过`;
          return <button type="button" role="gridcell" className={`activity-day activity-level-${level}${selected === key ? ' activity-selected' : ''}`} key={key} ref={node => { if (node) buttons.current.set(key, node); else buttons.current.delete(key); }}
            tabIndex={focused === key ? 0 : -1} aria-label={description} aria-selected={selected === key} title={description} onFocus={() => { focusRef.current = key; setFocused(key); }} onClick={() => { focusRef.current = key; setFocused(key); setSelected(key); }} />;
        })}
      </div></div>
      <div className="activity-calendar-caption"><span role="status">{focused} · {focusedData.submissions || 0} 次提交 · {focusedData.accepted || 0} 次本地通过 · {focusedData.officialAccepted || 0} 次官方通过</span><span className="activity-legend">少{[0, 1, 2, 3, 4].map(level => <i key={level} className={`activity-level-${level}`} />)}多</span></div>
      <p className="progress-small">方向键移动，Enter 查看当天；每格数据也可在下方日期明细中读取。</p>
    </section>
    <section className="progress-section activity-day-detail"><div className="progress-section-heading"><h2>{selected || '日期详情'}</h2><span>{selectedData.submissions || selectedData.accepted || selectedData.officialAccepted ? '已经留下训练记录' : '这一天没有提交记录'}</span></div><div className="progress-stat-line"><span><b>{number(selectedData.submissions)}</b> 次提交</span><span><b>{number(selectedData.accepted)}</b> 次本地通过</span><span><b>{number(selectedData.officialAccepted)}</b> 次官方通过</span></div></section>
    <section className="progress-section"><details className="activity-details" open><summary>查看日期明细（{selectedDays.length} 天）</summary>{selectedDays.length ? <div className="progress-table-scroll"><table><thead><tr><th>日期</th><th>提交</th><th>本地通过</th><th>官方通过</th></tr></thead><tbody>{selectedDays.slice().reverse().map(key => { const item = activity.get(key); return <tr key={key}><td><button type="button" className="progress-text-button" onClick={() => { setSelected(key); focusDay(key); }}>{key}</button></td><td>{number(item.submissions)}</td><td>{number(item.accepted)}</td><td>{number(item.officialAccepted)}</td></tr>; })}</tbody></table></div> : <p className="progress-muted">这一年还没有记录。完成正式提交后会自动记录。</p>}</details>
      {insights.recommendations?.[0]?.ids?.[0] && onTrain && <button type="button" className="progress-button" onClick={() => onTrain(insights.recommendations[0].ids[0])}>继续练习<ArrowRight size={13} /></button>}
    </section>
  </div>;
}

function contestGroups(rows) {
  const map = new Map();
  for (const row of list(rows)) {
    const key = `${row.platform || ''}::${row.contest}`;
    if (!map.has(key)) map.set(key, { key, name: row.contest, platform: row.platform, series: row.series, rows: [] });
    map.get(key).rows.push(row);
  }
  return [...map.values()].map(group => ({ ...group, rows: group.rows.sort((a, b) => String(a.problem).localeCompare(String(b.problem), 'en', { numeric: true })) })).sort(compareContestNewest);
}
function Difficulty({ row, locked = false }) { return <span className={`competition-difficulty competition-difficulty-${locked ? 'unknown' : difficultyBand(row.difficulty)}${locked ? ' competition-hidden-difficulty' : ''}`} title={locked ? '比赛进行中，赛后显示难度' : row.difficultySource || '统一训练难度'}>{locked ? '赛中隐藏' : row.difficulty == null ? '未定级' : row.difficulty}</span>; }
export function CompetitionPage({ rows, workspace, hub, onTrain, onJoin, initialContest, onBack }) {
  const groups = useMemo(() => contestGroups(rows), [rows]);
  const [query, setQuery] = useState(''), [platform, setPlatform] = useState(''), [filter, setFilter] = useState('all');
  const [selected, setSelected] = useState(null), [joining, setJoining] = useState(false), [joinError, setJoinError] = useState('');
  const progress = useMemo(() => new Map(list(workspace?.training).map(row => [row.id, row])), [workspace?.training]);
  const lockedIds = new Set(workspace?.activeContest?.status === 'running' ? list(workspace.activeContest.slots).map(row => row.id) : []);
  useEffect(() => {
    if (!initialContest) return;
    const name = typeof initialContest === 'string' ? initialContest : initialContest.name || initialContest.contest || initialContest.id;
    const group = groups.find(item => item.key === name || item.name === name);
    if (group) setSelected(group.key);
  }, [initialContest, groups]);
  if (!rows) return <Loading text="正在读取比赛列表" />;
  const current = groups.find(group => group.key === selected);
  const activeCount = group => group.rows.filter(row => progress.has(row.id)).length;
  const acceptedCount = group => group.rows.filter(row => progress.get(row.id)?.accepted).length;
  const filtered = groups.filter(group => (!platform || group.platform === platform)
    && (!query.trim() || `${group.name} ${group.platform} ${group.rows.map(row => `${row.title} ${row.problem} ${lockedIds.has(row.id) ? '' : list(row.tags).join(' ')}`).join(' ')}`.toLowerCase().includes(query.trim().toLowerCase()))
    && (filter === 'all' || filter === 'joined' ? filter === 'all' || activeCount(group) > 0 : filter === 'available' ? activeCount(group) === 0 : acceptedCount(group) < group.rows.length));
  const join = async group => { if (!onJoin || joining) return; setJoining(true); setJoinError(''); try { await onJoin(group.name); } catch (issue) { setJoinError(issue.message || '暂时无法加入训练，请重试。'); } finally { setJoining(false); } };
  if (current) {
    const inMock = current.rows.some(row => lockedIds.has(row.id));
    return <div className="competition-page competition-detail" aria-label={`${current.name}比赛详情`}>
      <div className="competition-detail-heading"><button type="button" className="progress-button" onClick={() => { setSelected(null); if (initialContest) onBack?.(); }}><ArrowLeft size={14} />全部比赛</button><div><h2>{current.name}</h2><span>{current.platform} · {contestDateLabel(current)} · {current.rows.length} 题 · 已通过 {acceptedCount(current)} 题</span></div>{onJoin && <button type="button" className="progress-button progress-primary" disabled={joining || inMock || activeCount(current) === current.rows.length} onClick={() => join(current)}>{joining ? <LoaderCircle size={14} className="progress-spin" /> : <Flag size={14} />}{activeCount(current) === current.rows.length ? '已加入训练' : activeCount(current) ? '加入剩余题目' : '加入我的训练'}</button>}</div>
      {inMock && <div className="competition-notice">本场部分题目正在模拟赛中，难度和知识点将在赛后显示。请从模拟赛页继续。</div>}
      {joinError && <p className="connection-error" role="alert">{joinError}</p>}
      <div className="competition-question-list">{current.rows.map(row => {
        const state = progress.get(row.id), locked = lockedIds.has(row.id);
        return <div className="competition-question" key={row.id}><span className="competition-letter">{row.problem}</span><div className="competition-question-main"><strong>{row.title}</strong><div className="competition-question-meta">{locked ? <span>模拟赛进行中</span> : list(row.tags).map(tag => <span className="competition-tag" key={tag}>{tag}</span>)}<span>{row.solutionAvailable === false ? '题解未生成' : row.solutionAvailable === true ? '有题解' : '题解状态未知'}</span></div></div><Difficulty row={row} locked={locked} /><span className={`competition-result${state?.accepted ? ' competition-accepted' : ''}`}>{locked ? '考场中' : state?.accepted ? '本地通过' : state?.verdict === 'SAMPLE_PASS' ? '样例通过' : state ? '已加入' : '未加入'}</span><button type="button" className="progress-button" disabled={!onTrain || locked} onClick={() => onTrain?.(row.id)}>练习<ArrowRight size={13} /></button></div>;
      })}</div>
    </div>;
  }
  return <div className="competition-page" aria-label="比赛列表">
    <div className="competition-toolbar"><label className="competition-search"><Search size={16} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索比赛、题名或知识点" aria-label="搜索比赛" /></label><select value={platform} onChange={event => setPlatform(event.target.value)} aria-label="比赛平台"><option value="">全部平台</option>{[...new Set(groups.map(group => group.platform).filter(Boolean))].map(item => <option key={item}>{item}</option>)}</select><select value={filter} onChange={event => setFilter(event.target.value)} aria-label="比赛训练情况"><option value="all">全部比赛</option><option value="joined">已加入训练</option><option value="available">尚未加入</option><option value="unfinished">尚未全部通过</option></select><span className="competition-count">{filtered.length} 场</span></div>
    {hub?.sync?.message && <p className="competition-sync-note">{hub.sync.message}</p>}
    <div className="competition-list">{filtered.map(group => <button type="button" className="competition-card" key={group.key} onClick={() => setSelected(group.key)} aria-label={`查看 ${group.platform} ${group.name}，${group.rows.length} 道题`}><span className="competition-platform">{group.platform}</span><span className="competition-card-title"><strong>{group.name}</strong><small>{contestDateLabel(group)} · {group.rows.length} 题 · {activeCount(group) ? `已加入 ${activeCount(group)}，通过 ${acceptedCount(group)}` : '尚未加入训练'}</small></span><span className="competition-problem-tokens">{group.rows.map(row => <span className={`competition-problem-token${progress.get(row.id)?.accepted ? ' competition-token-accepted' : ''}`} key={row.id}><b>{row.problem}</b><Difficulty row={row} locked={lockedIds.has(row.id)} /></span>)}</span><ChevronRight size={16} /></button>)}</div>
    {!filtered.length && <Empty><Flag size={24} /><span>{groups.length ? '没有匹配的比赛，试试减少筛选条件。' : '题库还没有收录比赛。'}</span></Empty>}
  </div>;
}

function accountDraft(hub) { return Object.fromEntries(PLATFORMS.map(([key]) => [key, hub?.settings?.accounts?.[key] || ''])); }
export function TranslationSettings({ api, onError }) {
  const apiRef = useRef(api), saving = useRef(false);
  apiRef.current = api;
  const [settings, setSettings] = useState(null), [draft, setDraft] = useState({ provider: 'deepseek', model: '', baseUrl: '' });
  const [apiKey, setApiKey] = useState(''), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [error, setError] = useState(''), [message, setMessage] = useState(''), [loadAttempt, setLoadAttempt] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true); setError('');
    if (!apiRef.current) { setLoading(false); return; }
    apiRef.current('translation/settings').then(answer => {
      if (!alive) return;
      setSettings(answer); setDraft({ provider: answer.provider, model: answer.model || '', baseUrl: answer.baseUrl || '' });
    }).catch(issue => { if (alive) setError(issue.message || '暂时无法读取翻译配置。'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [loadAttempt]);
  const save = async clearKey => {
    if (!apiRef.current || !settings || saving.current) return;
    saving.current = true; setBusy(true); setError(''); setMessage('');
    const body = { provider: draft.provider, model: draft.model.trim(), ...(draft.provider === 'custom' ? { baseUrl: draft.baseUrl.trim() } : {}), ...(clearKey ? { apiKey: '' } : apiKey.trim() ? { apiKey: apiKey.trim() } : {}) };
    try {
      const answer = await apiRef.current('translation/settings', body);
      setSettings(answer); setDraft({ provider: answer.provider, model: answer.model || '', baseUrl: answer.baseUrl || '' }); setApiKey('');
      setMessage(clearKey ? '已清除本机保存的密钥；已有环境配置仍可能继续生效。' : '翻译配置已保存，首次翻译时验证连接。');
    } catch (issue) { setError(issue.message || '未能保存翻译配置。'); onError?.(issue.message || '未能保存翻译配置'); }
    finally { saving.current = false; setBusy(false); }
  };
  const providers = list(settings?.providers).some(item => item.id === 'custom') ? list(settings.providers) : [...list(settings?.providers), { id: 'custom', name: '自定义 API', defaultModel: '' }], disabled = loading || busy || !settings;
    async function testConnection() {
    if (busy) return;setBusy(true);setError('');setMessage('');
    try { const result=await api('translation/test',{});setSettings(result);setMessage(result.message || '连接成功'); }
    catch(issue) { setError(issue.message);onError?.(issue.message); }
    finally { setBusy(false); }
  }
  return <div className="translation-settings" aria-label="题面翻译配置"><div className="progress-section-heading"><h3>题面翻译</h3><span>{loading ? '读取配置…' : settings?.verified ? '连接已验证' : settings?.configured ? '已配置 · 尚待实际翻译验证' : '尚未配置'}</span></div>
    <p className="progress-small">只翻译公开题面。在练习页点击“中文”，失败时保留原文。</p>
    <form onSubmit={event => { event.preventDefault(); save(false); }}><div className="translation-fields">
      <label><span>服务</span><select aria-label="翻译服务" value={draft.provider} disabled={disabled} onChange={event => { const provider = providers.find(item => item.id === event.target.value); setDraft({ provider: event.target.value, model: provider?.defaultModel || '', baseUrl: '' }); setApiKey(''); setMessage(''); }}>{providers.length ? providers.map(item => <option key={item.id} value={item.id}>{item.name}</option>) : <option value="deepseek">DeepSeek</option>}</select></label>
      <label><span>模型 / 接入点 ID</span><input aria-label="翻译模型" value={draft.model} disabled={disabled} required={['huoshan', 'custom'].includes(draft.provider)} maxLength={128} autoComplete="off" spellCheck={false} onChange={event => setDraft(previous => ({ ...previous, model: event.target.value }))} /></label>
      {draft.provider === 'custom' && <label className="translation-base-field"><span>Base URL</span><input type="url" aria-label="翻译 API Base URL" value={draft.baseUrl} disabled={disabled} required placeholder="https://api.example.com/v1" autoComplete="off" spellCheck={false} onChange={event => setDraft(previous => ({ ...previous, baseUrl: event.target.value }))} /></label>}
      <label className="translation-key-field"><span>API Key（可选）</span><input type="password" aria-label="翻译服务 API Key" value={apiKey} disabled={disabled} autoComplete="off" spellCheck={false} placeholder="留空保留当前密钥" onChange={event => setApiKey(event.target.value)} /></label>
    </div><p className="progress-small">{draft.provider === 'custom' ? '支持兼容 OpenAI 的接口。填写 Base URL、模型与 API Key；本地网关可不填密钥。' : '密钥不回显；更换服务时使用对应服务的密钥。'}</p><div className="progress-actions"><button type="submit" className="progress-button" disabled={disabled}>{busy ? <LoaderCircle size={14} className="progress-spin" /> : <Check size={14} />}保存翻译配置</button><button type="button" className="progress-button" disabled={disabled || !settings?.configured} onClick={testConnection}><RefreshCw size={14} />测试连接</button>{settings?.keyStored && draft.provider === settings.provider && <button type="button" className="progress-text-button" disabled={disabled} onClick={() => save(true)}>清除本机密钥</button>}{!settings && !loading && <button type="button" className="progress-text-button" onClick={() => setLoadAttempt(value => value + 1)}>重新读取</button>}</div></form>
    {settings?.notice && <p className="progress-small">{settings.notice}</p>}
    {settings?.lastError && !error && <p className="connection-error">上次翻译：{settings.lastError}</p>}
    {error && <p className="connection-error" role="alert">{error}</p>}{message && <p className="connection-message" role="status">{message}</p>}
  </div>;
}
export function ConnectionsPanel({ hub, api, onChanged, onError, includeTranslation = true }) {
  const [draft, setDraft] = useState(() => accountDraft(hub)), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState('');
  const dirty = useRef(false), editRevision = useRef(0);
  useEffect(() => { if (!dirty.current) setDraft(accountDraft(hub)); }, [hub?.settings?.accounts]);
  const request = async (path, body) => {
    if (!api || busy) return;
    const revision = editRevision.current;
    setBusy(true); setError(''); setMessage('');
    try { const result = await api(path, body); onChanged?.(result); if (path === 'hub/configure') { if (editRevision.current === revision) { dirty.current = false; setDraft(accountDraft(result)); } setMessage('账号设置已保存，正在后台读取公开记录。'); } else setMessage(result.sync?.message || '已开始刷新公开记录。'); }
    catch (issue) { setError(issue.message || '未能更新账号，请重试。'); onError?.(issue.message || '未能更新账号'); }
    finally { setBusy(false); }
  };
  return <section className="connection-panel" aria-label="公开账号连接"><div className="progress-section-heading"><h2><UserRound size={17} />公开账号</h2><span>可选</span></div><p className="progress-muted">读取公开评分与通过记录，补充成长参考；不会把历史题目自动加入训练。</p>
    <form onSubmit={event => { event.preventDefault(); request('hub/configure', { accounts: Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, value.trim()])) }); }}>
      <div className="connection-fields">{PLATFORMS.map(([key, name, placeholder]) => <label key={key}><span>{name}</span><input value={draft[key]} onChange={event => { dirty.current = true; editRevision.current += 1; setDraft(value => ({ ...value, [key]: event.target.value })); }} placeholder={placeholder} aria-label={`${name}公开账号`} autoComplete="off" spellCheck={false} /></label>)}</div>
      <div className="progress-actions"><button type="submit" className="progress-button progress-primary" disabled={busy || !api}>{busy ? <LoaderCircle size={14} className="progress-spin" /> : <Check size={14} />}保存账号</button><button type="button" className="progress-button" disabled={busy || hub?.sync?.busy || !api} onClick={() => request('hub/sync', {})}><RefreshCw size={14} />刷新公开记录</button><span className="progress-small">清空后保存，可解除关联。</span></div>
    </form>
    {error && <p className="connection-error" role="alert">{error}</p>}{message && <p className="connection-message" role="status">{message}</p>}
    <div className="connection-account-list">{list(hub?.accounts).filter(account => account.handle).map(account => <div className="connection-account" key={account.platform}><div className="connection-account-heading"><strong>{LABELS[account.platform] || account.platform}</strong>{account.url ? <a href={account.url} target="_blank" rel="noreferrer">{account.displayName || account.handle}<ExternalLink size={12} /></a> : <span>{account.displayName || account.handle}</span>}<span className={`connection-status connection-status-${account.status}`}>{({ ready: '已更新', partial: '公开信息有限', error: '暂未读取' })[account.status] || '尚未配置'}</span></div><div className="connection-evidence"><span>评分 <b>{number(account.rating)}</b></span><span>最高 <b>{number(account.maxRating)}</b></span><span>通过 <b>{number(account.solvedCount)}</b></span><span>提交 <b>{number(account.submissionCount)}</b></span><span>{dateLabel(account.updatedAt)}</span></div>{account.error && <p>{account.error}</p>}</div>)}</div>
    {includeTranslation && <TranslationSettings api={api} onError={onError} />}
  </section>;
}

function updateDraft(hub) { return { autoSync: hub?.settings?.autoSync ?? true, intervalHours: hub?.settings?.intervalHours ?? 6, minDifficulty: hub?.settings?.minDifficulty ?? 1000, maxDifficulty: hub?.settings?.maxDifficulty ?? 2199 }; }
export function UpdatePanel({ hub, api, onChanged, onError, onContent, showNotifications = true }) {
  const [draft, setDraft] = useState(() => updateDraft(hub)), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState(''), [unreadOnly, setUnreadOnly] = useState(false);
  const dirty = useRef(false), editRevision = useRef(0);
  useEffect(() => { if (!dirty.current) setDraft(updateDraft(hub)); }, [hub?.settings]);
  const change = (key, value) => { dirty.current = true; editRevision.current += 1; setDraft(previous => ({ ...previous, [key]: value })); };
  const request = async (path, body) => {
    if (!api || busy) return;
    const revision = editRevision.current;
    setBusy(true); setError(''); setMessage('');
    try { const result = await api(path, body); onChanged?.(result); if (path === 'hub/configure') { if (editRevision.current === revision) { dirty.current = false; setDraft(updateDraft(result)); } setMessage('更新偏好已保存。'); } else if (path === 'hub/sync') setMessage(result.sync?.message || '已安排后台检查。'); }
    catch (issue) { setError(issue.message || '未能完成操作，请重试。'); onError?.(issue.message || '未能完成操作'); }
    finally { setBusy(false); }
  };
  const updates = hub?.updates || {}, sync = hub?.sync || {};
  const notifications = list(hub?.notifications).filter(item => !unreadOnly || !item.read);
  return <section className="update-panel" aria-label="题库与版本更新"><div className="progress-section-heading"><h2><Github size={17} />题库与版本更新</h2><span>当前 {hub?.version || updates.currentVersion || __TB_VERSION__}</span></div>
    <div className="update-project-source"><span>项目公开仓库</span><a href={PROJECT_URL} target="_blank" rel="noreferrer">acm-agent-workflow<ExternalLink size={12} /></a></div>
    {updates.sourceNotice && <p className="progress-small">{updates.sourceNotice}</p>}
    <form onSubmit={event => { event.preventDefault(); request('hub/configure', { ...draft, intervalHours: Number(draft.intervalHours), minDifficulty: Number(draft.minDifficulty), maxDifficulty: Number(draft.maxDifficulty) }); }}>
      <div className="update-options"><label className="progress-check"><input type="checkbox" checked={draft.autoSync} onChange={event => change('autoSync', event.target.checked)} />自动检查已结束的比赛</label><label>检查间隔<select value={draft.intervalHours} onChange={event => change('intervalHours', event.target.value)} aria-label="自动检查间隔">{[1, 3, 6, 12, 24].map(hours => <option key={hours} value={hours}>{hours} 小时</option>)}</select></label></div>
      <div className="update-difficulty-range"><span>新题难度范围</span><label><span className="update-sr-only">最低难度</span><input type="number" min="1000" max="2199" step="1" value={draft.minDifficulty} onChange={event => change('minDifficulty', event.target.value)} aria-label="自动收录最低难度" required /></label><span>至</span><label><span className="update-sr-only">最高难度</span><input type="number" min={Math.max(1000, Number(draft.minDifficulty) || 1000)} max="2199" step="1" value={draft.maxDifficulty} onChange={event => change('maxDifficulty', event.target.value)} aria-label="自动收录最高难度" required /></label></div>
      <div className="progress-actions"><button type="submit" className="progress-button progress-primary" disabled={busy || !api}><Check size={14} />保存更新偏好</button><button type="button" className="progress-button" disabled={busy || sync.busy || !api} onClick={() => request('hub/sync', {})}>{sync.busy ? <LoaderCircle size={14} className="progress-spin" /> : <RefreshCw size={14} />}现在检查</button></div>
    </form>
    {error && <p className="connection-error" role="alert">{error}</p>}{message && <p className="connection-message" role="status">{message}</p>}
    <div className="update-status"><span>上次检查：{dateLabel(sync.lastCheckedAt || updates.checkedAt)}</span><span>下次检查：{dateLabel(sync.nextCheckAt)}</span>{updates.latestVersion && <span>公开版本：{updates.url ? <a href={updates.url} target="_blank" rel="noreferrer">{updates.latestVersion}<ExternalLink size={12} /></a> : updates.latestVersion}</span>}</div>
    {sync.message && <p className="progress-small">{sync.message}</p>}{updates.error && <p className="connection-error">{updates.error}</p>}
    {list(sync.providers).length > 0 && <div className="update-providers">{list(sync.providers).map(item => <div key={item.platform}><strong>{LABELS[item.platform] || item.platform}</strong><span>{item.message || item.status}</span><small>新增 {number(item.added)} · 待定级 {number(item.pending)}</small></div>)}</div>}
    {updates.notes && <details className="update-release-notes"><summary>版本说明</summary><p>{updates.notes}</p></details>}
    {showNotifications && <><div className="progress-section-heading update-notification-heading"><h3>更新通知</h3><label className="progress-check"><input type="checkbox" checked={unreadOnly} onChange={event => setUnreadOnly(event.target.checked)} />只看未读</label></div>
    <div className="update-notifications">{notifications.length ? notifications.map(item => {
      const targets = [...list(item.problemIds), ...list(item.solutionIds), ...list(item.problemUrls)];
      const clickable = targets.length > 0 && Boolean(onContent), Main = clickable ? 'button' : 'div';
      return <div className={`update-notification${item.read ? ' update-read' : ''}`} key={item.id}><span className="update-notification-kind">{({ release: '版本', content: '内容', catalog: '题库' })[item.type] || '更新'}</span><div><Main className="update-notification-main" type={clickable ? 'button' : undefined} onClick={clickable ? () => onContent(item) : undefined}><strong>{item.title}</strong><span className="update-notification-body">{item.body}</span><small>{dateLabel(item.createdAt)}{item.count != null ? ` · ${number(item.count)} 项` : ''}</small></Main><div className="update-notification-actions">{clickable && <button type="button" className="progress-text-button" onClick={() => onContent(item)}>查看新增内容<ArrowRight size={12} /></button>}{item.url && <a href={item.url} target="_blank" rel="noreferrer">{targets.length ? '查看来源' : '在仓库查看'}<ExternalLink size={12} /></a>}{!item.read && <button type="button" className="progress-text-button" disabled={busy || !api} onClick={() => request('hub/dismiss', { id: item.id })}><Check size={12} />标为已读</button>}</div></div></div>;
    }) : <p className="progress-muted">{unreadOnly ? '没有未读通知。' : '新题入库或版本发布后，通知会显示在这里。'}</p>}</div></>}
  </section>;
}
