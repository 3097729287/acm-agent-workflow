import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { createServer } from 'vite';
import { mkdir } from 'node:fs/promises';

// Every API request is isolated from the user's database and external accounts.
const vite = await createServer({ server: { host: '127.0.0.1', port: 18775, strictPort: true } });
await vite.listen();
const browser = await chromium.launch({ channel: process.env.CI ? undefined : 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 2048, height: 1152 } });
page.setDefaultTimeout(10000);
await page.addInitScript(() => localStorage.setItem('tb.preferences', JSON.stringify({ theme: 'light', fontSize: 18, accent: 'teal', pageBookmarks: [{ id: 'legacy', page: 'lectures', name: '旧书签' }] })));
const errors = [], writes = [], now = () => new Date().toISOString(), date = now().slice(0, 10);
page.on('pageerror', issue => errors.push(issue.message));
const rows = ['A', 'B', 'C', 'D', 'E', 'F'].map((letter, index) => ({ id: '测试比赛::' + letter, contest: '测试比赛', problem: letter, title: ['区间统计练习', '位运算练习', '背包练习', '枚举练习', '数论练习', '字符串练习'][index], tags: [['前缀和'], ['位运算'], ['背包 DP'], ['枚举'], ['素数'], ['KMP']][index], knowledge: '知识点', platform: index % 2 ? 'AtCoder' : '牛客', series: '周赛', difficulty: 1000 + index * 200, contestDate: '2026-10-01T12:00:00Z', url: 'https://example.com/problem/' + letter, solutionAvailable: true }));
const categories = [{ name: '基础技巧', tags: ['前缀和', '枚举', '位运算'], children: [{ name: '前缀和', tags: ['前缀和'], children: [] }, { name: '位运算', tags: ['位运算'], children: [] }] }, { name: '动态规划', tags: ['背包 DP'], children: [{ name: '背包 DP', tags: ['背包 DP'], children: [] }] }];
const completed = { id: 'mock-old', name: '完成的模拟赛', duration: 60, startedAt: now(), deadline: now(), status: 'finished', accepted: 1, total: 3, slots: rows.slice(0, 3).map((row, index) => ({ ...row, letter: 'ABC'[index], accepted: index === 0, verdict: index === 0 ? 'AC' : 'WA', attempts: 1 })) };
let activeContest = null;
const training = rows.slice(0, 4).map((row, index) => ({ id: row.id, accepted: index === 0, verdict: index === 0 ? 'AC' : null, attempts: 1 }));
const contests = [completed];
const workspace = () => ({ training, sets: [], contests, activeContest, summary: { total: training.length, accepted: 1, attempts: 3, due: 0, pending: 0, streak: 1 }, now: now() });
const insights = { summary: { localAccepted: 1, officialSolved: 4, submissions: 3, activeDays: 1, streak: 1, completedContests: 1 }, growth: { level: 1, currentLevelXp: 10, nextLevelXp: 500, totalXp: 10, levelName: '初次启程' }, knowledge: [], recommendations: [{ name: '前缀和', reason: '巩固前缀和隐藏知识点', ids: [rows[3].id], stage: 'foundation', problem: rows[3] }], achievements: [{ id: 'first', name: '首次通过', description: '独立完成一道题', unlocked: true, unlockedAt: now(), progress: 1, target: 1 }, { id: 'ten', name: '十题积累', description: '通过十道不同题目', unlocked: false, progress: 1, target: 10 }], activity: [{ date, submissions: 3, accepted: 1, officialAccepted: 0 }], assessment: { rating: null, recommendationLevel: 1100, recommendationBasis: '基础练习', platforms: [] }, dailyTasks: { date, timezone: 'Asia/Shanghai', totalClaimedXp: 0, claimable: 1, tasks: [{ id: 'warmup', title: '每日热身', description: '完成一次有效提交', progress: 1, target: 1, xp: 20, completed: true, claimed: false }, { id: 'hard', title: '进阶挑战', description: '通过一道难度至少 1800 的题目', progress: 0, target: 1, xp: 100, completed: false, claimed: false, minDifficulty: 1800 }] } };
const notice = { id: 'update-1', type: 'content', title: '新题已加入', body: '新增测试题目', createdAt: now(), read: false, count: 1, problemIds: [rows[4].id] };
const hub = { version: '0.5.0', settings: { githubRepo: '3097729287/acm-agent-workflow', autoSync: true, intervalHours: 6, minDifficulty: 1000, maxDifficulty: 2199, accounts: { codeforces: 'tester', atcoder: 'tester', nowcoder: '', luogu: '' } }, accounts: [{ platform: 'codeforces', handle: 'tester', rating: 415, maxRating: 500, solvedCount: 22, submissionCount: 67, updatedAt: now(), status: 'ready' }, { platform: 'atcoder', handle: 'tester', rating: 98, maxRating: 101, solvedCount: 14, submissionCount: 38, updatedAt: now(), status: 'ready' }], sync: { busy: false, message: '同步完成', providers: [] }, updates: { configured: true, currentVersion: '0.5.0', latestVersion: '0.5.0', repository: '3097729287/acm-agent-workflow' }, notifications: [notice] };
const lecture = { id: 'lesson-1', concept: '位运算：$v \\oplus (v-1)$', displayTitle: '位运算：$v \\oplus (v-1)$', title: '原题旧标题', originalTitle: '旧题应用标题', category: '基础技巧 / 位运算', categories: ['基础技巧 / 位运算'], tags: ['位运算'], sourceContest: '测试比赛', sourceProblem: 'B', sourceTitle: rows[1].title, sourceProblemIds: [rows[1].id], markdown: '## 位运算\n\n一个可手算的例子：$4 \\oplus 3 = 7$。\n\n```cpp\nint value = 4 ^ 3;\n```', images: {} };
const profile = { userId: 'TB-fixture-00001', nickname: '测试用户', displayName: '测试用户#TB-fixture-00001', createdAt: now() };
let rankingPolls = 0;
const connection = { configured: false, endpoint: '', status: 'not_configured', notice: '共享排行榜尚未配置。' };
const translation = { provider: 'deepseek', providerName: 'DeepSeek', model: 'deepseek-chat', baseUrl: '', configured: false, keyStored: false, providers: [{ id: 'deepseek', name: 'DeepSeek', defaultModel: 'deepseek-chat' }, { id: 'custom', name: '自定义 API', defaultModel: '' }] };
const submissions = [{ id: 'sub-1', problemId: rows[3].id, mode: 'submit', verdict: 'WA', submittedAt: now(), timeMs: 14, code: '#include <iostream>\nint main(){std::cout << 1;}', message: '输出不匹配' }];
for (let index = 1; index <= 100; index++) submissions.push({ ...submissions[0], id: 'sub-older-' + index, submittedAt: new Date(Date.now() - index * 60000).toISOString(), verdict: index === 100 ? 'CE' : 'WA', code: 'int main(){return 0;}' });
let preview = null;
await page.route('**/api/**', async route => {
  const request = route.request(), url = new URL(request.url()), path = url.pathname;
  if (!path.startsWith('/api/')) return route.continue();
  const body = request.method() === 'POST' ? request.postDataJSON() : null;
  if (body) { assert.equal(request.headers()['x-tb-token'], 'fixture'); writes.push({ path, body }); }
  let value;
  if (path === '/api/data') value = { rows, categories, token: 'fixture', today: date, revision: 'fixture' };
  else if (path === '/api/goals') value = { goals: [] };
  else if (path === '/api/desktop/fullscreen') value = { available: false, fullscreen: false };
  else if (path === '/api/workspace') value = workspace();
  else if (path === '/api/inbox') value = { pending: 0, errors: [] };
  else if (path === '/api/hub') value = hub;
  else if (path === '/api/insights') value = insights;
  else if (path === '/api/submissions') { const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 100); value = { submissions: submissions.slice(offset, offset + limit), total: submissions.length, offset, limit, hasMore: offset + limit < submissions.length }; }
  else if (path === '/api/lectures') value = { lectures: [lecture] };
  else if (path === '/api/lecture') value = lecture;
  else if (path === '/api/profile') { if (body) { profile.nickname = body.nickname; profile.displayName = `${profile.nickname}#${profile.userId}`; connection.endpoint = body.endpoint || ''; connection.configured = !!connection.endpoint; connection.status = connection.configured ? 'syncing' : 'not_configured'; connection.notice = connection.configured ? '已连接测试排行榜' : '共享排行榜尚未配置。'; } value = { profile, leaderboard: connection }; }
  else if (path === '/api/leaderboard') { if (connection.configured && ++rankingPolls > 1) connection.status = 'ready'; value = { period: url.searchParams.get('period'), date, ...connection, entries: connection.status === 'ready' ? [{ rank: 1, userId: profile.userId, nickname: profile.nickname, count: 1 }] : [], self: connection.configured ? profile : null }; }
  else if (path === '/api/leaderboard/sync') value = { queued: true };
  else if (path === '/api/translation/settings') { if (body) { Object.assign(translation, body); if (body.apiKey !== undefined) translation.keyStored = !!body.apiKey; translation.configured = true; delete translation.apiKey; } value = translation; }
  else if (path === '/api/daily-tasks/claim') { const task = insights.dailyTasks.tasks.find(item => item.id === body.id); if (!task.claimed) { task.claimed = true; insights.growth.totalXp += task.xp; insights.growth.currentLevelXp += task.xp; } value = { dailyTasks: insights.dailyTasks }; }
  else if (path === '/api/contests/preview') { preview = { previewId: 'preview-fixture', name: '测试专项训练', duration: body.duration, constraints: body, slots: rows.slice(3, body.mode === 'single' ? 4 : 6).map((row, index) => ({ id: row.id, letter: 'ABC'[index], title: row.title, judgeScope: 'samples', tags: ['不应泄露考点'], difficulty: 2100 })) }; value = { plan: preview }; }
  else if (path === '/api/contests/start') { assert.equal(body.previewId, preview.previewId); activeContest = { id: 'mock-new', name: body.name, status: 'running', duration: body.duration, startedAt: now(), deadline: new Date(Date.now() + body.duration * 60000).toISOString(), total: body.ids.length, accepted: 0, slots: preview.slots.map(({ tags, difficulty, ...slot }) => ({ ...slot, verdict: null, accepted: false })) }; contests.unshift(activeContest); value = { contest: activeContest, workspace: workspace() }; }
  else if (path === '/api/contests/finish') { const finished = { ...activeContest, status: 'finished', slots: activeContest.slots.map(slot => ({ ...slot, tags: ['枚举'], difficulty: 1600 })) }; contests[0] = finished; activeContest = null; value = { contest: finished, workspace: workspace() }; }
  else if (path === '/api/contest') value = { contest: contests.find(item => item.id === url.searchParams.get('id')) };
  else if (path === '/api/problem') value = { id: url.searchParams.get('id'), title: rows.find(row => row.id === url.searchParams.get('id'))?.title, locked: false, markdown: '## 题目描述\n\n输出整数 $n$。\n\n## 输入\n一个整数。', samples: [{ name: '样例 1', input: '1\n', output: '1\n' }], limits: { timeMs: 2000, memoryMb: 256 }, judge: { scope: 'samples', cases: 1 }, statementAvailable: true, draft: '', submissions: [] };
  else if (path === '/api/draft') value = { savedAt: now() };
  else if (path === '/api/hub/dismiss') { notice.read = true; value = hub; }
  else if (path === '/api/hub/configure') { Object.assign(hub.settings, body); value = hub; }
  else if (path === '/api/hub/sync') value = hub;
  else throw new Error('Unhandled fixture request: ' + path);
  await route.fulfill({ json: value });
});

