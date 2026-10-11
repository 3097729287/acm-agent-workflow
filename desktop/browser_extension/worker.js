// Capabilities stay in the extension's session storage, never in an OJ page.
const hosts = new Set(['codeforces.com', 'www.codeforces.com', 'atcoder.jp', 'ac.nowcoder.com', 'www.nowcoder.com', 'nowcoder.com', 'www.luogu.com.cn', 'luogu.com.cn', 'login.luogu.com.cn']);
const queues = new Map();
const connections = new Map();
let queueBusy = false;
async function backgroundRequest(base, path, body, key = '') {
  const response = await fetch(base + '/api/browser/' + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TB-Browser': key, 'X-TB-Browser-Client': chrome.runtime.id },
    body: JSON.stringify(body), signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) { connections.delete(base); throw new Error('TB 后台连接不可用'); }
  return response.json();
}
async function pollQueues() {
  if (queueBusy) return;
  queueBusy = true;
  try {
    const settings = await chrome.storage.local.get(['bases', 'clientId']);
    const clientId = settings.clientId || crypto.randomUUID();
    if (!settings.clientId) await chrome.storage.local.set({ clientId });
    const bases = settings.bases || ['http://127.0.0.1:18765'];
    for (const base of bases) {
      try {
        const local = new URL(base);
        if (local.protocol !== 'http:' || local.hostname !== '127.0.0.1' || local.origin !== base) continue;
        if (!connections.has(base)) connections.set(base, (await backgroundRequest(base, 'register', { clientId })).key);
        const answer = await backgroundRequest(base, 'queue', { clientId }, connections.get(base));
        for (const item of answer.jobs || []) {
          const saved = (await chrome.storage.session.get('jobs')).jobs || {};
          if (Object.values(saved).some(j => j.sessionId === item.sessionId && j.base === base)) continue;
          // Never create/activate a browser window. Reuse an existing window in
          // the background solely as the authenticated origin for site requests.
          const windows = await chrome.windows.getAll({ windowTypes: ['normal'] });
          if (!windows.length) continue;
          const job = { ...item, base, owned: true };
          const claim = await exchange(job, { claim: true });
          if (['closed', 'finished', 'error'].includes(claim.status)) continue;
          const target = new URL(claim.url);
          if (target.protocol !== 'https:' || !hosts.has(target.hostname)) continue;
          const tab = await chrome.tabs.create({ windowId: (windows.find(w => w.focused) || windows[0]).id, url: 'about:blank', active: false });
          job.tabId = tab.id;
          saved[tab.id] = job;
          await chrome.storage.session.set({ jobs: saved });
          await chrome.tabs.update(tab.id, { url: target.href });
        }
      } catch { /* No browser window or missing TB: wait for the next heartbeat. */ }
    }
  } finally { queueBusy = false; }
}
async function exchange(job, body) {
  const response = await fetch(job.base + '/api/browser/exchange', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TB-Browser': job.key, 'X-TB-Browser-Client': chrome.runtime.id },
    body: JSON.stringify({ sessionId: job.sessionId, ...body }), signal: AbortSignal.timeout(10000),
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'TB 连接失败');
  return value;
}
async function handle(message, sender) {
  if (sender.id !== chrome.runtime.id || sender.frameId !== 0 || !sender.tab?.id) return {};
  const page = new URL(sender.url);
  if (message.type === 'pair') {
    if (page.protocol !== 'http:' || page.hostname !== '127.0.0.1' || page.pathname !== '/browser-connect.html') return {};
    const params = new URLSearchParams(page.hash.slice(1));
    if (params.get('session') !== message.sessionId || params.get('key') !== message.key || !/^official-[a-f0-9]{32}$/.test(message.sessionId) || !/^[A-Za-z0-9_-]{40,64}$/.test(message.key)) return {};
    const job = { base: page.origin, sessionId: message.sessionId, key: message.key, tabId: sender.tab.id };
    const settings = await chrome.storage.local.get('bases');
    await chrome.storage.local.set({ bases: [...new Set([page.origin, ...(settings.bases || [])])].slice(0, 4) });
    const claim = await exchange(job, { claim: true });
    if (['closed', 'finished', 'error'].includes(claim.status)) return { error: '本次连接已结束，请回 TB 重新提交。' };
    const target = new URL(claim.url);
    if (target.protocol !== 'https:' || !hosts.has(target.hostname)) throw new Error('原站地址无效');
    // A reconnect reuses its own submission tab instead of creating a second submitter.
    const saved = (await chrome.storage.session.get('jobs')).jobs || {};
    const old = Object.values(saved).find(j => j.sessionId === job.sessionId && j.base === job.base);
    if (old && old.tabId !== job.tabId) {
      try { await chrome.tabs.get(old.tabId); job.tabId = old.tabId; } catch { delete saved[old.tabId]; }
    }
    saved[job.tabId] = job;
    await chrome.storage.session.set({ jobs: saved });
    await chrome.tabs.update(job.tabId, { url: target.href, active: true });
    if (job.tabId !== sender.tab.id) await chrome.tabs.remove(sender.tab.id);
    return { connected: true };
  }
  if (page.protocol !== 'https:' || !hosts.has(page.hostname)) return {};
  const jobs = (await chrome.storage.session.get('jobs')).jobs || {}, job = jobs[sender.tab.id];
  if (!job) return {};
  if (message.type === 'event' && message.value?.sessionId !== job.sessionId) return {};
  if (!['tick', 'event'].includes(message.type)) return {};
  const answer = await exchange(job, { pageUrl: page.href, ...(message.type === 'event' ? { event: message.value } : {}) });
  if (answer.stop) {
    const latest = (await chrome.storage.session.get('jobs')).jobs || {};
    delete latest[sender.tab.id]; await chrome.storage.session.set({ jobs: latest });
    if (job.owned && answer.status === 'finished') await chrome.tabs.remove(sender.tab.id).catch(() => {});
  }
  return answer;
}
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  // Serialize commands and receipts for each tab, including async storage writes.
  const key = sender.tab?.id;
  const next = (queues.get(key) || Promise.resolve()).catch(() => {}).then(() => handle(message, sender));
  queues.set(key, next);
  next.then(respond, () => respond({ error: '与 TB 的连接中断，请回到 TB 查看状态。' })).finally(() => { if (queues.get(key) === next) queues.delete(key); });
  return true;
});
chrome.alarms.create('tb-browser-heartbeat', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(async alarm => {
  if (alarm.name !== 'tb-browser-heartbeat') return;
  await pollQueues();
  const jobs = (await chrome.storage.session.get('jobs')).jobs || {};
  for (const job of Object.values(jobs)) {
    try { await chrome.tabs.sendMessage(job.tabId, { type: 'wake' }); } catch { /* Desktop detects a lost tab with a bounded timeout. */ }
  }
});
chrome.runtime.onStartup.addListener(pollQueues);
chrome.runtime.onInstalled.addListener(pollQueues);
// Requests keep an active desktop session responsive; the alarm revives an idle
// service worker. No cookies, account passwords or CSRF tokens leave the browser.
setInterval(pollQueues, 1000);
pollQueues();
