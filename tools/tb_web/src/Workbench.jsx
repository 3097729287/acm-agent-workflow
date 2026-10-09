import { memo, useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import {
  ArrowLeft, ArrowRight, BookOpen, Check, ChevronDown, ChevronUp,
  Code2, Copy, ExternalLink, FileCode2, History, LoaderCircle,
  PanelLeft, PanelsTopLeft, Play, RotateCcw, Save, Send, Terminal,
} from 'lucide-react';
import { normalizeMarkdown } from './normalizeMarkdown.js';
import { normalizeStatement } from './normalizeStatement.js';
import CodeEditor from './CodeEditor.jsx';
import './Workbench.css';

const TEMPLATE = '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    \n    return 0;\n}\n';
const MAX_BYTES = 64 * 1024;
const byteLength = value => new TextEncoder().encode(value).byteLength;
const VERDICTS = {
  QUEUED: '等待评测', RUNNING: '正在评测', AC: '本地 AC', SAMPLE_PASS: '样例通过', RUN_OK: '运行完成（未校验）',
  WA: '答案错误', TLE: '超时', MLE: '内存超限', RE: '运行错误',
  CE: '编译错误', OLE: '输出超限', ERROR: '评测不可用',
};
const OFFICIAL_STATES = { loading: '载入原站', needs_login: '需要登录', needs_verification: '需要验证', ready: '等待提交', submitted: '已提交到原站', judging: '官方评测中', finished: '官方评测完成', error: '原站面板异常', closed: '已返回训练' };
const OFFICIAL_TERMINAL = new Set(['finished', 'error', 'closed']);

// Serialize saves across mounts as well as edits. An older request must never
// finish after a newer draft for the same problem and overwrite it on disk.
const draftQueues = new Map();
const latestDraftRevision = new Map();
let draftRevision = 0;
function touchDraft(record) {
  record.revision = ++draftRevision;
  latestDraftRevision.set(record.key, record.revision);
}
function queuedSave(key, body, api, revision) {
  const previous = draftQueues.get(key) || Promise.resolve();
  const request = previous.catch(() => undefined).then(() => {
    // A retired editor may still be draining its save loop after this problem
    // has been reopened. Its queued snapshot must not overwrite newer edits.
    if ((latestDraftRevision.get(key) || 0) > revision) return { skipped: true };
    return api('draft', body);
  });
  draftQueues.set(key, request);
  const clear = () => { if (draftQueues.get(key) === request) draftQueues.delete(key); };
  request.then(clear, clear);
  return request;
}
function draftKey(id, contestId) {
  return `tb.draft.v2.${encodeURIComponent(contestId || 'solo')}.${encodeURIComponent(id)}`;
}
function readDraft(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return value && typeof value.code === 'string' ? value : null;
  } catch { return null; }
}
function retainDraft(record, dirty = true) {
  try {
    localStorage.setItem(record.key, JSON.stringify({
      code: record.code, dirty, owner: record.owner, version: record.version,
      modifiedAt: Date.now(),
    }));
    record.retained = true;
    return true;
  } catch {
    record.retained = false;
    return false;
  }
}
function markDraftSaved(record, version) {
  const value = readDraft(record.key);
  if (value?.owner === record.owner && value.version === version) retainDraft(record, false);
}
function submissionPending(submission) {
  return !submission.finishedAt && ['QUEUED', 'RUNNING'].includes(submission.verdict);
}
function mergeSubmission(rows, submission) {
  return [submission, ...rows.filter(row => row.id !== submission.id)]
    .sort((a, b) => String(b.submittedAt || '').localeCompare(String(a.submittedAt || '')));
}
function verdictText(submission) {
  if (!submission) return '尚未运行';
  return VERDICTS[submission.verdict] || submission.verdict;
}
function dateText(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}
function elapsedText(timeMs) {
  if (timeMs == null) return null;
  return timeMs < 1000 ? `${Math.round(timeMs)} ms` : `${(timeMs / 1000).toFixed(2)} s`;
}
function queryPath(path, id, contestId) {
  return `${path}?id=${encodeURIComponent(id)}${contestId ? `&contestId=${encodeURIComponent(contestId)}` : ''}`;
}
function requestBody(record, extra = {}) {
  return { id: record.id, ...(record.contestId ? { contestId: record.contestId } : {}), ...extra };
}

function Verdict({ submission }) {
  const pending = submission && submissionPending(submission);
  return <span className={`wb-verdict wb-verdict-${String(submission?.verdict || 'none').toLowerCase()}`}>
    {pending && <LoaderCircle size={13} className="wb-spinner" aria-hidden="true" />}
    {submission?.verdict === 'AC' && <Check size={13} aria-hidden="true" />}
    {verdictText(submission)}
  </span>;
}

// The statement can contain substantial math. Editing code or moving the
// caret must not parse and typeset the same document again.
const StatementMarkdown = memo(function StatementMarkdown({ markdown, samples, title }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false, trust: false }]]}
    components={{ a: ({ node, ...props }) => <a {...props} target="_blank" rel="noreferrer" /> }}>{normalizeMarkdown(normalizeStatement(markdown, samples, title))}</ReactMarkdown>;
});

