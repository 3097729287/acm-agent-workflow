import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';

// Run only against an isolated --serve-check installation. The preflight below
// rejects a populated personal database before any write or UI interaction.
assert.ok(process.env.BASE_URL, 'Set BASE_URL to the temporary installed TB server.');
const target = new URL(process.env.BASE_URL);
assert.equal(target.protocol, 'http:');
assert.ok(['127.0.0.1', 'localhost'].includes(target.hostname), 'Probe accepts loopback servers only.');
assert.ok(target.port && target.port !== '18765', 'Never probe the normal personal server.');
assert.ok(!target.username && !target.password && !target.search && !target.hash);
assert.ok(['', '/'].includes(target.pathname));
const base = target.origin;
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 1480, height: 920 } });
page.setDefaultTimeout(15000);
await page.addInitScript(() => localStorage.setItem('tb.preferences', JSON.stringify({ theme: 'light', fontSize: 18, accent: 'teal' })));
const errors = [];
page.on('pageerror', error => errors.push(error.message));
let token;
async function get(path) {
  const response = await page.request.get(`${base}/api/${path}`, { timeout: 60000 });
  assert.equal(response.ok(), true, `GET ${path}: ${response.status()}`);
  return response.json();
}
async function post(path, body) {
  const response = await page.request.post(`${base}/api/${path}`, { data: body, headers: { 'X-TB-Token': token, Origin: base }, timeout: 60000 });
  assert.equal(response.ok(), true, `POST ${path}: ${response.status()} ${await response.text()}`);
  return response.json();
}
async function screenshot(name) {
  if (!process.env.SCREENSHOT_DIR) return;
  await mkdir(process.env.SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: join(process.env.SCREENSHOT_DIR, name + '.png'), animations: 'disabled' });
}
function assertBlind(slots, context) {
  assert.ok(slots.length, `${context}: contains a question`);
  for (const slot of slots) {
    for (const field of ['tags', 'knowledge', 'difficulty', 'url', 'solution', 'markdown']) {
      assert.equal(field in slot, false, `${context}: ${field} stays hidden`);
    }
  }
}

