// Luogu Columba routes and RecordStatus, verified from /_lfe/config?version=0.
function installLuoguReceipts(ctx, report) {
  if (ctx.platform !== '洛谷' || !['www.luogu.com.cn', 'luogu.com.cn'].includes(location.hostname)) return null;
  const pageData = () => { try { return JSON.parse(document.querySelector('#lentille-context')?.textContent || 'null'); } catch { return null; } };
  const owner = () => pageData()?.user?.uid || window._feInjection?.currentUser?.uid;
  const numericId = value => /^\d+$/.test(String(value ?? '')) && BigInt(value) > 0n ? String(value) : null;
  const problem = () => new URL(ctx.originalUrl).pathname.split('/')[2];
  const previous = window.__tbLuogu;
  if (previous?.sessionId === ctx.sessionId) {
    if (!previous.pending && ctx.attempted && numericId(ctx.submissionId)) previous.pending = { id: String(ctx.submissionId), owner: numericId(owner()) };
    return previous;
  }
  const state = window.__tbLuogu = { sessionId: ctx.sessionId, armed: false, pending: null, receipt: null, polling: false };
  if (ctx.attempted && numericId(ctx.submissionId)) state.pending = { id: String(ctx.submissionId), owner: numericId(owner()) };
  const notify = value => {
    state.receipt = value;
    if (report) report(value);
    else chrome.webview.postMessage(JSON.stringify({ tbOfficial: true, sessionId: ctx.sessionId, ...value }));
  };
  const parseUrl = value => { try { return new URL(value, location.href); } catch { return null; } };
  const fields = body => {
    if (typeof body === 'string') { try { return JSON.parse(body); } catch { return Object.fromEntries(new URLSearchParams(body)); } }
    try { return Object.fromEntries(body.entries()); } catch { return {}; }
  };
  const requestInfo = (url, method, body) => {
    const target = parseUrl(url), params = fields(body);
    if (!state.armed || method.toUpperCase() !== 'POST' || target?.origin !== location.origin || target.pathname !== '/fe/api/problem/submit/' + problem()) return null;
    if (location.pathname !== new URL(ctx.originalUrl).pathname || String(params.code || '').replace(/\r\n/g, '\n').trim() !== ctx.code.replace(/\r\n/g, '\n').trim()) return null;
    if (!numericId(owner()) || target.searchParams.has('contestId')) return null;
    return { owner: numericId(owner()) };
  };
  const observeSubmit = (request, value) => {
    if (!request) return;
    const remoteId = numericId(typeof value === 'object' ? value?.rid ?? value?.data?.rid ?? value?.data : value);
    if (value?.errorType || !remoteId) {
      if (value?.errorType) {
        const verification = /Captcha|验证|验证码/i.test(value.errorType + ' ' + (value.errorMessage || ''));
        notify({ status: verification ? 'needs_verification' : 'error', attempted: false,
          message: verification ? '洛谷要求验证，请打开原站完成验证后再提交。' : '洛谷未受理代码：' + String(value.errorMessage || '请检查原站提交要求。').slice(0,160) });
      }
      return;
    }
    state.pending = { id: remoteId, owner: request.owner };
    notify({ status: 'judging', submissionId: remoteId, acceptedAt: new Date().toISOString(), message: '洛谷已接收本次提交 #' + remoteId + '，正在评测。' });
  };
  const inspectRecord = payload => {
    const record = payload?.data?.record || payload?.currentData?.record || payload?.record;
    if (!state.pending || numericId(record?.id) !== state.pending.id || record.problem?.pid !== problem() || numericId(record.user?.uid) !== state.pending.owner) return;
    const verdict = { 2: 'CE', 3: 'OLE', 4: 'MLE', 5: 'TLE', 6: 'WA', 7: 'RE', 12: 'AC', 14: 'WA' }[record.status];
    if (verdict) notify({ status: 'finished', submissionId: state.pending.id, verdict,
      message: '洛谷确认本次提交 #' + state.pending.id + '：' + (record.status === 14 ? '未通过全部用例' : verdict) });
    else if (![0, 1].includes(record.status)) notify({ status: 'error', submissionId: state.pending.id, message: '洛谷返回评测状态 ' + record.status + '，请在原站核对本次记录。' });
  };
  const originalFetch = window.fetch;
  state.poll = async () => {
    if (!state.pending || state.polling || state.receipt?.status === 'finished' || typeof originalFetch !== 'function') return;
    state.polling = true;
    try {
      const response = await originalFetch.call(window, '/record/' + state.pending.id, { credentials: 'same-origin', cache: 'no-store', headers: { 'x-lentille-request': 'content-only' }, signal: AbortSignal.timeout(15000) });
      if (response.ok && parseUrl(response.url || '/record/' + state.pending.id)?.origin === location.origin) inspectRecord(await response.json());
    } catch {} finally { state.polling = false; }
  };
  if (typeof originalFetch === 'function') window.fetch = function(resource, options) {
    const url = typeof resource === 'string' || resource instanceof URL ? String(resource) : resource.url;
    const method = options?.method || resource?.method || 'GET';
    const info = options?.body != null ? Promise.resolve(requestInfo(url, method, options.body)) :
      typeof resource?.clone === 'function' && method.toUpperCase() === 'POST' ? resource.clone().text().then(body => requestInfo(url, method, body)).catch(() => null) : Promise.resolve(null);
    const answer = originalFetch.apply(this, arguments);
    answer.then(response => {
      if (response.ok && parseUrl(response.url || url)?.origin === location.origin) {
        // Clone immediately, before the site's own .json() consumes the body.
        const copy = response.clone();
        info.then(request => { if (request) copy.json().then(value => observeSubmit(request, value)).catch(() => {}); }).catch(() => {});
      }
    }).catch(() => {});
    return answer;
  };
  if (window.XMLHttpRequest) {
    const proto = window.XMLHttpRequest.prototype, open = proto.open, send = proto.send;
    proto.open = function(method, url) { this.__tbLuoguRequest = { method, url }; return open.apply(this, arguments); };
    proto.send = function(body) {
      const meta = this.__tbLuoguRequest, request = meta && requestInfo(meta.url, meta.method, body);
      if (request) this.addEventListener('load', () => {
        if (this.status < 200 || this.status >= 300 || parseUrl(this.responseURL || meta.url)?.origin !== location.origin) return;
        try { observeSubmit(request, this.responseType === 'json' ? this.response : JSON.parse(this.responseText)); } catch {}
      }, { once: true });
      return send.apply(this, arguments);
    };
  }
  return state;
}
