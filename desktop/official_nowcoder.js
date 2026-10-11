// Observe the original site's requests without replacing submit or judge behavior.
// Protocol: Nowcoder public terminal bundle 2.0.114 (2026-10-10).
function installNowcoderReceipts(ctx) {
  if (ctx.platform !== '牛客') return null;
  if (window.__tbNowcoder?.sessionId === ctx.sessionId) return window.__tbNowcoder;
  const state = { sessionId: ctx.sessionId, armed: false, pending: null, receipt: null, early: [] };
  window.__tbNowcoder = state;
  const notify = value => {
    state.receipt = value;
    chrome.webview.postMessage(JSON.stringify({ tbOfficial: true, sessionId: ctx.sessionId, ...value }));
  };
  const textCode = value => String(value || '').replace(/\r\n/g, '\n').trim();
  const fields = body => {
    if (!body) return {};
    if (typeof body === 'string') {
      try { return JSON.parse(body); } catch { return Object.fromEntries(new URLSearchParams(body)); }
    }
    try { return Object.fromEntries(body.entries()); } catch { return {}; }
  };
  const parseUrl = value => { try { return new URL(value, location.href); } catch { return null; } };
  const allowed = url => url && url.origin === location.origin && location.hostname === 'ac.nowcoder.com';
  const submitPaths = new Set(['/submit_cd', '/api/service/judge/submit']);
  const statusPaths = new Set(['/status', '/api/service/judge/submit-status']);
  const id = value => /^\d+$/.test(String(value ?? '')) && BigInt(value) > 0n ? String(value) : null;
  const requestInfo = (url, method, body) => {
    const target = parseUrl(url), params = fields(body);
    if (!allowed(target)) return null;
    if (statusPaths.has(target.pathname)) return { kind: 'status', target, params: { ...Object.fromEntries(target.searchParams), ...params } };
    if (!state.armed || method.toUpperCase() !== 'POST' || !submitPaths.has(target.pathname)) return null;
    const original = parseUrl(ctx.originalUrl), info = window.pageInfo;
    if (!original || location.pathname !== original.pathname || !info || String(info.contestId) !== original.pathname.split('/')[3]) return null;
    if (String(params.questionId) !== String(info.questionId) || textCode(params.content) !== textCode(ctx.code)) return null;
    if (target.pathname === '/api/service/judge/submit' && String(params.submitType) !== '1') return null;
    if (params.selfType != null || params.selfInputData != null || params.input != null || params.isSelfTest) return null;
    const owner = id(window.globalInfo?.ownerId);
    if (params.userId != null && (!owner || String(params.userId) !== owner)) return null;
    return { kind: 'submit', target, params, owner };
  };
  // Evaluate a status payload against the confirmed pending submission.
  const evaluateStatus = (pending, params, data) => {
    if (!pending || id(params.submissionId ?? params.id) !== pending.submissionId || !data || typeof data !== 'object') return null;
    if (params.submitType != null && String(params.submitType) !== '1') return null;
    if (data.submissionId != null && id(data.submissionId) !== pending.submissionId || data.id != null && id(data.id) !== pending.submissionId) return null;
    for (const key of ['userId', 'appId', 'tagId']) {
      if (pending[key] != null && String(params[key]) !== String(pending[key])) return null;
      if (pending[key] != null && data[key] != null && String(data[key]) !== String(pending[key])) return null;
    }
    if (pending.owner && window.globalInfo?.ownerId != null && String(window.globalInfo.ownerId) !== pending.owner) return null;
    if (data.error || !Number.isInteger(data.status)) return null;
    if (data.status >= 0 && data.status <= 2) return null;
    const descriptions = { '编译错误': 'CE', '答案错误': 'WA', '运行超时': 'TLE', '超时': 'TLE', '内存超限': 'MLE', '运行错误': 'RE', '输出超限': 'OLE' };
    const failure = descriptions[String(data.desc || '').trim()] || normal(data.desc);
    return data.status === 5 ? 'AC' : failure && failure !== 'AC' && failure !== 'JUDGING' ? failure : null;
  };
  const observe = (request, value) => {
    if (!request || !value || typeof value !== 'object' || value.code !== 0 || value.error) return;
    const data = value.data;
    if (request.kind === 'submit') {
      const submissionId = id(typeof data === 'object' ? data?.submissionId ?? data?.id : data);
      if (!submissionId) return;
      state.pending = { submissionId, owner: request.owner, userId: request.params.userId, appId: request.params.appId, tagId: request.params.tagId };
      state.attempted = true;
      // 受理时刻随 judging 消息一起发出：宿主据此持久化 pending，并用它（而非
      // 收到回执的时间）记 submitted_at。不额外多发消息，保持既有消息条数契约。
      notify({ status: 'judging', submissionId, acceptedAt: new Date().toISOString(), message: '牛客已接收本次提交 #' + submissionId + '，正在评测。' });
      // Replay any status payload that arrived before we knew the submission ID.
      const early = state.early; state.early = [];
      for (const item of early) {
        if (id(item.params.submissionId ?? item.params.id) !== submissionId) continue;
        const verdict = evaluateStatus(state.pending, item.params, item.data);
        if (verdict) { notify({ status: 'finished', submissionId, verdict, message: '牛客确认本次提交 #' + submissionId + '：' + verdict }); break; }
      }
      return;
    }
    // Status response. If the pending submission is not known yet, buffer it so a
    // late-arriving submit response can still promote a real terminal verdict
    // instead of the client hanging in "judging" forever.
    if (!state.pending) {
      if (id(request.params.submissionId ?? request.params.id)) {
        state.early.push({ params: request.params, data });
        if (state.early.length > 10) state.early.shift();
      }
      return;
    }
    const verdict = evaluateStatus(state.pending, request.params, data);
    if (verdict) notify({ status: 'finished', submissionId: state.pending.submissionId, verdict, message: '牛客确认本次提交 #' + state.pending.submissionId + '：' + verdict });
  };
  if (typeof window.fetch === 'function') {
    const originalFetch = window.fetch;
    window.fetch = function(resource, options) {
      const url = typeof resource === 'string' || resource instanceof URL ? String(resource) : resource.url;
      const method = options?.method || resource?.method || 'GET';
      const info = options?.body != null ? Promise.resolve(requestInfo(url, method, options.body)) :
        typeof resource?.clone === 'function' && method.toUpperCase() === 'POST' ? resource.clone().text().then(body => requestInfo(url, method, body)).catch(() => null) : Promise.resolve(requestInfo(url, method));
      const response = originalFetch.apply(this, arguments);
      response.then(result => {
        if (result.ok && allowed(parseUrl(result.url || url))) {
          const copy = result.clone();
          info.then(request => { if (request) copy.json().then(value => observe(request, value)).catch(() => {}); });
        }
      }).catch(() => {});
      return response;
    };
  }
  if (window.XMLHttpRequest) {
    const proto = window.XMLHttpRequest.prototype, open = proto.open, send = proto.send;
    proto.open = function(method, url) { this.__tbRequest = { method, url }; return open.apply(this, arguments); };
    proto.send = function(body) {
      const meta = this.__tbRequest, request = meta && requestInfo(meta.url, meta.method, body);
      if (request) this.addEventListener('load', () => {
        if (this.status < 200 || this.status >= 300 || !allowed(parseUrl(this.responseURL || meta.url))) return;
        try { observe(request, this.responseType === 'json' ? this.response : JSON.parse(this.responseText)); } catch {}
      }, { once: true });
      return send.apply(this, arguments);
    };
  }
  return state;
}