try {
  const [initial, logs, identity, initialInsights, hub, settings] = await Promise.all([
    get('workspace'), get('submissions'), get('profile'), get('insights'), get('hub'), get('translation/settings'),
  ]);
  assert.equal(initial.summary.total, 0, 'Probe needs a fresh temporary personal database.');
  assert.equal(initial.summary.accepted, 0);
  assert.equal(initial.contests.length, 0);
  assert.equal(initial.sets.length, 0);
  assert.equal(initial.activeContest, null);
  assert.equal(logs.total, 0, 'Refuse to overwrite or add submissions to an existing personal database.');
  assert.equal(initialInsights.growth.totalXp, 0);
  assert.equal(initialInsights.achievements.some(item => item.unlocked), false);
  assert.match(identity.profile.userId, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  assert.equal(identity.leaderboard.configured, false);
  assert.equal('authToken' in identity.profile, false);
  assert.equal('auth_token' in identity.profile, false);
  assert.equal(settings.configured, false);
  assert.equal(settings.verified, false);
  for (const secret of ['apiKey', 'protectedKey', 'key']) assert.equal(secret in settings, false);
  assert.equal(hub.accounts.every(account => !account.handle), true);

  const library = await get('data');
  token = library.token;
  const tested = library.rows.find(row => row.contest === '入门赛 49' && row.problem === 'D');
  assert.ok(tested, 'Packaged archive includes the reviewed stair problem.');
  const profile = await post('profile', { nickname: '安装包验证', endpoint: '' });
  assert.equal(profile.profile.userId, identity.profile.userId, 'Nickname changes preserve the installation identity.');
  assert.ok(profile.profile.displayName.includes('安装包验证') && profile.profile.displayName.includes(identity.profile.userId));

  await page.goto(base);
  await page.getByRole('heading', { name: '从第一道题开始', exact: true }).waitFor();
  assert.equal(await page.locator('.sidebar-statistics').count(), 0);
  await page.keyboard.press('Control+2');
  await page.getByRole('textbox', { name: '搜索题目', exact: true }).fill('入门赛 49 D');
  await page.locator('.problem-table tbody tr .problem-title').first().click();
  const editor = page.getByRole('textbox', { name: 'C++ 代码', exact: true });
  await page.waitForFunction(() => document.querySelector('.cm-content[contenteditable=true]'));
  assert.equal(await page.locator('.wb-scope-local').count(), 1, 'Bundled complete reviewed tests are available.');
  const solution = '#include <bits/stdc++.h>\nusing namespace std; int main(){int n;cin>>n;long long one[61]={1},two[61]={0};for(int i=1;i<=n;++i){one[i]=one[i-1]+two[i-1];if(i>=2)two[i]=one[i-2];}cout<<one[n]+two[n]<<"\\n";}\n';
  await editor.fill(solution);
  await editor.press('Control+r');
  await page.waitForFunction(() => ['运行完成', '样例通过'].some(label => document.querySelector('.wb-result-summary')?.textContent.includes(label)), null, { timeout: 45000 });
  assert.equal((await get('workspace')).summary.accepted, 0, 'Running samples never counts as an accepted problem.');
  assert.equal((await get('daily-tasks')).tasks.some(task => task.completed), false, 'A run cannot complete a daily solve task.');
  await editor.press('Control+Enter');
  await page.waitForFunction(() => document.querySelector('.wb-result-summary')?.textContent.includes('本地 AC'), null, { timeout: 60000 });
  let progress = await get('workspace');
  assert.equal(progress.summary.total, 1);
  assert.equal(progress.summary.accepted, 1, 'The packaged C++ toolchain compiles and passes actual reviewed cases.');
  const acceptedInsights = await get('insights');
  assert.equal(acceptedInsights.summary.localAccepted, 1);
  const daily = await get('daily-tasks');
  const reward = daily.tasks.find(task => task.completed && !task.claimed);
  assert.ok(reward, 'A first reviewed acceptance completes a daily mission.');
  assert.ok(daily.tasks.filter(task => task.minDifficulty > 0).every(task => task.xp > daily.tasks.find(item => item.id === 'solve-1').xp), 'Harder missions offer more experience.');
  await screenshot('v5-packaged-local-ac');

  // Re-submit the same accepted original problem. It must not farm daily solves
  // or experience, and the real historical source remains accessible.
  await editor.press('Control+Enter');
  await page.waitForFunction(() => !document.querySelector('.wb-result-summary')?.textContent.includes('评测中') && document.querySelector('.wb-result-summary')?.textContent.includes('本地 AC'), null, { timeout: 60000 });
  await page.waitForFunction(async base => {
    const value = await fetch(base + '/api/submissions').then(response => response.json());
    return value.submissions.filter(item => item.mode === 'submit' && item.verdict === 'AC').length === 2;
  }, base, { timeout: 60000 });
  assert.equal((await get('insights')).growth.totalXp, acceptedInsights.growth.totalXp);
  assert.equal((await get('daily-tasks')).tasks.find(task => task.id === 'solve-1').progress, 1);
  await page.getByRole('button', { name: '返回列表', exact: true }).click();
  await page.keyboard.press('Control+7');
  const taskCard = page.locator('.daily-task').filter({ hasText: reward.title });
  await taskCard.getByRole('button', { name: '领取经验', exact: true }).click();
  await taskCard.getByRole('button', { name: '已领取', exact: true }).waitFor();
  const afterClaim = await get('insights');
  assert.equal(afterClaim.growth.totalXp, acceptedInsights.growth.totalXp + reward.xp);
  const duplicate = await post('daily-tasks/claim', { id: reward.id, date: daily.date });
  assert.equal(duplicate.alreadyClaimed, true);
  assert.equal((await get('insights')).growth.totalXp, afterClaim.growth.totalXp, 'Claim retry awards no duplicate XP.');
  await page.getByRole('button', { name: '成就', exact: true }).click();
  await page.getByRole('dialog').getByText('首次本地通过', { exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await screenshot('v5-packaged-daily-tasks');

  await page.keyboard.press('Control+6');
  await page.getByLabel('搜索历史提交').waitFor();
  await page.locator('.submission-log-row').first().click();
  const source = page.getByRole('dialog').locator('.submission-source');
  await source.waitFor();
  assert.equal((await source.textContent()).trim(), solution.trim());
  await page.keyboard.press('Escape');
  const history = await get('submissions');
  assert.equal(history.total, 3);
  assert.equal(history.submissions.filter(item => item.verdict === 'AC' && item.scope === 'local').length, 2);
  assert.equal(history.submissions.every(item => item.code === solution), true);
  assert.equal(await page.getByRole('tab', { name: /模拟赛记录/ }).count(), 0, 'Submission page contains submission history only.');

  await page.keyboard.press('Control+5');
  await page.getByRole('button', { name: /专项训练.*指定某个/ }).click();
  await page.getByLabel('模拟赛题目数').selectOption('1');
  await page.getByLabel('模拟赛最低难度').fill(String(tested.difficulty));
  await page.getByLabel('模拟赛最高难度').fill(String(tested.difficulty));
  await page.getByLabel('组题平台').selectOption(tested.platform);
  await page.getByLabel('排除已通过题目').uncheck();
  await page.getByLabel('只选本地完整评测题').check();
  const topicValues = await page.getByLabel('专项训练知识点').locator('option').evaluateAll(options => options.map(option => option.value));
  const topic = tested.tags.find(tag => topicValues.includes(tag));
  assert.ok(topic, 'Reviewed source knowledge can be selected for targeted practice.');
  await page.getByLabel('专项训练知识点').selectOption(topic);
  const previewResponse = page.waitForResponse(response => response.url() === `${base}/api/contests/preview` && response.request().method() === 'POST');
  await page.getByRole('button', { name: '生成试卷', exact: true }).click();
  const targeted = (await (await previewResponse).json()).plan;
  assert.equal(targeted.constraints.strategy, 'topic');
  assert.equal(targeted.constraints.platform, tested.platform);
  assert.ok(targeted.constraints.tags.includes(topic));
  assert.equal(targeted.constraints.reviewedOnly, true);
  assert.equal(targeted.slots.length, 1);
  assertBlind(targeted.slots, 'targeted preview');
  const rowById = new Map(library.rows.map(row => [row.id, row]));
  assert.ok(targeted.slots.every(slot => rowById.get(slot.id)?.tags.includes(topic)));
  await page.getByLabel('训练试卷预览').waitFor();
  assert.equal(await page.getByLabel('训练试卷预览').locator('.difficulty,.tag').count(), 0);

  await page.getByRole('button', { name: /随机单题.*抽取一道/ }).click();
  const singleResponse = page.waitForResponse(response => response.url() === `${base}/api/contests/preview` && response.request().method() === 'POST');
  await page.getByRole('button', { name: '抽取单题', exact: true }).click();
  const single = (await (await singleResponse).json()).plan;
  assert.equal(single.slots.length, 1);
  assertBlind(single.slots, 'random single preview');
  await page.getByRole('button', { name: '开始 120 分钟训练', exact: true }).click();
  await page.getByRole('button', { name: '结束比赛', exact: true }).waitFor();
  progress = await get('workspace');
  assert.equal(progress.activeContest.total, 1);
  assert.equal(progress.activeContest.accepted, 0, 'A previous personal acceptance is not a solve in this mock.');
  assertBlind(progress.activeContest.slots, 'active mock');
  const locked = await page.request.get(`${base}/api/solution?id=${encodeURIComponent(progress.activeContest.slots[0].id)}`);
  assert.equal(locked.status(), 403, 'Real backend locks mock solutions.');
  await screenshot('v5-packaged-blind-mock');
  await page.getByRole('button', { name: '结束比赛', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '结束并复盘', exact: true }).click();
  await page.locator('.record-detail').waitFor();
  progress = await get('workspace');
  assert.equal(progress.activeContest, null);
  assert.equal(progress.contests.length, 1);
  assert.equal(progress.contests[0].accepted, 0);
  assert.ok(progress.contests[0].slots.every(slot => Array.isArray(slot.tags) && typeof slot.difficulty === 'number'), 'Finished mocks unlock tags and difficulty.');
  const afterMock = await get('insights');
  assert.equal(afterMock.growth.totalXp, afterClaim.growth.totalXp, 'An empty immediate finish awards no experience.');
  assert.equal(afterMock.achievements.find(item => item.id === 'contest-1').unlocked, false, 'An empty immediate finish earns no completion achievement.');
  await page.getByRole('tab', { name: /模拟赛记录/ }).click();
  await page.getByRole('button', { name: /随机单题|模拟赛|安装包验证/ }).filter({ has: page.locator('small') }).first().waitFor();

  await page.keyboard.press('Control+1');
  await page.getByLabel('训练分组').selectOption('@single');
  await page.getByLabel('训练分组').selectOption(progress.contests[0].id);
  await page.getByLabel('训练分组').selectOption('');
  await page.keyboard.press('Control+8');
  assert.equal(await page.locator('.activity-details').getAttribute('open'), '');

  const lectures = await get('lectures');
  assert.ok(lectures.lectures.length >= 373, 'Full foundations remain available in the installed corpus.');
  assert.equal(lectures.lectures.every(item => item.knowledgeName && item.category && item.tags?.includes(item.knowledgeName) && item.quality?.normalized), true, 'Every lecture has a canonical name and classification.');
  assert.equal(lectures.lectures.some(item => 'markdown' in item), false, 'Index returns summaries, not hundreds of full lessons.');
  const bitLesson = lectures.lectures.find(item => item.sourceProblemIds?.includes('ABC 470::C') && item.tags.includes('位运算'));
  assert.ok(bitLesson, 'Original mathematical lecture is included with a standard keyword.');
  const lecture = await get('lecture?id=' + encodeURIComponent(bitLesson.id));
  assert.ok(lecture.markdown.length > 300 && lecture.sourceProblemIds.length > 0);
  await page.keyboard.press('Control+9');
  await page.getByLabel('搜索从零讲知识').fill('ABC 470');
  await page.locator('.lectures-list button').filter({ hasText: bitLesson.concept }).first().click();
  await page.locator('.lecture-markdown .katex').first().waitFor();
  assert.equal(await page.locator('.lecture-markdown .katex-error').count(), 0);
  assert.equal(await page.locator('.lecture-markdown').evaluate(node => getComputedStyle(node).userSelect), 'text');
  assert.equal(await page.locator('.page-identity h1').evaluate(node => getComputedStyle(node).userSelect), 'none');
  await screenshot('v5-packaged-canonical-lecture');

  await page.getByRole('button', { name: '排行榜', exact: true }).click();
  await page.getByText('共享排行榜尚未连接', { exact: true }).waitFor();
  assert.equal(await page.locator('.ranking-table').count(), 0, 'An unconfigured install shows no fictitious shared standings.');
  assert.equal((await get('profile')).profile.userId, identity.profile.userId);
  await page.keyboard.press('Control+0');
  await page.getByRole('tab', { name: '翻译 API', exact: true }).click();
  await page.getByLabel('翻译服务', { exact: true }).selectOption('custom');
  await page.getByLabel('翻译 API Base URL').fill('http://127.0.0.1:1234/v1');
  await page.getByLabel('翻译模型', { exact: true }).fill('custom-model');
  await page.getByLabel('翻译服务 API Key').fill('probe-unsaved-key');
  assert.equal((await get('translation/settings')).configured, false, 'Checking custom fields never sends translation or stores credentials.');
  await page.getByRole('tab', { name: '更新', exact: true }).click();
  assert.equal(await page.locator('.settings-page .update-notifications').count(), 0);
  await page.setViewportSize({ width: 1050, height: 760 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Installed UI fits the smaller viewport at 18 px.');
  await screenshot('v5-packaged-settings');
  await page.reload();
  await page.locator('.page-identity').waitFor();
  assert.equal((await get('profile')).profile.userId, identity.profile.userId, 'Reload preserves the same unique ID.');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: true, localAccepted: 1, submissions: history.total, xp: afterMock.growth.totalXp, lectures: lectures.lectures.length, mockAccepted: 0, sharedRankingConfigured: false, checks: ['fresh isolated profile', 'bundled C++17 run and reviewed AC', 'nonduplicating daily experience', 'historical source code', 'targeted and single blind mock', 'instant finish earns no reward', 'canonical mathematics lectures', 'custom API fields', 'persistent identity', 'responsive installed UI'] }, null, 2));
} finally {
  await browser.close();
}
