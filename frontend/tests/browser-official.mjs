import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const python = process.env.TB_PYTHON || 'C:/Users/lenovo/AppData/Local/Programs/Python/Python313/python.exe';
const server = spawn(python, ['desktop/tests/browser_server.py'], { cwd: root, env: { ...process.env, TB_OFFLINE: '1', PYTHONIOENCODING: 'utf-8' }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
let serverErrors = '';
server.stderr.on('data', c => { serverErrors += c; });
const { port } = await new Promise((resolve, reject) => {
  let text = '';
  server.stdout.on('data', chunk => { text += chunk; if (text.includes('\n')) resolve(JSON.parse(text.split('\n')[0])); });
  server.on('exit', code => reject(new Error('Fixture server exited: ' + code + ' ' + serverErrors)));
});
const base = `http://127.0.0.1:${port}`;
const profile = await mkdtemp(path.join(os.tmpdir(), 'tb-browser-extension-'));
const extension = path.join(root, 'build/browser-extension');
let browser;
const posted = [], cookieChecks = [], errors = [];
let cfSubmitted = false, acSubmitted = false, ncReject = false, luoguLoggedIn = true;
const source = 'int main(){}';
const headers = { 'access-control-allow-origin': 'https://ac.nowcoder.com', 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET, POST, OPTIONS' };
const form = (platform, task = '') => `<select name="${platform === 'AtCoder' ? 'data.TaskScreenName' : 'submittedProblemIndex'}"><option value="${task}">${task}</option></select><select name="${platform === 'AtCoder' ? 'data.LanguageId' : 'programTypeId'}"><option value="2">GNU C++17</option></select><textarea id="sourceCode" name="source"></textarea><button type="submit">提交</button>`;
const row = (platform, submitted) => `<table class="status-frame-datatable"><tr><th>Submission</th><th>Verdict</th></tr>${submitted ? platform === 'Codeforces' ? '<tr><td><a href="/contest/123/submission/1002">1002</a><a href="/contest/123/problem/A">A</a><a href="/profile/fixture">fixture</a></td><td class="submissionVerdictWrapper">Accepted</td></tr>' : '<tr><td><a href="/contests/abc100/submissions/2002">2002</a><a href="/contests/abc100/tasks/abc100_a">A</a></td><td><span class="label">AC</span></td></tr>' : ''}</table>`;
try {
  browser = await chromium.launchPersistentContext(profile, {
    channel: 'msedge', headless: true, ignoreHTTPSErrors: true,
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  const worker = browser.serviceWorkers()[0] || await browser.waitForEvent('serviceworker', { timeout: 15000 });
  assert.ok(worker.url().includes('blgkmkjbdekeoenepgnajpeafofccbjm'));
  browser.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  for (const domain of ['codeforces.com', 'atcoder.jp', 'ac.nowcoder.com', 'www.luogu.com.cn']) {
    await browser.addCookies([{ name: 'fixture_login', value: 'existing-browser-session', domain, path: '/', secure: true, sameSite: 'Lax' }]);
  }
  await browser.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.hostname === '127.0.0.1') return route.continue();
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    const json = value => route.fulfill({ contentType: 'application/json', headers, body: JSON.stringify(value) });
    const html = body => route.fulfill({ contentType: 'text/html; charset=utf-8', body: '<!doctype html><html><head><meta charset="utf-8"><title>Fixture official page</title></head><body>' + body + '</body></html>' });
    if (request.method() === 'POST') {
      posted.push(url.hostname + url.pathname);
      if (url.hostname !== 'victorinox.nowcoder.com') cookieChecks.push((await request.allHeaders()).cookie?.includes('fixture_login=existing-browser-session'));
      if (url.hostname === 'codeforces.com') { cfSubmitted = true; assert.equal(new URLSearchParams(request.postData()).get('source'), source); return route.fulfill({ status: 302, headers: { location: '/contest/123/my' }, body: '' }); }
      if (url.hostname === 'atcoder.jp') { acSubmitted = true; assert.ok(request.postData().includes('int main()')); return json({ ok: true }); }
      if (url.hostname === 'victorinox.nowcoder.com') {
        assert.equal(JSON.parse(request.postData()).content, source);
        return json(ncReject ? { code: 1125, msg: '验证码错误' } : { code: 0, data: 3002 });
      }
      if (url.hostname === 'www.luogu.com.cn') { assert.equal(JSON.parse(request.postData()).code, source); return json({ rid: 4002 }); }
      return route.abort();
    }
    if (url.hostname === 'codeforces.com') {
      if (url.pathname.endsWith('/my')) return html('<div id="header"><a href="/profile/fixture">fixture</a></div>' + row('Codeforces', cfSubmitted));
      if (url.pathname.endsWith('/submit')) return html('<div id="header"><a href="/profile/fixture">fixture</a></div><form method="post" action="/contest/123/submit">' + form('Codeforces', 'A') + '</form>');
    }
    if (url.hostname === 'atcoder.jp') {
      if (url.pathname.endsWith('/submissions/me')) return html(row('AtCoder', acSubmitted));
      if (url.pathname.endsWith('/submit')) return html('<form>' + form('AtCoder', 'abc100_a') + '</form><script>document.querySelector("form").onsubmit=e=>{e.preventDefault();fetch(location.pathname,{method:"POST",body:document.querySelector("textarea").value})}</script>');
    }
    if (url.hostname === 'ac.nowcoder.com') return html(`<select name="language"><option value="2">C++（clang++18）</option></select><div class="CodeMirror">原站编辑器</div><div style="display:none"><button>保存并提交</button></div><button class="btn-submit">保存并提交</button><script>
      window.pageInfo={contestId:'127263',questionId:'11604979'};window.globalInfo={ownerId:12345};
      const cachedFetch=window.fetch;let code='';document.querySelector('.CodeMirror').CodeMirror={setValue(value){code=value},getValue(){return code}};
      document.querySelector('.btn-submit').onclick=()=>cachedFetch('https://victorinox.nowcoder.com/api/service/judge/submit',{method:'POST',body:JSON.stringify({questionId:'11604979',content:code,submitType:1,userId:12345,appId:6,tagId:4,token:'page-only-fixture'})});
    </script>`);
    if (url.hostname === 'victorinox.nowcoder.com') return json({ code: 0, data: { status: 5 } });
    if (url.hostname === 'www.luogu.com.cn') {
      if (url.pathname.startsWith('/record/')) return json({ data: { record: { id: 4002, problem: { pid: 'P1001' }, user: { uid: 12345 }, status: 12 } } });
      if (url.pathname.startsWith('/auth/login')) return html('<input type="password">');
      return html(`<script id="lentille-context" type="application/json">${JSON.stringify({ user: luoguLoggedIn ? { uid: 12345 } : null })}</script><form>${form('洛谷')}</form><script>
        document.querySelector('form').onsubmit=e=>{e.preventDefault();fetch('/fe/api/problem/submit/P1001',{method:'POST',body:JSON.stringify({code:document.querySelector('textarea').value,lang:2})})};
      </script>`);
    }
    return route.abort();
  });
  async function submit(key, url) {
    const result = await (await fetch(base + '/fixture/create?' + new URLSearchParams({ key, url }))).json();
    assert.ok(result.connect, JSON.stringify(result));
    const page = await browser.newPage();
    await page.goto(result.connect);
    return page;
  }
  async function state(key, status, timeout = 25000) {
    const until = Date.now() + timeout;
    let value;
    while (Date.now() < until) {
      value = (await (await fetch(base + '/fixture/status')).json())[key];
      if (value?.status === status) return value;
      if (['error', 'unconfirmed'].includes(value?.status)) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    throw new Error(key + ': expected ' + status + ', got ' + JSON.stringify(value));
  }
  for (const [key, url] of [
    ['cf', 'https://codeforces.com/contest/123/problem/A'],
    ['atcoder', 'https://atcoder.jp/contests/abc100/tasks/abc100_a'],
    ['nowcoder', 'https://ac.nowcoder.com/acm/contest/127263/B'],
    ['luogu', 'https://www.luogu.com.cn/problem/P1001'],
  ]) {
    const page = await submit(key, url);
    const result = await state(key, 'finished');
    assert.equal(result.verdict, 'AC');
    assert.equal(new URL(page.url()).protocol, 'https:');
    assert.ok((await page.context().cookies(url)).some(cookie => cookie.name === 'fixture_login'));
  }
  assert.equal(posted.length, 4, 'each platform issues exactly one native submission');
  assert.ok(cookieChecks.every(Boolean), 'submissions reuse cookies already in the ordinary browser');
  assert.equal((await (await fetch(base + '/fixture/saved')).json()).length, 4, 'all four receipts reach desktop persistence callback');
  ncReject = true;
  await submit('captcha', 'https://ac.nowcoder.com/acm/contest/127263/B');
  await state('captcha', 'needs_verification');
  assert.equal((await (await fetch(base + '/fixture/saved')).json()).length, 4);
  luoguLoggedIn = false;
  const login = await submit('login', 'https://www.luogu.com.cn/problem/P1001');
  await state('login', 'needs_login');
  const before = posted.length;
  luoguLoggedIn = true;
  await login.reload();
  await state('login', 'ready');
  assert.equal(posted.length, before, 'logging in does not auto-submit');
  await submit('login', 'https://www.luogu.com.cn/problem/P1001');
  await state('login', 'finished');
  assert.equal(posted.length, before + 1);
  assert.deepEqual(errors, []);
  console.log('Browser extension: four platforms, existing browser cookies, early cached-fetch observer, native forms, receipts, captcha, login retry and no duplicate submits passed.');
} finally {
  if (browser) await browser.close();
  server.kill();
  assert.equal(path.dirname(path.resolve(profile)), path.resolve(os.tmpdir()));
  assert.ok(path.basename(profile).startsWith('tb-browser-extension-'));
  await rm(profile, { recursive: true, force: true });
}
