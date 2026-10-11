fetch('/api/browser/setup').then(r => r.json()).then(value => {
  if (value.extensionPath) document.querySelector('#folder').textContent = value.extensionPath;
}).catch(() => {});
document.querySelector('#retry').addEventListener('click', () => location.reload());
document.querySelector('#copy').addEventListener('click', async event => {
  await navigator.clipboard.writeText(document.querySelector('#folder').textContent);
  event.target.textContent = '已复制';
});
