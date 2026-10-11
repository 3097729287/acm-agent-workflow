import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const server = await createServer({ root, server: { host: '127.0.0.1', port: 18768, strictPort: true } });
await server.listen();
const browser = await chromium.launch({ channel: process.env.CI ? undefined : 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 1050, height: 700 } });
await page.addInitScript(() => {
  window.acceptedTones = 0;
  const create = AudioContext.prototype.createOscillator;
  AudioContext.prototype.createOscillator = function() { window.acceptedTones++; return create.apply(this, arguments); };
});
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:18768/tests/workbench-fixture.html');
  const editor = page.getByRole('textbox', { name: 'C++ 代码' });
  await editor.waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.querySelector('.cm-content')?.getAttribute('contenteditable') === 'true');
  assert.ok(await page.locator('.wb-statement .katex').count() >= 3);
  assert.equal(await page.locator('.wb-console').count(), 0, 'console stays collapsed initially');
  assert.ok(await page.locator('.cm-line > span').count() > 0, 'C++ syntax uses colored tokens');
  await editor.fill('fori');
  await editor.press('Control+Space');
  await page.locator('.cm-tooltip-autocomplete').waitFor();
  await page.waitForTimeout(150);
  await editor.press('Tab');
  assert.ok((await page.evaluate(() => window.workbenchFixture.readCode())).startsWith('for (int'), 'C++ snippet completion inserts a loop');
  await editor.press('Control+f');
  await page.locator('.cm-search').waitFor();
  await page.locator('.cm-search input').first().press('Escape');

  await editor.fill('int main(){\n    return 0;\n}\n');
  await editor.press('Control+s');
  await page.waitForFunction(() => window.workbenchFixture.drafts['solo:A']?.startsWith('int main'));
  await page.evaluate(() => window.workbenchFixture.selectCode(0));
  await editor.press('Tab');
  assert.ok((await page.evaluate(() => window.workbenchFixture.readCode())).startsWith('    int main'), 'editor Tab indents');
  await editor.press('Control+Tab');
  assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), '输入与样例', 'keyboard can leave editor');

  // A save is in flight while the user changes questions. It must keep its
  // original ID and must not contaminate B, even when A is revisited quickly.
  await page.evaluate(() => { window.workbenchFixture.draftDelay = 450; });
  await editor.fill('draft A newest');
  await editor.press('Control+s');
  await page.evaluate(() => window.workbenchFixture.changeProblem('B'));
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '最长的路径');
  await editor.fill('draft B newest');
  await editor.press('Control+s');
  await page.evaluate(() => window.workbenchFixture.changeProblem('A'));
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '两数之和');
  assert.equal(await page.evaluate(() => window.workbenchFixture.readCode()), 'draft A newest');
  await editor.fill('draft A latest after revisit');
  await editor.press('Control+s');
  await page.waitForFunction(() => window.workbenchFixture.drafts['solo:A'] === 'draft A latest after revisit' && window.workbenchFixture.drafts['solo:B'] === 'draft B newest');

  // The first old A save is pending, an additional old A edit exists, and a
  // newly mounted A saves again. The old loop must not write after the new one.
  await page.evaluate(() => { window.workbenchFixture.draftDelay = 650; });
  await editor.fill('old A first in-flight');
  await editor.press('Control+s');
  await editor.fill('old A second dirty edit');
  await page.evaluate(() => window.workbenchFixture.changeProblem('B'));
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '最长的路径');
  await page.evaluate(() => window.workbenchFixture.changeProblem('A'));
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '两数之和');
  await editor.fill('reopened A final code');
  await editor.press('Control+s');
  await page.waitForFunction(() => window.workbenchFixture.drafts['solo:A'] === 'reopened A final code');
  await page.waitForTimeout(900);
  assert.equal(await page.evaluate(() => window.workbenchFixture.drafts['solo:A']), 'reopened A final code');
  await page.evaluate(() => { window.workbenchFixture.draftDelay = 15; });

  await page.getByRole('button', { name: '中文', exact: true }).click();
  await page.getByText('机器翻译 · Fixture provider', { exact: true }).waitFor();
  assert.ok(await page.locator('.wb-statement').textContent().then(text => text.includes('A 的中文题面')));
  assert.equal(await page.evaluate(() => 'code' in window.workbenchFixture.calls.filter(call => call.path === 'problem/translate').at(-1).body), false, 'translation sends only problem identity');
  await page.getByRole('button', { name: '原文', exact: true }).click();
  assert.ok(await page.locator('.wb-statement').textContent().then(text => text.includes('给出两个整数')));

  await editor.press('Control+r');
  await page.waitForFunction(() => document.querySelector('.wb-result-summary')?.textContent.includes('样例通过'));
  assert.equal(await page.locator('.wb-case').count(), 2, 'all official samples are compared');
  assert.equal(await page.locator('.wb-case-mismatch').count(), 0, 'CRLF difference is not flagged');
  assert.equal(await page.evaluate(() => window.workbenchFixture.calls.filter(call => call.path === 'submissions').at(-1).body.sampleRun), true);
  assert.equal(await page.evaluate(() => window.workbenchFixture.progress.length), 0, 'running does not report accepted progress');

  await page.evaluate(() => { window.workbenchFixture.nextRunVerdict = 'WA'; });
  await editor.press('Control+r');
  await page.waitForFunction(() => document.querySelector('.wb-result-summary')?.textContent.includes('答案错误'));
  assert.equal(await page.locator('.wb-case-mismatch').count(), 2, 'WA highlights expected and actual mismatch lines');
  assert.ok(await page.getByRole('generic', { name: '样例 2 实际输出' }).count() || await page.locator('pre[aria-label="样例 2 实际输出"]').count());
  await page.getByLabel('运行输入', { exact: true }).selectOption('custom');
  await page.getByRole('button', { name: '输入与样例', exact: true }).click();
  await page.getByRole('textbox', { name: '标准输入', exact: true }).fill('');
  await editor.press('Control+r');
  await page.waitForFunction(() => document.querySelector('.wb-result-summary')?.textContent.includes('运行完成（未校验）'));
  assert.equal(await page.evaluate(() => window.workbenchFixture.calls.filter(call => call.path === 'submissions').at(-1).body.sampleRun), false, 'empty custom input is not sample execution');
  assert.ok(await page.getByText('自定义输入没有预期答案，仅检查程序是否正常运行。', { exact: true }).isVisible());
  assert.equal(await page.evaluate(() => window.workbenchFixture.progress.length), 0);
  assert.deepEqual(await page.locator('.wb-run-actions button').allTextContents(), ['运行输入', '提交']);
  assert.equal(await page.getByRole('button', { name: '本地提交', exact: true }).count(), 0);
  assert.equal(await page.getByRole('button', { name: '官方提交', exact: true }).count(), 0);
  await editor.press('Control+Enter');
  await page.getByText('请先登录授权。', { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => window.workbenchFixture.calls.filter(call => call.path === 'official/submit').at(-1).body.code), 'reopened A final code');
  assert.equal(await page.evaluate(() => window.workbenchFixture.submissions.length), 3, 'submit never invokes local judging');
  await page.getByRole('button', { name: '登录授权', exact: true }).click();
  await page.getByText('请先登录授权。', { exact: true }).waitFor();
  assert.ok(await page.evaluate(() => window.workbenchFixture.calls.some(call => call.path === 'official/open')));
  assert.equal(await page.evaluate(() => window.workbenchFixture.progress.length), 0, 'login/opening never manufactures accepted progress');
  await page.evaluate(() => { window.workbenchFixture.officialStatus = 'ready'; });
  await page.getByText('登录成功，可以提交。', { exact: true }).waitFor();
  await page.getByRole('button', { name: '提交', exact: true }).click();
  await page.evaluate(() => { window.workbenchFixture.officialStatus = 'judging'; });
  await page.getByText('评测中', { exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: '提交', exact: true }).isDisabled(), true);
  const beforeDuplicate = await page.evaluate(() => window.workbenchFixture.calls.filter(call => call.path === 'official/submit').length);
  await editor.press('Control+Enter');
  assert.equal(await page.evaluate(() => window.workbenchFixture.calls.filter(call => call.path === 'official/submit').length), beforeDuplicate);
  assert.equal(await editor.isVisible(), true, 'editor stays available while official judging');
  assert.equal(await page.evaluate(() => window.acceptedTones), 0, 'samples, WA, login and pending do not play the AC sound');
  await page.evaluate(() => { window.workbenchFixture.officialStatus = 'finished'; });
  await page.waitForFunction(() => document.querySelector('.wb-result-summary .wb-verdict-confirmed')?.textContent.trim() === 'AC');
  await page.waitForFunction(() => window.workbenchFixture.progress.length === 1);
  assert.ok(await page.locator('.wb-result-summary .wb-verdict-confirmed').evaluate(el => parseFloat(getComputedStyle(el).fontSize) >= 32));
  assert.equal(await page.evaluate(() => window.acceptedTones), 4, 'one confirmed AC plays one four-note chime');
  assert.equal(await page.locator('.wb-result-summary').textContent().then(value => value.includes('官方')), false);
  await page.waitForTimeout(1200);
  assert.equal(await page.evaluate(() => window.acceptedTones), 4, 'repeat receipt polling does not replay the sound');
  await page.getByRole('button', { name: /^记录/ }).click();
  await page.locator('.wb-history-main').first().click();
  assert.equal(await page.evaluate(() => window.acceptedTones), 4, 'viewing an accepted history record stays silent');

  // Button Enter must remain a native click, not a preview toggle/global key.
  const solution = page.getByRole('button', { name: '题解', exact: true });
  await solution.focus();
  await solution.press('Enter');
  assert.equal(await page.evaluate(() => window.workbenchFixture.solutionCount), 1);
  await editor.focus();
  await editor.press('Alt+1');
  assert.equal(await editor.isVisible(), false);
  await page.locator('.wb-statement').press('Alt+2');
  assert.equal(await editor.isVisible(), true);
  await editor.press('Alt+0');

  // Late problem fetches cannot replace the currently selected problem.
  await page.evaluate(() => { window.workbenchFixture.problemDelay.B = 650; window.workbenchFixture.changeProblem('B'); });
  await page.waitForFunction(() => document.querySelector('.tb-workbench').dataset.problemId === 'B');
  await page.evaluate(() => window.workbenchFixture.changeProblem('C'));
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '第三道题');
  await page.waitForTimeout(700);
  assert.equal(await page.locator('.wb-heading strong').textContent(), '第三道题');

  await page.evaluate(() => { window.workbenchFixture.translationError = '翻译服务暂不可用，已保留原文。'; });
  await page.getByRole('button', { name: '中文', exact: true }).click();
  await page.getByText('翻译服务暂不可用，已保留原文。', { exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: '原文', exact: true }).getAttribute('aria-pressed'), 'true');
  assert.ok(await page.locator('.wb-statement').textContent().then(text => text.includes('给出两个整数')));
  await page.evaluate(() => { window.workbenchFixture.translationError = ''; });
  await page.locator('.wb-translation-error').getByRole('button', { name: '重试', exact: true }).click();
  await page.getByText('机器翻译 · Fixture provider', { exact: true }).waitFor();

  await page.evaluate(() => { window.workbenchFixture.problemDelay.B = 10; window.workbenchFixture.officialStatus = 'judging'; window.workbenchFixture.changeProblem('B'); });
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '最长的路径');
  await editor.fill('int main() { return 0; }');
  await editor.press('Control+Enter');
  await page.evaluate(() => { window.workbenchFixture.officialStatus = 'finished'; });
  await page.waitForFunction(() => document.querySelector('.wb-result-summary')?.textContent.includes('AC'));
  await page.waitForFunction(() => window.workbenchFixture.progress.length === 2);
  assert.equal(await page.evaluate(() => window.workbenchFixture.progress.at(-1).summary.accepted), 1);
  await editor.fill('unsaved edit before restoring history');
  await page.getByRole('button', { name: /^记录/ }).click();
  await page.getByRole('button', { name: '载入代码', exact: true }).first().click();
  assert.equal(await page.evaluate(() => window.workbenchFixture.readCode()), 'int main() { return 0; }');
  await page.getByRole('button', { name: '撤销载入代码', exact: true }).click();
  assert.equal(await page.evaluate(() => window.workbenchFixture.readCode()), 'unsaved edit before restoring history');
  await page.evaluate(() => window.workbenchFixture.changeProblem('A'));
  await page.waitForFunction(() => document.querySelector('.wb-heading strong').textContent === '两数之和');

  await page.evaluate(() => window.workbenchFixture.changeContest({ id: 'mock1', status: 'running', slots: [{ id: 'A', letter: 'A' }] }));
  await page.waitForFunction(() => document.querySelector('.wb-letter')?.textContent === 'A' && document.querySelector('.cm-content')?.getAttribute('contenteditable') === 'true');
  assert.equal(await page.getByRole('button', { name: '题解', exact: true }).count(), 0, 'mock never offers solutions while running');
  assert.equal(await page.getByRole('button', { name: '官方提交', exact: true }).count(), 0, 'mock never opens official submission');
  assert.notEqual(await page.evaluate(() => window.workbenchFixture.readCode()), 'reopened A final code', 'mock draft is separate from solo draft');
  await editor.fill('contest draft');
  await editor.press('Control+s');
  await page.waitForFunction(() => window.workbenchFixture.drafts['mock1:A'] === 'contest draft');
  await page.evaluate(() => window.workbenchFixture.changeContest({ id: 'mock1', status: 'finished', slots: [{ id: 'A', letter: 'A' }] }));
  await page.waitForFunction(() => document.querySelector('.cm-content')?.getAttribute('aria-readonly') === 'true');
  assert.equal(await editor.getAttribute('aria-readonly'), 'true');
  assert.equal(await page.getByRole('button', { name: '提交', exact: true }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: '运行样例', exact: true }).isDisabled(), true);

  const overflow = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth > innerWidth,
    body: document.querySelector('.wb-body').scrollWidth > document.querySelector('.wb-body').clientWidth,
  }));
  assert.deepEqual(overflow, { page: false, body: false }, '1050px layout does not overflow');
  await page.screenshot({ path: path.join(root, 'tests', 'screenshots', 'workbench-light.png'), animations: 'disabled' });
  assert.deepEqual(errors, []);
  console.log('Workbench: draft isolation, save ordering, keyboard, honest verdicts, mock locks, layout passed.');
} finally {
  await browser.close();
  await server.close();
}
