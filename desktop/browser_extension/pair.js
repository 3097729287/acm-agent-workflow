if (location.pathname === '/browser-connect.html') {
  const params = new URLSearchParams(location.hash.slice(1));
  chrome.runtime.sendMessage({ type: 'pair', sessionId: params.get('session'), key: params.get('key') }).then(answer => {
    const status = document.querySelector('#connection-status');
    if (status) status.textContent = answer?.connected ? '已连接，正在打开原站。' : answer?.error || '连接已失效，请回到 TB 重试。';
  }).catch(() => {});
}
