(() => {
  let busy = false, stopped = false;
  const channel = crypto.randomUUID();
  const run = answer => {
    if (answer?.stop) { stopped = true; return; }
    if (answer?.context) window.postMessage({ tbBrowserCommand: channel, ...answer }, location.origin);
  };
  async function tick() {
    if (busy || stopped || document.readyState === 'loading') return;
    busy = true;
    try { run(await chrome.runtime.sendMessage({ type: 'tick' })); } catch {} finally { busy = false; }
  }
  window.addEventListener('message', event => {
    if (event.source !== window || event.origin !== location.origin || event.data?.tbBrowserResult !== channel) return;
    const requestId = event.data.requestId;
    chrome.runtime.sendMessage({ type: 'event', value: event.data.value }).then(answer => {
      if (requestId) window.postMessage({ tbBrowserAck: channel, requestId, ok: answer?.ack === true }, location.origin);
      run(answer);
    }).catch(() => {
      if (requestId) window.postMessage({ tbBrowserAck: channel, requestId, ok: false }, location.origin);
    });
  });
  chrome.runtime.onMessage.addListener(message => { if (message.type === 'wake') tick(); });
  document.addEventListener('DOMContentLoaded', tick, { once: true });
  setInterval(tick, 2000);
})();
