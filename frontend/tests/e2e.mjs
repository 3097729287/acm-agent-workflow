import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, rm, realpath } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { chromium } from 'playwright';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const state = await mkdtemp(join(tmpdir(), 'tb-api-e2e-'));
const service = spawn(process.env.TB_PYTHON || 'python', [join(root, 'backend/backend.py'), '--offline', '--port', '0', '--state-dir', state], {
  cwd: root, windowsHide: true,
  env: { ...process.env, TB_STATE_DIR: state, TB_OFFLINE: '1', DSH_HOME: join(state, 'absent'), PYTHONIOENCODING: 'utf-8' },
});
let stderr = '';
service.stderr.on('data', part => { stderr += part; });
let vite, browser, page;
const errors = [];
try {
  const apiUrl = await new Promise((done, fail) => {
    const timer = setTimeout(() => fail(new Error('API startup timed out: ' + stderr)), 30000);
    service.stdout.on('data', part => {
      const match = String(part).match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timer); done(match[0]); }
    });
    service.on('exit', code => { clearTimeout(timer); fail(new Error('API exited ' + code + ': ' + stderr)); });
  });
  process.env.TB_API_URL = apiUrl;
  vite = await createServer({ server: { host: '127.0.0.1', port: 0 } });
  await vite.listen();
  const frontendUrl = `http://127.0.0.1:${vite.httpServer.address().port}`;
  browser = await chromium.launch({ channel: process.env.CI ? undefined : 'msedge', headless: true });
  page = await browser.newPage({ viewport: { width: 1480, height: 920 } });
  page.setDefaultTimeout(30000);
  await page.addInitScript(() => localStorage.setItem('tb.preferences', JSON.stringify({ theme: 'light', fontSize: 15, accent: 'teal' })));
  page.on('pageerror', error => errors.push(error.message));
  const catalog = await (await page.request.get(frontendUrl + '/api/data')).json();
  assert.equal(catalog.rows.length, 607);
  assert.ok(catalog.rows.every(row => row.solutionAvailable));
  const problem = catalog.rows.find(row => row.title === 'Xterfusion');
  const solution = await (await page.request.get(frontendUrl + '/api/solution?id=' + encodeURIComponent(problem.id))).json();
  assert.ok(solution.markdown.length > 4000);
  assert.equal(solution.lectures.length, 1);
  await page.goto(frontendUrl);
  await page.getByRole('heading', { name: '从第一道题开始', exact: true }).waitFor();
  await page.keyboard.press('Control+2');
  await page.getByRole('textbox', { name: '搜索题目', exact: true }).fill('Xterfusion');
  await page.locator('.problem-table .problem-title').first().click();
  await page.getByRole('textbox', { name: 'C++ 代码' }).waitFor();
  const code = '// SQL draft preservation\nint main(){return 0;}\n';
  const editor = page.getByRole('textbox', { name: 'C++ 代码' });
  await editor.fill(code);
  await editor.press('Control+s');
  await page.waitForFunction(() => document.querySelector('.wb-save-state')?.textContent.includes('已保存') || document.body.innerText.includes('草稿已保存'));
  // This write went through the separate frontend's proxy with a real session token.
  const current = await (await page.request.get(frontendUrl + '/api/problem?id=' + encodeURIComponent(problem.id))).json();
  assert.equal(current.draft, code);
  assert.equal(await page.locator('.wb-heading').getByRole('button', { name: '官方提交', exact: true }).count(), 0);
  assert.equal(await page.locator('.wb-run-actions').getByRole('button', { name: '官方提交', exact: true }).count(), 1);
  assert.equal(await page.locator('.wb-run-actions').getByRole('button', { name: '本地提交', exact: true }).count(), 1);
  await page.getByRole('button', { name: '题解', exact: true }).click();
  await page.locator('.reader-panel .markdown').first().waitFor();
  await page.getByText('本题的基础讲解与引用', { exact: true }).waitFor();
  assert.ok(await page.locator('.reader-panel').getByText(/固定步长/).count());
  await editor.fill('#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    return 0;\n}\n');
  await mkdir('tests/screenshots', { recursive: true });
  await page.screenshot({ path: 'tests/screenshots/workbench-real.png', animations: 'disabled' });
  for (const width of [2048, 1050]) {
    await page.setViewportSize({ width, height: width === 1050 ? 760 : 1152 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({ path: `tests/screenshots/workbench-real-${width}.png`, animations: 'disabled' });
  }
  await page.setViewportSize({ width: 1480, height: 920 });
  await page.locator('.nav-item').filter({hasText: '成长与能力'}).click();
  await page.getByRole('heading', {name: '每日任务', exact: true}).waitFor();
  assert.equal(await page.locator('.daily-task').count(), 6);
  assert.equal(await page.locator('.progress-recommendation').count(), 4);
  await page.getByRole('button', {name: /查看其余.*题/}).click();
  assert.ok(await page.locator('.progress-recommendation').count() > 4);
  await page.getByRole('button', {name: '收起推荐'}).click();
  assert.equal(await page.locator('.progress-recommendation').count(), 4);
  const heights = await page.evaluate(() => {
    const left = document.querySelector('.progress-growth-left').getBoundingClientRect();
    const right = document.querySelector('.progress-recommendations').getBoundingClientRect();
    return {left: left.height, right: right.height};
  });
  assert.ok(Math.abs(heights.left - heights.right) < 180, JSON.stringify(heights));
  await page.screenshot({path: 'tests/screenshots/growth-real.png', animations: 'disabled'});
  await page.getByRole('tree', {name: '知识点目录', exact: true}).getByRole('treeitem').first().focus();
  await page.keyboard.press('ArrowRight');
  await page.locator('.tree-line[data-depth="1"]').first().waitFor();
  await page.screenshot({path: 'tests/screenshots/knowledge-real.png', animations: 'disabled'});
  assert.deepEqual(errors, []);
  console.log('End-to-end passed: independent API, 607 SQLite solutions, precise lecture, saved draft through Vite, submit placement and responsive workbench.');
} catch (error) {
  console.error('Browser errors:', errors, '\nAPI stderr:', stderr);
  if (page) {
    console.error('Page:', (await page.locator('body').innerText()).slice(0, 4000));
    await mkdir('tests/screenshots', { recursive: true });
    await page.screenshot({ path: 'tests/screenshots/e2e-failure.png' });
  }
  throw error;
} finally {
  await browser?.close();
  await vite?.close();
  if (service.exitCode === null) {
    const closed = new Promise(done => service.once('exit', done));
    service.kill();
    await closed;
  }
  const actual = await realpath(state), temporaryRoot = await realpath(tmpdir());
  assert.ok(actual.startsWith(temporaryRoot + sep) && basename(actual).startsWith('tb-api-e2e-'));
  await rm(actual, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
}