async function noOverflow(selector) {
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'viewport has no horizontal overflow');
  if (selector) assert.ok(await page.locator(selector).evaluate(node => node.scrollWidth <= node.clientWidth + 1), `${selector} has no horizontal overflow`);
}
try {
  await mkdir('tests/screenshots', { recursive: true });
  await page.goto('http://127.0.0.1:18775');
  await page.locator('.problem-table').waitFor();
  assert.equal(await page.locator('.sidebar-statistics').count(), 0);
  assert.equal(await page.getByRole('button', { name: '提交记录', exact: true }).count(), 1);
  await page.getByLabel('训练分组').selectOption('@single');
  assert.equal(await page.locator('.problem-table tbody tr[data-id]').count(), 1);
  await page.getByLabel('训练分组').selectOption('');
  await page.getByRole('button', { name: '筛选', exact: true }).click();
  assert.ok(await page.getByLabel('排序方式').evaluate(node => node.clientWidth >= 180));
  await page.getByLabel('平台筛选').selectOption('AtCoder');
  assert.equal(await page.locator('.problem-table tbody tr[data-id]').count(), 2);
  assert.equal(await page.locator('.page-identity h1').evaluate(node => getComputedStyle(node).userSelect), 'none');
  assert.equal(await page.locator('.sidebar .knowledge-search,.sidebar .knowledge-tree-tools,.sidebar-section-title').count(), 0);
  assert.ok(await page.locator('.sidebar').getByRole('treeitem').count() > 0);
  assert.equal(await page.locator('.sidebar nav').evaluate(node => node.scrollHeight > node.clientHeight + 1), false);

  await page.keyboard.press('Control+7');
  assert.equal(await page.locator('.progress-recommendations').getByText('巩固前缀和隐藏知识点', { exact: true }).count(), 0);
  const task = page.locator('.daily-task').filter({ hasText: '每日热身' });
  await task.getByRole('button', { name: '领取经验' }).click();
  await task.getByRole('button', { name: '已领取' }).waitFor();
  assert.equal(insights.growth.totalXp, 30);
  assert.equal(writes.filter(item => item.path === '/api/daily-tasks/claim').length, 1);
  assert.equal(await page.locator('.progress-page .progress-achievements').count(), 0);
  await page.screenshot({ path: 'tests/screenshots/v5-growth-light-2048.png', animations: 'disabled' });
  await page.getByRole('button', { name: '成就', exact: true }).click();
  await page.getByRole('dialog').getByText('十题积累', { exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Control+8');
  assert.equal(await page.locator('.activity-details').getAttribute('open'), '');
  await page.keyboard.press('Control+9');
  await page.locator('.lectures-list .katex').waitFor();
  await page.locator('.lectures-list button').first().click();
  await page.locator('.lecture-markdown .katex').waitFor();
  assert.equal(await page.locator('.lecture-markdown').evaluate(node => getComputedStyle(node).userSelect), 'text');
  await page.screenshot({ path: 'tests/screenshots/v5-lectures-light-2048.png', animations: 'disabled' });

  await page.keyboard.press('Control+6');
  await page.getByLabel('搜索历史提交').waitFor();
  assert.equal(await page.getByRole('tab', { name: /模拟赛记录/ }).count(), 0);
  await page.locator('.submission-log-row').first().click();
  await page.getByRole('dialog').locator('.submission-source').getByText('#include <iostream>', { exact: false }).waitFor();
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.submission-log-row').count(), 100);
  await page.getByRole('button', { name: '加载更早提交' }).click();
  await page.waitForFunction(() => document.querySelectorAll('.submission-log-row').length === 101);
  await page.getByLabel('历史提交结果').selectOption('CE');
  assert.equal(await page.locator('.submission-log-row').count(), 1);
  await page.getByLabel('历史提交结果').selectOption('');
  await page.keyboard.press('Control+5');
  assert.equal(await page.locator('.mock-followup').count(), 0);
  await page.getByRole('tab', { name: /模拟赛记录/ }).click();
  await page.getByRole('button', { name: /完成的模拟赛/ }).click();
  await page.locator('.record-detail').waitFor();
  await page.getByRole('tab', { name: '创建训练', exact: true }).click();
  await page.getByRole('button', { name: /专项训练.*指定某个/ }).click();
  assert.ok(await page.getByRole('button', { name: '生成试卷', exact: true }).isDisabled());
  await page.getByLabel('专项训练知识点').selectOption('前缀和');
  await page.getByLabel('组题平台').selectOption('AtCoder');
  await page.getByLabel('只选本地完整评测题').check();
  await page.getByRole('button', { name: '生成试卷', exact: true }).click();
  await page.getByLabel('训练试卷预览').waitFor();
  assert.equal(await page.getByLabel('训练试卷预览').getByText('不应泄露考点').count(), 0);
  assert.deepEqual(writes.findLast(item => item.path === '/api/contests/preview').body.tags, ['前缀和']);
  assert.equal(writes.findLast(item => item.path === '/api/contests/preview').body.platform, 'AtCoder');
  assert.equal(writes.findLast(item => item.path === '/api/contests/preview').body.reviewedOnly, true);
  await page.screenshot({ path: 'tests/screenshots/v5-mock-light-2048.png', animations: 'disabled' });
  await page.getByRole('button', { name: /随机单题.*抽取一道/ }).click();
  await page.getByRole('button', { name: '抽取单题', exact: true }).click();
  await page.getByRole('button', { name: /开始 120 分钟训练/ }).waitFor();
  assert.equal(writes.findLast(item => item.path === '/api/contests/preview').body.count, 1);
  await page.getByRole('button', { name: /开始 120 分钟训练/ }).click();
  await page.getByRole('button', { name: '结束比赛', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '结束并复盘', exact: true }).click();
  await page.locator('.record-detail').waitFor();
  assert.equal(await page.locator('.page-identity h1').textContent(), '模拟赛');

  await page.getByRole('button', { name: '排行榜', exact: true }).click();
  await page.getByText('共享排行榜尚未连接', { exact: true }).waitFor();
  assert.equal(await page.locator('.ranking-table').count(), 0);
  await page.getByRole('button', { name: '设置昵称与连接' }).click();
  await page.getByLabel('用户昵称').fill('测试新昵称');
  await page.getByLabel('排行榜服务地址').fill('https://fixture.example.com');
  await page.getByRole('button', { name: '保存身份' }).click();
  await page.getByText('昵称与排行榜连接已保存。').waitFor();
  assert.equal(profile.userId, 'TB-fixture-00001');
  await page.getByRole('button', { name: '排行榜', exact: true }).click();
  await page.locator('.ranking-table').getByText('测试新昵称', { exact: true }).waitFor();

  await page.keyboard.press('Control+0');
  await page.getByRole('tab', { name: '翻译 API', exact: true }).click();
  await page.getByLabel('翻译服务', { exact: true }).selectOption('custom');
  await page.getByLabel('翻译 API Base URL').fill('http://127.0.0.1:1234/v1');
  await page.getByLabel('翻译模型', { exact: true }).fill('my-custom-model');
  await page.getByLabel('翻译服务 API Key').fill('fixture-secret');
  await page.getByRole('button', { name: '保存翻译配置', exact: true }).click();
  await page.getByText('翻译配置已保存，首次翻译时验证连接。').waitFor();
  const saved = writes.findLast(item => item.path === '/api/translation/settings').body;
  assert.equal(saved.baseUrl, 'http://127.0.0.1:1234/v1');
  assert.equal(saved.model, 'my-custom-model');
  assert.equal(await page.getByLabel('翻译服务 API Key').inputValue(), '');
  await page.getByRole('tab', { name: '更新', exact: true }).click();
  assert.equal(await page.locator('.settings-page .update-notifications').count(), 0);
  await page.getByRole('button', { name: '更新通知', exact: true }).click();
  await page.getByRole('dialog').getByText('新题已加入', { exact: true }).waitFor();
  await page.keyboard.press('Escape');

  for (const width of [2048, 1050]) {
    await page.setViewportSize({ width, height: width === 1050 ? 760 : 1152 });
    await page.keyboard.press('Control+0');
    for (const tab of ['外观与导航', '账号与身份', '翻译 API', '更新']) {
      await page.getByRole('tab', { name: tab, exact: true }).click();
      await noOverflow('.settings-page');
      await page.screenshot({ path: `tests/screenshots/v5-settings-${tab}-${width}.png`, animations: 'disabled' });
    }
    await page.keyboard.press('Control+1');
    await page.getByRole('button', { name: '筛选', exact: true }).click();
    await noOverflow('.list-page');
    await page.screenshot({ path: `tests/screenshots/v5-filters-${width}.png`, animations: 'disabled' });
    await page.keyboard.press('Control+5');
    await page.getByRole('tab', { name: '创建训练', exact: true }).click();
    await noOverflow('.mock-create');
    await page.screenshot({ path: `tests/screenshots/v5-mock-light-${width}.png`, animations: 'disabled' });
    await page.keyboard.press('Control+7');
    await noOverflow('.progress-page');
    await page.screenshot({ path: `tests/screenshots/v5-growth-light-${width}.png`, animations: 'disabled' });
  }
  await page.keyboard.press('Control+0');
  await page.getByRole('tab', { name: '外观与导航', exact: true }).click();
  await page.getByRole('button', { name: '石墨深色', exact: true }).click();
  await page.screenshot({ path: 'tests/screenshots/v5-settings-dark-1050.png', animations: 'disabled' });
  for (const width of [1050, 2048]) {
    await page.setViewportSize({ width, height: width === 1050 ? 760 : 1152 });
    await page.keyboard.press('Control+5');
    await page.getByRole('tab', { name: '创建训练', exact: true }).click();
    await noOverflow('.mock-create');
    await page.screenshot({ path: `tests/screenshots/v5-mock-dark-${width}.png`, animations: 'disabled' });
    await page.keyboard.press('Control+7');
    await noOverflow('.progress-page');
    await page.screenshot({ path: `tests/screenshots/v5-growth-dark-${width}.png`, animations: 'disabled' });
  }
  await page.setViewportSize({ width: 1050, height: 760 });
  await page.keyboard.press('Control+0');
  await page.getByLabel('导航名称 records').fill('历史提交');
  await page.getByLabel('页面组合 records').fill('我的记录');
  await page.getByLabel('页面组合 activity').fill('我的记录');
  await page.getByRole('button', { name: '上移 排行榜', exact: true }).click();
  assert.equal(await page.getByText('我的书签', { exact: true }).count(), 0);
  assert.equal(await page.getByRole('button', { name: '添加书签', exact: true }).count(), 0);
  assert.equal(await page.getByRole('button', { name: '书签 旧书签', exact: true }).count(), 0, 'stored bookmarks stay removed after upgrade');
  await page.keyboard.press('Control+8');
  await page.getByRole('tab', { name: '活动记录', exact: true }).waitFor();
  await page.getByRole('tab', { name: '活动记录', exact: true }).click();
  await page.locator('.activity-details').waitFor();
  await page.keyboard.press('Control+6');
  assert.equal(await page.locator('.page-identity h1').textContent(), '历史提交', 'fixed keyboard shortcut survives reorder/rename/group');
  await noOverflow('.records-page');
  assert.deepEqual(errors, []);
  console.log('v5 UI passed: blind mock + filters + single groups, mock history/submission history, daily XP claims, visible achievements, canonical math lectures, custom API, persistent identity/offline and connected ranking states, configurable navigation and removed bookmarks and large-font responsive layouts.');
} finally { await browser.close(); await vite.close(); }