function CaseResults({ cases }) {
  const lines = value => String(value ?? '').replace(/\r\n?/g, '\n').replace(/\n$/, '').split('\n');
  return <div className="wb-case-results" aria-label="逐例运行结果">{cases.map((item, index) => {
    const known = item.expected != null, expected = lines(item.expected), actual = lines(item.actual);
    const mismatch = known && item.verdict === 'WA';
    const failed = !['AC', 'SAMPLE_PASS', 'RUN_OK'].includes(item.verdict);
    const name = item.name || (known ? `样例 ${index + 1}` : '自定义输入');
    const renderOutput = (values, other, label) => <pre tabIndex={0} aria-label={`${name} ${label}`}>{Array.from({ length: mismatch ? Math.max(values.length, other.length) : values.length }, (_, line) => {
      const differs = mismatch && values[line] !== other[line];
      return <span className={`wb-case-line${differs ? ' wb-case-mismatch' : ''}`} key={line}><i aria-hidden="true">{line + 1}</i><span>{values[line] ?? '（无此行）'}{values[line] === '' && values.length === 1 ? '（空输出）' : ''}</span>{differs && <small>不同</small>}</span>;
    })}</pre>;
    return <details className="wb-case" key={`${index}-${name}`} open={index === 0 || failed}>
      <summary><strong>{name}</strong><Verdict submission={{ verdict: item.verdict === 'AC' ? 'SAMPLE_PASS' : item.verdict, finishedAt: true, mode: 'run' }} />{item.timeMs != null && <span>{elapsedText(item.timeMs)}</span>}</summary>
      {item.message && <p className="wb-result-message">{item.message}</p>}
      <div className={`wb-case-outputs${known ? '' : ' wb-case-custom'}`}>
        {known ? <div><span>预期输出</span>{renderOutput(expected, actual, '预期输出')}</div> : <p className="wb-result-message">自定义输入没有预期答案，仅检查程序是否正常运行。</p>}
        <div><span>实际输出</span>{renderOutput(actual, expected, '实际输出')}</div>
      </div>
      <details className="wb-case-input"><summary>查看输入</summary><pre tabIndex={0}>{item.input || '（空输入）'}</pre></details>
      {item.exitCode != null && item.exitCode !== 0 && <p className="wb-result-message">退出码：{item.exitCode}</p>}
    </details>;
  })}</div>;
}

