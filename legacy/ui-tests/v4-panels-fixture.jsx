import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CompetitionPage, ConnectionsPanel, GrowthPage, UpdatePanel } from '../src/ProgressPanels.jsx';

document.documentElement.dataset.theme = 'light';
const style = document.createElement('style');
style.textContent = `:root{font-family:"Segoe UI","Microsoft YaHei UI",sans-serif;font-size:16px;--bg:#f5f6f8;--panel:#fff;--panel-2:#f7f8fa;--text:#262b38;--muted:#657087;--line:#dfe4eb;--accent:#137e6c;--accent-soft:#137e6c14;--success:#137e6c;--danger:#be394c;--warning:#a16419}:root[data-theme="dark"]{--bg:#111722;--panel:#19212e;--panel-2:#202b3b;--text:#e3eaf4;--muted:#a3b1c7;--line:#334157;--accent:#66d1bc;--accent-soft:#66d1bc16;--success:#66d1bc;--danger:#fa9baf;--warning:#e6b66f}*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--text)}button,input,select{font:inherit;color:inherit}button{cursor:pointer;border:0}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}a{color:var(--accent)}#root,.fixture{height:calc(100dvh - 32px)}.fixture{display:flex;flex-direction:column;gap:12px}.fixture-nav{display:flex;gap:10px}.fixture-content{display:flex;flex:1;min-height:0;min-width:0;overflow:auto;align-items:flex-start}.fixture-content>.progress-page,.fixture-content>.competition-page{height:100%}.fixture-content>.update-panel{width:100%}`;
document.head.append(style);

const rows = [
  { id: 'A', title: '基础枚举', platform: 'Codeforces', series: 'Div.3', contest: 'Round 2240', problem: 'A', difficulty: 1100, contestDate: '2026-10-01T10:00:00Z', updatedAt: '2026-10-08', tags: ['枚举'] },
  { id: 'B', title: '排序入门', platform: 'Codeforces', series: 'Div.3', contest: 'Round 2250', problem: 'B', difficulty: 1300, contestDate: '2026-10-06T10:00:00Z', tags: ['排序'] },
  { id: 'C', title: '中级题', platform: 'Codeforces', series: 'Div.3', contest: 'Round 2250', problem: 'C', difficulty: 1600, tags: ['前缀和'] },
  { id: 'D', title: '挑战题', platform: 'Codeforces', series: 'Div.3', contest: 'Round 2256', problem: 'D', difficulty: 1900, tags: ['动态规划'] },
  { id: 'E', title: '存量进阶题', platform: 'Codeforces', series: 'Div.3', contest: 'Round 2257', problem: 'E', difficulty: 2200, tags: ['图论'] },
];
const insights = {
  summary: { localAccepted: 0, officialSolved: 0, submissions: 0, activeDays: 0, streak: 0, completedContests: 0 },
  growth: { level: 1, levelName: '开始积累', currentLevelXp: 0, nextLevelXp: 500, totalXp: 0 },
  assessment: { rating: null, confidence: 'none', evidenceCount: 0, recommendationLevel: 1100, recommendationBasis: '冷启动：先从基础题开始', explanation: '没有独立通过证据，不推测官方评分。', platforms: [{ platform: 'codeforces', rating: null, maxRating: null }, { platform: 'atcoder', rating: null, maxRating: null }] },
  recommendations: [{ name: '枚举', reason: '难度接近入门目标，练习基础枚举。', ids: ['A'], problem: rows[0], stage: 'foundation', band: { min: 1000, max: 1250, target: 1100 } }],
  knowledge: [], achievements: [],
};
const initialHub = {
  version: '0.3.0', settings: { githubRepo: '3097729287/acm-agent-workflow', autoSync: true, intervalHours: 6, minDifficulty: 1000, maxDifficulty: 2199 },
  updates: { latestVersion: '0.1.0', sourceNotice: '项目公开仓库，当前公开包为旧图形端；React 发行待发布。' }, sync: {},
  notifications: [
    { id: 'local-update', type: 'content', title: '两道题解更新', body: '对应题目可以直接查看。', count: 2, problemIds: ['A', 'C'], solutionIds: [], problemUrls: [], createdAt: '2026-10-08T10:00:00Z', read: false },
    { id: 'remote-update', type: 'release', title: '公开仓库旧版本', body: '当前公开包仍为旧图形端。', url: 'https://github.com/3097729287/acm-agent-workflow/releases', problemIds: [], createdAt: '2026-10-08T09:00:00Z', read: false },
  ],
};
const fixture = window.panelsFixture = { calls: [], train: [], content: [], join: [], translation: {
  provider: 'deepseek', model: 'deepseek-chat', configured: true, keyStored: true, keySource: 'local', verified: false,
  providers: [{ id: 'deepseek', name: 'DeepSeek', defaultModel: 'deepseek-chat' }, { id: 'huoshan', name: '火山引擎', defaultModel: '' }], notice: '配置不等于连接已经验证。', lastError: '',
} };
function Fixture() {
  const [view, setView] = useState('growth'), [hub, setHub] = useState(initialHub);
  fixture.changeView = setView;
  const api = async (path, body) => {
    fixture.calls.push({ path, body });
    if (path === 'translation/settings') {
      if (body) {
        const changed = body.provider !== fixture.translation.provider;
        fixture.translation = { ...fixture.translation, provider: body.provider, model: body.model, keyStored: 'apiKey' in body ? Boolean(body.apiKey) : changed ? false : fixture.translation.keyStored };
        fixture.translation.configured = fixture.translation.keyStored;
      }
      return { ...fixture.translation };
    }
    if (path === 'hub/configure') return { ...hub, settings: { ...hub.settings, ...body } };
    if (path === 'hub/dismiss') return { ...hub, notifications: hub.notifications.map(item => item.id === body.id ? { ...item, read: true } : item) };
    throw new Error('Unknown fixture endpoint');
  };
  return <div className="fixture"><nav className="fixture-nav" aria-label="Fixture views"><button onClick={() => setView('growth')}>成长</button><button onClick={() => setView('competition')}>赛事</button><button onClick={() => setView('updates')}>更新</button><button onClick={() => setView('connections')}>账号与翻译</button></nav><div className="fixture-content">
    {view === 'growth' ? <GrowthPage insights={insights} hub={hub} onTrain={id => fixture.train.push(id)} /> : view === 'competition' ? <CompetitionPage rows={rows} workspace={{ training: [] }} onTrain={id => fixture.train.push(id)} onJoin={name => fixture.join.push(name)} /> : view === 'connections' ? <ConnectionsPanel hub={hub} api={api} onChanged={setHub} /> : <UpdatePanel hub={hub} api={api} onChanged={setHub} onContent={notification => fixture.content.push(notification)} />}
  </div></div>;
}
createRoot(document.getElementById('root')).render(<React.StrictMode><Fixture /></React.StrictMode>);
