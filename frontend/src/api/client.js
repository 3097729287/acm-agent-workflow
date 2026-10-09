// HTTP contract shared by the browser build and the desktop webview.
export async function request(path, body, token) {
  const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
  const response = await fetch(`${base}/${path}`, body === undefined
    ? { cache: 'no-store' }
    : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TB-Token': token }, body: JSON.stringify(body) });
  const text = await response.text();
  let result;
  try { result = JSON.parse(text); }
  catch { throw new Error('TB 服务没有返回有效数据，请检查服务连接'); }
  if (!response.ok) throw new Error(result.error || '操作未完成，请重试');
  return result;
}