export default function Workbench({ problemId, contest = null, api, onProgress, onExit, onSolution, onNext }) {
  const contestId = contest?.id || null;
  const runningContest = contest?.status === 'running';
  const endedContest = Boolean(contest && !runningContest);
  const contextKey = draftKey(problemId, contestId);
  const apiRef = useRef(api);
  const callbacks = useRef({ onProgress, onExit, onSolution, onNext });
  apiRef.current = api;
  callbacks.current = { onProgress, onExit, onSolution, onNext };

  const activeRecord = useRef(null);
  const sectionRef = useRef(null);
  const statementRef = useRef(null);
  const editorRef = useRef(null);
  const consoleButtonRef = useRef(null);
  const fileRef = useRef(null);
  const undoReplace = useRef(null);
  const officialRef = useRef(null);
  const officialReported = useRef(new Set());
  const [problem, setProblem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [code, setCode] = useState('');
  const [saveState, setSaveState] = useState({ kind: 'automatic' });
  const [pane, setPane] = useState('both');
  const [cursor, setCursor] = useState({ line: 1, column: 1 });
  const [submissions, setSubmissions] = useState([]);
  const [resultId, setResultId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState('');
  const [pollError, setPollError] = useState('');
  const [consoleOpen, setConsoleOpen] = useState(false);
  const [consoleTab, setConsoleTab] = useState('input');
  const [sample, setSample] = useState('custom');
  const [input, setInput] = useState('');
  const [restoreAvailable, setRestoreAvailable] = useState(false);
  const [outputTab, setOutputTab] = useState('output');
  const [copied, setCopied] = useState(false);
  const [openingOfficial, setOpeningOfficial] = useState(false);
  const [officialSession, setOfficialSession] = useState(null);
  const [officialPollError, setOfficialPollError] = useState('');
  const [language, setLanguage] = useState('original');
  const [translation, setTranslation] = useState(null);
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationError, setTranslationError] = useState('');

  const isActive = record => activeRecord.current === record;
  const saveRecord = useCallback(record => {
    if (!record?.loaded || record.closed || record.version <= record.savedVersion) return Promise.resolve(true);
    if (byteLength(record.code) > MAX_BYTES) {
      if (isActive(record)) setSaveState({ kind: 'error', retained: record.retained, message: '代码超过 64 KiB，请缩短后保存。' });
      return Promise.resolve(false);
    }
    if (record.saving) return record.saving;
    record.saving = (async () => {
      while (record.version > record.savedVersion && !record.closed) {
        const version = record.version;
        const snapshot = record.code;
        const revision = record.revision;
        if (byteLength(snapshot) > MAX_BYTES) {
          if (isActive(record)) setSaveState({ kind: 'error', retained: record.retained, message: '代码超过 64 KiB，请缩短后保存。' });
          return false;
        }
        if (isActive(record)) setSaveState({ kind: 'saving' });
        try {
          const answer = await queuedSave(record.key, requestBody(record, { code: snapshot }), apiRef.current, revision);
          record.savedVersion = version;
          if (!answer.skipped) markDraftSaved(record, version);
          if (isActive(record)) setSaveState({
            kind: record.version > version ? 'unsaved' : 'saved', savedAt: answer.savedAt,
          });
        } catch (error) {
          if (isActive(record)) setSaveState({ kind: 'error', retained: record.retained, message: error.message || '草稿保存失败' });
          return false;
        }
      }
      return true;
    })().finally(() => { record.saving = null; });
    return record.saving;
  }, []);

  useEffect(() => {
    let alive = true;
    const record = {
      key: contextKey, id: problemId, contestId, owner: `${Date.now()}-${Math.random()}`,
      code: '', version: 0, savedVersion: 0, loaded: false, closed: endedContest,
      timer: null, saving: null,
    };
    activeRecord.current = record;
    undoReplace.current = null;
    setProblem(null);
    setLoading(true);
    setLoadError('');
    setCode('');
    setSubmissions([]);
    setResultId(null);
    setCreating(false);
    setActionError('');
    setPollError('');
    setSaveState({ kind: 'automatic' });
    setCursor({ line: 1, column: 1 });
    setRestoreAvailable(false);
    setConsoleOpen(false);
    setConsoleTab('input');
    setOutputTab('output');
    setCopied(false);
    setOpeningOfficial(false);
    setOfficialSession(null);
    setOfficialPollError('');
    setLanguage('original');
    setTranslation(null);
    setTranslationBusy(false);
    setTranslationError('');
    setSample('custom');
    setInput('');
    (async () => {
      try {
        const answer = await apiRef.current(queryPath('problem', problemId, contestId));
        if (!alive || !isActive(record)) return;
        const backup = readDraft(record.key);
        record.locked = Boolean(answer.locked && !contestId);
        record.closed = record.closed || record.locked;
        record.code = backup?.dirty ? backup.code : (answer.draft || TEMPLATE);
        record.loaded = true;
        record.revision = latestDraftRevision.get(record.key) || 0;
        if (backup?.dirty) {
          record.version = 1;
          touchDraft(record);
        }
        setCode(record.code);
        setProblem(answer);
        const history = (answer.submissions || []).slice().sort((a, b) => String(b.submittedAt || '').localeCompare(String(a.submittedAt || '')));
        setSubmissions(history);
        setResultId(history[0]?.id || null);
        const first = answer.samples?.[0];
        setSample(first ? 'samples' : 'custom');
        setInput('');
        setLoading(false);
        setSaveState({ kind: record.closed ? 'closed' : backup?.dirty ? 'unsaved' : answer.draft ? 'saved' : 'automatic' });
        if (backup?.dirty && !record.closed) record.timer = setTimeout(() => saveRecord(record), 850);
        requestAnimationFrame(() => {
          if (!isActive(record)) return;
          if (statementRef.current) statementRef.current.scrollTop = 0;
          if (editorRef.current) editorRef.current.scrollTop = 0;
          if (document.activeElement === document.body) statementRef.current?.focus();
        });
      } catch (error) {
        if (alive && isActive(record)) {
          setLoading(false);
          setLoadError(error.message || '题目载入失败');
        }
      }
    })();
    return () => {
      alive = false;
      clearTimeout(record.timer);
      saveRecord(record);
      if (officialRef.current?.record === record) {
        const session = officialRef.current;
        officialRef.current = null;
        apiRef.current('official/close', { sessionId: session.id }).catch(() => undefined);
      }
      if (isActive(record)) activeRecord.current = null;
    };
    // api and callback references may change with workspace polling. A draft
    // belongs to its identity, so those renders must not reload the editor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextKey, problemId, contestId, loadAttempt, saveRecord]);

  useEffect(() => {
    const record = activeRecord.current;
    if (!record || record.key !== contextKey) return;
    record.closed = endedContest || Boolean(record.locked);
    if (record.closed) {
      clearTimeout(record.timer);
      setSaveState({ kind: 'closed' });
    }
  }, [endedContest, contextKey]);

  const pending = submissions.find(submissionPending) || null;
  const result = submissions.find(row => row.id === resultId) || submissions[0] || null;
  const sidePracticeLocked = Boolean(problem?.locked && !runningContest);
  const unavailable = loading || !problem || endedContest || sidePracticeLocked || activeRecord.current?.key !== contextKey;
  const busy = creating || Boolean(pending);
  const samples = problem?.samples || [];
  const slot = contest?.slots?.find(row => row.id === problemId);

  const announceCompletion = useCallback(async answer => {
    const submission = answer.submission;
    if (!submission?.finishedAt || submission.mode !== 'submit') return;
    try {
      const workspace = answer.workspace || await apiRef.current('workspace');
      callbacks.current.onProgress?.(workspace);
    } catch { /* The parent also refreshes the workspace; keep the verdict visible. */ }
  }, []);

  useEffect(() => {
    if (!pending) return;
    let alive = true;
    let timer;
    const record = activeRecord.current;
    const poll = async () => {
      try {
        const answer = await apiRef.current(`submission?id=${encodeURIComponent(pending.id)}`);
        if (!alive || !isActive(record)) return;
        setPollError('');
        setSubmissions(rows => mergeSubmission(rows, answer.submission));
        if (answer.submission.finishedAt) {
          await announceCompletion(answer);
        } else timer = setTimeout(poll, 650);
      } catch (error) {
        if (alive && isActive(record)) {
          setPollError(error.message || '暂时无法取得评测结果，正在重试');
          timer = setTimeout(poll, 1800);
        }
      }
    };
    timer = setTimeout(poll, 200);
    return () => { alive = false; clearTimeout(timer); };
  }, [pending?.id, contextKey, announceCompletion]);

  const announceOfficialCompletion = useCallback(async (session, record) => {
    if (session.status !== 'finished' || !session.verdict || !session.submissionId || officialReported.current.has(session.sessionId)) return;
    officialReported.current.add(session.sessionId);
    try {
      const workspace = await apiRef.current('workspace');
      if (isActive(record)) callbacks.current.onProgress?.(workspace);
    } catch { /* Keep the genuine official receipt visible if a refresh fails. */ }
  }, []);

  useEffect(() => {
    if (!officialSession?.sessionId || OFFICIAL_TERMINAL.has(officialSession.status)) return;
    let alive = true, timer;
    const record = activeRecord.current, sessionId = officialSession.sessionId;
    const poll = async () => {
      try {
        const answer = await apiRef.current(`official/status?sessionId=${encodeURIComponent(sessionId)}`);
        if (!alive || !isActive(record) || officialRef.current?.id !== sessionId) return;
        setOfficialSession({ ...answer, sessionId });
        setOfficialPollError('');
        await announceOfficialCompletion({ ...answer, sessionId }, record);
        if (!OFFICIAL_TERMINAL.has(answer.status)) timer = setTimeout(poll, ['needs_login', 'needs_verification', 'ready'].includes(answer.status) ? 2200 : 900);
      } catch (error) {
        if (alive && isActive(record)) {
          setOfficialPollError(error.message || '暂时无法读取原站状态，正在重试。');
          timer = setTimeout(poll, 2500);
        }
      }
    };
    timer = setTimeout(poll, 450);
    return () => { alive = false; clearTimeout(timer); };
  }, [officialSession?.sessionId, contextKey, announceOfficialCompletion]);

  const updateCode = useCallback(value => {
    const record = activeRecord.current;
    if (!record?.loaded || record.closed) return;
    record.code = value;
    record.version += 1;
    touchDraft(record);
    retainDraft(record);
    setCode(value);
    setSaveState({ kind: 'unsaved' });
    clearTimeout(record.timer);
    record.timer = setTimeout(() => saveRecord(record), 850);
  }, [saveRecord]);

  const manualSave = () => {
    const record = activeRecord.current;
    if (!record?.loaded || record.closed || sidePracticeLocked) return;
    if (record.version <= record.savedVersion) {
      record.version += 1;
      touchDraft(record);
      retainDraft(record);
    }
    clearTimeout(record.timer);
    saveRecord(record);
  };
  const execute = async mode => {
    const record = activeRecord.current;
    if (!record?.loaded || unavailable || busy) return;
    if (!record.code.trim()) {
      setActionError('先写入 C++ 代码，再运行或提交。');
      editorRef.current?.focus();
      return;
    }
    if (byteLength(record.code) > MAX_BYTES || (mode === 'run' && sample === 'custom' && byteLength(input) > MAX_BYTES)) {
      setActionError(byteLength(record.code) > MAX_BYTES ? '代码超过 64 KiB，请缩短后再提交。' : '标准输入超过 64 KiB，请缩短测试数据。');
      return;
    }
    setCreating(true);
    setActionError('');
    setConsoleOpen(true);
    setConsoleTab('result');
    setOutputTab('output');
    clearTimeout(record.timer);
    saveRecord(record);
    try {
      const answer = await apiRef.current('submissions', requestBody(record, {
        code: record.code, mode, ...(mode === 'run' ? { input: sample === 'custom' ? input : '', sampleRun: sample !== 'custom' } : {}),
      }));
      if (!isActive(record)) return;
      setSubmissions(rows => mergeSubmission(rows, answer.submission));
      setResultId(answer.submission.id);
      await announceCompletion(answer);
    } catch (error) {
      if (isActive(record)) setActionError(error.message || '未能开始评测，请重试。');
    } finally {
      if (isActive(record)) setCreating(false);
    }
  };
  const focusPane = next => {
    setPane(next);
    requestAnimationFrame(() => (next === 'statement' ? statementRef.current : editorRef.current)?.focus());
  };
  const openOfficial = async (path = 'official/submit') => {
    const record = activeRecord.current;
    if (!record?.loaded || unavailable || runningContest || sidePracticeLocked || record.officialBusy) return;
    if (!record.code.trim() || byteLength(record.code) > MAX_BYTES) {
      setActionError(!record.code.trim() ? '先写入代码，再提交到原站。' : '代码超过 64 KiB，请缩短后再提交。');
      return;
    }
    record.officialBusy = true;
    setOpeningOfficial(true); setActionError(''); setOfficialPollError('');
    saveRecord(record);
    try {
      const answer = await apiRef.current(path, requestBody(record, { code: record.code }));
      if (!answer.sessionId) throw new Error('原站面板未返回会话，请重试。');
      if (!isActive(record)) {
        apiRef.current('official/close', { sessionId: answer.sessionId }).catch(() => undefined);
        return;
      }
      officialRef.current = { id: answer.sessionId, record };
      setOfficialSession(answer);
      await announceOfficialCompletion(answer, record);
    } catch (error) {
      if (isActive(record)) setActionError(error.message || '暂时无法提交到原站，请稍后重试。');
    } finally { record.officialBusy = false; if (isActive(record)) setOpeningOfficial(false); }
  };
  const closeOfficial = async () => {
    const session = officialRef.current;
    if (!session || openingOfficial) return;
    setOpeningOfficial(true);
    try {
      const answer = await apiRef.current('official/close', { sessionId: session.id });
      if (isActive(session.record) && officialRef.current?.id === session.id) {
        officialRef.current = null;
        setOfficialSession({ ...answer, sessionId: session.id, status: 'closed' });
        setOfficialPollError('');
        editorRef.current?.focus();
      }
    } catch (error) { if (isActive(session.record)) setOfficialPollError(error.message || '暂时无法关闭原站面板。'); }
    finally { if (isActive(session.record)) setOpeningOfficial(false); }
  };
  const translateStatement = async () => {
    const record = activeRecord.current;
    if (!record?.loaded || loading || !problem?.markdown) return;
    setLanguage('zh');
    if (translation || record.translationBusy) return;
    record.translationBusy = true;
    setTranslationBusy(true); setTranslationError('');
    try {
      const answer = await apiRef.current('problem/translate', requestBody(record));
      if (!isActive(record)) return;
      if (!answer.markdown || answer.targetLanguage !== 'zh-CN') throw new Error('翻译服务未返回中文题面，已保留原文。');
      setTranslation(answer);
    } catch (error) {
      if (isActive(record)) { setTranslationError(error.message || '暂时无法翻译，已保留原文。'); setLanguage('original'); }
    } finally { record.translationBusy = false; if (isActive(record)) setTranslationBusy(false); }
  };
  const editorCommand = command => {
    if (command === 'official') openOfficial();
    else if (command === 'submit' || command === 'run') execute(command);
    else if (command === 'save') manualSave();
    else if (command === 'pane-0') setPane('both');
    else if (command === 'pane-1') focusPane('statement');
    else if (command === 'pane-2') focusPane('code');
  };
  const handleKeys = event => {
    if (event.defaultPrevented || event.nativeEvent.isComposing) return;
    const command = (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey;
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && !event.altKey && event.key === 'Enter') {
      event.preventDefault(); event.stopPropagation(); openOfficial();
    } else if (command && event.key === 'Enter') {
      event.preventDefault(); event.stopPropagation(); execute('submit');
    } else if (command && event.key.toLowerCase() === 'r') {
      event.preventDefault(); event.stopPropagation(); execute('run');
    } else if (command && event.key.toLowerCase() === 's') {
      event.preventDefault(); event.stopPropagation(); manualSave();
    } else if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && ['0', '1', '2'].includes(event.key)) {
      event.preventDefault(); event.stopPropagation();
      if (event.key === '0') setPane('both');
      else focusPane(event.key === '1' ? 'statement' : 'code');
    }
  };
  const loadOwnCode = value => {
    if (unavailable || typeof value !== 'string') return;
    undoReplace.current = activeRecord.current.code;
    setRestoreAvailable(true);
    updateCode(value);
    if (pane === 'statement') setPane('both');
    requestAnimationFrame(() => editorRef.current?.focus());
  };
  const importCode = async event => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setActionError('请选择不超过 64 KiB 的代码文件。');
      return;
    }
    const record = activeRecord.current;
    try {
      const value = await file.text();
      if (isActive(record)) {
        if (byteLength(value) > MAX_BYTES) setActionError('代码超过 64 KiB，请缩短后再导入。');
        else loadOwnCode(value);
      }
    } catch { if (isActive(record)) setActionError('无法读取这份代码文件。'); }
  };
  const selectSample = event => {
    setSample(event.target.value);
  };
  const selectConsole = tab => {
    if (consoleOpen && consoleTab === tab) setConsoleOpen(false);
    else { setConsoleTab(tab); setConsoleOpen(true); }
  };
  const copyOutput = async () => {
    try {
      await navigator.clipboard.writeText(result?.[outputTab] || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { setActionError('暂时无法复制，可以选中输出后按 Ctrl+C。'); }
  };
  const exit = () => { saveRecord(activeRecord.current); callbacks.current.onExit?.(); };
  const saveLabel = saveState.kind === 'saving' ? '保存中…' : saveState.kind === 'unsaved' ? '等待保存'
    : saveState.kind === 'error' ? (saveState.retained ? '保存失败 · 本机草稿已保留' : '草稿保存失败')
    : saveState.kind === 'closed' ? (endedContest ? '本场已结束' : '考场题目')
    : saveState.kind === 'automatic' ? '自动保存' : '草稿已保存';

  return <section className={`tb-workbench wb-pane-${pane}`} ref={sectionRef} onKeyDown={handleKeys} aria-label="代码训练工作台" data-problem-id={problemId}>
    <div className="wb-toolbar">
      <button type="button" className="wb-icon-button" onClick={exit} title="返回列表" aria-label="返回列表"><ArrowLeft size={17} /></button>
      <div className="wb-heading">
        {slot && <span className="wb-letter">{slot.letter}</span>}
        <strong title={problem?.title}>{problem?.title || (loading ? '载入题目…' : '题目')}</strong>
        {problem && <span className="wb-limits">{elapsedText(problem.limits?.timeMs)} · {problem.limits?.memoryMb || '—'} MB</span>}
      </div>
      <div className="wb-pane-buttons" role="group" aria-label="工作台布局">
        <button type="button" className="wb-icon-button" aria-pressed={pane === 'statement'} onClick={() => focusPane('statement')} title="只看题面 · Alt+1" aria-label="只看题面"><PanelLeft size={16} /></button>
        <button type="button" className="wb-icon-button" aria-pressed={pane === 'both'} onClick={() => setPane('both')} title="题面与代码 · Alt+0" aria-label="题面与代码"><PanelsTopLeft size={16} /></button>
        <button type="button" className="wb-icon-button" aria-pressed={pane === 'code'} onClick={() => focusPane('code')} title="只看代码 · Alt+2" aria-label="只看代码"><Code2 size={16} /></button>
      </div>
      {!runningContest && <button type="button" className="wb-button" disabled={unavailable || openingOfficial} onClick={() => openOfficial()} title="带入当前代码，提交到原站 · Ctrl+Shift+Enter">{openingOfficial ? <LoaderCircle size={14} className="wb-spinner" /> : <ExternalLink size={14} />}官方提交</button>}
      {onSolution && !runningContest && !problem?.locked && <button type="button" className="wb-button wb-solution-button" disabled={!problem} onClick={() => callbacks.current.onSolution?.(problemId)}><BookOpen size={14} />题解</button>}
      {onNext && <button type="button" className="wb-button wb-next-button" onClick={() => { saveRecord(activeRecord.current); callbacks.current.onNext?.(); }}>下一题<ArrowRight size={14} /></button>}
    </div>

    {sidePracticeLocked && !endedContest && <div className="wb-notice">这题正在模拟赛中，请进入考场运行与提交。</div>}
    {officialSession && !runningContest && <div className="wb-official-status" aria-label="原站提交状态"><div role="status"><strong>{OFFICIAL_STATES[officialSession.status] || '原站面板'}</strong><span>{officialSession.message}</span>{officialSession.submissionId && <span>提交 #{officialSession.submissionId}</span>}{officialSession.verdict && <b>官方 {officialSession.verdict}</b>}</div><div className="wb-official-actions">
      {['needs_login', 'needs_verification', 'ready', 'error'].includes(officialSession.status) && <button type="button" className="wb-button" disabled={unavailable || openingOfficial} onClick={() => openOfficial()}>重试官方提交</button>}
      {!['submitted', 'judging', 'loading'].includes(officialSession.status) && <button type="button" className="wb-button" disabled={unavailable || openingOfficial} onClick={() => openOfficial('official/open')}>原站面板 / 登录</button>}
      {officialSession.status !== 'closed' && <button type="button" className="wb-button" disabled={openingOfficial} onClick={closeOfficial}>返回训练</button>}
      {officialSession.status === 'closed' && <button type="button" className="wb-icon-button" aria-label="收起原站状态" onClick={() => setOfficialSession(null)}><ChevronUp size={14} /></button>}
    </div>{officialPollError && <p className="wb-poll-error" role="alert">{officialPollError}</p>}</div>}
    {actionError && <div className="wb-error-strip" role="alert"><span>{actionError}</span><button type="button" onClick={() => setActionError('')}>知道了</button></div>}

    <div className="wb-body">
      <div className="wb-statement-pane">
        <div className="wb-pane-header"><span><BookOpen size={14} />题面</span><div className="wb-statement-actions"><div className="wb-language-toggle" role="group" aria-label="题面语言"><button type="button" aria-pressed={language === 'original'} onClick={() => setLanguage('original')}>原文</button><button type="button" aria-pressed={language === 'zh'} disabled={loading || !problem?.markdown || translationBusy} onClick={translateStatement}>{translationBusy ? '翻译中…' : '中文'}</button></div>{problem?.url && !runningContest && <a href={problem.url} target="_blank" rel="noreferrer" title="在浏览器打开原题">原题<ExternalLink size={12} /></a>}</div></div>
        {translationBusy && <p className="wb-translation-note" role="status"><LoaderCircle size={12} className="wb-spinner" />正在翻译公开题面，原文仍可阅读。</p>}
        {translationError && <div className="wb-translation-note wb-translation-error" role="alert"><span>{translationError}</span><button type="button" onClick={translateStatement}>重试</button></div>}
        {language === 'zh' && translation && <p className="wb-translation-note">机器翻译 · {translation.provider}{translation.cached ? ' · 已缓存' : ''}{translation.notice ? ` · ${translation.notice}` : ''}</p>}
        <article className="wb-statement" ref={statementRef} tabIndex={0} aria-label="题面内容">
          {loading ? <div className="wb-empty"><LoaderCircle className="wb-spinner" size={22} /><span>正在载入题面</span></div>
            : loadError ? <div className="wb-empty"><span>{loadError}</span><button type="button" className="wb-button" onClick={() => setLoadAttempt(value => value + 1)}><RotateCcw size={14} />重新载入</button></div>
            : problem?.markdown ? <StatementMarkdown markdown={language === 'zh' && translation ? translation.markdown : problem.markdown} samples={problem.samples} title={problem.title} />
            : <div className="wb-empty"><BookOpen size={24} /><strong>本地尚未缓存原题面</strong><span>打开原题后，可以在右侧编写并提交代码。</span>{problem?.url && <a className="wb-button" href={problem.url} target="_blank" rel="noreferrer">打开原题<ExternalLink size={14} /></a>}</div>}
        </article>
      </div>

      <div className="wb-code-pane">
        <div className="wb-pane-header wb-editor-header">
          <span><Code2 size={14} />C++17</span>
          <span className={`wb-save-state wb-save-${saveState.kind}`} title={saveState.message || '草稿自动保存；Ctrl+S 立即保存'} aria-live="polite">{saveState.kind === 'saving' ? <LoaderCircle size={11} className="wb-spinner" /> : saveState.kind === 'saved' ? <Check size={11} /> : null}{saveLabel}</span>
          <div className="wb-editor-actions">
            {restoreAvailable && <button type="button" className="wb-icon-button" disabled={unavailable} aria-label="撤销载入代码" title="撤销载入代码" onClick={() => {
              const previous = undoReplace.current;
              undoReplace.current = null;
              setRestoreAvailable(false);
              if (typeof previous === 'string') updateCode(previous);
            }}><RotateCcw size={14} /></button>}
            <button type="button" className="wb-icon-button" disabled={unavailable} title="导入自己的 C++ 代码" aria-label="导入代码" onClick={() => fileRef.current?.click()}><FileCode2 size={14} /></button>
            <button type="button" className="wb-icon-button" disabled={unavailable} title="保存草稿 · Ctrl+S" aria-label="保存草稿" onClick={manualSave}><Save size={14} /></button>
            <input className="wb-file-input" type="file" accept=".cpp,.cc,.cxx,.txt" ref={fileRef} onChange={importCode} tabIndex={-1} />
          </div>
        </div>
        <div className="wb-editor">
          <CodeEditor ref={editorRef} value={code} docKey={contextKey} onChange={updateCode} onCursorChange={setCursor} onCommand={editorCommand} onLeave={() => consoleButtonRef.current?.focus()} readOnly={unavailable} disabled={loading || !problem} ariaLabel="C++ 代码" />
        </div>
        <div className="wb-editor-status"><span>Ln {cursor.line}, Col {cursor.column}</span><span title="Tab 缩进，Shift+Tab 取消缩进，Ctrl+Tab 离开编辑器">Tab 缩进 · Ctrl+Tab 离开</span></div>
        <div className="wb-run-toolbar">
          <select value={sample} onChange={selectSample} aria-label="运行输入" disabled={loading || !problem}>
            {samples.length > 0 && <option value="samples">全部样例（{samples.length}）</option>}
            <option value="custom">自定义输入</option>
          </select>
          <span className={`wb-scope wb-scope-${problem?.judge?.scope || 'samples'}`} title={problem?.judge?.scope === 'local' ? `本地验证用例 ${problem.judge.cases || 0} 个` : '仅使用公开样例，通过样例不会计入已 AC'}>{problem?.judge?.label || (problem?.judge?.scope === 'local' ? '本地验证' : '样例评测')}</span>
          <div className="wb-run-actions">
            <button type="button" className="wb-button" disabled={unavailable || busy} onClick={() => execute('run')} title={sample === 'samples' ? '编译并对比全部官方样例 · Ctrl+R' : '编译并运行自定义输入 · Ctrl+R'}><Play size={14} />运行</button>
            <button type="button" className="wb-button wb-primary" disabled={unavailable || busy} onClick={() => execute('submit')} title="提交到本地评测 · Ctrl+Enter">{busy ? <LoaderCircle size={14} className="wb-spinner" /> : <Send size={14} />}提交</button>
          </div>
        </div>
        <div className="wb-console-tabs" role="group" aria-label="输入与评测记录">
          <button type="button" ref={consoleButtonRef} aria-pressed={consoleOpen && consoleTab === 'input'} onClick={() => selectConsole('input')}><Terminal size={13} />输入与样例</button>
          <button type="button" aria-pressed={consoleOpen && consoleTab === 'result'} onClick={() => selectConsole('result')}><Play size={12} />运行结果{pending && <span className="wb-pending-dot" />}</button>
          <button type="button" aria-pressed={consoleOpen && consoleTab === 'history'} onClick={() => selectConsole('history')}><History size={13} />记录<span className="wb-count">{submissions.filter(row => row.mode === 'submit').length}</span></button>
          <button type="button" className="wb-console-toggle" onClick={() => setConsoleOpen(value => !value)} aria-label={consoleOpen ? '收起控制台' : '展开控制台'} aria-expanded={consoleOpen}>{consoleOpen ? <ChevronDown size={15} /> : <ChevronUp size={15} />}</button>
        </div>
        {consoleOpen && <div className={`wb-console wb-console-${consoleTab}`}>
          {consoleTab === 'input' ? sample === 'samples' ? <div className="wb-sample-list">{samples.map((item, index) => <details key={index} open={index === 0}><summary>{item.name || `样例 ${index + 1}`}</summary><div className="wb-case-outputs"><div><span>样例输入</span><pre tabIndex={0}>{item.input || '（空输入）'}</pre></div><div><span>预期输出</span><pre tabIndex={0}>{item.output || '（空输出）'}</pre></div></div></details>)}<p className="wb-result-message">运行会对比全部样例；通过样例不会计入已 AC。</p></div> : <div className="wb-input-grid">
            <label><span>标准输入</span><textarea value={input} onChange={event => { setInput(event.target.value); setSample('custom'); }} aria-label="标准输入" spellCheck={false} placeholder="输入测试数据；Ctrl+R 编译运行" /></label>
          </div> : consoleTab === 'history' ? <div className="wb-history">
            {submissions.length ? submissions.map(row => <div className={`wb-history-row${row.id === resultId ? ' wb-history-selected' : ''}`} key={row.id}>
              <button type="button" className="wb-history-main" onClick={() => { setResultId(row.id); setConsoleTab('result'); setOutputTab(row.stderr && !row.output ? 'stderr' : 'output'); }}>
                <span className="wb-history-kind">{row.mode === 'run' ? '运行' : '提交'}</span><Verdict submission={row} /><time dateTime={row.submittedAt}>{dateText(row.submittedAt)}</time>
              </button>
              <button type="button" className="wb-history-load" disabled={unavailable || !row.code} onClick={() => loadOwnCode(row.code)} title="将这次自己的代码载入编辑器">载入代码</button>
            </div>) : <div className="wb-empty"><History size={21} /><span>运行或提交后，记录会保存在这里。</span></div>}
          </div> : <div className="wb-result">
            {creating && !pending ? <div className="wb-empty"><LoaderCircle size={20} className="wb-spinner" /><span>正在开始评测</span></div> : result ? <>
              <div className="wb-result-summary" aria-live="polite"><Verdict submission={result} />
                {result.timeMs != null && <span>{elapsedText(result.timeMs)}</span>}
                {result.memoryKb != null && <span>{(result.memoryKb / 1024).toFixed(1)} MB</span>}
                {result.total > 0 && <span>{result.passed || 0}/{result.total} 用例</span>}
              </div>
              {result.message && <p className="wb-result-message">{result.message}</p>}
              {result.mode === 'submit' && result.verdict === 'SAMPLE_PASS' && <p className="wb-sample-note">仅通过公开样例，暂不计入已 AC。</p>}
              {pollError && <p className="wb-poll-error" role="status">{pollError} · 正在重试</p>}
              {result.caseResults?.length > 0 && <CaseResults cases={result.caseResults} />}
              {((!result.caseResults?.length && result.output) || result.stderr) && <>
                <div className="wb-output-tabs">
                  <button type="button" aria-pressed={outputTab === 'output'} onClick={() => { setOutputTab('output'); setCopied(false); }}>标准输出</button>
                  <button type="button" aria-pressed={outputTab === 'stderr'} onClick={() => { setOutputTab('stderr'); setCopied(false); }}>诊断信息{result.stderr && <span className="wb-pending-dot" />}</button>
                  <button type="button" className="wb-copy" onClick={copyOutput} aria-label={copied ? '已复制' : '复制输出'} title={copied ? '已复制' : '复制输出'}>{copied ? <Check size={12} /> : <Copy size={12} />}</button>
                </div>
                <pre className="wb-output" tabIndex={0}>{result[outputTab] || '（无输出）'}</pre>
              </>}
            </> : <div className="wb-empty"><Terminal size={21} /><span>Ctrl+R 运行输入 · Ctrl+Enter 提交</span></div>}
          </div>}
        </div>}
      </div>
    </div>
  </section>;
}
