import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { EditorView } from '@codemirror/view';
import Workbench from '../src/Workbench.jsx';
import 'katex/dist/katex.min.css';

const style = document.createElement('style');
style.textContent = `:root {font-family:"Segoe UI","Microsoft YaHei UI",sans-serif;--bg:#f5f6f8;--panel:#fff;--panel-2:#f7f8fa;--text:#262b38;--muted:#657087;--line:#dfe4eb;--accent:#137e6c;--accent-soft:#137e6c14;--success:#137e6c;--danger:#be394c;--warning:#a16419}*{box-sizing:border-box}body{margin:0;padding:18px;background:var(--bg)}#root{height:calc(100dvh - 36px);min-height:500px}.fixture{height:100%}`;
document.head.append(style);

const fixture = window.workbenchFixture = {
  drafts: {}, calls: [], submissions: [], progress: [], problemDelay: {}, draftDelay: 15,
  nextVerdict: 'SAMPLE_PASS', nextRunVerdict: 'SAMPLE_PASS', exitCount: 0, solutionCount: 0, nextCount: 0,
  officialStatus: 'needs_login', officialSessions: {}, translationError: '', translationDelay: 10,
};
const currentEditor = () => EditorView.findFromDOM(document.querySelector('.cm-content'));
fixture.readCode = () => currentEditor().state.doc.toString();
fixture.selectCode = (start, end = start) => currentEditor().dispatch({ selection: { anchor: start, head: end } });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const key = body => `${body.contestId || 'solo'}:${body.id}`;
const problem = id => ({
  id, title: id === 'A' ? '两数之和' : id === 'B' ? '最长的路径' : '第三道题',
  markdown: '# 输入与输出\n\n给出两个整数 $a$ 和 $b$，输出 $a+b$。\n\n## 输入\n\n一行两个整数。\n\n## 输出\n\n它们的和。\n\n## 示例\n\n```text\n1 2\n```\n',
  url: 'https://example.com/problem', samples: [{ name: '样例 1', input: '1 2\n', output: '3\n' }, { name: '样例 2', input: '4 5\n', output: '9\n' }],
  limits: { timeMs: 2000, memoryMb: 256 }, judge: { scope: id === 'B' ? 'local' : 'samples', label: id === 'B' ? '本地验证' : '样例评测', cases: id === 'B' ? 20 : 1 },
  locked: false, statementAvailable: true,
});
async function api(path, body) {
  fixture.calls.push({ path, body, at: Date.now() });
  const url = new URL('http://fixture/' + path);
  if (path === 'problem/translate') {
    await sleep(fixture.translationDelay);
    if (fixture.translationError) throw new Error(fixture.translationError);
    return { id: body.id, markdown: `## 题目描述\n\n真实翻译服务模拟：${body.id} 的中文题面，计算 $a+b$。`, sourceLanguage: 'en', targetLanguage: 'zh-CN', provider: 'Fixture provider', cached: false };
  }
  if (path === 'official/open' || path === 'official/submit') {
    const sessionId = `official-${Object.keys(fixture.officialSessions).length + 1}`;
    fixture.officialSessions[sessionId] = { id: body.id, status: 'loading' };
    return { sessionId, status: 'loading', platform: 'AtCoder', message: '正在载入原站面板。' };
  }
  if (url.pathname === '/official/status') {
    const sessionId = url.searchParams.get('sessionId'), session = fixture.officialSessions[sessionId];
    const status = session.status === 'closed' ? 'closed' : fixture.officialStatus;
    return { sessionId, status, message: ({ needs_login: '请在原站面板登录。', ready: '原站已就绪，可以提交。', closed: '已关闭原站面板，返回训练。' })[status] || '等待原站回执。' };
  }
  if (path === 'official/close') {
    fixture.officialSessions[body.sessionId].status = 'closed';
    return { sessionId: body.sessionId, status: 'closed', message: '已关闭原站面板，返回训练。' };
  }
  if (url.pathname === '/problem') {
    const id = url.searchParams.get('id');
    await sleep(fixture.problemDelay[id] || 10);
    const context = { id, contestId: url.searchParams.get('contestId') };
    return { ...problem(id), draft: fixture.drafts[key(context)] || '', submissions: fixture.submissions.filter(row => row.problemId === id && row.contestId === context.contestId) };
  }
  if (path === 'draft') {
    await sleep(fixture.draftDelay);
    fixture.drafts[key(body)] = body.code;
    return { savedAt: new Date().toISOString() };
  }
  if (path === 'submissions' && body) {
    const row = { id: `s${fixture.submissions.length + 1}`, problemId: body.id, contestId: body.contestId || null, mode: body.mode,
      verdict: 'QUEUED', scope: problem(body.id).judge.scope, code: body.code, submittedAt: new Date().toISOString(), finishedAt: null,
      timeMs: null, memoryKb: null, passed: 0, total: 0, output: '', stderr: '', message: '', sampleRun: body.sampleRun, input: body.input,
      target: body.mode === 'run' ? body.sampleRun ? fixture.nextRunVerdict : 'RUN_OK' : fixture.nextVerdict };
    fixture.submissions.push(row);
    return { submission: { ...row } };
  }
  if (url.pathname === '/submission') {
    await sleep(35);
    const row = fixture.submissions.find(row => row.id === url.searchParams.get('id'));
    Object.assign(row, { verdict: row.target, finishedAt: new Date().toISOString(), timeMs: 12, memoryKb: 2560, passed: row.target === 'WA' ? 0 : row.sampleRun ? 2 : 1, total: row.sampleRun ? 2 : 1, output: '3\n',
      message: row.mode === 'run' ? '运行完成' : row.target === 'SAMPLE_PASS' ? '已通过公开样例。' : row.target === 'AC' ? '已通过本地验证用例。' : '输出与预期不同。' });
    if (row.mode === 'run') row.caseResults = row.sampleRun ? problem(row.problemId).samples.map((item, index) => ({ name: item.name, input: item.input, expected: item.output,
      actual: row.target === 'WA' && index === 1 ? '8\r\n' : item.output.replaceAll('\n', '\r\n'), verdict: row.target === 'WA' && index === 1 ? 'WA' : 'SAMPLE_PASS', timeMs: 12, exitCode: 0 }))
      : [{ name: '自定义输入', input: row.input, expected: null, actual: '3\n', verdict: 'RUN_OK', timeMs: 12, exitCode: 0 }];
    return { submission: { ...row }, workspace: { summary: { total: 1, accepted: row.target === 'AC' ? 1 : 0 } } };
  }
  if (path === 'workspace') return { summary: { total: 1, accepted: 0 } };
  throw new Error('Unknown fixture call ' + path);
}
function Fixture() {
  const [id, setId] = useState('A');
  const [contest, setContest] = useState(null);
  fixture.changeProblem = setId;
  fixture.changeContest = setContest;
  return <div className="fixture"><Workbench problemId={id} contest={contest} api={api}
    onProgress={workspace => fixture.progress.push(workspace)} onExit={() => fixture.exitCount++}
    onSolution={() => fixture.solutionCount++} onNext={() => fixture.nextCount++} /></div>;
}
createRoot(document.getElementById('root')).render(<React.StrictMode><Fixture /></React.StrictMode>);
