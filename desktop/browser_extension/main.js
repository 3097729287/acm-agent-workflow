(() => {
  const platform = ({ 'codeforces.com': 'Codeforces', 'www.codeforces.com': 'Codeforces', 'atcoder.jp': 'AtCoder', 'ac.nowcoder.com': '牛客', 'www.luogu.com.cn': '洛谷', 'luogu.com.cn': '洛谷' })[location.hostname];
  const context = { platform, originalUrl: location.href, sessionId: 'unbound', code: '', attempted: false };
  let channel = '', submitted = '';
  const acknowledgments = new Map();
  const report = value => {
    if (!channel) return;
    for (const key of ['attempted', 'baseline', 'baselineKnown', 'baselineOwner', 'submissionId']) if (key in value) context[key] = value[key];
    if (value.status === 'submitted' && value.attempted) {
      return new Promise((resolve, reject) => {
        const requestId = crypto.randomUUID();
        const timer = setTimeout(() => { acknowledgments.delete(requestId); reject(new Error('TB 未确认连接，尚未点击原站提交按钮。')); }, 10000);
        acknowledgments.set(requestId, ok => { clearTimeout(timer); acknowledgments.delete(requestId); ok ? resolve() : reject(new Error('TB 连接已失效，尚未点击原站提交按钮。')); });
        window.postMessage({ tbBrowserResult: channel, value, requestId }, location.origin);
      });
    }
    window.postMessage({ tbBrowserResult: channel, value }, location.origin);
  };
  // Observe before the site can cache fetch/XHR. Context is filled later, without
  // replacing the observer or losing closures retained by the site's editor.
  tbOfficialPage(context, 'observe', report);
  window.addEventListener('message', event => {
    const packet = event.data;
    if (event.source === window && event.origin === location.origin && channel && packet?.tbBrowserAck === channel) {
      acknowledgments.get(packet.requestId)?.(packet.ok === true);
      return;
    }
    if (event.source !== window || event.origin !== location.origin || !packet?.tbBrowserCommand || !packet.context || packet.context.platform !== platform) return;
    if (channel && channel !== packet.tbBrowserCommand) return;
    channel = packet.tbBrowserCommand;
    Object.assign(context, packet.context);
    for (const state of [window.__tbNowcoder, window.__tbLuogu]) if (state) state.sessionId = context.sessionId;
    if (packet.action === 'submit') {
      const key = context.sessionId + ':' + packet.command;
      if (submitted === key) return;
      submitted = key;
    }
    try {
      const result = tbOfficialPage(context, packet.action, report);
      if (result?.status && packet.action !== 'submit') report({ tbOfficial: true, sessionId: context.sessionId, ...result });
    } catch {
      report({ sessionId: context.sessionId, status: 'error', message: '原站页面尚未就绪，请检查浏览器中的提交页面。' });
    }
  });
})();
